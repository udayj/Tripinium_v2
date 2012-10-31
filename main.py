from google.appengine.ext.webapp.util import run_wsgi_app
import cgi
import os
from google.appengine.ext import db
from google.appengine.api import memcache
import sys
import spell_check
import logging
import codecs
from random import choice
import urllib
import datetime
import json

import webapp2
import jinja2
from google.appengine.api import users
from google.appengine.api import mail
from db_classes import *
from db_initialization import *
from utility import *


#Feature list for MVP
#pending
#about page
#design
#error message if location not found - done
#static google maps
#sanity checking, normalisation while getting location from search box
#form for entering place information
#machine learning module that decides canonical place based on user input
#auto complete for location names
#code refactoring
#unit tests
#browser tests
#facebook integration (main page like, results page like and share)
#twitter (main page tweet)
#google +1 integration for main page
#performance enhancement - caching using memcache, google servers


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

error_suggestions=['Rome','Paris','Lyon','Barcelona','Munich']



class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        user=get_user()
        self.render('front.html',current_user=user,login_url=users.create_login_url('/'),logout_url=users.create_logout_url('/'))
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class InsertPage(webapp2.RequestHandler):
    def get(self):
        self.render('insert.html')
    def post(self):
        place=self.request.get('p')
        item_name=self.request.get('name')
        item_description=self.request.get('description')
        if not place or place is None or item_name is None or place is '' or item_name is '':
            #if place is none, then we cant insert data
            self.render('insert.html',message='Place or item name is null')
        place=normalize(place)
        place_info=get_place_from_db(place)
        if place_info is None:
            place_info=Place(name=place)
            place_info.put()
        item=Item(place=place_info,item_name=item_name,item_description=item_description)
        item.put()
        self.render('tipmodify.html',tips=place_info.items,place=place)
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class InsertLocalPage(webapp2.RequestHandler):
    def get(self):
        self.render('insertlocal.html')
    def post(self):
        place=self.request.get('p')
        local_name=self.request.get('name')
        local_email=self.request.get('email')
        local_address=self.request.get('address')
        if not place or place is None or local_name is None or place is '' or local_name is '':
            self.render('insertlocal.html',message='Place or local contact name is null')
        place_info=get_place_from_db(place)
        if place_info is None:
            place_info=Place(name=place)
            place_info.put()
        local_contact=LocalContact(place=place_info,name=local_name,email=local_email,address=local_address)
        local_contact.put()
        self.render('insertlocal.html',message='Successfully inserted record')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

cache={}
place_list_created=False
place_list=[]
country_capital={}
no_data_place_list=[]
def spell_checker(word):
    return spell_check.correct(word)
def in_place_list(word):
    global place_list_created
    if place_list_created:
        if word in place_list or word in no_data_place_list:
            return True
        else:
            return False
    #create in-memory places list to check future queries
    f=codecs.open('resources/places','r','utf-8')
    fc=codecs.open('resources/country_capitals','r','utf-8')
    fnc=codecs.open('resources/no_data_cities','r','utf-8')
    while True:
        place=f.readline()

        if not place:
            break
        else:
            place_list.append(normalize(place[:-1]))
    f.close()
    place_list_created=True
    while True:
        place=fc.readline()

        if not place:
            break
        else:
            country,capital=place.split('\t')
            country_capital[country.strip().lower()]=capital[:-1].strip().lower()
            #logging.error(country+capital[:-1])
    fc.close()
    while True:
        place=fnc.readline()

        if not place:
            break
        else:
            no_data_place_list.append(normalize(place[:-1]))
            #logging.error(country+capital[:-1])
    if word in place_list:
        return True


def is_country(query):
    return query in country_capital


def getPlaceFromQuery(query,is_spell_correct=True):
    query=normalize(query)
    
    if in_place_list(query):
        return query
    #return spell correction required, return spell corrected word
    if is_country(query):
        return country_capital[query]
    if is_spell_correct is True:
        probable_word=spell_checker(query)
        if probable_word is not None:
            return probable_word
    else:
        return query
    return query


def get_milestone(user,place):
    place_milestone='Submit your first tip for this place to join the Infantry!'
    social_milestone='Tweet to beocme a Humming-Bird!'
    if not user.points:
        place_milestone='Submit your first tip for this place to join the Infantry!'
    else:
        place_points_dict=eval(user.points)
        place_milestone=calc_next_place_milestone(place_points_dict,place)
    if not user.social_points:
        social_milestone='Tweet from this page to become a Humming-Bird!'
    else:
        social_points_dict=eval(user.social_points)
        if 'tweet' not in social_points_dict:
            social_milestone=get_next_social_milestone(0)
        else:
            social_milestone=get_next_social_milestone(social_points_dict['tweet'])
    logging.info(place_milestone)
    logging.info(social_milestone)
    return choice([place_milestone,social_milestone])


#This class should be thread-safe as only read operation are being performed to prepare data
class ResultPage(webapp2.RequestHandler):
	
    def get(self):
       	self.response.headers['Content-Type'] = 'text/html'
        query=self.request.get('q')
        if query is None or query=='':
            query=self.request.get('location')
        spell_correct=self.request.get('spellcorrect')
        #logging.error(spell_correct)
        is_spell_correct=True
        #only do spell correction if spellcorrect query parameter is present
        if  spell_correct:
            is_spell_correct=False
        #if 'q' query parameter is none, render error.html
        user=get_user()

        if query is None or query=='':
            self.render('error.html',place='',suggestion=choice(error_suggestions),current_user=user,login_url=users.create_login_url('/'),logout_url=users.create_logout_url('/'))
            return
        #query=query.lower()
        
        place=getPlaceFromQuery(query,is_spell_correct)
        #if place is same as normalized query then assume no spell correction has taken place
        if place == normalize(query):
            is_spell_corrected=False
        elif is_country(normalize(query)):
            is_spell_corrected=False
        else:
            is_spell_corrected=True
        if place is None:
            
            self.render('error.html',place=place,suggestion=choice(error_suggestions),current_user=user,login_url=users.create_login_url('/'),logout_url=users.create_logout_url('/'))
            return
        place_info=memcache.get(place)
        recommended_places=None
        #logging.error(place_info.recommendations)
        gov=None
        if place_info is not None:
            logging.info('Retreived from memcache:'+place)
            if place_info.recommendations is not None:
                recommended_places=place_info.recommendations.split('|')
            leader_message,leader_class=self.get_gov(place_info,place)
            milestone=''
            if not user:
                milestone='Submit your first tip to join the Infantry!'
            else:
                milestone=get_milestone(user,place)
            visited=False
            count=place_info.visited_count or 1
            if user and place in user.visited:
                visited=True
                count-=1
            self.render('place.html',place_info=place_info,place=place,is_spell_corrected=is_spell_corrected,orig_query=query,recommendations=recommended_places,user=user,
                        login_url=users.create_login_url('/search?location='+place),milestone=milestone,
                        logout_url=users.create_logout_url('/search?q='+place),leader_message=leader_message,leader_class=leader_class,gov=gov,
                        visited=visited,visited_count=count)

        else:
            place_info=get_place_from_db(place)
            if not place_info:
                logging.info('No place for this query:'+query)
                logging.info('Canonical place from query:'+place)
                self.render('error.html',place=place,suggestion=choice(error_suggestions),current_user=user,login_url=users.create_login_url('/'),logout_url=users.create_logout_url('/'))
            else:
                #store result in memcache
                memcache.set(place,place_info)
                if place_info.recommendations is not None:
                    recommended_places=place_info.recommendations.split('|')
                leader_message,leader_class=self.get_gov(place_info,place)
                milestone=''
                if not user:
                    milestone='Submit your first tip to join the Infantry!'
                else:
                    milestone=get_milestone(user,place)
                    logging.info(milestone)
                visited=False
                count=place_info.visited_count or 1
                if user and place in user.visited:
                    visited=True
                    count-=1

                self.render('place.html',place_info=place_info,place=place,is_spell_corrected=is_spell_corrected,orig_query=query,recommendations=recommended_places,user=user,
                            login_url=users.create_login_url('/search?location='+place),milestone=milestone,gov=gov,
                            logout_url=users.create_logout_url('/search?q='+place),leader_message=leader_message,leader_class=leader_class,
                            visited=visited,visited_count=count)
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    def get_gov(self,place_info,place):
        if place_info.gov!=None:
            gov=get_user_by_name(place_info.gov)
            leader_message='Governor of '+place.title()+': '+gov.nickname
            leader_class='badge badge-governor'
            return (leader_message,leader_class)
        else:
            leader_message='This place does not yet have a governor! Submit 3 tips to become the governor'
            leader_class='alert alert-error'
            return (leader_message,leader_class)

class HowPage(webapp2.RequestHandler):
    def get(self):
        user=get_user()
        self.render('how.html',current_user=user,login_url=users.create_login_url('/how.html'),logout_url=users.create_logout_url('/how.html'))
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
class FeedbackPage(webapp2.RequestHandler):
    def get(self):
        user=get_user()
        self.render('feedback.html',current_user=user,login_url=users.create_login_url('/feedback.html'),logout_url=users.create_logout_url('/feedback.html'))
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
class AnalyticsPage(webapp2.RequestHandler):
    def get(self):
        self.render('no_analytics.html')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

def calc_next_place_milestone(points_dict,place):
    def plural(num):
        if num==1:
            return ''
        else:
            return 's'

    milestone_rules={0:'Submit your first tip for this place to be a part of the Infantry',
                    1:'Submit another tip for this place to join the Cavalry'}
    if place not in points_dict:
        return milestone_rules[0]
    count=points_dict[place]
    if count in milestone_rules:
        return milestone_rules[count]
    if count>=2:
        gov_milestone=get_gov_milestone(place,count)
        more_tips=gov_milestone-count
        if more_tips>0:
            
            return 'Submit '+str(more_tips)+' more tip'+plural(more_tips)+' to become the Governor of this place'
        else:
            return None
    return None
    

def calc_next_cross_place_milestone(points_dict):
    def filter_func(x):
        if x>0:
            return True
        else:
            return False
    count=len([value for value in points_dict.values() if filter_func(value)])
    milestone_rules={0:'Submit your first tip for this place to join the Infantry',
                    1:'Great going so far! Submit a tip for a different place to become an Ambassador',
                    2:'Submit a tip for some place else to become an esteemed Envoy',
                    3:'You need tips for two more places to become a Diplomat',
                    4:'You are almost there! Submit a tip for some other place to become a true Diplomat'}
    if count in milestone_rules:
        return milestone_rules[count]
    else:
        return None

def get_gov_milestone(place,count):
    place_info=get_place_info(place)
    if not place_info.gov_points:
        return 3
    current_gov_points=place_info.gov_points
    return current_gov_points

def get_place_info(place):
    place_info=memcache.get(place)
    if not place_info:
        place_info=get_place_from_db(place)
        if not place_info:
            return None
        else:
            return place_info
    else:
        return place_info

class SocialActionPage(webapp2.RequestHandler):
    def post(self):
        action=self.request.get('action')
        place=self.request.get('place')
        place=normalize(place)
        user=get_user()
        if user==None:
            logging.info('No user logged in')
            self.response.headers['Content-Type'] = 'application/json'
            output_json=json.dumps({'badges_earned':[],'place_milestone':'Submit your first tip to join the Infantry!',
                                    'social_milestone':'','user':'n','thanks':'Thanks for letting the word out!'})
            self.response.out.write(output_json)
        else:
            points_dict=None
            if user.social_points==None:
                points_dict={action:1}
            else:
                points_dict=eval(user.social_points)
                if action in points_dict:
                    points_dict[action]+=1
                else:
                    points_dict[action]=1
            badges=''
            if action=='tweet':
                new_badge=self.calc_social_badges(points_dict[action])
                if user.social_badges==None:
                    user.social_badges=[]
                if new_badge:
                    badges=new_badge
                    user.social_badges=user.social_badges+[badges]
                logging.info(badges)
            social_milestone=get_next_social_milestone(points_dict['tweet'])
            place_points_dict={}
            if user.points!=None:
                place_points_dict=eval(user.points)
            place_milestone=calc_next_place_milestone(place_points_dict,place)
            user.social_points=repr(points_dict)
            logging.info(social_milestone)
            logging.info(place_milestone)
            user.put()
            self.response.headers['Content-Type'] = 'application/json'
            output_json=json.dumps({'badges_earned':[badges.title()],'place_milestone':choice([place_milestone,social_milestone]),
                                    'social_milestone':social_milestone,'user':'y','thanks':''})
            self.response.out.write(output_json)

            

    def calc_social_badges(self,points):
        badge_rules={1:'Humming-Bird',2:'Koel',3:'Nightingale'}
        if points in badge_rules:
            return badge_rules[points]
        else:
            return None

def get_next_social_milestone(points):
    milestone_rules={0:'Becoming a Humming-Bird by tweeting about this page',
                    1:'You sing like a humming-bird! Become a Koel by tweeting regularly.',
                    2:'Tweet your way to becoming a Nightingale!'}
    if points in milestone_rules:
        return milestone_rules[points]
    else:
        return 'You are awesome! Keep tweeting !'

def toTitle(string):
    return string.title()

class UserTipsPage(webapp2.RequestHandler):
    def post(self):
        tip=self.request.get('tip')
        place=self.request.get('place')
        place=normalize(place)
        user=get_user()
        if not user:
            self.store_tentative(None,tip,place,datetime.datetime.now())
            logging.info('User not logged in, submitted tip')
            self.response.headers['Content-Type'] = 'application/json'
            output_json=json.dumps({'badges_earned':[],'place_milestone':'Submit your first tip to join the Infantry!',
                                    'social_milestone':'','user':'n','thanks':'Thanks for submitting a tip!'})
            
            self.response.out.write(output_json)
        else:
            points_dict=None

            if not user.points:
                points_dict={place:1}
            else:
                points_dict=eval(user.points)
                if place in points_dict:
                    points_dict[place]+=1
                else:
                    points_dict[place]=1
            user.points=repr(points_dict)
            self.store_tentative(user.username,tip,place,datetime.datetime.now())
            badges=[]
            new_badges=self.calc_place_badges(points_dict[place],place,user.username)
            if new_badges !=None and new_badges not in user.badges:
                badges.append(new_badges)
            logging.info(badges)
            new_badges=self.calc_cross_place_badges(points_dict)
            if new_badges!=None and new_badges not in user.badges:
                badges.append(new_badges)
            user.badges=user.badges+badges
            logging.info(badges)


            place_milestone=calc_next_place_milestone(points_dict,place)
            cross_place_milestone=calc_next_cross_place_milestone(points_dict)
            logging.info(place_milestone)
            logging.info(cross_place_milestone)
            if user.social_points==None or user.social_points==0 :
                social_milestone=get_next_social_milestone(0)
            else:
                social_points_dict=eval(user.social_points)
                if 'tweet' in social_points_dict:
                    social_milestone=get_next_social_milestone(social_points_dict['tweet'])
                else:
                    social_milestone=get_next_social_milestone(0)
            logging.info(social_milestone)
            user.put()
            self.response.headers['Content-Type'] = 'application/json'
            badges=map(toTitle,badges)
            badges_earned=[]
            if badges !=[]:
                badges_earned=choice(badges)

            output_json=json.dumps({'badges_earned':[badges_earned],'place_milestone':choice([place_milestone,cross_place_milestone,social_milestone]),
                                    'social_milestone':social_milestone,'user':'y','thanks':''})
            self.response.out.write(output_json)
            #governor badge rollback wont work in concurrent tip submission case





    def calc_cross_place_badges(self,points_dict):
        def filter_func(x):
            if x>0:
                return True
            else:
                return False
        count=len([value for value in points_dict.values() if filter_func(value)])
        badge_rules={2:'Ambassador',3:'Envoy',5:'Diplomat'}
        if count in badge_rules:
            return badge_rules[count]
        else:
            return None

    def calc_place_badges(self,points,place,username):
        badge_rules={1:'Infantry',2:'Cavalry'}
        if points>=3:
            return self.gov_reward(points,place,username)
            

        if badge_rules[points]:
            return place+':'+badge_rules[points]

    
    def gov_reward(self,points,place,username):
        (new_gov,place_info)=self.is_new_gov(points,place)
        if new_gov==True:
            #current_gov=self.get_user(place_info.gov)
            if place_info.gov==None or place_info.gov=='':
                self.set_place_gov(place,place_info,username,points)
                return place+':Governor'
            else:
                self.set_place_gov(place,place_info,username,points)
                current_gov=self.get_user(place_info.gov)
                self.remove_place_badge_from_user(place+':Governor',current_gov)
                return place+':Governor'
        else:
            return None

    def get_user(self,username):
        if username==None:
            return None
        user=get_user_from_db(username)
        if not user:
            return -1
        else:
            return user

    def remove_place_badge_from_user(self,badge,user):
        logging.info(user)
        logging.info(badge)
        user.badges.remove(badge)
        user.put()

    def set_place_gov(self,place,place_info,username,points):
        place_info.gov=username
        place_info.gov_points=points
        place_info.put()
        memcache.set(place,place_info)


    def is_new_gov(self,points,place):
        place_info=memcache.get(place)
        if not place_info:
            place_info=get_place_from_db(place)
            if not place_info:
                logging.info('Problem with tip submission, cannot find place:'+place)
                return -1
        if place_info.gov_points==None or place_info.gov_points==0:
            return (True,place_info)
        elif place_info.gov_points>=points:
            return (False,None)
        else:
            return (True,place_info)
    def store_tentative(self,user,tip,place,date):
        tentative_tip=TentativeTip(user=user,tip=tip,place=place)
        tentative_tip.put()

    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
class SendVotes(webapp2.RequestHandler):
    def post(self):
        value={'p':1,'n':-1}
        key=self.request.get('key')
        vote_type=self.request.get('type')
        item_id=self.request.get('id')
        logging.info('Received tip vote type:'+vote_type+' for tip:'+key)
        if vote_type is None or vote_type =='':
            return
        if key is None or key is '':
            return
        item=get_item_from_db_with_key(key)
        if item is None:
            logging.error('Problem submitting votes for:'+key)
            return
        if hasattr(item,'votes') and item.votes is not None:
            item.votes=item.votes+value[vote_type]
        else:
            item.votes=value[vote_type]
        item.put()
        
        self.response.out.write('Success')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class SendCityRating(webapp2.RequestHandler):
    def post(self):
        score=self.request.get('score')
        place=self.request.get('place')
        place=normalize(place)
        logging.info(score)
        score=float(score)
        place_info=get_place_from_db(place)
        if place_info is None:
            logging.info('Problem while rating place:'+place)
            return
        if place_info.total_rating_count is None:
            place_info.total_rating_count=1
            place_info.total_rating=score
        else:
            place_info.total_rating_count=place_info.total_rating_count+1
            place_info.total_rating=place_info.total_rating+score
        logging.info('Received rating for:'+place)
        place_info.put()
        memcache.set(place,place_info)
        self.response.out.write('Success')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
class SendEmail(webapp2.RequestHandler):
  
    def post(self):
        logging.info('Sending email')
        emails=self.request.get('emails').split(';')
        name=self.request.get('name')
        place=self.request.get('place')
        timestamp=str(datetime.datetime.now().strftime('%m/%d/%y'))+'\n'
        place=normalize(place)
        place_info=memcache.get(place)
        logging.info('Sending email to:'+emails)
        logging.info('Sending email from:'+name)
        logging.info('Sending emil for place:'+place)
        if place_info is None:
            place_info=get_place_from_db(place)
            if not place_info:
                logging.error('Cannot find place for sending email:'+place)
                return
            else:
                #store result in memcache
                memcache.set(place,place_info)
        content=''
        if place_info is not None:
            count=1
            for item in place_info.items:
                content=content+str(count)+'. '+item.item_name+'<br>'
                count=count+1
            content='<b>Tips for '+place_info.name.title()+'</b><br><br>'+content
            if name is not None and name != '':
                content='<br>Requested by:'+name+'<br>'+'Date:'+timestamp+'<br>'+content
            else:
                content='Date:'+timestamp+'<br>'+content
            content=content+'<br><br>Visit <a href="http://www.tripinium.com">www.tripinium.com</a> for more tips<br>'
            for email in emails:
                sender_address='Tripinium Admin <dev@tripinium.com>'
                subject='Tips for '+place.title()+' from Tripinium.com'
                body=content
                mail.send_mail(sender_address, email, subject, '',html=body)
                logging.info('Sending email to:'+email)

        self.response.out.write('Success')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
class ShowUserTipsPage(webapp2.RequestHandler):
    def get(self):
        
        feedback_list=db.GqlQuery('select * from Feedback order by created desc')
        if feedback_list is not None:
            self.render("show_user_tips.html",output=feedback_list)
        else:
            self.render("show_user_tips.html",error='No feedback available')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)            

class UserProfile(webapp2.RequestHandler):
    def get(self):
        current_user=get_user()
        error_message=''

        user_id=self.request.get('user')
        logging.info(user_id)
        user=None
        if not user_id or user_id=='':
            error_message='No such user exists...incorrect url'
        else:
            user=SystemUser.get_by_id(int(user_id))
        logging.info(user)
        nickname=''
        use_place_badges=[]
        use_social_badges=[]
        if not user:
            error_message='No such user exists'
        else:
            nickname=user.nickname
            place_badges=map(toTitle,user.badges)
            social_badges=map(toTitle,user.social_badges)
            for badge in place_badges:
                if badge in ['Ambassador','Envoy','Governor']:
                    use_place_badges.append((badge,'badge-'+badge.lower()))
                else:
                    use_place_badges.append((badge,'badge-'+badge[badge.index(':')+1:].lower()))
            for badge in social_badges:
                use_social_badges.append((badge,'badge-'+badge.lower()))

        self.render("profile.html",error_message=error_message,user=nickname,place_badges=use_place_badges,social_badges=use_social_badges,
                    current_user=current_user,login_url=users.create_login_url('/'),logout_url=users.create_logout_url('/'))
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
class TipAdmin(webapp2.RequestHandler):
    def get(self):
        tips=db.GqlQuery('select * from TentativeTip')

        self.render('tipadmin.html',tips=tips)
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class TipModify(webapp2.RequestHandler):
    def get(self):
        place=self.request.get('place')
        if not place:
            self.render('tipmodify.html',tips=[],error_message='No place found')
            return
        place=normalize(place)
        place_info=get_place_from_db(place)
        if not place_info:
            self.render('tipmodify.html',tips=[],error_message='No place found')
        else:
            self.render('tipmodify.html',place=place.title(),tips=place_info.items,error_message=None)            
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class TipModifyAction(webapp2.RequestHandler):
    def post(self):
        tip_id=self.request.get('id')
        status=self.request.get('status')
        content=self.request.get('content')
        tip_id=int(tip_id)
        tip=Item.get_by_id(tip_id)
        self.response.headers['Content-Type'] = 'application/json'
        if not tip:
            output_json=json.dumps({'status':'failure'})
            self.response.out.write(output_json)
            return
        if status=='delete':
            result=self.delete_tip(tip)
            if result==0:
                output_json=json.dumps({'status':'success'})
                self.response.out.write(output_json)
                return
            else:
                output_json=json.dumps({'status':'failure'})
                self.response.out.write(output_json)
                return
        else:
            result=self.save_tip(tip,content)
            if result==0:
                output_json=json.dumps({'status':'success'})
                self.response.out.write(output_json)
                return
            else:
                output_json=json.dumps({'status':'failure'})
                self.response.out.write(output_json)
                return


    def delete_tip(self,tip):
        tip.delete()
        return 0
    def save_tip(self,tip,content):
        tip.item_name=content
        tip.put()
        return 0
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class Visited(webapp2.RequestHandler):
    def post(self):
        place=self.request.get('place')
        user=get_user()
        if place is None or user is None:
            return
        place=normalize(place)
        logging.info(place)
        logging.info(user)
        place_info=get_place_from_db(place)
        if place_info is None:
            return
        place_info.visited_count+=1
        user.visited.append(place)
        user.put()
        place_info.put()
        memcache.set(place,place_info)
        self.response.headers['Content-Type'] = 'application/json'
        output_json=json.dumps({'status':'success','count':str(place_info.visited_count-1)})
        self.response.out.write(output_json)

    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    


class TipReview(webapp2.RequestHandler):
    def post(self):
        tip_id=self.request.get('id')
        status=self.request.get('status')
        content=self.request.get('content')
        logging.info(content)
        logging.info(tip_id)
        logging.info(status)
        result=-1
        if status=='accept':
            result=self.perform_accept(tip_id,content)
        else:
            result=self.perform_reject(tip_id)
        self.response.headers['Content-Type'] = 'application/json'
        if result==0:   
            output_json=json.dumps({'status':'success'})
        else:
            output_json=json.dumps({'status':'failure'})
        self.response.out.write(output_json)


    def perform_accept(self,tip_id,content):
        #save in main db
        #calc_place_badges
        #for every badge if not in user badge list, remove
        #if removing gov badge, restore gov from prev gov list
        tip_id=int(tip_id)
        tip=TentativeTip.get_by_id(tip_id)
        if not tip:
            return -1
        tip.tip=content
        place=tip.place
        place_info=get_place_from_db(place)
        if not place_info:
            return -1
        item=Item(place=place_info,item_name=tip.tip,submitted_by=tip.user)
        logging.info(place_info.name)
        if tip.user!=None and place_info.gov==tip.user:
            if place_info.prev_gov:
                place_info.prev_gov=place_info.prev_gov.insert(0,tip.user)
            else:
                place_info.gov=tip.user

        item.put()
        place_info.put()
        memcache.set(place,place_info)
        tip.delete()
        return 0
    def perform_reject(self,tip_id):
        tip_id=int(tip_id)
        tip=TentativeTip.get_by_id(tip_id)
        if not tip:
            return -1
        place=tip.place
        place_info=get_place_from_db(place)
        if not place_info:
            return -1
        rejected_tip=RejectedTip(user=tip.user,place=tip.place,tip=tip.tip,date=tip.date)
        user=self.get_user(tip.user)
        if not tip.user:
            rejected_tip.put()
            tip.delete()
            return 0
        if place_info.gov==tip.user:
            place_info.gov_points=place_info.gov_points-1
        points_dict=eval(user.points)
        points_dict[place]=points_dict[place]-1
        cross_place_badges=self.get_cross_place_badges(points_dict,user)
        badges_to_remove=set(['Ambassador','Envoy','Diplomat'])
        badges_to_remove=badges_to_remove-set(cross_place_badges)
        place_badges=[place+':'+value for value in self.get_place_badges(points_dict,tip.place,place_info)]
        logging.info(place_badges)
        place_badges_to_remove=set([place+':'+value for value in set(['Infantry','Cavalry','Governor'])])
        place_badges_to_remove=place_badges_to_remove-set(place_badges)
        bad_badges=badges_to_remove.union(place_badges_to_remove)
        logging.info(bad_badges)
        logging.info(user.badges)
        user.badges=[badge for badge in user.badges if badge not in bad_badges]
        logging.info(user.badges)
        governor_badge=place+':Governor'
        if governor_badge in bad_badges and place_info.gov==tip.user:
            if place_info.prev_gov:
                place_info.gov=place_info.prev_gov[0]
            else:
                place_info.gov=None
        user.points=repr(points_dict)
        rejected_tip.put()
        place_info.put()
        memcache.set(place,place_info)
        user.put()
        tip.delete()
        return 0

    def get_place_badges(self,points_dict,place,place_info):
        rules={1:['Infantry'],2:['Infantry','Cavalry']}
        count=points_dict[place]
        if count in rules:
            return rules[count]
        total=['Infantry','Cavalry','Governor']
        if place_info.gov_points and count>place_info.gov_points:
            return total
        elif count>2:
            return rules[2]
        else:
            return []



    def get_cross_place_badges(self,points_dict,user):
        def filter_func(x):
            if x>0:
                return True
            else:
                return False
        count=len([value for value in points_dict.values() if filter_func(value)])
        rules={2:['Ambassador'],3:['Ambassador','Envoy'],4:['Ambassador','Envoy'],5:['Ambassador','Envoy','Diplomat']}
        if count in rules:
            return rules[count]
        elif count>5:
            return rules[5]
        else:
            return []


    def get_user(self,username):
        if username==None:
            return None
        user=get_user_from_db(username)
        if not user:
            return -1
        else:
            return user



    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
def get_user_by_name(username):
        if username==None:
            return None
        user=get_user_from_db(username)
        if not user:
            return -1
        else:
            return user


def func():
    print "google app engine"
app = webapp2.WSGIApplication(
                                     [('/', MainPage),
                                      ('/search',ResultPage),
                                      ('/insert12345',InsertPage),
                                      ('/insertbulk',InsertBulkPage),
                                      ('/insertbulkv2',InsertBulkPagev2),
                                      ('/insertimages',InsertImagesPage),
                                      ('/insertrecommendations',InsertRecommendationsPage),
                                      ('/insertlocal12345',InsertLocalPage),
                                      ('/how.html',HowPage),
                                      ('/no_analytics.html',AnalyticsPage),
                                      ('/user_tips',UserTipsPage),
                                      ('/send_email',SendEmail),
                                      ('/send_votes',SendVotes),
                                      ('/send_city_rating',SendCityRating),
                                      ('/show_user_tips',ShowUserTipsPage),
                                      ('/send_social_action',SocialActionPage),
                                      ('/profile',UserProfile),
                                      ('/tipadmin',TipAdmin),
                                      ('/tipmodify',TipModify),
                                      ('/tipmodifyaction',TipModifyAction),
                                      ('/send_review',TipReview),
                                      ('/visited',Visited),
                                      ('/feedback.html',FeedbackPage)],
                                     debug=False)
#Need more comments



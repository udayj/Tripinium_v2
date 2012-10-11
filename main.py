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
class SystemUser(db.Model):
    username=db.StringProperty(required=True)
    created=db.DateTimeProperty(auto_now_add=True)
    email=db.StringProperty()
    usertype=db.StringProperty()
    password=db.StringProperty()
    nickname=db.StringProperty()
    points=db.TextProperty()
    badges=db.StringListProperty()
    social_points=db.TextProperty()
    social_badges=db.StringListProperty()
class TentativeTip(db.Model):
    user=db.StringProperty()
    tip=db.TextProperty()
    place=db.StringProperty()
    date=db.DateTimeProperty(auto_now_add=True)
    status=db.StringProperty()
def get_user():
    user=users.get_current_user()
    if user is not None:
        system_user=db.GqlQuery('select * from SystemUser where username=:1 limit 1',user.email())
        system_user=system_user.get()
        if system_user:
            logging.info('Returning user')
            return system_user
        else:
            logging.info('New User')
            system_user=SystemUser(username=user.email(),email=user.email(),nickname=user.email().split('@')[0],usertype='Google')
            system_user.put()
            return system_user
    else:
        return None

class Place(db.Model):
    name = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)
    coordinates=db.GeoPtProperty()
    synonyms=db.StringProperty()
    recommendations=db.TextProperty()
    image=db.StringProperty()
    total_rating=db.FloatProperty()
    total_rating_count=db.IntegerProperty()
    gov_points=db.IntegerProperty()
    gov=db.StringProperty()
    prev_gov=db.StringProperty()
    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

class Item(db.Model):
    #items need to have a foreign reference to a place entity
    place=db.ReferenceProperty(Place,collection_name='items')
    item_name=db.TextProperty()
    item_description=db.TextProperty()
    submitted_by=db.StringProperty()
    votes=db.IntegerProperty()

class Feedback(db.Model):
    #items need to have a foreign reference to a place entity
    feedback=db.TextProperty()
    created=db.DateTimeProperty(auto_now_add=True)


def is_valid_data(data):
    if data[0] == '' or data is None or len(data[0].strip())<=1:
        return False
    return True

class InsertImagesPage(webapp2.RequestHandler):
    def get(self):
        password=self.request.get('password')
        if password !='difficultpassword':
            self.response.out.write('You are not authorized to access this page')
            return
        f=codecs.open('resources/place_images','r','utf-8')
        while True:
            data=f.readline()
            if not data:
                break
            else:
                parts=data
                place=normalize(parts)
                place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
                place_info=place_info.get()
                if place_info is None:
                    logging.error('error while calculating recommendations for'+place)
                    continue
                place_info.image='/images/'+place.replace(' ','')+'_display.jpg'
                place_info.put()
        f.close()
        self.response.out.write('Successfully written data')

class InsertBulkPage(webapp2.RequestHandler):
    def get(self):
        password=self.request.get('password')
        if password !='difficultpassword':
            self.response.out.write('You are not authorized to access this page')
            return
        f=codecs.open('resources/places_tips_v2','r','utf-8')
        while True:
            data=f.readline()
            if not data:
                break
            else:
                parts=data.split('\t')
                if len(parts)<=1:
                    continue
                #logging.error(parts[0])
                if not is_valid_data(parts[1:]):
                    continue
                place_info=Place(name=normalize(parts[0]))
                place_info.put()

                for item_data in parts[1:]:
                    if item_data == '' or item_data is None or len(item_data)<1 or len(item_data.strip())<1:
                        continue
                    item=Item(place=place_info,item_name=item_data)
                    item.put()
        f.close()
        self.response.out.write('Successfully written data')
class InsertBulkPagev2(webapp2.RequestHandler):
    def get(self):
        password=self.request.get('password')
        if password !='difficultpassword':
            self.response.out.write('You are not authorized to access this page')
            return
        f=codecs.open('resources/places_tips_v2_part2','r','utf-8')
        while True:
            data=f.readline()
            if not data:
                break
            else:
                parts=data.split('\t')
                if len(parts)<=1:
                    continue
                #logging.error(parts[0])
                if not is_valid_data(parts[1:]):
                    continue
                place_info=Place(name=normalize(parts[0]))
                place_info.put()

                for item_data in parts[1:]:
                    if item_data == '' or item_data is None or len(item_data)<1 or len(item_data.strip())<1:
                        continue
                    item=Item(place=place_info,item_name=item_data)
                    item.put()
        f.close()
        self.response.out.write('Successfully written data')
class InsertRecommendationsPage(webapp2.RequestHandler):
    def get(self):
        password=self.request.get('password')
        if password !='difficultpassword':
            self.response.out.write('You are not authorized to access this page')
            return
        f=codecs.open('resources/place_recommendations','r','utf-8')
        while True:
            data=f.readline()
            if not data:
                break
            else:
                parts=data.split('\t')
                if len(parts)<=1:
                    continue
                #logging.error(parts[0])
                place=normalize(parts[0])
                place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
                place_info=place_info.get()
                if place_info is None:
                    logging.error('error while calculating recommendations for'+place)
                    continue
                place_info.recommendations='|'.join(parts[1:])
                place_info.put()
        f.close()
        self.response.out.write('Successfully written data')

error_suggestions=['Rome','Paris','Lyon','Barcelona','Munich']

class LocalContact(db.Model):
    #local contacts need to have a foreign reference to a place entity
    place=db.ReferenceProperty(Place,collection_name='local_contacts')
    name=db.TextProperty(required=True)
    email=db.EmailProperty()
    address=db.TextProperty()

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        user=get_user()
        self.render('front.html',user=user,login_url=users.create_login_url('/'),logout_url=users.create_logout_url('/'))
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
        place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
        place_info=place_info.get()
        if place_info is None:
            place_info=Place(name=place)
            place_info.put()
        item=Item(place=place_info,item_name=item_name,item_description=item_description)
        item.put()
        self.render('insert.html',message='Successfully inserted record')
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
        place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
        place_info=place_info.get()
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
def normalize(query):
    return query.lower().strip()

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
            self.render('error.html',place='',suggestion=choice(error_suggestions),user=user,login_url=users.create_login_url('/'),logout_url=users.create_logout_url('/'))
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
            logging.info(users.create_login_url())
            self.render('error.html',place=place,suggestion=choice(error_suggestions),user=user,login_url=users.create_login_url('/'),logout_url=users.create_logout_url('/'))
            return
        place_info=memcache.get(place)
        recommended_places=None
        #logging.error(place_info.recommendations)
        if place_info is not None:
            if place_info.recommendations is not None:
                recommended_places=place_info.recommendations.split('|')
            if place_info.gov!=None:
                leader_message='Governor of '+place.title()+': '+place_info.gov
                leader_class='badge badge-governor'
            else:
                leader_message='This place does not yet have a governor! Submit 3 tips to become the governor'
                leader_class='alert alert-error'
            milestone=''
            if not user:
                milestone='Submit your first tip to join the Infantry!'
            else:
                milestone=get_milestone(user,place)
                logging.info(milestone)
            self.render('place.html',place_info=place_info,place=place,is_spell_corrected=is_spell_corrected,orig_query=query,recommendations=recommended_places,user=user,
                        login_url=users.create_login_url('/search?location='+place),milestone=milestone,
                        logout_url=users.create_logout_url('/search?q='+place),leader_message=leader_message,leader_class=leader_class)

        else:
            place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
            place_info=place_info.get()
            if not place_info:
                logging.error(query)
                logging.error(place)
                self.render('error.html',place=place,suggestion=choice(error_suggestions),user=user,login_url=users.create_login_url('/'),logout_url=users.create_logout_url('/'))
            else:
                #store result in memcache
                memcache.set(place,place_info)
                #logging.error(place_info.recommendations)
                if place_info.recommendations is not None:
                    recommended_places=place_info.recommendations.split('|')
                if place_info.gov!=None:
                    leader_message='Governor of '+place.title()+': '+place_info.gov
                    leader_class='badge badge-governor'
                else:
                    leader_message='This place does not yet have a governor! Submit 3 tips to become the governor'
                    leader_class='alert alert-error'
                milestone=''
                if not user:
                    milestone='Submit your first tip to join the Infantry!'
                else:
                    milestone=get_milestone(user,place)
                    logging.info(milestone)
                self.render('place.html',place_info=place_info,place=place,is_spell_corrected=is_spell_corrected,orig_query=query,recommendations=recommended_places,user=user,
                            login_url=users.create_login_url('/search?location='+place),milestone=milestone,
                            logout_url=users.create_logout_url('/search?q='+place),leader_message=leader_message,leader_class=leader_class)
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class HowPage(webapp2.RequestHandler):
    def get(self):
        user=get_user()
        self.render('how.html',user=user,login_url=users.create_login_url('/how.html'),logout_url=users.create_logout_url('/how.html'))
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
class FeedbackPage(webapp2.RequestHandler):
    def get(self):
        user=get_user()
        self.render('feedback.html',user=user,login_url=users.create_login_url('/feedback.html'),logout_url=users.create_logout_url('/feedback.html'))
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
        place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
        place_info=place_info.get()
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
        #feedback=self.request.get('feedback')
        #logging.info('feedback:'+feedback)
        #feedback=feedback[:300]
        #feedback='Submitted on '+str(datetime.datetime.now())+'\n'+feedback
        #db_feedback=Feedback(feedback=feedback)
        #db_feedback.put()
        #self.response.out.write('Success')
        tip=self.request.get('tip')
        place=self.request.get('place')
        place=normalize(place)
        user=get_user()
        if not user:
            self.store_tentative(None,tip,place,datetime.datetime.now())
            logging.info('User not logged in')
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
            output_json=json.dumps({'badges_earned':[choice(badges)],'place_milestone':choice([place_milestone,cross_place_milestone,social_milestone]),
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
            (new_gov,place_info)=self.is_new_gov(points,place)
            if new_gov==True:
                current_gov=self.get_user(place_info.gov)
                if current_gov==None:
                    self.set_place_gov(place,place_info,username,points)
                    return place+':Governor'
                else:
                    self.set_place_gov(place,place_info,username,points)
                    self.remove_place_badge_from_user(place+':Governor',current_gov)
                    return place+':Governor'
            else:
                return None

        if badge_rules[points]:
            return place+':'+badge_rules[points]

    def get_user(self,username):
        if username==None:
            return None
        user=db.GqlQuery('select * from SystemUser where username=:1 limit 1',username)
        user=user.get()
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
            place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
            place_info=place_info.get()
            if not place_info:
                logging.info('Problem')
                return -1
        if place_info.gov_points==None or place_info.gov_points==0:
            logging.info('New Governor')
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
        logging.info(vote_type)
        if vote_type is None or vote_type =='':
            return
        if key is None or key is '':
            return
        item=db.GqlQuery('select * from Item where key=:1',key)
        item=Item.get(key)
        if item is None:
            logging.error('Problem submitting votes for:'+key)
            return
        if hasattr(item,'votes') and item.votes is not None:
            logging.info(item.votes)
            logging.info('hasattr'+str(value[vote_type]))
            item.votes=item.votes+value[vote_type]
        else:
            logging.info(value[vote_type])
            item.votes=value[vote_type]
        item.put()
        logging.info(str(item.votes)+' vote put')
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
        place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
        place_info=place_info.get()
        logging.info(score)
        if place_info is None:
            logging.info('Problem while rating '+place)
            return
        if place_info.total_rating_count is None:
            place_info.total_rating_count=1
            place_info.total_rating=score
        else:
            place_info.total_rating_count=place_info.total_rating_count+1
            place_info.total_rating=place_info.total_rating+score
        logging.info(str(place_info.total_rating)+' '+str(place_info.total_rating_count))
        place_info.put()
        memcache.set(place,place_info)
        self.response.out.write('Success')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
class SendEmail(webapp2.RequestHandler):
    #get email-ids
    #get name
    #get place
    #get tips for place from memcache
    #get tips for place from db if not available in memcache
    #setup content for email
    #send email to email-ids retrieved from json message    
    def post(self):
        logging.info('Sending email')
        emails=self.request.get('emails').split(';')
        name=self.request.get('name')
        place=self.request.get('place')
        timestamp=str(datetime.datetime.now().strftime('%m/%d/%y'))+'\n'
        place=normalize(place)
        place_info=memcache.get(place)
        logging.info(name)
        if place_info is None:
            place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
            place_info=place_info.get()
            if not place_info:
                logging.error(place)
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
        place_badges=None
        social_badges=None
        if not user:
            error_message='No such user exists'
        else:
            nickname=user.nickname
            place_badges=map(toTitle,user.badges)
            social_badges=map(toTitle,user.social_badges)

        self.render("profile.html",error_message=error_message,user=nickname,place_badges=place_badges,social_badges=social_badges)
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

class TipReview(webapp2.RequestHandler):
    def post(self):
        tip_id=self.request.get('id')
        status=self.request.get('status')
        logging.info(tip_id)
        logging.info(status)
        if status=='accept':
            self.perform_accept(tip_id)
        else:
            self.perform_reject(tip_id)
    def perform_accept(self,tip_id):
        #save in main db
        #calc_place_badges
        #for every badge if not in user badge list, remove
        #if removing gov badge, restore gov from prev gov list
        tip_id=int(tip_id)
        tip=TentativeTip.get_by_id(tip_id)
        if not tip:
            return -1
        place=tip.place
        place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
        place_info=place_info.get()
        if not place_info:
            return -1
        item=Item(place=place_info,item_name=tip.tip,submitted_by=tip.user)
        logging.info(place_info.name)
        if place_info.gov==tip.user:
            if place_info.prev_gov:
                place_info.prev_gov=place_info.prev_gov.insert(0,tip.user)
            else:
                place_info.gov=[tip_user]
        item.put()
        place_info.put()
        memcache.set(place,place_info)
        return 0
    def perform_reject(tip_id):
        tip_id=int(tip_id)
        tip=TentativeTip.get_by_id(tip_id)
        if not tip:
            return -1
        place=tip.place
        place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
        place_info=place_info.get()
        if not place_info:
            return -1




    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)


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
                                      ('/send_review',TipReview),
                                      ('/feedback.html',FeedbackPage)],
                                     debug=False)
#Need more comments



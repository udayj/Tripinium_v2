from google.appengine.ext.webapp.util import run_wsgi_app
import cgi
import os
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import taskqueue
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
from countries import *
import flickr


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

error_suggestions=['Rome','Paris','London','Barcelona','Singapore']



class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        user=get_user(self.request.cookies)
        self.render('front.html',active='front',
            meta_description="""Tour with great confidence. Smart local tips for your next trip. 
            We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)



class AllPlacesPage(webapp2.RequestHandler):
    def get(self):
        places_db=get_all_places_from_db()
        places=[]
        for place in places_db:
            places.append(place.name)
        
        self.response.headers['Content-Type'] = 'text/html'
        places.sort()
        #logging.info(str(places))
        count=0
        place_tuple=()
        place_list=[]
        temp=()
        for place in places:
            count+=1
            if count%3==1:
                place_tuple=()
            place_tuple=place_tuple+(place,)
            if count%3==0:
                place_list.append(place_tuple)
            temp=place_tuple
        if count%3==1:
            place_list.append(temp+('',''))
            
        if count%3==2:
            place_list.append(temp+('',))
        
        #logging.info(str(place_list))    

        self.render('all_places.html',places=place_list,active="cities",
            meta_description="""Tour with great confidence. Smart local tips for your next trip. 
            We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
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
        recommendations=self.request.get('recommendations')
        if not place or place is None or item_name is None or place is '' or item_name is '':
            #if place is none, then we cant insert data
            self.render('insert.html',message='Place or item name is null')
        place=normalize(place)
        place_info=get_place_from_db(place)
        if place_info is None:
            place_info=Place(name=place,recommendations=recommendations)
            place_info.put()
        if recommendations!= None and len(recommendations)>5:
            place_info.recommendations=recommendations
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

def spell_checker(word):
    return spell_check.correct(word)



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
        user=get_user(self.request.cookies)

        if query is None or query=='':
            self.render('error.html',place='',suggestion=choice(error_suggestions),
                meta_description="""Tour with great confidence. Smart local tips for your next trip.
                 We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
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
            
            self.render('error.html',place=place,suggestion=choice(error_suggestions),
                meta_description="""Tour with great confidence. Smart local tips for your next trip. 
                We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
            return
        if type(place) is list and is_country(normalize(query)):
            places=place
            self.response.headers['Content-Type'] = 'text/html'
            places.sort()
            logging.info(str(places))
            count=0
            place_tuple=()
            place_list_country=[]
            temp=()
            for place in places:
                if place not in place_list:
                    continue
                """count+=1
                if count%3==1:
                    place_tuple=()
                place_tuple=place_tuple+(place,)
                if count%3==0:"""
                place_list_country.append((place,))
                temp=place_tuple
            
            

            """if count%3==1:
                place_list_country.append(temp+('',''))
                
            if count%3==2:
                place_list_country.append(temp+('',))"""
            logging.info(place_list_country)

            if len(place_list_country)<1:
                self.render('error.html',place=query,suggestion=choice(error_suggestions),
                meta_description="""Tour with great confidence. Smart local tips for your next trip. 
                We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
                return
            #logging.info(str(place_list))    

            self.render('all_places.html',places=place_list_country,
                meta_description="""Useful travel tips for """+query.title()+"""Things to do, when to visit, what to wear, where to eat,
                local language help, places to visit.""" ,title="""Useful travel tips for """+query.title(),
                message='Where in '+query.title()+' do you want to go?',country=True)
            return

        place_info=memcache.get(place)
        recommended_places=None
        #logging.error(place_info.recommendations)
        
        urls=None
        

        logging.info(str(urls))
        spell_message=''
        if is_spell_corrected:
            spell_message="Showing results for "+place.title()
        if place_info is not None:
            logging.info('Retreived from memcache:'+place)
            if place_info.recommendations is not None:
                recommended_places=place_info.recommendations.split('|')
            
            
            
            urls=[]
            if hasattr(place_info,'image'):
                try:
                    urls=place_info.image.split(',')
                except AttributeError:
                    pass
            classes=['label-default','label-primary','label-success','label-warning','label-danger','label-info']
            tips_classes={}
            class_counter=0
            tip_list=[]
            title='Useful travel tips and suggestions for '+place_info.name.title()+' - Tripinium'
            meta_description='Useful travel tips for '+place_info.name.title()+""". Best time to visit, where to eat, what to pack for the trip,
                            popular places to visit, things to do, local language help, currency conversion outlets, local transportation, cab services,
                            user submitted and voted tips. Visit """+place_info.name.title()+' with confidence'
            for tips in place_info.items:
                #meta_description+=tips.item_name+' '
                if tips.item_category and tips.item_category not in tip_list:
                   tip_list.append(tips.item_category)
            tip_list.sort()
            
            for tips in tip_list:
                tips_classes[tips]=classes[class_counter%6]
                class_counter+=1
            logging.info(tips_classes)
            self.render('place.html',place_info=place_info,place=place,is_spell_corrected=is_spell_corrected,orig_query=query,recommendations=recommended_places,
                        urls=urls,tips_classes=tips_classes,meta_description=meta_description,title=title,
                        spell_message=spell_message,query=query)

        else:
            place_info=get_place_from_db(place)
            if not place_info:
                logging.info('No place for this query:'+query)
                logging.info('Canonical place from query:'+place)
                self.render('error.html',place=place,suggestion=choice(error_suggestions),
                    meta_description="""Tour with great confidence. Smart local tips for your next trip. 
                    We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
            else:
                #store result in memcache
                memcache.set(place,place_info)
                if place_info.recommendations is not None:
                    recommended_places=place_info.recommendations.split('|')
                spell_message=''
                if is_spell_corrected:
                    spell_message="Showing results for "+place.title()
                urls=[]
                if hasattr(place_info,'image'):
                    try:
                        urls=place_info.image.split(',')
                    except AttributeError:
                        pass
                classes=['label-default','label-primary','label-success','label-warning','label-danger','label-info']
                tips_classes={}
                class_counter=0
                tip_list=[]
                title='Useful travel tips and suggestions for '+place_info.name.title()+' - Tripinium'
                meta_description='Useful travel tips for '+place_info.name.title()+""". Best time to visit, where to eat, what to pack for the trip,
                            popular places to visit, things to do, local language help, currency conversion outlets, local transportation, cab services,
                            user submitted and voted tips. Visit """+place_info.name.title()+' with confidence'
                for tips in place_info.items:
                    
                    if tips.item_category and tips.item_category not in tip_list:
                       tip_list.append(tips.item_category)
                tip_list.sort()
                for tips in tip_list:
                    tips_classes[tips]=classes[class_counter%6]
                    class_counter+=1
                logging.info(tips_classes)
                self.render('place.html',place_info=place_info,place=place,is_spell_corrected=is_spell_corrected,orig_query=query,recommendations=recommended_places,
                            urls=urls,tips_classes=tips_classes,
                            meta_description=meta_description,title=title,spell_message=spell_message,query=query)
                            
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    

class HowPage(webapp2.RequestHandler):
    def get(self):
        user=get_user(self.request.cookies)
        self.render('how.html',active="how",
            meta_description="""Tour with great confidence. Smart local tips for your next trip.
             We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
class FeedbackPage(webapp2.RequestHandler):
    def get(self):
        user=get_user(self.request.cookies)
        self.render('feedback.html',active="feedback",
            meta_description="""Tour with great confidence. Smart local tips for your next trip.
             We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
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



            





def toTitle(string):
    return string.title()

class UserTipsPage(webapp2.RequestHandler):
    def post(self):
        tip=self.request.get('tip')
        place=self.request.get('place')
        place=normalize(place)
        user=get_user(self.request.cookies)
        if not user:
            self.store_tentative(None,tip,place,datetime.datetime.now())
            logging.info('User not logged in, submitted tip')
            self.response.headers['Content-Type'] = 'application/json'
            output_json=json.dumps({'thanks':'Thanks for submitting a tip!'})
            
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
            


            
            user.put()
            self.response.headers['Content-Type'] = 'application/json'
            

            output_json=json.dumps({'thanks':''})
            self.response.out.write(output_json)
            #governor badge rollback wont work in concurrent tip submission case





    

    

    
    

    def get_user(self,username):
        if username==None:
            return None
        user=get_user_from_db(username)
        if not user:
            return -1
        else:
            return user

    

    


    
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
            if hasattr(place_info,'image'):
                self.render('tipmodify.html',place=place.title(),tips=place_info.items,error_message=None,images=place_info.image)            
            else:
                self.render('tipmodify.html',place=place.title(),tips=place_info.items,error_message=None,images='')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class DataRefresh(webapp2.RequestHandler):
    def get(self):
        task=self.request.get('task')
        if task=='tips':
            taskqueue.add(url='/insertbulk',method='GET')
            logging.info('insert tips - enqueued')
        elif task=='recommendations':
            taskqueue.add(url='/insertrecommendations',method='GET')
            logging.info('insert recommendations - enqueued')
        else:
            return
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class TipModifyAction(webapp2.RequestHandler):
    def post(self):
        tip_id=self.request.get('id')
        status=self.request.get('status')
        content=self.request.get('content')
        category=self.request.get('category')
        if status=='save_image':
            logging.info(tip_id)
            place=get_place_from_db(normalize(tip_id))
            logging.info(place)
            place.image=content
            place.put()
            self.response.headers['Content-Type'] = 'application/json'
            output_json=json.dumps({'status':'success'})
            self.response.out.write(output_json)
            return

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
            result=self.save_tip(tip,content,category)
            logging.info(category)
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
    def save_tip(self,tip,content,category):
        tip.item_name=content
        if len(normalize(category))!=0:
            tip.item_category=category
        tip.put()
        return 0

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
                                      ('/cities',AllPlacesPage),
                                      ('/no_analytics.html',AnalyticsPage),
                                      ('/user_tips',UserTipsPage),
                                      ('/send_email',SendEmail),
                                      ('/send_votes',SendVotes),
                                      ('/send_city_rating',SendCityRating),
                                      ('/show_user_tips',ShowUserTipsPage),
                                      
                                      
                                      ('/tipadmin',TipAdmin),
                                      ('/tipmodify',TipModify),
                                      ('/tipmodifyaction',TipModifyAction),
                                      ('/send_review',TipReview),
                                      
                                    
                                      ('/datarefresh',DataRefresh),
                                      ('/feedback',FeedbackPage)],
                                     debug=False)
#Need more comments



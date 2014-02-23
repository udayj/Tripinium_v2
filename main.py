from flask import Flask, request, render_template, Response, redirect, url_for,flash, jsonify

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




template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

app = Flask(__name__)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

error_suggestions=['Rome','Paris','London','Barcelona','Singapore']


@app.route('/')
def main_page():

    return render_template('front.html',active='front',
        meta_description="""Tour with great confidence. Smart local tips for your next trip. 
        We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')



@app.route('/cities')
def all_places_page():

    places_db=get_all_places_from_db()
    places=[]
    for place in places_db:
        places.append(place.name)
        
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
        
        

    return render_template('all_places.html',places=place_list,active="cities",
            meta_description="""Tour with great confidence. Smart local tips for your next trip. 
            We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')

@app.route('/insert12345',methods=['GET','POST'])
def insert_page():
    if request.method=='GET':
        return render_template('insert.html')
    else:
        place=request.args.get('p')
        data={}
        for name,value1 in dict(request.form).iteritems():
            data[name]=value1[0]
        item_name=data['name']
        item_description=None
        recommendations=data['recommendations']
        if not place or place is None or item_name is None or place is '' or item_name is '':
            #if place is none, then we cant insert data
            return render_template('insert.html',message='Place or item name is null')
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
        return render_template('tipmodify.html',tips=place_info.items,place=place)

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
@app.route('/search')
def result_page():	


    query=request.args.get('q')
    if query is None or query=='':
        query=request.args.get('location')
    spell_correct=request.args.get('spellcorrect')
        #logging.error(spell_correct)
    is_spell_correct=True
        #only do spell correction if spellcorrect query parameter is present
    if  spell_correct:
        is_spell_correct=False
        #if 'q' query parameter is none, render error.html
    

    if query is None or query=='':
            return render_template('error.html',place='',suggestion=choice(error_suggestions),
            meta_description="""Tour with great confidence. Smart local tips for your next trip.
             We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
        
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
            
        return render_template('error.html',place=place,suggestion=choice(error_suggestions),
            meta_description="""Tour with great confidence. Smart local tips for your next trip. 
            We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
        return
    if type(place) is list and is_country(normalize(query)):
        places=place
        
        places.sort()
        logging.info(str(places))
        count=0
        place_tuple=()
        place_list_country=[]
        temp=()
        for place in places:
            if place not in place_list:
                continue
            
            place_list_country.append((place,))
            temp=place_tuple
            
            

            
        logging.info(place_list_country)

        if len(place_list_country)<1:
            return render_template('error.html',place=query,suggestion=choice(error_suggestions),
            meta_description="""Tour with great confidence. Smart local tips for your next trip. 
            We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
            return
            #logging.info(str(place_list))    

        return render_template('all_places.html',places=place_list_country,
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
        logging.info(place_info)
        return render_template('place.html',place_info=place_info,place=place,is_spell_corrected=is_spell_corrected,orig_query=query,recommendations=recommended_places,
                    urls=urls,tips_classes=tips_classes,meta_description=meta_description,title=title,
                    spell_message=spell_message,query=query)

    else:
        place_info=get_place_from_db(place)
        if not place_info:
            logging.info('No place for this query:'+query)
            logging.info('Canonical place from query:'+place)
            return render_template('error.html',place=place,suggestion=choice(error_suggestions),
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
            return render_template('place.html',place_info=place_info,place=place,is_spell_corrected=is_spell_corrected,orig_query=query,recommendations=recommended_places,
                        urls=urls,tips_classes=tips_classes,
                        meta_description=meta_description,title=title,spell_message=spell_message,query=query)
                            

    
@app.route('/how.html')
def how_page():
    
    return render_template('how.html',active="how",
        meta_description="""Tour with great confidence. Smart local tips for your next trip.
         We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')
    
@app.route('/feedback')
def feedback_page():

    return render_template('feedback.html',active="feedback",
        meta_description="""Tour with great confidence. Smart local tips for your next trip.
        We help you organise the little details of your trip.""",title='Tripinium - Gateway to travel planning information')

@app.route('/no_analytics.html')
def analytics_page():
        
    return render_template('no_analytics.html')

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


@app.route('/user_tips',methods=['POST'])
def user_tips_page():

    def store_tentative(user,tip,place,date):
        tentative_tip=TentativeTip(user=user,tip=tip,place=place)
        tentative_tip.put()

    data={}
    for name,value1 in dict(request.form).iteritems():
        data[name]=value1[0]
    tip=data['tip']
    place=data['place']
    place=normalize(place)

    store_tentative(None,tip,place,datetime.datetime.now())
    logging.info('User not logged in, submitted tip')
    #self.response.headers['Content-Type'] = 'application/json'
    #output_json=json.dumps({'thanks':'Thanks for submitting a tip!'})
    
    return jsonify({'thanks':'Thanks for submitting a tip!'})
    

    

@app.route('/send_votes',methods=['POST'])
def send_votes():
    
    value={'p':1,'n':-1}
    data={}
    for name,value1 in dict(request.form).iteritems():
        data[name]=value1[0]
    key=data['key']
    vote_type=str(data['type'])
    item_id=data['id']
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
    
    return jsonify({'status':'Success'})
    
@app.route('/send_city_rating',methods=['POST'])
def send_city_rating():
 
    score=request.args.get('score')
    place=request.args.get('place')
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
    return jsonify({'status':'Success'})
    
@app.route('/send_email',methods=['POST'])    
def send_email():
  

    logging.info('Sending email')
    emails=request.args.get('emails').split(';')
    name=request.args.get('name')
    place=request.args.get('place')
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

    return jsonify({'status':'Success'})
    
@app.route('/show_user_tips')
def show_user_tips():

        
    feedback_list=db.GqlQuery('select * from Feedback order by created desc')
    if feedback_list is not None:
        return render_template("show_user_tips.html",output=feedback_list)
    else:
        return render_template("show_user_tips.html",error='No feedback available')

@app.route('/tipadmin')
def tip_admin():

    tips=db.GqlQuery('select * from TentativeTip')

    return render_template('tipadmin.html',tips=tips)
    
@app.route('/tipmodify')
def tip_modify():

    place=request.args.get('place')
    if not place:
        return render_template('tipmodify.html',tips=[],error_message='No place found')
    place=normalize(place)
    place_info=get_place_from_db(place)
    if not place_info:
        return render_template('tipmodify.html',tips=[],error_message='No place found')
    else:
        if hasattr(place_info,'image'):
            return render_template('tipmodify.html',place=place.title(),tips=place_info.items,error_message=None,images=place_info.image)            
        else:
            return render_template('tipmodify.html',place=place.title(),tips=place_info.items,error_message=None,images='')

@app.route('/datarefresh')
def data_refresh():

    task=request.args.get('task')
    if task=='tips':
        taskqueue.add(url='/insertbulk',method='GET')
        logging.info('insert tips - enqueued')
    elif task=='recommendations':
        taskqueue.add(url='/insertrecommendations',method='GET')
        logging.info('insert recommendations - enqueued')
    else:
        return jsonify({'status':'Success'})
    
@app.route('/tipmodifyaction',methods=['POST'])
def tip_modify_action():

    data={}
    for name,value1 in dict(request.form).iteritems():
        data[name]=value1[0]
    tip_id=data['id']
    status=data['status']
    content=data['content']
    category=data['category']
    if status=='save_image':
        logging.info(tip_id)
        place=get_place_from_db(normalize(tip_id))
        logging.info(place)
        place.image=content
        place.put()
        #self.response.headers['Content-Type'] = 'application/json'
        return jsonify({'status':'success'})


    tip_id=int(tip_id)
    tip=Item.get_by_id(tip_id)
    #self.response.headers['Content-Type'] = 'application/json'
    if not tip:
        #output_json=json.dumps({'status':'failure'})
        return jsonify({'status':'failure'})

    if status=='delete':
        result=delete_tip(tip)
        if result==0:
            return jsonify({'status':'success'})
            
        else:
            return jsonify({'status':'failure'})
    else:
        result=save_tip(tip,content,category)
        logging.info(category)
        if result==0:
            return jsonify({'status':'success'})
        else:
            return jsonify({'status':'failure'})


def delete_tip(tip):
    tip.delete()
    return 0
def save_tip(tip,content,category):
    tip.item_name=content
    if len(normalize(category))!=0:
        tip.item_category=category
    tip.put()
    return 0

    


    

@app.route('/send_review',methods=['POST'])
def tip_review():
    def perform_accept(tip_id,content):
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
    def perform_reject(tip_id):
        tip_id=int(tip_id)
        tip=TentativeTip.get_by_id(tip_id)
        if not tip:
            return -1
        place=tip.place
        place_info=get_place_from_db(place)
        if not place_info:
            return -1
        rejected_tip=RejectedTip(user=tip.user,place=tip.place,tip=tip.tip,date=tip.date)
        rejected_tip.put()
        tip.delete()
        return 0

    data={}
    for name,value1 in dict(request.form).iteritems():
        data[name]=value1[0]
    tip_id=data['id']
    status=data['status']
    content=data['content']
    logging.info(content)
    logging.info(tip_id)
    logging.info(status)
    result=-1
    if status=='accept':
        result=perform_accept(tip_id,content)
    else:
        result=perform_reject(tip_id)
    #self.response.headers['Content-Type'] = 'application/json'
    if result==0:   
        return jsonify({'status':'success'})
    else:
        return jsonify({'status':'failure'})
    


    
        

    



    


    def get_user(self,username):
        if username==None:
            return None
        user=get_user_from_db(username)
        if not user:
            return -1
        else:
            return user



    
def get_user_by_name(username):
        if username==None:
            return None
        user=get_user_from_db(username)
        if not user:
            return -1
        else:
            return user

@app.route('/insertimages')
def call_insert_images():
    return insert_images()

@app.route('/insertbulk')
def call_insert_bulk():
    return insert_bulk()

@app.route('/insertbulkv2')
def call_insert_bulk_v2():
    return insert_bulk_v2()

@app.route('/insertrecommendations')
def call_insert_recommendations():
    return insert_recommendations()

def func():
    print "google app engine"
"""app = webapp2.WSGIApplication(
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
                                     debug=False)"""
#Need more comments



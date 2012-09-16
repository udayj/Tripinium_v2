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

import webapp2
import jinja2

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
    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

class Item(db.Model):
    #items need to have a foreign reference to a place entity
    place=db.ReferenceProperty(Place,collection_name='items')
    item_name=db.TextProperty()
    item_description=db.TextProperty()
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
        self.render('front.html')
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
        if query is None or query=='':
            self.render('error.html',place='',suggestion=choice(error_suggestions))
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
            self.render('error.html',place=place,suggestion=choice(error_suggestions))
            return
        place_info=memcache.get(place)
        recommended_places=None
        #logging.error(place_info.recommendations)
        if place_info is not None:
            if place_info.recommendations is not None:
                recommended_places=place_info.recommendations.split('|')
            self.render('place.html',place_info=place_info,place=place,is_spell_corrected=is_spell_corrected,orig_query=query,recommendations=recommended_places)

        else:
            place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
            place_info=place_info.get()
            if not place_info:
                logging.error(query)
                logging.error(place)
                self.render('error.html',place=place,suggestion=choice(error_suggestions))
            else:
                #store result in memcache
                memcache.set(place,place_info)
                #logging.error(place_info.recommendations)
                if place_info.recommendations is not None:
                    recommended_places=place_info.recommendations.split('|')
                self.render('place.html',place_info=place_info,place=place,is_spell_corrected=is_spell_corrected,orig_query=query,recommendations=recommended_places)
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

class HowPage(webapp2.RequestHandler):
    def get(self):
        self.render('how.html')
    def render(self, template, **kw):
        self.write(render_str(template, **kw))
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
class FeedbackPage(webapp2.RequestHandler):
    def get(self):
        self.render('feedback.html')
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
class UserTipsPage(webapp2.RequestHandler):
    def post(self):
        feedback=self.request.get('feedback')
        logging.info('feedback:'+feedback)
        feedback=feedback[:300]
        feedback='Submitted on '+str(datetime.datetime.now())+'\n'+feedback
        db_feedback=Feedback(feedback=feedback)
        db_feedback.put()
        self.response.out.write('Success')
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
        timestamp=str(datetime.datetime.now())+'\n'
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
                content=content+str(count)+'. '+item.item_name+'\n'
                count=count+1
            content='Tips for '+place_info.name.title()+'\n'+content
            if name is not None or name != '':
                content='Requested by:'+name+'\n'+'Date:'+timestamp+'\n'+content
            else:
                content='Date:'+timestamp+'\n'+content
            content=content+'\n\nVisit www.tripinium.com for more tips\n'
            for email in emails:
                sender_address='Tripinium Admin <dev@tripinium.com>'
                subject='Tips for '+place.title()+' from Tripinium.com'
                body=content
                mail.send_mail(sender_address, email, subject, body)
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
                                      ('/feedback.html',FeedbackPage)],
                                     debug=False)
#Need more comments



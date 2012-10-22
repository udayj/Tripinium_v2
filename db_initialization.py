from google.appengine.ext.webapp.util import run_wsgi_app
import cgi
import os
from google.appengine.ext import db
from db_classes import *
import logging
import codecs
import webapp2
from utility import *

#These classes help initialize the database with seed data


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
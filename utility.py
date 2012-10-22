from db_classes import *
from google.appengine.api import users
import logging

def normalize(query):
    return query.lower().strip()

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

def is_valid_data(data):
    if data[0] == '' or data is None or len(data[0].strip())<=1:
        return False
    return True
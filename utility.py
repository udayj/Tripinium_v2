from db_classes import *
from google.appengine.api import users
import logging
import facebook
import webapp2
import urllib
import cgi
import json
import base64
import cgi
import Cookie
import email.utils
import hashlib
import hmac
import os.path
import time



FACEBOOK_APP_ID = "232003813594670"
FACEBOOK_APP_SECRET = "97bdb48673eecb4006c36d34186fe88e"

def normalize(query):
    return query.lower().strip()

def get_user(cookies=None):
    user=users.get_current_user()
    if user is not None:
        system_user=db.GqlQuery('select * from SystemUser where username=:1 limit 1',user.email())
        system_user=system_user.get()
        if system_user:
            logging.info('Returning user')
            return system_user
        else:
            logging.info('New User')
            system_user=SystemUser(username=user.email(),email=user.email(),nickname=user.email().split('@')[0],usertype='Google',
                                   key_name_=user.email())
                                    
            system_user.put()
            return system_user
    logging.info(cookies)
    cookie = parse_cookie(cookies.get('fb_user'))
    logging.info(cookie)
    if cookie:
            # Store a local instance of the user data so we don't need
            # a round-trip to Facebook on every request
        user = db.GqlQuery('select * from SystemUser where key_name_=:1 limit 1',cookie)
        user=user.get()
        if not user:
            return None
            graph = facebook.GraphAPI(cookie["access_token"])
            profile = graph.get_object("me")
            user = SystemUser(
                        key_name_=str(profile["id"]),
                        username=profile["name"],
                        nickname=profile["name"],
                        profile_url=profile["link"],
                        access_token=cookie["access_token"],
                        usertype='Facebook',
                        email=profile["email"])
            user.put()
        else:
            logging.info(user)
            return user
    else:
        return None

def is_valid_data(data):
    if data[0] == '' or data is None or len(data[0].strip())<=1:
        return False
    return True

class LoginHandler(webapp2.RequestHandler):
    def get(self):
        verification_code = self.request.get("code")
        args = dict(client_id=FACEBOOK_APP_ID,
                    redirect_uri=self.request.path_url)
        if self.request.get("code"):
            args["client_secret"] = FACEBOOK_APP_SECRET
            args["code"] = self.request.get("code")
            response = cgi.parse_qs(urllib.urlopen(
                "https://graph.facebook.com/oauth/access_token?" +
                urllib.urlencode(args)).read()+"&scope=email")
            access_token = response["access_token"][-1]

            # Download the user profile and cache a local instance of the
            # basic profile info
            profile = json.load(urllib.urlopen(
                "https://graph.facebook.com/me?" +
                urllib.urlencode(dict(access_token=access_token))))
            user = db.GqlQuery('select * from SystemUser where key_name_=:1 limit 1',str(profile["id"]))
            user=user.get()
            if not user:
                user = SystemUser(
                            key_name_=str(profile["id"]),
                            username=profile["name"],
                            nickname=profile["name"],
                            profile_url=profile["link"],
                            access_token=access_token,
                            usertype='Facebook',
                            email=profile["email"]) 
                user.put()
            set_cookie(self.response, "fb_user", str(profile["id"]),
                       expires=time.time() + 30 * 86400)
            self.redirect("/")
        else:
            self.redirect(
                "https://graph.facebook.com/oauth/authorize?scope=email&" +
                urllib.urlencode(args))


class LogoutHandler(webapp2.RequestHandler):
    def get(self):
        set_cookie(self.response, "fb_user", "", expires=time.time() - 86400)
        self.redirect("/")

def set_cookie(response, name, value, domain=None, path="/", expires=None):
    """Generates and signs a cookie for the give name/value"""
    timestamp = str(int(time.time()))
    value = base64.b64encode(value)
    signature = cookie_signature(value, timestamp)
    cookie = Cookie.BaseCookie()
    cookie[name] = "|".join([value, timestamp, signature])
    cookie[name]["path"] = path
    if domain:
        cookie[name]["domain"] = domain
    if expires:
        cookie[name]["expires"] = email.utils.formatdate(
            expires, localtime=False, usegmt=True)
    response.headers.add_header("Set-Cookie", cookie.output()[12:])


def parse_cookie(value):
    """Parses and verifies a cookie value from set_cookie"""
    if not value:
        return None
    parts = value.split("|")
    if len(parts) != 3:
        return None
    if cookie_signature(parts[0], parts[1]) != parts[2]:
        logging.warning("Invalid cookie signature %r", value)
        return None
    timestamp = int(parts[1])
    if timestamp < time.time() - 30 * 86400:
        logging.warning("Expired cookie %r", value)
        return None
    try:
        return base64.b64decode(parts[0]).strip()
    except:
        return None


def cookie_signature(*parts):
    """Generates a cookie signature.

    We use the Facebook app secret since it is different for every app (so
    people using this example don't accidentally all use the same secret).
    """
    hash = hmac.new(FACEBOOK_APP_SECRET, digestmod=hashlib.sha1)
    for part in parts:
        hash.update(part)
    return hash.hexdigest()

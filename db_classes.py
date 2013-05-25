from google.appengine.ext import db


class RejectedTip(db.Model):
    """This class encapsulates a tip that has been rejected by the moderator"""
    user=db.StringProperty()
    tip=db.TextProperty()
    place=db.StringProperty()
    date=db.DateTimeProperty(auto_now_add=True)
   

class SystemUser(db.Model):
    """This class encapsulates a user account"""
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
    visited=db.StringListProperty()
    access_token=db.StringProperty()
    profile_url=db.StringProperty()
    key_name_=db.StringProperty()

class TentativeTip(db.Model):
    """This class encapsulates a tip that has ben submitted but not yet approved"""
    user=db.StringProperty()
    tip=db.TextProperty()
    place=db.StringProperty()
    date=db.DateTimeProperty(auto_now_add=True)
    status=db.StringProperty()

class Place(db.Model):
    """ This class encapsulates a place entity, which was its connection to a list of tips (items)"""
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
    visited_count=db.IntegerProperty()
    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

class Item(db.Model):
    """This class encapsulates a tip"""
    #items need to have a foreign reference to a place entity
    place=db.ReferenceProperty(Place,collection_name='items')
    item_name=db.TextProperty()
    item_description=db.TextProperty()
    submitted_by=db.StringProperty()
    votes=db.IntegerProperty()

class Feedback(db.Model):
    #items need to have a foreign reference to a place entity
    """Feedback submitted through the feedback page is saved using this class"""
    feedback=db.TextProperty()
    created=db.DateTimeProperty(auto_now_add=True)

class LocalContact(db.Model):
    """Not being used presently but this class saves information about a local contact"""
    #local contacts need to have a foreign reference to a place entity
    place=db.ReferenceProperty(Place,collection_name='local_contacts')
    name=db.TextProperty(required=True)
    email=db.EmailProperty()
    address=db.TextProperty()

def get_place_from_db(place):
    place_info=db.GqlQuery('select * from Place where name=:1 limit 1',place)
    place_info=place_info.get()
    return place_info

def get_user_from_db(username):
    user=db.GqlQuery('select * from SystemUser where username=:1 limit 1',username)
    user=user.get()
    return user

def get_item_from_db_with_key(key):
    db.GqlQuery('select * from Item where key=:1',key)
    item=Item.get(key)
    return item

def get_all_places_from_db():
    place_info=db.GqlQuery('select * from Place')
    return place_info    
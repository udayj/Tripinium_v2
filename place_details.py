import requests
import json
import time
import codecs
import math

def get_lat_long(place):
    print place
    payload={'appid':'Rw6NZrDV34FzZ8ktM_wVHTvxiiurZF2qNtjge.gqHWkGABGWhjmPgrHCGysTiAuXf7l5XPXEuGE-','format':'json'}
    r=requests.get("http://where.yahooapis.com/v1/places.q('"+place+"');count=1",params=payload)

    try:
        content=json.loads(r.text)
        try:
            latitude=content['places']['place'][0]['centroid']['latitude']
            longitude=content['places']['place'][0]['centroid']['longitude']
            return (latitude,longitude)
        except:
            print "problem "+place
            return None
    except:
        print "problem "+place
        return None

def get_place_details():
    f=codecs.open('resources/place_list_refresh_v2_part1','r','utf-8')
    fw=codecs.open('lat_long','w','utf-8')
    while True:
        data=f.readline()
        if not data:
            break
        else:
            content=get_lat_long(data)
            if content is not None:
                latitude,longitude=content
                result=data+'\t'+str(latitude)+'\t'+str(longitude)+'\n'
                print result
                fw.write(result)
        time.sleep(1)
    fw.close()
    f.close()



def distance_on_unit_sphere(lat1, long1, lat2, long2):

    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0
        
    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
        
    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians
        
    # Compute spherical distance from spherical coordinates.
        
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = 
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
    
    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
           math.cos(phi1)*math.cos(phi2))
    arc = math.acos( cos )

    # Remember to multiply arc by the radius of the earth 
    # in your favorite set of units to get length.
    return arc

def cmp(x,y):
    if x[1]>y[1]:
        return 1
    if x[1]==y[1]:
        return 0
    if x[1]<y[1]:
        return -1
def calc_recommendations():

    f=codecs.open('lat_long','r','utf-8')
    fw=codecs.open('recommendations','w','utf-8')
    recommendations={}
    places={}
    while True:
        data=f.readline()
        if not data:
            break
        else:
            parts=data.split('\t')
            places[parts[0]]=(float(parts[1]),float(parts[2]))
    for place in places:
        dist=[]
        lat1,long1=places[place]
        for innerplace in places:
            if place==innerplace:
                continue
            lat2,long2=places[innerplace]
            arc=distance_on_unit_sphere(lat1,long1,lat2,long2)
            dist.append((innerplace,arc))
        dist.sort(cmp)
        fw.write(place+'\t'+dist[0][0]+'\t'+dist[1][0]+'\t'+dist[2][0]+'\t'+dist[3][0]+'\t'+dist[4][0]+'\n')
    fw.close()
    f.close()



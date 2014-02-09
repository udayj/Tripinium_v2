import codecs
import logging
from utility import *

place_list_created=False
place_list=[]
country_capital={}
no_data_place_list=[]

def in_place_list(word):
    logging.error(place_list_created)    
    global place_list_created
    if place_list_created:
        if word in place_list or word in no_data_place_list:
            return True
        else:
            return False
    #create in-memory places list to check future queries

    logging.error(place_list_created)
    logging.error('problem')
    f=codecs.open('resources/place_list_refresh_v2_part1','r','utf-8')
    fc=codecs.open('resources/country_capitals','r','utf-8')
    fnc=codecs.open('resources/no_data_cities','r','utf-8')
    while True:
        place=f.readline()

        if not place:
            break
        else:
            place_list.append(normalize(place[:-1]))
    f.close()
    global place_list_created
    place_list_created=True
    while True:
        place=fc.readline()

        if not place:
            break
        else:
            country,capital=place.split('\t')
            if country.strip().lower() not in country_capital:
                country_capital[country.strip().lower()]=[]
            if capital[:-1].strip().lower() not in country_capital[country.strip().lower()]:
                country_capital[country.strip().lower()].append(capital[:-1].strip().lower())
            logging.error(country+capital[:-1])
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
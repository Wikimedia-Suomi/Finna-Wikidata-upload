# Script creates wikidata item for a band.
#
# Usage:
# python3 
#
# 

import re
import sys
import pywikibot

import json
#import psycopg2
#import sqlite3

import requests

import urllib
import urllib.request
import urllib.parse


def escapesinglequote(s):
    return s.replace("'", "''")

def isDisambiguation(item):
    isdis = False
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        if (claim.getTarget().id == 'Q4167410'):
            #print("target is disambiguation page")
            isdis = True
            break
        
    return isdis

def getitembyqcode(repo, itemqcode):
    if (itemqcode == None or itemqcode == ""):
        print("no qcode for item")
        return None

    item = pywikibot.ItemPage(repo, itemqcode)
    if (item.isRedirectPage() == True):
        return None
    return item

def getlabelbylangfromitem(item, lang):

    for li in item.labels:
        label = item.labels[li]
        if (li == lang):
            print("DEBUG: found label for ", item.getID() ," in lang ", lang ,": ", label)
            return label
    return None

# note: we need "WbTime" which is not a standard datetime
def getwbdate(year, month=0, day=0):
    if (year != 0 and month != 0 and day != 0):
        #print("DEBUG: setting year, month, day")
        return pywikibot.WbTime(year, month, day)
    elif (year != 0 and month != 0):
        #print("DEBUG: setting year, month")
        return pywikibot.WbTime(year, month)
    else:
        #print("DEBUG: setting year only")
        return pywikibot.WbTime(year)

def checkproperties(repo, itemqcode):
    if (len(itemqcode) == 0):
        return False

    itemfound = pywikibot.ItemPage(repo, itemqcode)
    if (itemfound.isRedirectPage() == True):
        return False
    
    dictionary = itemfound.get()

    return True


# todo: read config for mapping
def getgenreqcode(commands):

    # mapping genre to qcode
    d_genretoqcode = dict()
    d_genretoqcode["power metal"] = "Q57143"
    d_genretoqcode["sinfoninen metalli"] = "Q486415"
    d_genretoqcode["metalcore"] = "Q183862"
    d_genretoqcode["black metal"] = "Q132438"
    
    if "genre" not in commands:
        return ""

    genre = commands["genre"]
    if genre in d_genretoqcode:
        return d_genretoqcode[genre]
    return ""

# todo: read config for mapping
def getlabelqcode(commands):

    # mapping label to qcode
    d_labeltoqcode = dict()
    d_labeltoqcode["Nuclear Blast"] = "Q158886"
    d_labeltoqcode["Napalm Records"] = "Q693194"
    d_labeltoqcode["Century Media Records"] = "Q158867"
    d_labeltoqcode["Spikefarm Records"] = "Q51794339"
    
    if "muslabel" not in commands:
        return ""

    lbl = commands["muslabel"]
    if lbl in d_labeltoqcode:
        return d_labeltoqcode[lbl]
    return ""

# todo: read config for mapping?
# don't need many so might as well hard-code?
# country of origin
def getcountryqcode(commands):

    # mapping country to qcode
    d_countryqcode = dict()
    d_countryqcode["Yhdysvallat"] = "Q30"
    d_countryqcode["Suomi"] = "Q33"
    d_countryqcode["Italia"] = "Q38"
    d_countryqcode["Chile"] = "Q298"
    

    if "country" not in commands:
        return ""

    cq = commands["country"]
    if cq in d_countryqcode:
        return d_countryqcode[cq]
    return ""

# todo: read config for mapping?
# don't need many so might as well hard-code?
# language of album
def getlanguageqcode(commands):

    # mapping language to qcode
    d_langqcode = dict()
    d_langqcode["englanti"] = "Q1860"
    d_langqcode["eng"] = "Q1860" # langcode
    d_langqcode["suomi"] = "Q1412"
    d_langqcode["fin"] = "Q1412" # langcode
    d_langqcode["ruotsi"] = "Q9027"
    d_langqcode["swe"] = "Q9027" # langcode
    d_langqcode["ranska"] = "Q150"
    d_langqcode["fra"] = "Q150" # langcode

    #espanja (Q1321)

    if "language" not in commands:
        return ""

    lq = commands["language"]
    if lq in d_langqcode:
        return d_langqcode[lq]
    return ""

def isBandItem(item):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        if (claim.getTarget().id == 'Q215380'):
            return True
        
    return False

def getArtistsFromItem(item):
    qlist = list()
    part_of = item.claims.get('P282', [])
    for claim in part_of:
        qid = claim.getTarget().id
        if (qid not in qlist):
            qlist.append(qid)
    return qlist


def add_item_link(repo, wditem, prop, qcode):
    claim = pywikibot.Claim(repo, prop)
    target = pywikibot.ItemPage(repo, qcode) 
    claim.setTarget(target)
    wditem.addClaim(claim)#, summary='Adding 1 claim')

def add_item_value(repo, wditem, prop, value):
    claim = pywikibot.Claim(repo, prop)
    claim.setTarget(value)
    wditem.addClaim(claim)#, summary='Adding 1 claim')


# todo: test this
def add_item_source(repo, p_claim, commands):
    if "source" not in commands:
        return 

    prop = 'P854'
    sourceurl = commands['source']
   
    u_claim = pywikibot.Claim(repo, prop, is_reference=True, is_qualifier=False)
    u_claim.setTarget(sourceurl)
    p_claim.addSource(u_claim)


def add_band_properties(repo, wditem, commands):
    # instance of
    if not 'P31' in wditem.claims:
        print("Adding claim: instance of band")
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, 'Q215380') # band
        claim.setTarget(target)
        wditem.addClaim(claim)#, summary='Adding 1 claim')

        
    # discogs artist
    if not 'P1953' in wditem.claims:
        if "discogs" in commands:
            discogs = commands["discogs"]
            
            print("Adding claim: discogs artist")
            add_item_value(repo, wditem, 'P1953', discogs)

    # metal archives band
    if not 'P1952' in wditem.claims:
        if "metalarchives" in commands:
            metalarc = commands["metalarchives"]
            
            print("Adding claim: metal archives band")
            add_item_value(repo, wditem, 'P1952', metalarc)

    # genre
    if not 'P136' in wditem.claims:
        genreqcode = getgenreqcode(commands)
        if (genreqcode != ""):
        
            print("Adding claim: genre")
            claim = pywikibot.Claim(repo, 'P136')
            target = pywikibot.ItemPage(repo, genreqcode) 
            claim.setTarget(target)
            wditem.addClaim(claim)#, summary='Adding 1 claim')

    # alkuperämaa: P495
    if not 'P495' in wditem.claims:
        countryqcode = getcountryqcode(commands)
        if (countryqcode != ""):
        
            print("Adding claim: country of origin")
            claim = pywikibot.Claim(repo, 'P495')
            target = pywikibot.ItemPage(repo, countryqcode) 
            claim.setTarget(target)

            # add source (if any)
            add_item_source(repo, claim, commands)
            
            wditem.addClaim(claim)#, summary='Adding 1 claim')

    # työskentelyajan alku (P2031)
    # getwbdate()..

    # muita?
    # luomisajankohta (P571), perustamisajankohta (Q3406134)
    


def add_band(commands, finnarecord = None):

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()
    
    artistlabel = commands["artist"]
    if (artistlabel == ""):
        print('WARN: cannot create, artist unknown')
        return None

    
    data = {"labels": {"en": artistlabel, "fi": artistlabel, "sv": artistlabel, "fr": artistlabel, "mul": artistlabel}}
    #"descriptions": {"en": album_desc_en, "sv": album_desc_sv, "fr": album_desc_fr}}


    print('Creating a new band item for', artistlabel)

    #create item
    newitem = pywikibot.ItemPage(repo, None)
    
    newitem.editEntity(data, summary=u'Edited item: set labels, descriptions')

    newitem.get()

    print('Adding properties...')

    add_band_properties(repo, newitem, commands)

    nid = newitem.getID()
    print('All done', nid)
    return nid



support_args = [
                "artist",
                "country",
                "genre",
                "discogs",
                "metalarchives",
                "source",
                ]

# TODO: check name to qcode mapping validity while parsing?
#
def parse_command_pars(argv):
    commands = dict()
    # something like this
    for arg in argv:
        ix = arg.find("=")
        if (ix < 0):
            continue
        key = arg[:ix]
        val = arg[ix+1:]
        if key in commands:
            print("WARN: duplicate arg:", key)
            exit()
        if key not in support_args:
            print("WARN: unsupported arg:", key)
            exit()
        if (key not in commands and key in support_args):
            val = val.replace('"', "") # remove double quotes from command line
            commands[key] = val
            
        if (key == "country"):
            if (getcountryqcode(commands) == ""):
                print("WARN: no qcode for country", commands["country"])
                exit()
        if (key == "genre"):
            if (getgenreqcode(commands) == ""):
                print("WARN: no qcode for genre", commands["genre"])
                exit()

    return commands


# main()

## main()
if __name__ == "__main__":
    
    if (len(sys.argv) < 2):
        print("no command given")
        exit()
        
    commands = parse_command_pars(sys.argv)
    print("DEBUG: commands", str(commands))

    
    confirmation = pywikibot.input_choice(
        "Do you want to continue with the edits?",
        [('Yes', 'y'), ('No', 'n')],
        default='n'
    )

    if confirmation == 'n':
        print("Operation cancelled.")
        exit()
    
    add_band(commands)
    print("all done")
        

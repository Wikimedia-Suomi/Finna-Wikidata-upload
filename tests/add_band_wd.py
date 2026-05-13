# Script creates wikidata item for a band.
#
# Usage:
# python3 
#
# 

import re
import sys
import pywikibot
from pywikibot.data import sparql
from pywikibot.data.sparql import SparqlQuery

import json
#import psycopg2
#import sqlite3

import requests

import urllib
import urllib.request
import urllib.parse

# in case query gives wikidata link instead of plain qcode
# -> parse to plain qcode
def parseqcodefromwikidatalink(text):

    ilast = text.rfind("/", 0, len(text)-1)
    if (ilast < 0):
        return text
    return text[ilast+1:]

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

def getlabelsbylangsfromitem(item, langlist):
    
    lbllist = dict()
    for li in item.labels:
        label = item.labels[li]
        if (li in langlist):
            print("DEBUG: found label for ", item.getID() ," in lang ", li ,": ", label)
            #return label
            lbllist[li] = label
    return lbllist

def isItemInstanceOf(item, qcode):

    if (qcode == None or qcode == ""):
        print("no qcode for instance")
        return False

    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        qid = claim.getTarget().id
        if (qid == qcode):
            print("ok, matching instance found")
            return True
        print("item is instance of: ", qid)
        
    print("item is not instance of:", qcode)
    return False

# note that while finna might give items in finnish, also swedish and english are possible..
# and if other sources are queried those might be in english.
# some items in wikidata might not have finnish label, but might have in "mul" or english, or vice versa..
def searchItembySparql(repo, text, instance, lang='fi'):

    print("DEBUG: searching item with label: ", text)

    endpoint = 'https://query.wikidata.org/sparql'
    entity_url = 'https://www.wikidata.org/entity/' # must be provided when endpoint is given
    
    # TODO: filter by instance of music style in query
    
    # this query might work for partial labels..
    #query = 'SELECT ?item ?itemLabel'
    #query += ' WHERE {'
    #query += ' ?item rdfs:label ?itemLabel.'
    #query += ' FILTER(CONTAINS(LCASE(?itemLabel), "' + genre + '"@' + lang +')).'
    #query += ' } limit 10'

    query = 'SELECT distinct ?item ?itemLabel ?itemDescription WHERE{'
    query += ' ?item ?label "'+ text +'"@' + lang + '.'
    query += ' ?article schema:about ?item .'
    query += ' ?article schema:inLanguage "' + lang + '" .' # note part of below
    query += ' ?article schema:isPartOf <https://' + lang + '.wikipedia.org/>.'
    query += ' SERVICE wikibase:label { bd:serviceParam wikibase:language "' + lang + '". } }'


    print("DEBUG: using endpoint: ", endpoint)

    query_object = sparql.SparqlQuery(endpoint=endpoint, entity_url=entity_url)

    print("DEBUG: executing SPARQL query: ", query)
    
    # Execute the SPARQL query and retrieve the data
    data = query_object.select(query, full_data=True)
    if data is None:
        print("SPARQL failed. query error or login BUG?")
        return None

    # if there are too many other results, might be too ambigious -> cancel?

    print("DEBUG: checking query results.. ")

    for row in data:
        print("DEBUG: row:", row)
        page_id = str(row['item'])
        
        # error: page_id is a link, not just qcode..
        # Http://www.wikidata.org/entity/Q484179
        # -> strip it
        itemqcode = parseqcodefromwikidatalink(page_id)
        
        item = getitembyqcode(repo, itemqcode)
        if (item == None):
            # invalid qcode?
            continue
        
        lbl = getlabelbylangfromitem(item, lang)
        if (lbl == None):
            # no label in this language?
            print("no label in language: ", lang)
            continue

        if (lbl != text):
            # not correct label for some reason
            print("label is not correct: ", lbl)
            continue

        # we would want to verify item is instance of correct type:
        # query may give anything at any type currently.
        # problem is that there may be many sub-types 
        # so filtering in query by instances might need a long list.
        # another issue is that data can be simply broken for some reason, so avoid using those.

        if (len(instance) > 0):
            if (isItemInstanceOf(item, instance) == True):
                print("ok, matching style")
                return itemqcode
        else:
            print("no instance qid given, using qid", itemqcode)
            return itemqcode

    print("did not find genre for:", genre)
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
    d_genretoqcode["death metal"] = "Q483251"

    if "genre" not in commands:
        return ""

    genre = commands["genre"]
    if genre in d_genretoqcode:
        return d_genretoqcode[genre]
    return ""

# todo: read config for mapping
def getmuslabelqcode(commands):

    # mapping label to qcode
    d_labeltoqcode = dict()
    d_labeltoqcode["Nuclear Blast"] = "Q158886"
    d_labeltoqcode["Nuclear Blast Records"] = "Q158886"
    d_labeltoqcode["Napalm Records"] = "Q693194"
    d_labeltoqcode["Century Media Records"] = "Q158867"
    d_labeltoqcode["Spikefarm Records"] = "Q51794339"
    d_labeltoqcode["Naturmacht Productions"] = "Q73783815"
    d_labeltoqcode["Avantgarde Music"] = "Q790187"
    d_labeltoqcode["Rockshots Records"] = "Q117885298"
    d_labeltoqcode["Warner Music Finland"] = "Q10831860"
    d_labeltoqcode["Inverse Records"] = "Q23045098"
    d_labeltoqcode["Candlelight Records"] = "Q852900"
    
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
    d_countryqcode["Espanja"] = "Q29"
    d_countryqcode["Kreikka"] = "Q41"
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
    d_langqcode["espanja"] = "Q1321"
    d_langqcode["spa"] = "Q1321" # langcode
    d_langqcode["italia"] = "Q652"
    d_langqcode["ita"] = "Q652" # langcode

    if "language" not in commands:
        return ""

    lq = commands["language"]
    if lq in d_langqcode:
        return d_langqcode[lq]
    return ""

def getQcodesFromItemProp(item, prop):
    qlist = list()
    p_claims = item.claims.get(prop, [])
    for claim in p_claims:
        qid = claim.getTarget().id
        if (qid not in qlist):
            qlist.append(qid)
    return qlist

def isBandItem(item):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:

        qid = claim.getTarget().id
        
        # band
        if (qid == 'Q215380'):
            return True
        # metal band
        if (qid == 'Q56816954'):
            return True
        # rockyhtye (Q5741069)
        if (qid == 'Q5741069'):
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
    return claim

def add_item_value(repo, wditem, prop, value):
    claim = pywikibot.Claim(repo, prop)
    claim.setTarget(value)
    wditem.addClaim(claim)#, summary='Adding 1 claim')
    return claim


# todo: other possible parameters
def add_item_source_url(repo, p_claim, commands):
    if "source" not in commands:
        return 

    prop = 'P854' # source-url
    sourceurl = commands['source']
   
    u_claim = pywikibot.Claim(repo, prop, is_reference=True, is_qualifier=False)
    u_claim.setTarget(sourceurl)
    p_claim.addSource(u_claim)

# todo: other sources to use? -> must have other related properties and qualifiers..

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
            genreclaim = add_item_link(repo, wditem, 'P136', genreqcode)

            # add source if given
            add_item_source_url(repo, genreclaim, commands, finnarecord)


    # alkuperämaa: P495
    if not 'P495' in wditem.claims:
        countryqcode = getcountryqcode(commands)
        if (countryqcode != ""):
        
            print("Adding claim: country of origin")
            countryclaim = add_item_link(repo, wditem, 'P495', countryqcode)

            # add source if given
            add_item_source_url(repo, countryclaim, commands, finnarecord)
            

    # työskentelyajan alku (P2031)
    if not 'P2031' in wditem.claims:
        if "year" in commands:
            start = commands["year"]

            # only year now
            wbdate = getwbdate(int(start))
            
            print("Adding claim: start of work")
            claim = pywikibot.Claim(repo, 'P2031')
            claim.setTarget(wbdate)

            # add source (if any)
            add_item_source_url(repo, claim, commands)
            
            wditem.addClaim(claim)#, summary='Adding 1 claim')

    # työskentelyajan loppu (P2032)
    if not 'P2032' in wditem.claims:
        if "endyear" in commands:
            end = commands["endyear"]

            # only year now
            wbdate = getwbdate(int(end))
            
            print("Adding claim: end of work")
            claim = pywikibot.Claim(repo, 'P2032')
            claim.setTarget(wbdate)

            # add source (if any)
            add_item_source_url(repo, claim, commands)
            
            wditem.addClaim(claim)#, summary='Adding 1 claim')


    # levymerkki (P264)
    if not 'P264' in wditem.claims:

        labelqcode = ""
        if "muslabelqid" in commands:
            labelqcode = commands["muslabelqid"]

        if (labelqcode == ""):
            labelqcode = getmuslabelqcode(commands)
        
        if (labelqcode != ""):
        
            print("Adding claim: record label")
            labelclaim = add_item_link(repo, wditem, 'P264', labelqcode)

            # add source if given
            add_item_source_url(repo, labelclaim, commands, finnarecord)

    # perustamispaikka (P740)
    
    # koostuu osista (P527), luettelo jäsenistä (qid)
    
    # artistin MusicBrainz-tunniste (P434)
    if not 'P434' in wditem.claims:
        if "musicbrainz" in commands:
            mbrainz = commands["musicbrainz"]
            
            print("Adding claim: musicbrainz artist")
            add_item_value(repo, wditem, 'P434', mbrainz)


def make_description(repo, commands):

    # languages to make descriptions for
    supportedLabels = "en", "fi", "mul"

    c_labels = {}
    countryqcode = ""
    if "country" in commands:
        # country given
        countryqcode = getcountryqcode(commands)
        if (countryqcode != ""):
            c_item = getitembyqcode(repo, countryqcode)
            if (c_item != None):
                c_labels = getlabelsbylangsfromitem(c_item, supportedLabels)
        

    if countryqcode == "" and "artistqid" in commands:
        # fallback, if we are updating check if item has property defined
        artistitem = getitembyqcode(repo, commands["artistqid"])
        if (artistitem != None):
            p_country = 'P495'
            q_country = getQcodesFromItemProp(artistitem, p_country)
            if (q_country != None):
                for qc in q_country:
                    c_item = getitembyqcode(repo, qc)
                    if (c_item != None):
                        c_labels = getlabelsbylangsfromitem(c_item, supportedLabels)

    # now make the labels for supported language:
    # "band from xxx" and so on
    #if (c_labels != None):
    #    for cl in c_labels:


def create_band_item(repo, artistlabel):

    data = {"labels": {"en": artistlabel, "fi": artistlabel, "sv": artistlabel, "fr": artistlabel, "mul": artistlabel}}
    #"descriptions": {"en": album_desc_en, "sv": album_desc_sv, "fr": album_desc_fr}}

    print('Creating a new band item for', artistlabel)

    #create item
    newitem = pywikibot.ItemPage(repo, None)
    
    newitem.editEntity(data, summary=u'Edited item: set labels, descriptions')

    # reload, ensure it is created
    # can we skip this and leave to later?
    newitem.get()
    return newitem


# check there is at least mul label if fr/sv/en/fi is missing:
# label could be copied but reduction in copies might be better
def check_and_add_labels(item, wtitle):

    modifiedItem = False

    #if "fi" in item.labels:
    #    label = item.labels["fi"]
    #    if (label != wtitle):
            # finnish label does not match -> wrong item?
    #        return False;
        
    # finnish label is not set -> don't modify (avoid mistakes)
    #if "fi" not in item.labels:
    #    return False;

    # start with supported languages
    copy_labels = {}
    #supportedLabels = "en", "fi", "sv", "fr", "it", "de", "es", "pt", "nl", "da", "nb", "nn", "et", "pl"
    supportedLabels = "en", "fi", "mul"
    for lang in supportedLabels:
        if lang not in item.labels:
            # example: "fi": "Virtanen"
            copy_labels[lang] = wtitle
    if (len(copy_labels) > 0):
        item.editLabels(labels=copy_labels, summary="Adding missing labels.")
        modifiedItem = True

    if (modifiedItem == True):
        item.get()
    return modifiedItem


def add_band(commands, finnarecord = None):

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()

    artistlabel = ""
    artistqcode = ""
    if "artist" in commands:
        artistlabel = commands['artist']
    if "artistqid" in commands:
        artistqcode = commands['artistqid']
    
    if (len(artistlabel) == 0 and len(artistqcode) == 0):
        print('WARN: cannot create, artist unknown and no qcode')
        return None

    artist_item = {}
    if (len(artistqcode) == 0):
        artist_item = create_band_item(repo, artistlabel)
    else:
        artist_item = getitembyqcode(repo, artistqcode)
        if (isBandItem(artist_item) == False):
            print('WARN: qid is not for artist', isBandItem)
            return None
        if (artistlabel != ""):
            check_and_add_labels(artist_item, artistlabel)

    print('Adding properties...')
    add_band_properties(repo, artist_item, commands)

    nid = artist_item.getID()
    print('All done', nid)
    return nid


support_args = [
                "artist",
                "artistqid",
                "country",
                "year",
                "genre",
                "muslabel",
                "muslabelqid",
                "discogs",
                "metalarchives",
                "musicbrainz",
                "source"
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
        

# Script creates wikidata item for last name.
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

import xml.etree.ElementTree as XEltree

# class FinnaRecord

class FinnaRecord:
    def __init__(self):
        self.finnaid = ""
        self.sourceref = None
        self.finnarecord = None
        
        self.albumtitle = None
        self.artistname = None
        self.publishername = None
        #self.releaseyear = None
        self.languagecode = None
        self.origlangcode = None

    # simple checks if received record could be usable
    def isFinnaRecordOk(self):
        if (self.finnarecord == None):
            print("WARN: failed to retrieve finna record for: ", self.finnaid)
            return False

        #print("DEBUG: full record: ", str(finnarecord))

        if (self.finnarecord['status'] != 'OK'):
            print("WARN: status not OK: ", self.finnaid ," status: ", self.finnarecord['status'])
            return False

        if (self.finnarecord['resultCount'] != 1):
            print("WARN: resultCount not 1: ", self.finnaid ," count: ", str(self.finnarecord['resultCount']))
            return False

        if "records" not in self.finnarecord:
            print("WARN: 'records' not found in finna record: ", self.finnaid)
            return False

        if (len(self.finnarecord['records']) == 0):
            print("WARN: empty array of 'records' for finna record: ", self.finnaid)
            return False

        #print("DEBUG: ", finnarecord)
        return True

    # get id given by Finna API (in case we use obsolete id in request),
    # check what server reports back
    def getFinnaIdFromRecord(self):
        records = self.finnarecord['records'][0]

        # this should not happen since it is one of the fields requested
        if "id" not in records:
            print("WARN: no id in finna record ")
            return ""

        # there is often id even if accession number is not there
        finna_id = records['id']

        print("DBEUG: found id in finna record: ", finna_id)
        return finna_id

    # get accession number / identifier string from finna
    def getFinnaAccessionIdentifier(self):
        records = self.finnarecord['records'][0]

        finna_id = ""
        if "id" in records:
            # there is often id even if accession number is not there
            finna_id = records['id']
        
        if "identifierString" not in records:
            print("WARN: no identifier in finna record, id:", finna_id)
            return ""

        finnaidentifier = records['identifierString']
        print("DBEUG: found identifier in finna record: ", str(finnaidentifier))
        return finnaidentifier

    def getTitleFromFinna(self, lang='fi'):
        records = self.finnarecord['records'][0]
        
        if "title" not in records:
            return ""
            
        f_title = records['title'] # Tääsosuma
        f_shorttitle = records['shortTitle'] # Tääsosuma
        #f_alttitle = records['alternativeTitles'] # ??
        f_titlestatement = records['titleStatement'] # Halavatun Papat
        #f_summary = records['summary'] # ??

        print("DBEUG: found title in finna record: ", f_title)
        return f_title

    # <datafield tag="338" ind1=" " ind2=" "><subfield code="a">äänilevy</subfield>
    def isalbum(self):
        records = self.finnarecord['records'][0]
        
        if "formats" not in records:
            return False

        # is there more generic "album" to check ?
        #f_type = records['formats']['value'] # 0/Sound/ or 1/Sound/CD/
        #f_typename = records['formats']['translated'] # Äänite or CD
        
        if "physicalDescriptions" not in records:
            return False

        f_pd = records['physicalDescriptions'] # 1 CD-äänilevy
        
        # TODO: need to improve this, parse the xml instead?
        # other values?
        if (f_pd == "1 CD-äänilevy"):
            return True
        return False

    def getlang(self):
        records = self.finnarecord['records'][0]
        
        if "languages" not in records and "originalLanguages" not in records:
            return ""
        
        # 'languages': ['eng'], 'originalLanguages': ['eng'],
        # 'languages': ['swe'], 'originalLanguages': [],

        if "languages" in records:
            return records['languages'] # fin
        if "originalLanguages" in records:
            return records['originalLanguages'] # fin
        return ""

    def getyear(self):
        records = self.finnarecord['records'][0]
        
        if "year" not in records:
            return ""
        
        f_year = records['year'] # 2017

        # should be a plain number..
        iyear = int(f_year)
        if (iyear < 1800 or iyear > 2100):
            # not usable as an album
            return ""
        
        # validate it is a date, decade or year?
        return f_year

    # publisher and publisher identifier
    # <subfield code="b">Ekvapoint</subfield><subfield code="a">HPCD-008</subfield>
    #def parsepublisher(self):
        #descriptive_notes = root.findall(".//inscriptionDescription/descriptiveNoteValue")
        #for note in descriptive_notes:

    # <datafield tag="110" ind1="2" ind2=" "><subfield code="a">Halavatun Papat,</subfield><subfield code="e">esittäjä.</subfield></datafield><datafield tag="245" ind1="1" ind2="0"><subfield code="a">Tääsosuma /</subfield><subfield code="c">Halavatun Papat.</subfield></datafield><datafield tag="264" ind1=" " ind2="1"><subfield code="a">[Kustannuspaikka tuntematon] :</subfield><subfield code="b">Ekvapoint Oy,</subfield><subfield code="c">[2017]</subfield></datafield><datafield tag="264" ind1=" " ind2="4"><subfield code="c">℗2017</subfield></datafield>
    #def parsealbum(self):

    def parseFullRecord_get_root(self):
        if "fullRecord" not in self.finnarecord['records'][0]:
            print("fullRecord does not exist in finna record")
            return None

        full_record_data = self.finnarecord['records'][0]["fullRecord"]
        if (len(full_record_data) == 0):
            print("empty full record")
            return None

        root = XEltree.fromstring(full_record_data)
        if (root == None):
            print("root not found")
            return None
        
        return root

    def parseFullRecord(self):

        root = self.parseFullRecord_get_root()
        
        # tags have namespace {http://www.loc.gov/MARC21/slim} so that affects all the paths as well:
        
        # {http://www.loc.gov/MARC21/slim}datafield
        # {http://www.loc.gov/MARC21/slim}subfield 
        
        print("root tag", root.tag)
        print("root attrib", root.attrib)
        
        #i = 0
        #for i < len(root.items()):
        #    print(root[i].text)

        for child in root:
            print(child.tag, child.attrib)


        #record = root.findall(".//collection")
        #record = root.iter("subfield")
        record = root.iter()
        for child in record:
            print(child.tag, child.attrib)

        # we can use datafield tag-attribute values to determine what they have,
        # and subfield code-attribute for more specifics
        #datafields = root.findall(".//datafield/subfield")
        #datafields = root.findall("./datafield/subfield")
        #datafields = root.findall(".//subfield")
        datafields = root.iter("{http://www.loc.gov/MARC21/slim}datafield")
        for df in datafields:
            # datafield attributes
            dftag = df.get("tag") # not sure what the values here are..
            dfind1 = df.get("ind1") # not sure what the values here are..
            dfind2 = df.get("ind2") # not sure what the values here are..
            
            print("tag,", dftag, "ind1", dfind1, "ind2", dfind2)

            # subfield and attributes
            #subfields = df.findall("subfield")
            subfields = df.iter("{http://www.loc.gov/MARC21/slim}subfield")
            for sf in subfields:
                sfcode = sf.get("code")
                sftext = sf.text

                print("code,", sfcode, "text", sftext)
                
                # if dftag == 110, ind1 == 2, ind2 == " " and sfcode == a -> artist name 
                # if dftag == 110, ind1 == 2, ind2 == " " and sfcode == e -> "esittäjä"

                # if dftag == 245, ind1 == 1, ind2 == 0 and sfcode == a -> album name 
                # if dftag == 245, ind1 == 1, ind2 == 0 and sfcode == c -> artist name 
                
                # if dftag == 264, ind1 == " ", ind2 == 1 and sfcode == a -> publishing place name 
                # if dftag == 264, ind1 == " ", ind2 == 1 and sfcode == b -> publisher name 
                # if dftag == 264, ind1 == " ", ind2 == 1 and sfcode == c -> year 

                # if dftag == 264, ind1 == " ", ind2 == 4 and sfcode == c -> year 

        print("parsed fields")
                
        return True

# / class FinnaRecord

# FinnaApi:

# urlencode Finna parameters
def finna_api_parameter(name, value):
   return "&" + urllib.parse.quote_plus(name) + "=" + urllib.parse.quote_plus(value)

# Get finna API record with most of the information
# Finna API documentation
# * https://api.finna.fi
# * https://www.kiwi.fi/pages/viewpage.action?pageId=53839221 

def append_finna_api_parameters(url):

    url += finna_api_parameter('field[]', 'id')
    url += finna_api_parameter('field[]', 'title')
    url += finna_api_parameter('field[]', 'subTitle')
    url += finna_api_parameter('field[]', 'alternativeTitles')
    url += finna_api_parameter('field[]', 'shortTitle')
    url += finna_api_parameter('field[]', 'titleSection')
    url += finna_api_parameter('field[]', 'titleStatement')
    url += finna_api_parameter('field[]', 'uniformTitles')
    url += finna_api_parameter('field[]', 'summary')
    url += finna_api_parameter('field[]', 'imageRights')
    url += finna_api_parameter('field[]', 'images')
    url += finna_api_parameter('field[]', 'imagesExtended')
    url += finna_api_parameter('field[]', 'onlineUrls')
    url += finna_api_parameter('field[]', 'openUrl')
    url += finna_api_parameter('field[]', 'nonPresenterAuthors')
    url += finna_api_parameter('field[]', 'onlineUrls')
    url += finna_api_parameter('field[]', 'subjects')
    url += finna_api_parameter('field[]', 'subjectsExtendet')
    url += finna_api_parameter('field[]', 'subjectPlaces')
    url += finna_api_parameter('field[]', 'subjectActors')
    url += finna_api_parameter('field[]', 'subjectDetails')
    url += finna_api_parameter('field[]', 'geoLocations')
    url += finna_api_parameter('field[]', 'buildings')
    url += finna_api_parameter('field[]', 'identifierString')
    url += finna_api_parameter('field[]', 'collections')
    url += finna_api_parameter('field[]', 'institutions')
    url += finna_api_parameter('field[]', 'classifications')
    url += finna_api_parameter('field[]', 'events')
    url += finna_api_parameter('field[]', 'languages')
    url += finna_api_parameter('field[]', 'originalLanguages')
    url += finna_api_parameter('field[]', 'year')
    url += finna_api_parameter('field[]', 'hierarchicalPlaceNames')
    url += finna_api_parameter('field[]', 'formats')
    url += finna_api_parameter('field[]', 'physicalDescriptions')
    url += finna_api_parameter('field[]', 'physicalLocations')
    url += finna_api_parameter('field[]', 'measurements')
    url += finna_api_parameter('field[]', 'recordLinks')
    url += finna_api_parameter('field[]', 'recordPage')
    url += finna_api_parameter('field[]', 'systemDetails')
    url += finna_api_parameter('field[]', 'fullRecord')
    return url

def get_finna_record(frsession, finnaid, quoteid=True):
    finnaid = finnaid.strip()
    
    if (finnaid.startswith("fmp.") == True and finnaid.find("%2F") > 0):
        quoteid = False
    # already quoted, don't mangle again
    if (finnaid.startswith("sls.") == True and finnaid.find("%25") > 0):
        quoteid = False
    if (finnaid.startswith("fng_simberg.") == True and (finnaid.find("%25") > 0 or finnaid.find("%C3") > 0)):
        quoteid = False

    if (finnaid.find("/") > 0):
        quoteid = True
    
    if (quoteid == True):
        print("DEBUG: quoting id:", finnaid)
        quotedfinnaid = urllib.parse.quote_plus(finnaid)
    else:
        quotedfinnaid = finnaid
        print("DEBUG: skipping quoting id:", finnaid)

    if (quotedfinnaid.find("Ö") > 0):
        quotedfinnaid = quotedfinnaid.replace("Ö", "%C3%96")
        #quotedfinnaid = quotedfinnaid.replace("Ö", "%25C3%2596")
        #quotedfinnaid = urllib.parse.quote_plus(quotedfinnaid)

    if (quotedfinnaid.find("å") > 0):
        quotedfinnaid = quotedfinnaid.replace("å", "%C3%A5")

    if (quotedfinnaid.find("+") > 0):
        quotedfinnaid = quotedfinnaid.replace("+", "%2B")
        
    print("DEBUG: fetching record with id:", quotedfinnaid, ", for id:", finnaid)

    url ="https://api.finna.fi/v1/record?id=" +  quotedfinnaid
    url = append_finna_api_parameters(url)

    #print("DEBUG: request url", url)

    try:
        #response = requests.get(url)
        response = frsession.get(url)
        return response.json()
    except:
        print("Finna API query failed: " + url)
        return None

# / FinnaApi


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
def getartistqcode(commands):

    # mapping name to artist qcode
    d_artisttoqcode = dict()
    d_artisttoqcode["Soulspell"] = "Q4049800"
    d_artisttoqcode["SoulSpell"] = "Q4049800"
    d_artisttoqcode["Crystal Lake"] = "Q5191254"
    d_artisttoqcode["Beyond the Black"] = "Q19520941"
    d_artisttoqcode["Havukruunu"] = "Q55220242"
    d_artisttoqcode["Corpus Christii"] = "Q11855528"
    d_artisttoqcode["Suotana"] = "Q53789374"
    d_artisttoqcode["Halavatun papat"] = "Q11861186"
    
    if "artist" not in commands:
        print("no artist in commands")
        return ""
    
    artist = commands["artist"]

    print("looking fo artist", artist)
    
    if artist in d_artisttoqcode:
        return d_artisttoqcode[artist]

    print("artist not found", d_artisttoqcode)
    return ""

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

# todo: use data from record instead from commandline
def add_album_properties(repo, wditem, commands):
    # instance of
    if not 'P31' in wditem.claims:
        print("Adding claim: instance of album")
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, 'Q482994') # music album
        claim.setTarget(target)
        wditem.addClaim(claim)#, summary='Adding 1 claim')

    # esittäjä
    if not 'P282' in wditem.claims:
        artist_qcode = getartistqcode(commands)
        if (artist_qcode != ""):
            
            print("Adding claim: artist")
            claim = pywikibot.Claim(repo, 'P175')
            target = pywikibot.ItemPage(repo, artist_qcode) 
            claim.setTarget(target)
            wditem.addClaim(claim)#, summary='Adding 1 claim')
        if "artistqid" in commands:
            print("Adding claim: artist")
            claim = pywikibot.Claim(repo, 'P175')
            target = pywikibot.ItemPage(repo, commands["artistqid"]) 
            claim.setTarget(target)
            wditem.addClaim(claim)#, summary='Adding 1 claim')
        
    # discogs master
    if not 'P1954' in wditem.claims:
        if "discogsmaster" in commands:
            discogs = commands["discogsmaster"]
            
            print("Adding claim: discogs master")
            add_item_value(repo, wditem, 'P1954', discogs)

    if not 'P2206' in wditem.claims:
        if "discogsrelease" in commands:
            discogs = commands["discogsrelease"]
            
            print("Adding claim: discogs release")
            add_item_value(repo, wditem, 'P2206', discogs)


    # metal archives release
    if not 'P2721' in wditem.claims:
        if "metalarchives" in commands:
            metalarc = commands["metalarchives"]
            
            print("Adding claim: metal archives release")
            add_item_value(repo, wditem, 'P2721', metalarc)

    # release date (date formatting?)
    if not 'P577' in wditem.claims:
        if "release" in commands:
            released = commands["release"]

            # only year now
            wbdate = getwbdate(int(released))
            
            print("Adding claim: released in")
            claim = pywikibot.Claim(repo, 'P577')
            #target = pywikibot.ItemPage(repo, released) 
            claim.setTarget(wbdate)
            wditem.addClaim(claim)#, summary='Adding 1 claim')

    # genre
    if not 'P136' in wditem.claims:
        genreqcode = getgenreqcode(commands)
        if (genreqcode != ""):
        
            print("Adding claim: genre")
            claim = pywikibot.Claim(repo, 'P136')
            target = pywikibot.ItemPage(repo, genreqcode) 
            claim.setTarget(target)
            wditem.addClaim(claim)#, summary='Adding 1 claim')


def check_artist(repo, commands, lang='fi'):
    
    if "artistqid" in commands and "artist" not in commands:
        qcode = commands["artistqid"]
        item = getitembyqcode(repo, qcode)
        artistlabel = getlabelbylangfromitem(item, lang)
        if (artistlabel == None):
            print("WARN: no label with lang", lang)
            return ""
        if (artistlabel != ""):
            print("ok, artist name found", artistlabel, " with lang", lang)
        if "artist" not in commands and artistlabel != "":
            commands["artist"] = artistlabel
        return artistlabel

    if "artist" in commands and "artistqid" not in commands:
        artistqcode = getartistqcode(commands)
        if (artistqcode == ""):
            print("WARN: no qcode for artist", commands["artist"])
            return ""
            
        artistitem = getitembyqcode(repo, artistqcode)
        artistlabel = getlabelbylangfromitem(artistitem, lang)
        if (artistlabel == None):
            print("WARN: no label with lang", lang)
            return ""
        if (artistlabel == commands["artist"]):
            print("ok, artist name and label in wikidata match", artistlabel)
        return artistlabel
        
    print("WARN: given artist name and label in wikidata do not match", artistlabel)
    return ""


# there is no easy way to do this: album by same name can exist for different artists
# and labels might not exist for all languages
def check_if_album_exists(repo, commands):
    #if "album" not in commands:
    
    album_name = commands["album"]
    #artistqcode = getartistqcode(commands["artist"])

    # TODO: search items by name, compare other information
    # 
    
    
    #albumitem = getitembyqcode(repo, albumqcode)
    #albumlabel = getlabelbylangfromitem(albumitem, lang)
    #qlist = getArtistsFromItem(albumitem)
    #if (artistqcode not in qlist):
        # not same artist
    #    return False
    
    # now check for year
    
    # get property for artist
    
    # for now, just assume it doesn't..
    return False


def add_album(commands, finnarecord = None):

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()
    
    album_name = ""
    if (finnarecord != None):
        album_name = finnarecord.getTitleFromFinna()
    elif "album" in commands:
        album_name = commands["album"]

    if (len(album_name) == 0):
        print('WARN: cannot create, album name missing')
        return None
    
    # just check given parameter makes sense
    artistlabel = check_artist(repo, commands)
    if (artistlabel == ""):
        print('WARN: cannot create, artist unknown')
        return None

    # album needs artist and album name since there can be 
    # multiple albums from different artists or even same artist
    #if (check_if_album_exists(repo, commands) == True):
    #    print('Album exists, skipping')
    #    return None

    album_desc_en = "album by " + artistlabel
    #album_desc_fi = artistlabel + " albumi"
    album_desc_sv = "album av " + artistlabel
    album_desc_fr = "album de " + artistlabel

    # more accurate date? parse to year
    if "release" in commands:
        # only year for now
        year = int(commands["release"])
        album_desc_en = str(year) + " " + album_desc_en
    #    album_desc_fi = album_desc_fi + " vuodelta " + str(year)
        album_desc_sv = album_desc_sv + " från " + str(year)
        album_desc_fr = album_desc_fr + " sorti en " + str(year)
    
    data = {"labels": {"en": album_name, "fi": album_name, "sv": album_name, "fr": album_name, "mul": album_name},
    "descriptions": {"en": album_desc_en, "sv": album_desc_sv, "fr": album_desc_fr}}


    print('Creating a new album item for', album_name)

    #create item
    newitem = pywikibot.ItemPage(repo, None)
    
    newitem.editEntity(data, summary=u'Edited item: set labels, descriptions')

    newitem.get()

    print('Adding properties...')

    add_album_properties(repo, newitem, commands)

    nid = newitem.getID()
    print('All done', nid)
    return nid


def add_album_from_finna(finnaid):
    # TODO: check and parse information in record..

    frsession = requests.Session()
    frsession.headers.update({'User-Agent': 'FinnaUploader 0.3b (https://commons.wikimedia.org/wiki/User:FinnaUploadBot)'}) # noqa

    fr = FinnaRecord()
    fr.finnaid = finnaid
  
    fr.finnarecord = get_finna_record(frsession, fr.finnaid)
    if (fr.isFinnaRecordOk() == False):
        print("Failed to get valid record with id:", fr.finnaid)
        return None

    print("Got finna record:", fr.getFinnaIdFromRecord())
    
    if (fr.isalbum() == False):
        print("Not as supported album record with id:", fr.finnaid)
        return None
    
    fr.parseFullRecord()
    
    #wdsite = pywikibot.Site('wikidata', 'wikidata')
    #wdsite.login()
    #repo = wdsite.data_repository()

    #add_album(commands, fr):


support_args = ["album",
                "artist",
                "artistqid",
                "muslabel",
                "genre",
                "discogsmaster",
                "discogsrelease",
                "metalarchives",
                "release",
                "finnaid"]

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
            
        if (key == "artist"):
            if (getartistqcode(commands) == ""):
                print("WARN: no qcode for artist", commands["artist"])
                exit()
        if (key == "muslabel"):
            if (getlabelqcode(commands) == ""):
                print("WARN: no qcode for label", commands["muslabel"])
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

    if "finnaid" not in commands:
        confirmation = pywikibot.input_choice(
            "Do you want to continue with the edits?",
            [('Yes', 'y'), ('No', 'n')],
            default='n'
        )

        if confirmation == 'n':
            print("Operation cancelled.")
            exit()
        
        add_album(commands)
        print("all done")
        
    else:
        
        # TODO: parse and print some kind of preview of what will be added

        add_album_from_finna(commands["finnaid"])
        print("all done")


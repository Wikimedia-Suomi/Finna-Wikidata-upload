# Script creates wikidata item for a music album.
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
        self.finnaid = "" # id used in query
        self.sourceref = None # url of metapage
        self.finnarecord = None # json data
        
        self.albumtitle = None
        self.artistname = None
        #self.publishername = None # must find from xml
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
    
    # record page (metadata page) path without domain
    def getRecordPage(self):
        records = self.finnarecord['records'][0]
        if "recordPage" not in records:
            print("WARN: no recordPage in finna record ")
            return ""

        # should be /Record.. without domain
        recordpage = records['recordPage']
        return recordpage

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
        
        # alternative titles may include list of song names..
        #f_alttitle = records['alternativeTitles'] # ??
        
        # "sov. Pedro Hietanen" -> not album title..
        #f_titlestatement = records['titleStatement'] # Halavatun Papat
        
        #f_summary = records['summary'] # ??

        print("DBEUG: found title in finna record: ", f_title)
        return f_title

    # <datafield tag="338" ind1=" " ind2=" "><subfield code="a">äänilevy</subfield>
    def isalbum(self):
        records = self.finnarecord['records'][0]
        
        if "formats" not in records:
            return False
        
        f_formats = records['formats']
        for fmt in f_formats:
            ff_value = fmt['value'].strip()
            ff_translated = fmt['translated'].strip()

            print("DBEUG: format in record: ", ff_value, " - ", ff_translated)
            
            if (ff_value == "0/Sound/"):
                return True
            if (ff_value == "1/Sound/CD/"):
                return True
            if (ff_translated == "Sound" or ff_translated == "Äänite"):
                return True
            if (ff_translated == "CD"):
                return True


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

    #def getnonpresenterauthors(self):
        # may have band name with "type": "Corporate Name"
        # may have band member name with "type": "Personal Name"
        # may have person id "id": "000103392", - kanto id?

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
            # not usable as a year
            return ""
        
        # validate it is a date, decade or year?
        return f_year

    # genres
    # <datafield tag="655" ind1=" " ind2="7"><subfield code="a">popmusiikki</subfield>
    # <datafield tag="655" ind1=" " ind2="7"><subfield code="a">reggae</subfield>

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
def getartistqcode(artistname):

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
    
    print("looking fo artist", artist)
    
    if artistname in d_artisttoqcode:
        return d_artisttoqcode[artistname]

    print("artist not found", d_artisttoqcode)
    return ""

# todo: read config for mapping
def gettypeqcode(commands):

    # mapping type to qcode
    d_typetoqcode = dict()
    d_typetoqcode["studioalbumi"] = "Q208569"
    d_typetoqcode["livealbumi"] = "Q209939"
    d_typetoqcode["kokoelma-albumi"] = "Q222910"
    d_typetoqcode["soundtrack-albumi"] = "Q4176708"

    if "type" not in commands:
        return ""

    reltype = commands["type"]
    if reltype in d_typetoqcode:
        return d_typetoqcode[reltype]
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
def getlabelqcode(muslabel):

    # mapping label to qcode
    d_labeltoqcode = dict()
    d_labeltoqcode["Nuclear Blast"] = "Q158886"
    d_labeltoqcode["Napalm Records"] = "Q693194"
    d_labeltoqcode["Century Media Records"] = "Q158867"
    d_labeltoqcode["Spikefarm Records"] = "Q51794339"
    d_labeltoqcode["Naturmacht Productions"] = "Q73783815"
    d_labeltoqcode["Avantgarde Music"] = "Q790187"
    d_labeltoqcode["Rockshots Records"] = "Q117885298"
    d_labeltoqcode["Warner Music Finland"] = "Q10831860"
    
    if muslabel in d_labeltoqcode:
        return d_labeltoqcode[muslabel]
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
def getlanguageqcode(lang):

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
    
    # useita kieliä
    #d_langqcode["mul"] = "Q20923490"

    
    if lang in d_langqcode:
        return d_langqcode[lang]
    return ""

# get qcode for artist by name from finna:
# this might need some extra mapping 
# since there may be multiple people with same name
#
def get_finna_artist_qcode(finnarecord):
    # TODO: add mapping for getting qcode by finna artist name,
    # otherwise it must be given as command separately
    if (finnarecord == None):
        return ""
    if (finnarecord.artistname == None):
        return ""
    return getartistqcode(finnarecord.artistname)

def get_finna_label_qcode(finnarecord):
    if (finnarecord == None):
        return ""
    #if (finnarecord.publishername == None):
    #    return ""
    #return getlabelqcode(finnarecord.publishername)
    return ""


def isArtistItem(item):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        qid = claim.getTarget().id

        # human
        if (qid == 'Q5'):
            return True
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

def isAlbumItem(item):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        if (claim.getTarget().id == 'Q482994'):
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
def add_item_source_url(repo, p_claim, commands, finnarecord = None):
    
    sourceurl = ""
    if (finnarecord != None):
        sourceurl = finnarecord.sourceref

    if "source" in commands and sourceurl == "":
        sourceurl = commands['source']
        
    if (sourceurl == ""):
        return None

    prop = 'P854' # source-url
   
    u_claim = pywikibot.Claim(repo, prop, is_reference=True, is_qualifier=False)
    u_claim.setTarget(sourceurl)
    p_claim.addSource(u_claim)

# todo: other sources to use? -> must have other related properties and qualifiers..


# todo: use data from record instead from commandline
def add_album_properties(repo, wditem, commands, finnarecord = None):
    
    # instance of
    if not 'P31' in wditem.claims:
        print("Adding claim: instance of album")
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, 'Q482994') # music album
        claim.setTarget(target)
        wditem.addClaim(claim)#, summary='Adding 1 claim')

    # esittäjä
    if not 'P175' in wditem.claims:
        
        # if finna record is given, try to find by name
        artist_qcode = get_finna_artist_qcode(finnarecord)
        if artist_qcode == "" and "artistqid" in commands:
            # fallback to qid in commands
            artist_qcode = commands["artistqid"]

        # further fallback if name is given in commands (deprecated)
        if "artist" in commands and artist_qcode == "":
            artist_qcode = getartistqcode(commands["artist"])
        
        if (artist_qcode != ""):
            
            print("Adding claim: artist")
            claim = pywikibot.Claim(repo, 'P175')
            target = pywikibot.ItemPage(repo, artist_qcode) 
            claim.setTarget(target)
            wditem.addClaim(claim)#, summary='Adding 1 claim')
        
    # release date (date formatting?)
    if not 'P577' in wditem.claims:
        releaseyear = ""
        if (finnarecord != None):
            releaseyear = finnarecord.getyear()
        
        if "released" in commands and releaseyear == "":
            releaseyear = commands["released"]

        if (releaseyear != ""):
            # only year now
            wbdate = getwbdate(int(releaseyear))
            
            print("Adding claim: released in")
            claim = pywikibot.Claim(repo, 'P577')
            #target = pywikibot.ItemPage(repo, released) 
            claim.setTarget(wbdate)
            
            add_item_source_url(repo, claim, commands, finnarecord)
            
            wditem.addClaim(claim)#, summary='Adding 1 claim')

    # genre
    if not 'P136' in wditem.claims:
        genreqcode = getgenreqcode(commands)
        if (genreqcode != ""):
        
            print("Adding claim: genre")
            genreclaim = add_item_link(repo, wditem, 'P136', genreqcode)

            # add source if given
            add_item_source_url(repo, genreclaim, commands, finnarecord)


    # kieli
    if not 'P407' in wditem.claims:
        
        albumlangs = None
        if (finnarecord != None):
            # may be a list
            albumlangs = finnarecord.getlang()

        if "language" in commands and albumlangs == None:
            albumlangs = list()
            albumlangs.append(commands["language"])

        for l in albumlangs:
            langqcode = getlanguageqcode(l)
            if (langqcode != ""):
                print("Adding claim: language for ", l)
                langclaim = add_item_link(repo, wditem, 'P407', langqcode)

                # add source if given
                add_item_source_url(repo, langclaim, commands, finnarecord)
        

    # levymerkki (P264)
    if not 'P264' in wditem.claims:
        
        # note: might have multiple publishers..
        
        # try to fetch qcode by name from record
        labelqcode = get_finna_label_qcode(finnarecord)
        if labelqcode == "" and "muslabelqid" in commands:
            # fallback if qcode is given in commands
            labelqcode = commands["muslabelqid"]

        # if name is given in commands (deprecated)
        if labelqcode == "" and "muslabel" in commands:
            labelqcode = getlabelqcode(commands["muslabel"])

        if (labelqcode != ""):
        
            print("Adding claim: record label")
            claim = pywikibot.Claim(repo, 'P264')
            target = pywikibot.ItemPage(repo, labelqcode) 
            claim.setTarget(target)

            add_item_source_url(repo, claim, commands, finnarecord)
            
            wditem.addClaim(claim)#, summary='Adding 1 claim')


    # teoksen tyyppi (P7937)
    if not 'P7937' in wditem.claims:
        typeqcode = gettypeqcode(commands)
        if (typeqcode != ""):
        
            print("Adding claim: type")
            claim = pywikibot.Claim(repo, 'P7937')
            target = pywikibot.ItemPage(repo, typeqcode) 
            claim.setTarget(target)
            wditem.addClaim(claim)#, summary='Adding 1 claim')

    # julkaisupaikka (P291)
    if not 'P291' in wditem.claims:
        # from name to qid? 
        # maailmanlaajuinen (Q13780930)

        placeqcode = ""
        if "placeqid" in commands:
            placeqcode = commands["placeqid"]

        if (placeqcode != ""):
        
            print("Adding claim: release place")
            claim = pywikibot.Claim(repo, 'P291')
            target = pywikibot.ItemPage(repo, placeqcode) 
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


    # julkaisun MusicBrainz-tunniste (P5813)
    # äänitteen MusicBrainz-tunniste (P4404)
    # teoksen MusicBrainz-tunniste (P435)

    # julkaisuryhmän MusicBrainz-tunniste (P436)
    if not 'P436' in wditem.claims:
        if "mbzgroup" in commands:
            mbgroup = commands["mbzgroup"]
            
            print("Adding claim: musicbrainz release group")
            add_item_value(repo, wditem, 'P436', mbgroup)


def check_artist(repo, commands, lang='fi', finnarecord = None):

    # try to find qcode by name from finna
    artistqcode = get_finna_artist_qcode(finnarecord)
    if artistqcode == "" and "artistqid" in commands:
        # fallback if qcode is given in commands
        artistqcode = commands["artistqid"]

    # if name is given in commands (deprecated)
    if artistqcode == "" and "artist" in commands:
        artistqcode = getartistqcode(commands["artist"])

    if (len(artistqcode) > 0):
        item = getitembyqcode(repo, artistqcode)
        if (isArtistItem(item) == False):
            print('WARN: qid is not for artist', artistqcode)
            return ""
        
        artistlabel = getlabelbylangfromitem(item, lang)
        if (artistlabel == None):
            print("WARN: no label with lang", lang)
            artistlabel = getlabelbylangfromitem(item, 'mul')
            if (artistlabel != ""):
                print("found artist name", artistlabel, " with lang 'mul'")
                return artistlabel
            return ""
        if (artistlabel != ""):
            print("ok, artist name found", artistlabel, " with lang", lang)
        return artistlabel

    print("WARN: given artist name and label in wikidata do not match or not given")
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


def create_album_item(repo, album_name, artistlabel, release=""):

    # album needs artist and album name since there can be 
    # multiple albums from different artists or even same artist
    #if (check_if_album_exists(repo, commands) == True):
    #    print('Album exists, skipping')
    #    return None

    # TOOD: if we have type == Q208569, 
    # then use descrption "studio album by..",
    # also check cases for live albums etc. 

    album_desc_en = "album by " + artistlabel
    #album_desc_fi = artistlabel + " albumi"
    album_desc_sv = "album av " + artistlabel
    album_desc_fr = "album de " + artistlabel

    # more accurate date? parse to year
    if (len(release) > 0):
        # only year for now, add support for date
        year = str(release)
        album_desc_en = year + " " + album_desc_en
    #    album_desc_fi = album_desc_fi + " vuodelta " + str(year)
        album_desc_sv = album_desc_sv + " från " + year
        album_desc_fr = album_desc_fr + " sorti en " + year
    
    data = {"labels": {"en": album_name, "fi": album_name, "sv": album_name, "fr": album_name, "mul": album_name},
    "descriptions": {"en": album_desc_en, "sv": album_desc_sv, "fr": album_desc_fr}}


    print('Creating a new album item for', album_name)

    #create item
    newitem = pywikibot.ItemPage(repo, None)
    
    newitem.editEntity(data, summary=u'Edited item: set labels, descriptions')

    # reload, ensure it is created
    # can we skip this and leave to later?
    newitem.get()
    return newitem


def add_album(commands, finnarecord = None):

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()
    
    album_name = ""
    if (finnarecord != None):
        album_name = finnarecord.getTitleFromFinna()
    if album_name == "" and "album" in commands:
        album_name = commands["album"]

    # updating existing album?
    albumqid = ""
    if "albumqid" in commands:
        albumqid = commands['albumqid']

    if (len(album_name) == 0 and len(albumqid) == 0):
        print('WARN: cannot create, album name and qid missing')
        return None

    # just check given parameter makes sense,
    # if we are just updating an album this might not be necessary,
    # but we should validate it if we are adding it to an album..
    artistlabel = check_artist(repo, commands, finnarecord)
    if (artistlabel == ""):
        print('WARN: cannot create, artist unknown')
        return None
    
    album_item = {}
    if (len(albumqid) == 0):

        # more accurate date? parse to year
        releaseyear = ""
        if (finnarecord != None):
            releaseyear = finnarecord.getyear()

        if "released" in commands and releaseyear == "":
            # only year for now
            releaseyear = commands["released"]
        
        album_item = create_album_item(repo, album_name, artistlabel, releaseyear)
    else:
        # update/expand existing item
        album_item = getitembyqcode(repo, albumqid)
        if (isAlbumItem(album_item) == False):
            print('WARN: qid is not for album', albumqid)
            return None

    # only add given properties
    print('Adding properties...')
    add_album_properties(repo, album_item, commands, finnarecord)

    nid = album_item.getID()
    print('All done', nid)
    return nid


# check and parse information in record..
def add_album_from_finna(commands):
    
    finnaid = commands["finnaid"]

    frsession = requests.Session()
    frsession.headers.update({'User-Agent': 'FinnaUploader 0.3b (https://commons.wikimedia.org/wiki/User:FinnaUploadBot)'}) # noqa

    fr = FinnaRecord()
    fr.finnaid = finnaid
  
    fr.finnarecord = get_finna_record(frsession, fr.finnaid)
    if (fr.isFinnaRecordOk() == False):
        print("Failed to get valid record with id:", fr.finnaid)
        return None

    print("Got finna record:", fr.getFinnaIdFromRecord())
    #if (fr.getFinnaIdFromRecord() != fr.finnaid):
    
    #frpage = ""
    #frpage = fr.getRecordPage()
    
    # keep metapage address
    frpage = "https://finna.fi/Record/" + finnaid
    fr.sourceref = frpage
    
    if (fr.isalbum() == False):
        print("Not a supported album record with id:", fr.finnaid)
        return None
    
    # TODO: more validation..
    fr.parseFullRecord()
    
    # pass both record and extra commands:
    # some we can't parse yet..
    add_album(commands, fr)


support_args = ["album",
                "albumqid",
                "artist",
                "artistqid",
                "muslabel",
                "muslabelqid",
                "genre",
                "released",
                "type",
                "language",
                "placeqid",
                "discogsmaster",
                "discogsrelease",
                "metalarchives",
                "mbzgroup",
                "finnaid",
                "source"]

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
            if (getartistqcode(commands["artist"]) == ""):
                print("WARN: no qcode for artist", commands["artist"])
                exit()
        if (key == "muslabel"):
            if (getlabelqcode(commands["muslabel"]) == ""):
                print("WARN: no qcode for label", commands["muslabel"])
                exit()
        if (key == "genre"):
            if (getgenreqcode(commands) == ""):
                print("WARN: no qcode for genre", commands["genre"])
                exit()
        if (key == "type"):
            if (gettypeqcode(commands) == ""):
                print("WARN: no qcode for type", commands["type"])
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

        add_album_from_finna(commands)
        print("all done")


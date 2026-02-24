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

#from requests import get

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
        
        #self.albumtitle = None
        #self.artistname = None
        #self.publishername = None
        #self.releaseyear = None
        #self.languagecode = None
        #self.origlangcode = None

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
            
        f_title = records['title'] # Naurun varjolla
        #f_subtitle = records['subTitle'] # 
        f_shorttitle = records['shortTitle'] # Naurun varjolla
        #f_alttitle = records['alternativeTitles'] # På skämt (ruotsinkielinen nimi)', 'När skämt börjar lukta (ruotsinkielinen televisioesitysnimi)', 'I skuggan av skrattet (leikekansiosta otettu nimi)', 'Laughing Matters (englanninkielinen nimi)', 'Rakkautta ennen valomerkkiä (työnimi)']
        #f_summary = records['summary'] # ??

        print("DBEUG: found title in finna record: ", f_title)
        return f_title

    # may have people that are actually companies
    def getAuthorsElonet(self):
        records = self.finnarecord['records'][0]
        
        if "nonPresenterAuthors" not in records:
            return ""

        # for each
        # "name"
        # "role" # kirjoittaja
        # "id" # asteri
        # "type" # personal name


    # must parse full record?
    # these may be empty
    def getlang(self):
        records = self.finnarecord['records'][0]
        
        #if "languages" not in records and "originalLanguages" not in records:
        #    return ""

        if "languages" in records:
            return records['languages'] # empty ?
        
        #if "originalLanguages" in records:
        #    f_origlang = records['originalLanguages'] # empty ?
        return ""

    def getyear(self):
        records = self.finnarecord['records'][0]
        
        if "year" not in records:
            return ""
        
        f_year = records['year'] # 2017

        # should be a plain number..
        iyear = int(f_year)
        if (iyear < 1800 or iyear > 2100):
            # not usable as a film
            return ""

        # validate it is a date, decade or year?
        return f_year

    def isfilm(self):
        records = self.finnarecord['records'][0]
        
        if "formats" not in records:
            return False

        f_type = records['formats'][0]['value'] # 0/Video/
        f_typename = records['formats'][0]['translated'] # Video
        
        # {'value': '1/Video/Feature/', 'translated': 'Elokuva, pitkä'}
        
        if (f_type == "0/Video/"):
            return True
       
        return False
    
    # "nonPresenterAuthors"
    #def getcreators(self):
        # "tag" elotekija "name" = person name, id = "elonet_henkilo_<num>"
        # tehtava = kuvaus, äänisuunnittelu, käsikirjoitus, pukusuunnittelu, maskeeraussuunnittelu, ilmakuvat, lisävaloteknikko..
        # role = apulaisohjaaja, dramaturgi, tuotantoassistentti, steadicam-operaattori, still-kuvaaja, lisävaloteknikko ..
    
    #def getdistributors(self):
        # multiple instances for different years
        # "tag" elolevittaja, "name" = "Oy Nordisk Film Ab" "type" = elonet_yhtio
        
    #def getproductioncompanies(self):
        #  {'tag': 'elotekijayhtio', "name" = "Magia..", "role" = äänistudio .. or kuvan jälkituotanto or visuaaliset efektit

    # must parse full record for the isbn?
    # <datafield tag="020" ind1=" " ind2=" "><subfield code="a">978-952-393-802-1</subfield><subfield code="q">pehmeäkantinen</subfield></datafield><datafield tag="035" ind1=" " ind2=" "><subfield code="a">(FI-BTJ)9789523938021</subfield></datafield><datafield tag="035" ind1=" " ind2=" "><subfield code="a">(FI-MELINDA)019396823</subfield></datafield><datafield tag="040" ind1=" " ind2=" "><subfield code="a">FI-E</subfield><subfield code="b">fin</subfield><subfield code="e">rda</subfield><subfield code="d">FI-BTJ</subfield><subfield code="d">FI-NL</subfield></datafield>
    #def getisbn(self):

    def parseFullRecord_get_root(self):
        if "fullRecord" not in self.finnarecord['records'][0]:
            print("fullRecord does not exist in finna record")
            return None

        full_record_data = self.finnarecord['records'][0]["fullRecord"]
        if (len(full_record_data) == 0):
            print("empty full record")
            return None
        
        print("full record:", full_record_data)

        root = XEltree.fromstring(full_record_data)
        if (root == None):
            print("root not found")
            return None
        
        return root

    def parseFullRecord(self):

        root = self.parseFullRecord_get_root()
        
        print("root tag", root.tag)
        print("root attrib", root.attrib)
        
        # <Identifier scheme="KAVI" IDTypeName="elonet_elokuva">1613545</Identifier>
        
        identitle = root.findall(".//Title/IdentifyingTitle")
        # <CountryOfReference><Country><RegionName elokuva-elomaa-maakoodi="FI">Suomi</RegionName>
        # <YearOfReference elokuva-valmistumisvuodenlahde="lopputeksti">2020</YearOfReference>

        titles = root.findall(".//Title/TitleText")
        for tt in titles:
            ttlang = tt.get("lang") 
            ttext = tt.text
            
            # note: lang might be "none" for finnish, but also for swedish..
            # "leikekansiosta otettu nimi" voi olla ilman kielikoodia?
            # TitleRelationship elokuva-elonimi-tyyppi="ty&#xF6;nimi">working< -> työnimi
            print("lang:", ttlang ,"title:", ttext)
            

        #record = root.iter()
        #for child in record:
        #    print(child.tag, child.attrib)

                

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


# try to support partial dates
class SimpleTimestamp:
    def __init__(self):
        self.year = 0
        self.month = 0
        self.day = 0
        self.precision = 0 # need to define more clearly..
        self.postepoch = True # before/after epoch

    def isValidDay(self, iday):
        if (iday < 1 or iday > 31):
            # not a valid day
            return False
        return True

    def isValidMonth(self, imon):
        if (imon < 1 or imon > 12):
            # not a valid month
            return False
        return True

    def isValidYear(self, iyr):
        if (iyr < 1 or iyr > 9999):
            # not a valid year
            return False
        return True
    
    def isValid(self):
        if (self.isValidDay(self.day) == True
            and self.isValidMonth(self.month) == True
            and self.isValidYear(self.year) == True):
            return True
        return False

    def setDate(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day

class NameToQcodeMap:
    def __init__(self):
        self.d_names = dict()
        
    def getqcode(self, name):
        if name in self.d_names:
            return self.d_names[name]
        return ""

class ItemToProperty:
    def __init__(self):
        self.prop = "" # property as 'Pnumber'
        self.qcode = "" # target as 'Qcode'

class ValueToProperty:
    def __init__(self):
        self.prop = "" # property as 'Pnumber'
        self.value = "" # just string as value (convert from number)

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

def isHumanItem(item):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        if (claim.getTarget().id == 'Q5'):
            return True
        
    return False

def getitembyqcode(repo, itemqcode):

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
def getdirectorqcode(commands):

    # mapping name to qcode
    d_directorqcode = dict()
    d_directorqcode["Edvin Laine"] = "Q2744992"
    d_directorqcode["Toivo Särkkä"] = "Q7813416"
    
    d_directorqcode["Pietari Koskinen"] = "Q16300082"
    
    
    if "director" not in commands:
        return ""
    
    director = commands["director"]    
    if director in d_directorqcode:
        return d_directorqcode[director]
    return ""

# todo: read config for mapping
# eroaa kirjan kirjoittajasta
def getscreenwriterqcode(commands):

    # mapping name to qcode
    d_writerqcode = dict()
    d_writerqcode["Seppo Lappalainen"] = "Q17382122"
    
    if "screenwriter" not in commands:
        return ""
    
    writer = commands["screenwriter"]    
    if writer in d_writerqcode:
        return d_writerqcode[writer]
    return ""


# todo: read config for mapping
def getproductioncompanyqcode(commands):

    # mapping name to qcode
    d_productionqcode = dict()
    d_productionqcode["Suomen Filmiteollisuus"] = "Q4050398"
    
    if "productioncompany" not in commands:
        return ""
    
    productioncompany = commands["productioncompany"]    
    if productioncompany in d_productionqcode:
        return d_productionqcode[productioncompany]
    return ""

# todo: read config for mapping
def getfilmgenreqcode(commands):

    # mapping genre to qcode
    d_genretoqcode = dict()
    d_genretoqcode["historiallinen elokuva"] = "Q17013749" # film genre
    
    d_genretoqcode["draamaelokuva"] = "Q130232" # film genre
    d_genretoqcode["rikoselokuva"] = "Q959790" # film genre
    d_genretoqcode["komediaelokuva"] = "Q157443" # film genre
    
    
    if "genre" not in commands:
        return ""

    genre = commands["genre"]
    if genre in d_genretoqcode:
        return d_genretoqcode[genre]
    return ""

# todo: read config for mapping
# don't need many so might as well hard-code?
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
def add_film_properties(repo, wditem, commands):

    # perustuu teokseen (P144)

    # ohjaaja (P57)
    if not 'P57' in wditem.claims:
        director_qcode = getdirectorqcode(commands)
        if (director_qcode != ""):
            
            print("Adding claim: director")
            add_item_link(repo, wditem, 'P57', director_qcode)

    # käsikirjoittaja (P58)
    if not 'P58' in wditem.claims:
        writer_qcode = getscreenwriterqcode(commands)
        if (writer_qcode != ""):
            
            print("Adding claim: writer")
            add_item_link(repo, wditem, 'P58', writer_qcode)
    
    # kuvaaja (P344)
    # säveltäjä (P86)
    # tuottaja (P162)
    
    # näyttelijä (P161)
    # + hahmon nimi (P4633)
    
    # tuotantoyhtiö (P272)
    if not 'P272' in wditem.claims:
        prod_qcode = getproductioncompanyqcode(commands)
        if (prod_qcode != ""):
            
            print("Adding claim: production company")
            add_item_link(repo, wditem, 'P272', prod_qcode)

    # genre, lajityyppi
    if not 'P136' in wditem.claims:
        genreqcode = getfilmgenreqcode(commands)
        if (genreqcode != ""):
        
            print("Adding claim: genre")
            add_item_link(repo, wditem, 'P136', genreqcode)
            
    # kesto (P2047)
    # väri (P462)
    # kuvasuhde (P2061)


def add_item_properties(repo, wditem, commands):
    # instance of
    if not 'P31' in wditem.claims:
        print("Adding claim: instance of elokuva")
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, 'Q11424') # elokuva
        claim.setTarget(target)
        wditem.addClaim(claim)#, summary='Adding 1 claim')

    # elonetid
    if not 'P2346' in wditem.claims:
        if "elonetid" in commands:
            elonetid = commands["elonetid"]
            
            print("Adding claim: elonet id")
            add_item_value(repo, wditem, 'P2346', elonetid)

    # publication date (date formatting?) julkaisupäivä
    # + julkaisupaikka (P291)
    if not 'P577' in wditem.claims:
        if "release" in commands:
            released = commands["release"]

            # only year now, parse date if given
            wbdate = getwbdate(int(released))
            
            print("Adding claim: released in")
            claim = pywikibot.Claim(repo, 'P577')
            claim.setTarget(wbdate)
            wditem.addClaim(claim)#, summary='Adding 1 claim')

    # alkuperämaa
    if not 'P495' in wditem.claims:
        countryqcode = getcountryqcode(commands)
        if (countryqcode != ""):
        
            print("Adding claim: country of origin")
            add_item_link(repo, wditem, 'P495', countryqcode)

    # alkuperäiskieli (P364)
    # kieli
    #if not 'P407' in wditem.claims:
    if not 'P364' in wditem.claims:
        langqcode = getlanguageqcode(commands)
        if (langqcode != ""):
        
            print("Adding claim: language")
            add_item_link(repo, wditem, 'P364', langqcode)


# there is no easy way to do this: album by same name can exist for different artists
# and labels might not exist for all languages
def check_if_film_exists(repo, commands):
    film_name = commands["title"]
    #artistqcode = getartistqcode(commands["artist"])

    # TODO: search items by name, compare other information
    # 
    
    
    # for now, just assume it doesn't..
    return False


def add_film(commands, finnarecord = None):

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()
    
    # just check given parameter makes sense
    #artistlabel = check_artist(repo, commands)
    #if (artistlabel == ""):
    #    return None
    #directorlabel = commands["director"]
    
    if (check_if_film_exists(repo, commands) == True):
        print('Film exists, skipping')
        return None

    print('Creating a new film item')

    #create item
    newitem = pywikibot.ItemPage(repo)
    
    film_title = commands["title"]
    
    #desc_en = "film by " + directorlabel
    #desc_fi = directorlabel + " elokuva"
    #desc_sv = "film av " + directorlabel
    #desc_fr = "film de " + directorlabel

    # more accurate date? parse to year
    if "release" in commands:
        # only year for now
        year = int(commands["release"])
        #desc_en = str(year) + " " + desc_en
    #    desc_fi = desc_fi + " vuodelta " + str(year)
        #desc_sv = desc_sv + " från " + str(year)
        #desc_fr = desc_fr + " sorti en " + str(year)
    
    data = {"labels": {"fi": film_title}
    #"descriptions": {"en": album_desc_en, "sv": album_desc_sv, "fr": album_desc_fr}
    }

    newitem.editEntity(data, summary=u'Edited item: set labels')

    newitem.get()

    print('Adding properties...')

    # generic properties
    add_item_properties(repo, newitem, commands)
    
    # other film specific properties
    add_film_properties(repo, newitem, commands)

    nid = newitem.getID()
    print('All done', nid)
    return nid


def add_film_from_elonet(finnaid):
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
    
    fr.parseFullRecord()
    
    #wdsite = pywikibot.Site('wikidata', 'wikidata')
    #wdsite.login()
    #repo = wdsite.data_repository()

    #add_film(commands, fr):


support_args = ["title",
                "director",
                "screenwriter",
                "genre",
                "elonetid",
                "release",
                "country",
                "language"]

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
            
        if (key == "director"):
            if (getdirectorqcode(commands) == ""):
                print("WARN: no qcode for director", commands["director"])
                exit()
        if (key == "screenwriter"):
            if (getscriptwriterqcode(commands) == ""):
                print("WARN: no qcode for screenwriter", commands["screenwriter"])
                exit()
        if (key == "genre"):
            if (getfilmgenreqcode(commands) == ""):
                print("WARN: no qcode for genre", commands["genre"])
                exit()
        if (key == "country"):
            if (getcountryqcode(commands) == ""):
                print("WARN: no qcode for country", commands["country"])
                exit()
        if (key == "language"):
            if (getlanguageqcode(commands) == ""):
                print("WARN: no qcode for language", commands["language"])
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

    if "elonetid" not in commands:
        confirmation = pywikibot.input_choice(
            "Do you want to continue with the edits?",
            [('Yes', 'y'), ('No', 'n')],
            default='n'
        )

        if confirmation == 'n':
            print("Operation cancelled.")
            exit()

        
        add_film(commands)
        print("all done")

    else:
        
        # TODO: parse and print some kind of preview of what will be added

        add_film_from_elonet(commands["elonetid"])
        print("all done")


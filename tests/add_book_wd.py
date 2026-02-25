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
            
        f_title = records['title'] # Tulilinja : Ukraina ja uusi maailmanjärjestys
        f_subtitle = records['subTitle'] # Ukraina ja uusi maailmanjärjestys
        f_shorttitle = records['shortTitle'] # Tulilinja
        #f_alttitle = records['alternativeTitles'] # ??
        f_titlestatement = records['titleStatement'] # Timo Hellenberg, Pekka Visuri
        #f_summary = records['summary'] # ??

        print("DBEUG: found title in finna record: ", f_title)
        return f_title

    def getAuthorsFinna(self):
        records = self.finnarecord['records'][0]
        
        if "nonPresenterAuthors" not in records:
            return ""
        
        # for each
        # "name"
        # "role" # kirjoittaja
        # "id" # asteri
        # "type" # personal name


    def getlang(self):
        records = self.finnarecord['records'][0]
        
        if "languages" not in records and "originalLanguages" not in records:
            return ""

        f_lang = records['languages'] # fin
        
        #if "originalLanguages" in records:
        #    f_origlang = records['originalLanguages'] # fin
        return f_lang

    def getyear(self):
        records = self.finnarecord['records'][0]
        
        if "year" not in records:
            return ""
        
        f_year = records['year'] # 2017

        # should be a plain number..
        iyear = int(f_year)
        if (iyear < 900 or iyear > 2100):
            # not usable as a book
            return ""

        # validate it is a date, decade or year?
        return f_year

    def isbook(self):
        records = self.finnarecord['records'][0]
        
        if "formats" not in records:
            return False

        isbook = False

        f_type = records['formats'][0]['value'] # 0/Book/
        f_typename = records['formats'][0]['translated'] # Kirja
        
        if (f_type == "0/Book/"):
            isbook = True

        # parse page count?
        if "physicalDescriptions" in records:
            f_pd = records['physicalDescriptions'] # 302 sivua, 8 numeroimatonta kuvasivua kuvitettu, karttoja ; 21 cm
        
        return isbook

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

# asteri-id to qcode
#def getwriterqcodebyasteri(commands):

# todo: read config for mapping
def getwriterqcode(commands):

    # mapping name to qcode
    d_writerqcode = dict()
    d_writerqcode["Suzanne Collins"] = "Q228624"
    d_writerqcode["Rauno Hietanen"] = "Q137754050"
    d_writerqcode["Hannu Salmi"] = "Q11861442"
    
    d_writerqcode["Outi Pakkanen"] = "Q16989624"
    
    d_writerqcode["Pekka Visuri"] = "Q11887222"
    
    if "writer" not in commands:
        return ""
    
    writer = commands["writer"]    
    if writer in d_writerqcode:
        return d_writerqcode[writer]
    return ""

# todo: read config for mapping
def getgenreqcode(commands):

    # mapping genre to qcode
    d_genretoqcode = dict()
    d_genretoqcode["science fiction"] = "Q24925"
    d_genretoqcode["muistelmateos"] = "Q112983"
    d_genretoqcode["romantasia"] = "Q930383"
    
    if "genre" not in commands:
        return ""

    genre = commands["genre"]
    if genre in d_genretoqcode:
        return d_genretoqcode[genre]
    return ""

# todo: read config for mapping
def getworktypecode(commands):

    # mapping worktype to qcode
    d_worktypeqcode = dict()
    d_worktypeqcode["romaani"] = "Q8261"
    d_worktypeqcode["tietokirja"] = "Q20540385"
    
    if "worktype" not in commands:
        return ""

    wt = commands["worktype"]
    if wt in d_worktypeqcode:
        return d_worktypeqcode[wt]
    return ""

# todo: read config for mapping
def getpublisherqcode(commands):

    # mapping publisher to qcode
    d_publisherqcode = dict()
    d_publisherqcode["WSOY"] = "Q3564797"
    d_publisherqcode["Otava"] = "Q2602805"
    d_publisherqcode["Docendo"] = "Q18680094"
    d_publisherqcode["Into Kustannus"] = "Q11864968"

    if "publisher" not in commands:
        return ""

    pub = commands["publisher"]
    if pub in d_publisherqcode:
        return d_publisherqcode[pub]
    return ""

# todo: read config for mapping?
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



#def getArtistsFromItem(item):
#    qlist = list()
#    part_of = item.claims.get('P282', [])
#    for claim in part_of:
#        qid = claim.getTarget().id
#        if (qid not in qlist):
#            qlist.append(qid)
#    return qlist


def add_item_link(repo, wditem, prop, qcode):
    claim = pywikibot.Claim(repo, prop)
    target = pywikibot.ItemPage(repo, qcode) 
    claim.setTarget(target)
    wditem.addClaim(claim)#, summary='Adding 1 claim')

def add_item_value(repo, wditem, prop, value):
    claim = pywikibot.Claim(repo, prop)
    claim.setTarget(value)
    wditem.addClaim(claim)#, summary='Adding 1 claim')

# book edition: painos, laitos tai käännös
# todo: use data from record instead from commandline
def create_book_edition(repo, parent_id, commands):

    if ("isbn13" not in commands
        and "isbn10" not in commands
        and "publisher" not in commands):
        return None

    print('Adding edition...')

    book_title = commands["title"]
    data = {"labels": {"fi": book_title}
    #"descriptions": {"en": album_desc_en, "sv": album_desc_sv, "fr": album_desc_fr}
    }

    #create item
    newitem = pywikibot.ItemPage(repo)
    newitem.editEntity(data, summary=u'Edited item: set labels')

    newitem.get()

    # instance of
    if not 'P31' in newitem.claims:
        print("Adding claim: instance of edition")
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, 'Q3331189') # painos, laitos tai käännös
        claim.setTarget(target)
        newitem.addClaim(claim)#, summary='Adding 1 claim')

    # painos tai käännös kohteesta (P629)
    if not 'P629' in newitem.claims:
        print("Adding claim: edition of work")
        claim = pywikibot.Claim(repo, 'P629')
        target = pywikibot.ItemPage(repo, parent_id) # parent item
        claim.setTarget(target)
        newitem.addClaim(claim)#, summary='Adding 1 claim')

    # julkaisija
    if not 'P123' in newitem.claims:
        pub_qcode = getpublisherqcode(commands)
        if (pub_qcode != ""):
            
            print("Adding claim: publisher")
            add_item_link(repo, newitem, 'P123', pub_qcode)

    # publication date (date formatting?)
    if not 'P577' in newitem.claims:
        if "release" in commands:
            released = commands["release"]

            # only year now
            wbdate = getwbdate(int(released))
            
            print("Adding claim: released in")
            claim = pywikibot.Claim(repo, 'P577')
            claim.setTarget(wbdate)
            newitem.addClaim(claim)#, summary='Adding 1 claim')

    # kieli
    if not 'P407' in wditem.claims:
        langqcode = getlanguageqcode(commands)
        if (langqcode != ""):
        
            print("Adding claim: language")
            add_item_link(repo, wditem, 'P407', langqcode)

    # isbn
    if not 'P212' in newitem.claims:
        if "isbn13" in commands:
            isbn = commands["isbn13"]
            
            print("Adding claim: isbn 13")
            add_item_value(repo, newitem, 'P212', isbn)

    if not 'P957' in newitem.claims:
        if "isbn10" in commands:
            isbn = commands["isbn10"]
            
            print("Adding claim: isbn 10")
            add_item_value(repo, newitem, 'P957', isbn)

    return newitem

# todo: use data from record instead from commandline
def add_book_properties(repo, wditem, commands):

    # finna id
    if not 'P9478' in wditem.claims:
        if "finnaid" in commands:
            finnaid = commands["finnaid"]
            
            print("Adding claim: finna id")
            add_item_value(repo, wditem, 'P9478', finnaid)

    # kirjoittaja (kirja)
    if not 'P50' in wditem.claims:
        writer_qcode = getwriterqcode(commands)
        if (writer_qcode != ""):
            
            print("Adding claim: writer")
            add_item_link(repo, wditem, 'P50', writer_qcode)

    # publication date (date formatting?)
    if not 'P577' in wditem.claims:
        if "release" in commands:
            released = commands["release"]

            # only year now
            wbdate = getwbdate(int(released))
            
            print("Adding claim: released in")
            claim = pywikibot.Claim(repo, 'P577')
            claim.setTarget(wbdate)
            wditem.addClaim(claim)#, summary='Adding 1 claim')

    # teoksen tyyppi
    if not 'P7937' in wditem.claims:
        typeqcode = getworktypecode(commands)
        if (typeqcode != ""):
        
            print("Adding claim: work type")
            add_item_link(repo, wditem, 'P7937', typeqcode)
            
    # alkuperämaa
    if not 'P495' in wditem.claims:
        countryqcode = getcountryqcode(commands)
        if (countryqcode != ""):
        
            print("Adding claim: country of origin")
            add_item_link(repo, wditem, 'P495', countryqcode)

    # genre
    if not 'P136' in wditem.claims:
        genreqcode = getgenreqcode(commands)
        if (genreqcode != ""):
        
            print("Adding claim: genre")
            add_item_link(repo, wditem, 'P136', genreqcode)

    # kieli
    if not 'P407' in wditem.claims:
        langqcode = getlanguageqcode(commands)
        if (langqcode != ""):
        
            print("Adding claim: language")
            add_item_link(repo, wditem, 'P407', langqcode)

def create_literary_work(repo, commands):

    book_title = commands["title"]
    
    #desc_en = "book by " + writerlabel
    #desc_fi = writerlabel + " kirja"
    #desc_sv = "album av " + writerlabel
    #desc_fr = "album de " + writerlabel

    # more accurate date? parse to year
    if "release" in commands:
        # only year for now
        year = int(commands["release"])
        #desc_en = str(year) + " " + desc_en
    #    desc_fi = desc_fi + " vuodelta " + str(year)
        #desc_sv = desc_sv + " från " + str(year)
        #desc_fr = desc_fr + " sorti en " + str(year)
    
    data = {"labels": {"fi": book_title}
    #"descriptions": {"en": album_desc_en, "sv": album_desc_sv, "fr": album_desc_fr}
    }


    print('Adding literary work...')

    #create item
    newitem = pywikibot.ItemPage(repo)
    newitem.editEntity(data, summary=u'Edited item: set labels')

    newitem.get()

    # instance of
    if not 'P31' in newitem.claims:
        print("Adding claim: instance of book")
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, 'Q7725634') # literary work
        claim.setTarget(target)
        newitem.addClaim(claim)#, summary='Adding 1 claim')
        
    return newitem

    

# writer names can be aliases often..
#def check_writer(repo, commands, lang='fi'):
    #artistqcode = getartistqcode(commands["writer"])
    #artistitem = getitembyqcode(repo, artistqcode)
    #artistlabel = getlabelbylangfromitem(artistitem, lang)
    #if (artistlabel == commands["artist"]):
    #    print("ok, artist name and label in wikidata match", artistlabel)
    #    return artistlabel
    #print("WARN: given artist name and label in wikidata do not match", artistlabel)
    #return ""


# there is no easy way to do this: album by same name can exist for different artists
# and labels might not exist for all languages
def check_if_book_exists(repo, commands):
    book_name = commands["title"]
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


def add_book(commands, finnarecord = None):

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()
    
    # just check given parameter makes sense
    #artistlabel = check_artist(repo, commands)
    #if (artistlabel == ""):
    #    return None
    #writerlabel = commands["writer"]
    
    if (check_if_book_exists(repo, commands) == True):
        print('Book exists, skipping')
        return None

    print('Creating a new book item')

    # TODO: skip this if all we want is edition?
    newitem = create_literary_work(repo, commands)

    print('Adding properties...')

    # generic properties
    add_book_properties(repo, newitem, commands)

    # other edition related properties (new item)
    edition = create_book_edition(repo, newitem.getID(), commands)

    # link back:
    # painos tai käännös (P747)
    if not 'P747' in newitem.claims and edition != None:
        
        print("Adding claim: edition id")
        add_item_link(repo, newitem, 'P747', edition.getID())

    nid = newitem.getID()
    print('All done', nid)
    return nid


def add_book_from_finna(finnaid):
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

    if (fr.isbook() == False):
        print("Not as supported book record with id:", fr.finnaid)
        return None
    
    fr.parseFullRecord()
    
    #wdsite = pywikibot.Site('wikidata', 'wikidata')
    #wdsite.login()
    #repo = wdsite.data_repository()

    #add_book(commands, fr):


# TODO: may have multiple writers, genres etc.

support_args = ["title",
                "writer",
                "genre",
                "finnaid",
                "release",
                "worktype",
                "publisher",
                "country",
                "language",
                "isbn13",
                "isbn10"]

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
            
        if (key == "writer"):
            if (getwriterqcode(commands) == ""):
                print("WARN: no qcode for writer", commands["writer"])
                exit()
        if (key == "publisher"):
            if (getpublisherqcode(commands) == ""):
                print("WARN: no qcode for publisher", commands["publisher"])
                exit()
        if (key == "worktype"):
            if (getworktypeqcode(commands) == ""):
                print("WARN: no qcode for worktype", commands["worktype"])
                exit()
        if (key == "genre"):
            if (getgenreqcode(commands) == ""):
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

    if "finnaid" not in commands:
        confirmation = pywikibot.input_choice(
            "Do you want to continue with the edits?",
            [('Yes', 'y'), ('No', 'n')],
            default='n'
        )

        if confirmation == 'n':
            print("Operation cancelled.")
            exit()

        
        add_book(commands)
        print("all done")
    else:
        
        # TODO: parse and print some kind of preview of what will be added

        add_book_from_finna(commands["finnaid"])
        print("all done")


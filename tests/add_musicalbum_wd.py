# Script creates wikidata item for a music album.
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

import xml.etree.ElementTree as XEltree

def endswith(text, char):
    if (len(text) < 1):
        return False
    ch = text[len(text)-1]
    if (ch == char):
        return True
    return False

def removelastchar(text):
    if (len(text) > 0):
        return text[:len(text)-1]
    return text

def endswithcommaordot(text):
    if (len(text) < 1):
        return False
    ch = text[len(text)-1]
    if (ch == ","):
        return True
    if (ch == "."):
        return True
    return False

def isinbrackets(text):
    if (text[0] == '[' and text[len(text)-1] == ']'):
        return True
    return False

# cleanup if string starts and ends with brackets,
# location name might be in brackets
def removefirstlastbracket(text):
    if (text[0] == '[' and text[len(text)-1] == ']'):
        return text[1:len(text)-1]
    
    # otherwise do nothing
    return text

def addtolist(dest, s):
    if (s == None):
        return
    if (len(s) == 0):
        return
    # throw up exception, python does not catch this otherwise
    if (dest == s):
        exit()
    if s in dest:
        return
    dest.append(s)

def additemtolist(dest, item):
    if item in dest:
        return
    dest.append(item)

# cleanup and normalize information to plain list without duplicates
def cleanupaddtolist(dest, source):
    if isinstance(source, list):
        for l in source:
            l = l.strip()
            addtolist(dest, l) 
        
    else:
        source = source.strip()
        addtolist(dest, source) 

# class FinnaRecord

class FinnaRecord:
    def __init__(self):
        self.finnaid = "" # id used in query
        self.sourceref = None # url of metapage
        self.finnarecord = None # json data
        
        self.albumtitle = None
        self.artistname = list()
        self.publishernames = list() # must find from xml
        self.publishingplaces = list()# must find from xml
        self.labelnames = list() # must find from xml
        self.genres = list()# must find from xml
        #self.releaseyear = None
        self.languagecode = None
        self.origlangcode = None
        self.duration = None
        self.location = list() # luontipaikka
        self.locationyso = list() # luontipaikka, yso-identifier (just number)
        self.recordedat = list() # äänitysstudio?
        self.recordingplace = list() # äänityspaikka
        
        self.catalogidentifiers = list() # catalog identifiers
        
        self.compilation = False
        
        # these are pretty self-explanatory..
        self.presenterasteri = list() # esittäjän asteri-id
        self.producerasteri = list() # tuottajan asteri-id

        # these are not used per-album but by per-track in wikidata?
        self.arrangerasteri = list() # sovittaja
        self.composerasteri = list() # säveltäjä
        
        # distribution formats, CD, LP..
        # we can only get this per each item,
        # for other formats we would need different finna items
        self.releaseformat = list()
        
        
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
        # 1/Sound/SoundDisc/ or "Äänilevy" -> LP-levy ?
        # 1 äänilevy
        if (f_pd == "1 CD-äänilevy"):
            return True
        return False

    # note: only use the result for explicit marking,
    # tag might be missing or different formats etc.
    def issingle(self):
        records = self.finnarecord['records'][0]

        # parse subjects for "singlet."
        # might have different tags as well, see what comes up..

        if "subjects" not in records:
            return False
        
        f_sub = records['subjects']
        for sub in f_sub:
            for s in sub:
                ff_value = s.strip()
                if (ff_value == "singlet."):
                    return True

        return False
        
    def iscompilation(self):
        records = self.finnarecord['records'][0]

        # parse subjects for "kokoelmat."
        # might have different tags as well, see what comes up..
        
        if (self.compilation == True):
            return True

        if "subjects" not in records:
            return False
        
        f_sub = records['subjects']
        for sub in f_sub:
            for s in sub:
                ff_value = s.strip()
                if (ff_value == "kokoelmat."):
                    return True

        return False

    def parsepresenters(self):
        
        records = self.finnarecord['records'][0]
        if "presenters" not in records:
            print("presenters does not exist in finna record", records)
            return False

        # this is weird, there is two levels of "presenters" in some cases?
        f_presenters = records['presenters']
        if "presenters" in f_presenters:
            f_presenters = f_presenters['presenters']
        
        for pres in f_presenters:

            print("DEBUG: pres", pres)

            # might not have some fields in all cases
            ff_name = ""
            ff_date = ""
            ff_role = ""
            ff_id = ""
            asteri = ""

            if "name" in pres:
                ff_name = pres['name'].strip()
            if "date" in pres:
                # if range -> split
                # otherwise just plain number
                ff_date = pres['date'].strip() # syntymävuosi? "1972-",
            if "role" in pres:
                # may have combinations ("sanoittaja, säveltäjä") or one ("esittäjä")
                # -> should normalize into proper list
                # -> find qid for roles
                ff_role = pres["role"].strip()
            if "id" in pres:
                # plain number or asteri-prefix?
                # -> normalize
                ff_id = pres["id"].strip()
                if (ff_id.find("(FI-ASTERI-N)") >= 0):
                    asteri = ff_id.replace("(FI-ASTERI-N)", "")

            # "esittäjä" for now, should parse combinations too
            if (len(asteri) > 0 and ff_role == "esittäjä"):
                print("DEBUG: found presenter with asteri", asteri)
                cleanupaddtolist(self.presenterasteri, asteri)
             
            # finna might have names as "lastname, firstname", "band (yhtye)"
            # or "name (birthday-)" format so further parsing might be needed
            # before used in wd lookups..
            #if (len(ff_name) > 0 and ff_role == "esittäjä"):
            #    cleanupaddtolist(self.artistname, ff_name)
        
        return True

    def parsenonpresenterauthors(self):
        # may have band name with "type": "Corporate Name"
        # may have band member name with "type": "Personal Name"
        # may have "role": sovittaja, tuottaja..
        # may have person id "id": "000103392", - kanto id? or asteri: "(FI-ASTERI-N)000187459",
        
        records = self.finnarecord['records'][0]
        
        if "nonPresenterAuthors" not in records:
            print("nonPresenterAuthors does not exist in finna record")
            return False
        
        f_npauthors = records['nonPresenterAuthors']
        for npa in f_npauthors:

            print("DEBUG: npa", npa)
            
            # might not have some fields in all cases
            ff_name = ""
            ff_date = ""
            ff_role = ""
            ff_id = ""
            ff_type = ""
            asteri = ""

            if "name" in npa:
                ff_name = npa['name'].strip()
            if "date" in npa:
                # if range -> split
                # otherwise just plain number
                ff_date = npa['date'].strip() # syntymävuosi? "1972-",
            if "role" in npa:
                # may have combinations ("sanoittaja, säveltäjä") or one ("tuottaja")
                # -> should normalize into proper list
                # -> find qid for roles
                ff_role = npa["role"].strip()
            if "id" in npa:
                # plain number or asteri-prefix?
                # -> normalize
                ff_id = npa["id"].strip()
                if (ff_id.find("(FI-ASTERI-N)") >= 0):
                    asteri = ff_id.replace("(FI-ASTERI-N)", "")
                #else: # plain number -> assume asteri-id ?
            if "type" in npa:
                # person or corporate -> make into enum
                ff_type = npa["type"].strip() # "Personanl name"

            # "tuottaja" or "tuottaja (ekspressio)" or "tuottaja, esittäjä"..
            # let's only use explicit for per-album cases for now
            if (len(asteri) > 0 and ff_role == "tuottaja"):
                print("DEBUG: found producer with asteri", asteri)
                cleanupaddtolist(self.producerasteri, asteri)

            # wikidata only has this per-track instead of per-album?
            if (len(asteri) > 0 and ff_role == "säveltäjä"):
                print("DEBUG: found composer with asteri", asteri)
                cleanupaddtolist(self.composerasteri, asteri)

            # wikidata only has this per-track instead of per-album?
            if (len(asteri) > 0 and ff_role == "sovittaja"):
                print("DEBUG: found arranger with asteri", asteri)
                cleanupaddtolist(self.arrangerasteri, asteri)

        
        #print("DEBUG: ", )
        return True


    # note: this might have nonsense like "zxx" in some cases
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
            dind1 = df.get("ind1") # not sure what the values here are..
            dind2 = df.get("ind2") # not sure what the values here are..
            
            #print("tag,", dftag, "ind1", dind1, "ind2", dind2)

            # subfield and attributes
            #subfields = df.findall("subfield")
            subfields = df.iter("{http://www.loc.gov/MARC21/slim}subfield")
            for sf in subfields:
                sfcode = sf.get("code")
                sftext = sf.text

                print("tag,", dftag, "ind1", dind1, "ind2", dind2, "code,", sfcode, "text", sftext)
                
                # if dftag == 110, ind1 == 2, ind2 == " " and sfcode == a -> artist name 
                # if dftag == 110, ind1 == 2, ind2 == " " and sfcode == e -> "esittäjä"

                # if dftag == 245, ind1 == 1, ind2 == 0 and sfcode == a -> album name 
                # if dftag == 245, ind1 == 1, ind2 == 0 and sfcode == c -> artist name 

                # <datafield tag="260" ind1=" " ind2=" "><subfield code="a">[Tampere] :</subfield><subfield code="b">Poko Records,</subfield><subfield code="c">℗ 1992.</subfield>
                # -> publisher, copyright, release
                # <datafield tag="260" ind1=" " ind2=" "><subfield code="a">[Helsinki] :</subfield><subfield code="b">Texicalli Records,</subfield><subfield code="c">[℗ 2003]</subfield></datafield>
                # <datafield tag="260" ind1=" " ind2=" "><subfield code="a">London :</subfield><subfield code="b">Century Media Records,</subfield><subfield code="c">p2012.</subfield>

                if (dftag == "260" and dind1 == " " and dind2 == " " and sfcode == "a"): # -> publisher location
                    # parse: if there is city/country in bracket remove brackets?
                    tmptext = sftext
                    if (endswith(tmptext, ":") == True or endswith(tmptext, ";") == True):
                        tmptext = removelastchar(tmptext)
                        tmptext = tmptext.strip()

                    if (isinbrackets(tmptext) == True):
                        tmptext = removefirstlastbracket(tmptext)
                    
                    # cleanup, don't add duplicates
                    cleanupaddtolist(self.publishingplaces, tmptext)

                if (dftag == "260" and dind1 == " " and dind2 == " " and sfcode == "b"): # -> publisher name 
                    
                    # if this is found, don't add from other similar tags to avoid duplicates?

                    tmptext = sftext
                    # check for ; as well?
                    if (endswith(tmptext, ",") == True):
                        tmptext = removelastchar(tmptext)
                        tmptext = tmptext.strip()

                    if (isinbrackets(tmptext) == True):
                        tmptext = removefirstlastbracket(tmptext)
                    
                    # cleanup, don't add duplicates
                    cleanupaddtolist(self.publishernames, tmptext)

                if (dftag == "260" and dind1 == " " and dind2 == " " and sfcode == "c"): # -> publishing year

                    tmptext = sftext
                    if (isinbrackets(tmptext) == True):
                        tmptext = removefirstlastbracket(tmptext)
                    # also remove other characters if anything besides a year (copyright mark or such)
                    #self.year = tmptext
                
                # <datafield tag="264" ind1=" " ind2="1"><subfield code="a">[Kustannuspaikka tuntematon] :</subfield><subfield code="b">Ekvapoint Oy,</subfield><subfield code="c">[2017]</subfield>
                # <datafield tag="264" ind1=" " ind2="1"><subfield code="a">[Espoo] :</subfield><subfield code="b">Ranka Kustannus,</subfield><subfield code="c">[2025]</subfield>
                if (dftag == "264" and dind1 == " " and dind2 == "1" and sfcode == "a"): # -> publishing place name 

                    tmptext = sftext
                    # check for ; as well?
                    if (endswith(tmptext, ",") == True or endswith(tmptext, ":") == True):
                        tmptext = removelastchar(tmptext)
                        tmptext = tmptext.strip()
                    
                    # cleanup, don't add duplicates
                    cleanupaddtolist(self.publishingplaces, tmptext)
                        
                if (dftag == "264" and dind1 == " " and dind2 == "1" and sfcode == "b"): # -> publisher name 

                    tmptext = sftext
                    # check for ; as well?
                    if (endswith(tmptext, ",") == True):
                        tmptext = removelastchar(tmptext)
                        tmptext = tmptext.strip()
                    
                    # cleanup, don't add duplicates
                    cleanupaddtolist(self.publishernames, tmptext)

                # if dftag == 264, ind1 == " ", ind2 == 1 and sfcode == c -> year 

                # if dftag == 264, ind1 == " ", ind2 == 4 and sfcode == c -> year 

                # decade.. not useful if we get year (which we want)
                # <datafield tag="388" ind1="1" ind2=" "><subfield code="a">2020-luku</subfield><subfield code="2">yso/fin</subfield><subfield code="0">http://www.yso.fi/onto/yso/p6202062029</subfield></datafield>

                # <datafield tag="028" ind1="0" ind2="1"><subfield code="b">New Music Community</subfield><subfield code="a">NMC-001</subfield>
                if (dftag == "028" and dind1 == "0" and dind2 == "1" and sfcode == "b"): # -> publisher name 
                    # this might be "brand" instead of actual publishing entity? try to use more accurate
                    # cleanup, don't add duplicates
                    cleanupaddtolist(self.labelnames, sftext)

                # <datafield tag="028" ind1="0" ind2="1"><subfield code="b">Poko</subfield><subfield code="a">PÄLP132</subfield></datafield>
                if (dftag == "028" and dind1 == "0" and dind2 == "1" and sfcode == "a"): # -> catalog identifier
                    cleanupaddtolist(self.catalogidentifiers, sftext)

                # <datafield tag="370" ind1=" " ind2=" "><subfield code="g">Suomi</subfield><subfield code="2">yso/fin</subfield><subfield code="0">http://www.yso.fi/onto/yso/p94426</subfield></datafield>
                # <datafield tag="370" ind1=" " ind2=" "><subfield code="g">Suomi</subfield> 
                if (dftag == "370" and dind1 == " " and dind2 == " " and sfcode == "g"): # -> luontipaikka
                    # cleanup, don't add duplicates
                    cleanupaddtolist(self.location, sftext)
                if (dftag == "370" and dind1 == " " and dind2 == " " and sfcode == "0"): # -> luontipaikka
                    # yso-url -> strip to plain identifier for search
                    tmptext = sftext
                    if (tmptext.find("yso.fi/onto") > 0):
                        tmptext = tmptext.replace("http://www.yso.fi/onto/yso/p", "")
                        tmptext = tmptext.replace("/", "")
                    cleanupaddtolist(self.locationyso, tmptext)
                    
                # <datafield tag="518" ind1=" " ind2=" "><subfield code="o">Äänitys:</subfield><subfield code="p">[Helsinki], Finnvox Studiot.</subfield><
                if (dftag == "518" and dind1 == " " and dind2 == " " and sfcode == "p"): # -> äänityspaikka
                    # parse: if there is city/country in bracket remove that?
                    # we would want the studio name only?

                    tmptext = sftext
                    icomma = tmptext.find(",")
                    if (icomma > 1):
                        recplace = tmptext[:icomma]
                        if (isinbrackets(recplace) == True):
                            recplace = removefirstlastbracket(recplace)
                        # cleanup, don't add duplicates
                        cleanupaddtolist(self.recordingplace, recplace)
                        tmptext = tmptext[icomma+1:]
                    
                    if (endswithcommaordot(tmptext) == True):
                        tmptext = removelastchar(tmptext)
                        tmptext = tmptext.strip()

                    # cleanup, don't add duplicates
                    cleanupaddtolist(self.recordedat, tmptext)

                 
                # <datafield tag="655" ind1=" " ind2="7"><subfield code="8">2\\u</subfield><subfield code="a">doom metal</subfield>
                # <datafield tag="655" ind1=" " ind2="7"><subfield code="a">popmusiikki</subfield>
                # <datafield tag="655" ind1=" " ind2="7"><subfield code="a">kokoomateokset
                # tag, 655 ind1   ind2 7 code, a text jazz
                if (dftag == "655" and dind1 == " " and dind2 == "7" and sfcode == "a"): # -> genre
                    if (sftext == "kokoomateokset"):
                        self.compilation = True
                    
                    # cleanup, don't add duplicates
                    cleanupaddtolist(self.genres, sftext)
               
                # kesto
                #<datafield tag="306" ind1=" " ind2=" "><subfield code="a">000349</subfield> # -> kesto 3'49
                #<datafield tag="306" ind1=" " ind2=" "><subfield code="a">000302</subfield> # -> kesto 3'02
                if (dftag == "306" and dind1 == " " and dind2 == " " and sfcode == "a"): #
                    strduration = sftext
                    if (len(sftext) == 6):
                        strhour = sftext[0:2]
                        strmin = sftext[2:4]
                        strsec = sftext[4:6]
                        print("found duration: ", strhour ,":", strmin, ":", strsec)
                        ihour = int(strhour)
                        imin = int(strmin)
                        isec = int(strsec)
                        isec += imin * 60
                        isec += ihour * 60 * 60
                        self.duration = str(isec)

                # <datafield tag="300" ind1=" " ind2=" "><subfield code="a">1 C-kasetti (00\'00)</subfield>
                if (dftag == "300" and dind1 == " " and dind2 == " " and sfcode == "a"): #
                    if (sftext.find("C-kasetti") > 0):
                        cleanupaddtolist(self.releaseformat, "C-kasetti")
                    if (sftext.find("CD-äänilevy") > 0):
                        cleanupaddtolist(self.releaseformat, "CD-äänilevy")


        print("parsed fields in xml record")
        return True

# / class FinnaRecord

# final parameters to push into wikidata:
# after parsing finna data and finding qcodes
class FinalParams:
    def __init__(self):
        self.artists = list() #dict() # name<-> qcode
        self.publishers = list() #dict() # name<-> qcode
        self.places = list() #dict() # name<-> qcode
        self.genres = list() #dict() # name<-> qcode
        self.languages = list() #dict() # name<-> qcode
        #self.countries = list() #dict() # name<-> qcode
        self.location = list()
        #self.arrangers = list() # not album but track specific?
        #self.composers = list() # not album but track specific?
        self.producers = list() # this has been used per album
        self.year = ""
        self.albumtitle = ""
        self.sourceurl = ""
        self.releasetype = "" # studio/live.. compilation?
        self.duration = ""

        # recording studio
        self.recordedat = list() #dict() # name<-> qcode
        
        # list of release formats is not readily available
        # as library information is per item
        self.releaseformat = list() # CD/LP/DVD..

        self.catalogidentifiers = list() # catalog identifiers

        self.issingle = False
        self.instancetype = ''

# / class FinalParams

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
    url += finna_api_parameter('field[]', 'presenters')
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

# in case query gives wikidata link instead of plain qcode
# -> parse to plain qcode
def parseqcodefromwikidatalink(text):

    # should have "entity/Q.."
    # should not have "entity/statement/Q.."

    ilast = text.rfind("/", 0, len(text)-1)
    if (ilast < 0):
        return text
    return text[ilast+1:]

# check that qcode seems valid
def isQcode(qcode):
    if (qcode == None):
        return False
    
    # must have at least Q and numbers
    if (len(qcode) < 2):
        return False
    ch = qcode[0]
    if (ch != "Q"):
        return False
    
    # uuid instead of plain qcode?
    if (qcode.find("-") > 0):
        return False

    # does it look like valid integer as well?
    qnum = qcode[1:]
    inum = int(qnum)
    if (inum < 1):
        return False
    return True

def escapesinglequote(s):
    return s.replace("'", "''")


# list qcodes only where it is linking
def getQcodesFromProperty(item, prop):
    qlist = list()
    
    propclaims = item.claims.get(prop, [])
    #propclaims = item.claims[prop]
    for claim in propclaims:
        qid = claim.getTarget().id
        if (qid not in qlist):
            qlist.append(qid)
    return qlist


def isDisambiguation(item):

    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        if (claim.getTarget().id == 'Q4167410'):
            #print("target is disambiguation page")
            return True
        
    return False

def getitembyqcode(repo, itemqcode):
    if (itemqcode == None or itemqcode == ""):
        print("no qcode for item")
        return None
    if (isQcode(itemqcode) == False):
        print("not a valid qcode")
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

def getlabelbyanylangfromitem(item, langs):

    for li in item.labels:
        label = item.labels[li]
        if li in langs:
            print("DEBUG: found label for ", item.getID() ," in lang ", li ,": ", label)
            return label
    return None

def getaliasesbylangfromitem(item, lang):

    # note: this can have multiple values, not just one like normal label
    for li in item.aliases:
        alabels = item.aliases[li]
        if (li == lang):
            #print("DEBUG: found label alias for ", item.getID() ," in lang ", lang ,": ", label)
            return alabels
    return None

# get labels (names) of entities in given property of given item
def getlabelofpropbylangfromitem(repo, item, prop, lang):

    qlist = list()
    
    propclaims = item.claims.get(prop, [])
    for claim in propclaims:
        qid = claim.getTarget().id
        propitem = getitembyqcode(repo, qid)
        if (propitem != None):
            lbls = getlabelbylangfromitem(propitem, lang)
            if (lbls != None):
                for l in lbls:
                    addtolist(qlist, qlist)
    return qlist

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

#def runSparqlQuery(repo, query):

def makeSparqlQuery(text, withabout=False, withschema=True, searchaltlabel=False, lang='fi', instanceof=None):

    # TODO: filter by instance of music style etc. in query, 
    # needs both property and qcodes..
    
    # this query might work for partial labels..
    #query = 'SELECT ?item ?itemLabel'
    #query += ' WHERE {'
    #query += ' ?item rdfs:label ?itemLabel.'
    #query += ' FILTER(CONTAINS(LCASE(?itemLabel), "' + genre + '"@' + lang +')).'
    #query += ' } limit 10'

    # TODO: also add instance of in results to simiplify further parsing?

    #query = 'SELECT distinct ?item ?itemLabel ?itemDescription WHERE {'
    query = ''
    if (searchaltlabel == False):
        query = 'SELECT distinct ?item ?itemLabel WHERE {'
        query += ' ?item ?label "'+ text +'"@' + lang + '.' 
    else:
        query = 'SELECT distinct ?item ?itemLabel ?itemAltLabel WHERE {'
        query += ' ?item ?altLabel "'+ text +'"@' + lang + '.' 

    # limit by instance whenever possible:
    # sometimes there are too many or unpredictable qcodes to use this..
    if (instanceof != None):
        query += ' ?item wdt:P31 wd:' + instanceof + ' .'

    # else: # return found instance (also add into select-part)
    # if we use this we would get two rows when there's two instances of in item..
    #query += ' ?item wdt:P31 ?instanceOf.'

    if (withabout == True):
        # without this query may timeout or result in error sometimes..
        # but might need to remove this sometimes to get any results,
        # also could be needed to filter out some other odd things..
        query += ' ?article schema:about ?item .' 
    
    if (withschema == True):
        # note: having this schema in query sometimes makes it impossible to find record labels for some reason
        query += ' ?article schema:inLanguage "' + lang + '" .' # note part of below
    
    #query += ' ?article schema:isPartOf <https://' + lang + '.wikipedia.org/>.' # not useful if there is no article in wikipedia?
    query += ' SERVICE wikibase:label { bd:serviceParam wikibase:language "' + lang + '". } }'

    return query

# note that while finna might give items in finnish, also swedish and english are possible..
# and if other sources are queried those might be in english.
# some items in wikidata might not have finnish label, but might have in "mul" or english, or vice versa..
def searchItembySparql(repo, text, withabout=False, withschema=True, searchaltlabel=False, lang='fi', instanceof=None):

    print("DEBUG: searching item with label: ", text)

    endpoint = 'https://query.wikidata.org/sparql'
    entity_url = 'https://www.wikidata.org/entity/' # must be provided when endpoint is given
    
    # TODO: filter by instance of music style etc. in query, 
    # needs both property and qcodes..
    
    query = makeSparqlQuery(text, withabout, withschema, searchaltlabel, lang, instanceof)
    

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

    # TODO:
    # might have multiple publishers for example,
    # add something like instance of to separate record label and record company (where it might matter)
    # -> store tuple instead of plain qcode?
    qcodes = list()

    # in case of multiple entries and multiple rows, don't check same again
    rejectedqcodes = list()

    accepteditems = list()

    for row in data:
        print("DEBUG: row:", row)
        page_id = str(row['item'])
        
        #page_instance = str(row['instanceOf'])
        
        # error: page_id is a link, not just qcode..
        # Http://www.wikidata.org/entity/Q484179
        # -> strip it
        itemqcode = parseqcodefromwikidatalink(page_id)
        if (isQcode(itemqcode) == False):
            # sometimes there is article url instead of qcode, verify
            print("not a valid qcode: ", itemqcode)
            continue

        print("DEBUG: page id:", page_id , " qcode:", itemqcode)

        # queries can give duplicates if items have multiple instances of
        # or alternative labels (depending on query) -> skip check if we already accepted same qcode
        if itemqcode in qcodes:
            continue
        if itemqcode in rejectedqcodes:
            # already rejected, duplicate row?
            continue
        
        # check: in some cases it is not in wd:qcode format but might have page link
        # like <https://fi.wikipedia.org/wiki/Universal_Music_Group>
        # this can be filtered out with schema:about row, 
        # but we can't locate some wikidata entries if that is applied for some reason..
        # so anyway, double-check regardless of whatever we use and skip if not valid qcode

        # should not give redirects but filter those out if any
        item = getitembyqcode(repo, itemqcode)
        if (item == None):
            # invalid qcode?
            #print("DEBUG: invalid qcode ", itemqcode, " or other error?")
            addtolist(rejectedqcodes, itemqcode)
            continue

        # disambiguation should not be used as targets
        if (isDisambiguation(item) == True):
            #print("DEBUG: item ", page_id, " is for disambiguation only")
            addtolist(rejectedqcodes, itemqcode)
            continue

        page_label = str(row['itemLabel'])
        # check: not in every query
        #page_altlabel = str(row['itemAltLabel'])
        print("DEBUG: id:", page_id, "label:", page_label)
        
        #lbl = getlabelbylangfromitem(item, lang)
        #if (lbl == None):
            # no label in this language?
        #    print("no label in language: ", lang)
        #    continue
        #if (lbl != page_label):
        #    print("WARN: id", page_id, "label", page_label, "differs from item", lbl)
        

        # TODO: comparison this way is bugged: 
        # 'itemLabel': Vallila Music House@fi does not match search Vallila Music House
        # -> strip()/trim() ?
        # also upper/lower-case might not match in some cases

        # TODO: compare with alternate label(s) if there are multiple
        # might have difference in upper/lower case in some cases? (Of, And..)
        #if (lbl != text and lbl.lower() != text.lower()):
        #if (page_label.strip() != text.strip() and searchaltlabel == False):
            # not correct label for some reason
        #    print("label does not match search: ", page_label)
        #    continue

        # we would want to verify item is instance of correct type:
        # query may give anything at any type currently.
        # problem is that there may be many sub-types 
        # so filtering in query by instances might need a long list.
        # another issue is that data can be simply broken for some reason, so avoid using those.

        #print("using qid", itemqcode)
        # avoid duplicates
        addtolist(qcodes, itemqcode)
        
        additemtolist(accepteditems, item)
        
        # should use qcode to name pair directly? map<> alternative?
        # if we fetch more information in same query we can get douple entries
        # due to multiple instances of and such, need to handle those as well.
        # instead, keep the item instance itself?
        #addtolist(qcodes, tuple((itemqcode, page_label)))

    if (len(accepteditems) == 0):
        print("did not find item for:", text)
    return accepteditems


# search by value in property instead of text in label:
# should be string or integer without language specific label(s)
def searchbySparqlPropValue(repo, propnum, pval):

    print("DEBUG: searching item with property ", propnum ," value: ", pval)

    endpoint = 'https://query.wikidata.org/sparql'
    entity_url = 'https://www.wikidata.org/entity/' # must be provided when endpoint is given
    
    query = 'SELECT ?item WHERE {'
    query += ' ?item wdt:'+ propnum + ' "' + pval + '" }'
    #query += ' }'

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

    qcodes = list()

    accepteditems = list()

    for row in data:
        print("DEBUG: row:", row)
        page_id = str(row['item'])
        
        # error: page_id is a link, not just qcode..
        # Http://www.wikidata.org/entity/Q484179
        # -> strip it
        itemqcode = parseqcodefromwikidatalink(page_id)
        if (isQcode(itemqcode) == False):
            print("not a valid qcode: ", itemqcode)
            continue

        item = getitembyqcode(repo, itemqcode)
        if (item == None):
            continue
        
        # a given property should be used on disambiguation pages?
        if (isDisambiguation(item) == True):
            continue
        
        #print("using qid", itemqcode)
        addtolist(qcodes, itemqcode)

        additemtolist(accepteditems, item)

    if (len(accepteditems) == 0):
        print("did not find item for:", pval)
    return accepteditems
    

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

# pywikibot/wikidata expects specific type
def getwbquantity(repo, amount, unit):
    
    # needs unit item so find it by qid
    unititem = pywikibot.ItemPage(repo, unit) 
    
    # pywikibot.WbQuantity(amount, unit=None, error=None, site=None)
    return pywikibot.WbQuantity(amount, unit=unititem)

def checkproperties(repo, itemqcode):
    if (len(itemqcode) == 0):
        return False

    itemfound = pywikibot.ItemPage(repo, itemqcode)
    if (itemfound.isRedirectPage() == True):
        return False
    
    dictionary = itemfound.get()

    return True


# todo: read config for mapping
def gettypeqcode(releasetype):

    # mapping type to qcode
    d_typetoqcode = dict()
    d_typetoqcode["studioalbumi"] = "Q208569"
    d_typetoqcode["livealbumi"] = "Q209939"
    d_typetoqcode["kokoelma-albumi"] = "Q222910"
    d_typetoqcode["soundtrack-albumi"] = "Q4176708"

    if releasetype in d_typetoqcode:
        return d_typetoqcode[releasetype]
    return ""


def getdistributionqcode(dist):

    # for jakelumuoto (P437)
    # - CD-levy (Q34467)
    # - CD single englanti (Q719645)
    # - vinyylilevy (Q178588)
    # - 7 tuuman single (Q6128115)
    # - LP-levy (Q841983)
    # - C-kasetti (Q149757)
    # - digitaalinen jakelu (Q269415)
    # - musiikin lataus (Q6473564)
    # - musiikin suoratoisto (Q15982450)
    
    d_disttoqcode = dict()
    d_disttoqcode["CD-äänilevy"] = "Q34467" # CD-levy
    
    d_disttoqcode["LP-levy"] = "Q841983"
    #d_disttoqcode["äänilevy"] = "Q841983"
    d_disttoqcode["C-äänikasetti"] = "Q149757" # C-kasetti 

    if dist in d_disttoqcode:
        return d_disttoqcode[dist]
    return ""


def getprenseterroleqcode(prole):

    d_roletoqcode = dict()
    d_roletoqcode["sanoittaja"] = ""
    d_roletoqcode["säveltäjä"] = ""
    d_roletoqcode["sovittaja"] = ""
    d_roletoqcode["tuottaja"] = ""
    d_roletoqcode["esittäjä"] = ""

    if prole in d_roletoqcode:
        return d_roletoqcode[prole]
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
    d_langqcode["norja"] = "Q9043"
    d_langqcode["nor"] = "Q9043" # langcode
    d_langqcode["ranska"] = "Q150"
    d_langqcode["fra"] = "Q150" # langcode
    d_langqcode["espanja"] = "Q1321"
    d_langqcode["spa"] = "Q1321" # langcode
    d_langqcode["italia"] = "Q652"
    d_langqcode["ita"] = "Q652" # langcode
    d_langqcode["portugali"] = "Q5146"
    d_langqcode["por"] = "Q5146" # langcode

    
    # useita kieliä
    #d_langqcode["mul"] = "Q20923490"

    
    if lang in d_langqcode:
        return d_langqcode[lang]
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
        #muusikkoduo (Q9212979)
        if (qid == 'Q9212979'):
            return True
        # kansanmusiikkiyhtye (Q113292621)
        if (qid == 'Q113292621'):
            return True
        
    return False

def isAlbumItem(item):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:

        qid = claim.getTarget().id
        
        # musiikkialbumi (Q482994)
        if (qid == 'Q482994'):
            return True
        # EP-levy (Q169930)
        if (qid == 'Q169930'):
            return True
        # single (Q134556)
        if (qid == 'Q134556'):
            return True
        
    return False

# if entity is for a music genre
def isGenreItem(item):
    
    # TODO: may be subclass of ?
    
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:

        qid = claim.getTarget().id
        
        # musiikkityyli (Q188451)
        if (qid == 'Q188451'):
            return True

    subclass_of = item.claims.get('P279', [])
    for sc in subclass_of:

        qid = sc.getTarget().id
        
        # pohjoismainen kansanmusiikki (Q7050752)
        if (qid == 'Q7050752'):
            return True
        
    return False

def isRecordLabel(item):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:

        qid = claim.getTarget().id
        
        # levymerkki (Q18127)
        if (qid == 'Q18127'):
            return True

        # levy-yhtiö (Q2442401)
        if (qid == 'Q2442401'):
            return True
        
        # itsenäinen levymerkki (Q1542343)
        if (qid == 'Q1542343'):
            return True
        
        # musiikkituotantoyhtiö (Q58318936)
        if (qid == 'Q58318936'):
            return True
        
    return False

def isStudioItem(item):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:

        qid = claim.getTarget().id
        
        # äänitysstudio (Q746369)
        if (qid == 'Q746369'):
            return True
        
    return False

def getArtistsFromItem(item):
    qlist = list()
    part_of = item.claims.get('P282', [])
    for claim in part_of:
        # avoid duplicates, catch errors
        addtolist(qlist, claim.getTarget().id)
    return qlist

def add_item_link(repo, prop, qcode):
    claim = pywikibot.Claim(repo, prop)
    target = pywikibot.ItemPage(repo, qcode) 
    claim.setTarget(target)
    return claim

def add_item_value(repo, prop, value):
    claim = pywikibot.Claim(repo, prop)
    claim.setTarget(value)
    return claim

# qualifier needs a property type and value
def add_item_qualifier(repo, qprop, qtarget):

    q_claim = pywikibot.Claim(repo, qprop, is_reference=False, is_qualifier=True)
    q_claim.setTarget(qtarget)
    return q_claim

# todo: other possible parameters,
# also set date of access ?
def add_item_source_url(repo, sourceurl):
    
    if (sourceurl == ""):
        return None

    prop = 'P854' # source-url
   
    u_claim = pywikibot.Claim(repo, prop, is_reference=True, is_qualifier=False)
    u_claim.setTarget(sourceurl)
    return u_claim

    # todo: other sources to use? -> must have other related properties and qualifiers..




# todo: use data from record instead from commandline

# TODO: move parsing and finding qcodes to before starting this,
# 

def add_album_properties(repo, wditem, final):
    
    # instance of
    if not 'P31' in wditem.claims:
        
        print("Adding claim: instance of, ", final.instancetype)
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, final.instancetype)
        claim.setTarget(target)
        wditem.addClaim(claim)#, summary='Adding 1 claim')

    # esittäjä
    if not 'P175' in wditem.claims:
        
        # note: it might be possible there is more than one artist,
        # such as split-albums, so prepare for a list
        
        for artist_qcode in final.artists:
            
            print("Adding claim: artist", artist_qcode)
            artistclaim = add_item_link(repo, 'P175', artist_qcode)

            # add source if given
            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                artistclaim.addSource(srcclaim)

            wditem.addClaim(artistclaim)#, summary='Adding 1 claim')
            

    # TODO: members of a band in specific album
    # just presenters? role for instrument?

    #existingproducerqcodes = getQcodesFromProperty(wditem, 'P162')
    #print("DEBUG: existing producers:", existingproducerqcodes)

    # tuottaja (P162)
    if not 'P162' in wditem.claims:
        
        for prodcode in final.producers:

            #if prodcode in existingproducerqcodes:
            #    print("Producer exists for ", prodcode)
            #    continue

            print("Adding claim: producer for ", prodcode)
            prodclaim = add_item_link(repo, 'P162', prodcode)

            # add source if given
            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                prodclaim.addSource(srcclaim)

            wditem.addClaim(prodclaim)#, summary='Adding 1 claim')


    # kappalelista (P658)
    # -> also need to create items for each track..?
    # taideteoksen osien lukumäärä (P2635) (ääniraitojen määrä)

    # jakelumuoto (P437), LP, CD, digitaalinen jakelu..
    # CD might be simple to get, other formats maybe not
    if not 'P437' in wditem.claims:

        for rform in final.releaseformat:
            print("Adding claim: releaseformat ", rform)
    
            rfclaim = add_item_link(repo, 'P437', rform)

            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                rfclaim.addSource(srcclaim)

            wditem.addClaim(rfclaim)#, summary='Adding 1 claim')


    # äänityspaikka (P483)
    # -> not always parseable in finna data (if given)
    if not 'P483' in wditem.claims:
        
        for rcode in final.recordedat:

            print("Adding claim: recording location ", rcode)
            rlclaim = add_item_link(repo, 'P483', rcode)

            # add source if given
            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                rlclaim.addSource(srcclaim)

            wditem.addClaim(rlclaim)#, summary='Adding 1 claim')
    
    # äänitysajankohta (P10135)
    # -> generally not in finna data
    
    # kesto (P2047) (sekuntia)
    if not 'P2047' in wditem.claims:

        # need to format into WbQuantity
        if (final.duration != ""):
            print("Adding claim: duration")

            # set duration in seconds
            wbquant = getwbquantity(repo, final.duration, 'Q11574')
            claim = pywikibot.Claim(repo, 'P2047')
            claim.setTarget(wbquant)
            
            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                claim.addSource(srcclaim)

            wditem.addClaim(claim)#, summary='Adding 1 claim')
 
    # release date julkaisupäivä (P577) (date formatting?)
    if not 'P577' in wditem.claims:

        # TODO: parse full date to wikibase-date (if given)

        if (final.year != ""):
            print("Adding claim: release date")

            # only year now
            wbdate = getwbdate(int(final.year))
            claim = pywikibot.Claim(repo, 'P577')
            #target = pywikibot.ItemPage(repo, released) 
            claim.setTarget(wbdate)
            
            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                claim.addSource(srcclaim)

            wditem.addClaim(claim)#, summary='Adding 1 claim')
            

    # genre
    if not 'P136' in wditem.claims:
        
        for gcode in final.genres:

            print("Adding claim: genre for ", gcode)
            genreclaim = add_item_link(repo, 'P136', gcode)

            # add source if given
            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                genreclaim.addSource(srcclaim)

            wditem.addClaim(genreclaim)#, summary='Adding 1 claim')


    # kieli, language(s) of the album - may be multiple
    if not 'P407' in wditem.claims:
        
        for langqcode in final.languages:
            
            # switch to sparql to fetch items by languages:
            # TODO: need a query by specific property with ISO-code instead of label
            
            print("Adding claim: language for ", langqcode)
            langclaim = add_item_link(repo, 'P407', langqcode)

            # add source if given
            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                langclaim.addSource(srcclaim)

            wditem.addClaim(langclaim)#, summary='Adding 1 claim')

    # teoksen tyyppi (P7937) - release type
    # (studio, live..)
    if not 'P7937' in wditem.claims:
        if (final.releasetype != ""):
        
            print("Adding claim: type", final.releasetype)
            typeclaim = add_item_link(repo, 'P7937', final.releasetype)

            # add source if given
            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                typeclaim.addSource(srcclaim)

            wditem.addClaim(typeclaim)#, summary='Adding 1 claim')

    # levymerkki (P264)
    if not 'P264' in wditem.claims:
        
        # note: might have multiple publishers..
        # -> in some cases, should be parsed/split 
        for lq in final.publishers:
            
            print("Adding claim: record label", lq)
            labelclaim = add_item_link(repo, 'P264', lq)
            
            # add qualifier catalog number if known, may have multiple
            # luettelointitunnus (P528)
            for catid in final.catalogidentifiers:
                print("Adding claim: catalog identifier", catid)
                
                catclaim = add_item_qualifier(repo, 'P528', catid)
                labelclaim.addQualifier(catclaim)
            
            # add source if given
            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                labelclaim.addSource(srcclaim)

            wditem.addClaim(labelclaim)#, summary='Adding 1 claim')


    # julkaisupaikka (P291)
    if not 'P291' in wditem.claims:
        # from name to qid? 
        # maailmanlaajuinen (Q13780930)
        # eurooppa
        # suomi
        
        for pq in final.places:
            
            print("Adding claim: release place", pq)
            
            # todo: also validate that qcode is for a city or a country?
            # TODO: we might need even better filtering before enabling this..

            #placeclaim = add_item_link(repo, 'P291', pq)

            # add source if given
            #if (final.sourceurl != ""):
                #srcclaim = add_item_source_url(repo, final.sourceurl)
                #placeclaim.addSource(srcclaim)

            #wditem.addClaim(placeclaim)#, summary='Adding 1 claim')

        for locq in final.location:
            
            print("Adding claim: release location", locq)
            
            # todo: also validate that qcode is for a city or a country?
            # TODO: we might need even better filtering before enabling this..

            locclaim = add_item_link(repo, 'P291', locq)

            # add source if given
            if (final.sourceurl != ""):
                srcclaim = add_item_source_url(repo, final.sourceurl)
                locclaim.addSource(srcclaim)

            wditem.addClaim(locclaim)#, summary='Adding 1 claim')

    # luettelointitunnus (P528)
    # -> only use as qualifier for release instead of as own property
    #if not 'P528' in wditem.claims:
        #for catid in final.catalogidentifiers:
            #print("Adding claim: catalog identifier", catid)
            
            #catclaim = add_item_value(repo, 'P528', catid)
            #if (final.sourceurl != ""):
            #    srcclaim = add_item_source_url(repo, final.sourceurl)
            #    catclaim.addSource(srcclaim)
            #wditem.addClaim(catclaim)#, summary='Adding 1 claim')


# external identifiers
def add_album_identifiers(repo, wditem, commands):
    
    # can we add all at once this way?
    # no, not supported..
    #vclaimlist = []
    
    # discogs master
    if not 'P1954' in wditem.claims:
        if "discogsmaster" in commands:
            discogs = commands["discogsmaster"]
            
            print("Adding claim: discogs master")
            vclaim = add_item_value(repo, 'P1954', discogs)
            wditem.addClaim(vclaim)#, summary='Adding 1 claim')
            #vclaimlist.append(vclaim)

    if not 'P2206' in wditem.claims:
        if "discogsrelease" in commands:
            discogs = commands["discogsrelease"]
            
            print("Adding claim: discogs release")
            vclaim = add_item_value(repo, 'P2206', discogs)
            wditem.addClaim(vclaim)#, summary='Adding 1 claim')
            #vclaimlist.append(vclaim)

    # metal archives release
    if not 'P2721' in wditem.claims:
        if "metalarchives" in commands:
            metalarc = commands["metalarchives"]
            
            print("Adding claim: metal archives release")
            vclaim = add_item_value(repo, 'P2721', metalarc)
            wditem.addClaim(vclaim)#, summary='Adding 1 claim')
            #vclaimlist.append(vclaim)


    # julkaisun MusicBrainz-tunniste (P5813)
    # äänitteen MusicBrainz-tunniste (P4404)
    # teoksen MusicBrainz-tunniste (P435)

    # julkaisuryhmän MusicBrainz-tunniste (P436)
    if not 'P436' in wditem.claims:
        if "mbzgroup" in commands:
            mbgroup = commands["mbzgroup"]
            
            print("Adding claim: musicbrainz release group")
            vclaim = add_item_value(repo, 'P436', mbgroup)
            wditem.addClaim(vclaim)#, summary='Adding 1 claim')
            #vclaimlist.append(vclaim)

    #wditem.addClaim(vclaimlist)#, summary='Adding claims')

def get_artist_label(repo, final, lang='fi'):

    for artistqcode in final.artists:
        item = getitembyqcode(repo, artistqcode)
        if (isArtistItem(item) == False):
            print('WARN: qid is not for artist', artistqcode)
            return None

        # TODO: keep labels when multiple artists
        
        artistlabel = getlabelbylangfromitem(item, lang)
        if (artistlabel == None):
            print("WARN: no label with lang", lang)
            artistlabel = getlabelbylangfromitem(item, 'mul')
            if (artistlabel == None):
                print("WARN: no label with lang mul")
                return None
            print("found artist name", artistlabel, " with lang 'mul'")
            return artistlabel
        print("ok, artist name found", artistlabel, " with lang", lang)
        return artistlabel

    print("WARN: given artist name and label in wikidata do not match or not given")
    return None


# there is no easy way to do this: album by same name can exist for different artists
# and labels might not exist for all languages
def check_if_album_exists_by_qid(repo, albumqid):
    
    albumitem = getitembyqcode(repo, albumqid)
    if (albumitem != None):
        if (isAlbumItem(albumitem) == True):
            print("album exists with qid", albumqid)
        else:
            print("qid is used by not supported album type", albumqid)
        return True

    return False


def check_if_album_exists_by_name(repo, albumtitle, artistqcode):

    albums = searchItembySparql(repo, albumtitle, True, True, False)
    if (len(albums) == 0):
        return False

    artistfound = False

    for albumitem in albums:
        #albumitem = getitembyqcode(repo, albumqid)
        if (isAlbumItem(albumitem) == False):
            continue

        qlist = getArtistsFromItem(albumitem)
        if artistqcode in qlist:
            artistfound = True
        # check if same artist and same year as well:
        # artists may have album with same name in different years
    
    
    
    # for now, just assume it doesn't..
    return False


# find wikidata items for different fields before starting writing to wikidata
#
def recordstoparams(repo, commands, finnarecord = None):
    final = FinalParams()

    # assume by default
    final.instancetype = 'Q482994' # music album

    album_name = ""
    if (finnarecord != None):
        album_name = finnarecord.getTitleFromFinna()
    if album_name == "" and "album" in commands:
        album_name = commands["album"]

    if (album_name != "" and album_name != None):
        final.albumtitle = album_name
        
        # TODO: checking if album exists needs name, artist, year..

    # updating existing album?
    albumqid = ""
    if "albumqid" in commands:
        albumitem = getitembyqcode(repo, commands['albumqid'])
        #if (albumitem == None):
            # qid given but not existing?
        #supportedlangs = {"fi", "en", "mul"}
        supportedLangs = "fi", "en", "mul"
        atitle = getlabelbyanylangfromitem(albumitem, supportedLangs)
        if (atitle != ""):
            final.albumtitle = atitle

    if "type" in commands:
        typeqcode = gettypeqcode(commands["type"])
        if (typeqcode != ""):
            final.releasetype = typeqcode

    if (finnarecord != None and final.releasetype == ""):
        if (finnarecord.iscompilation() == True):
            final.releasetype = gettypeqcode("kokoelma-albumi")

    #if "format" in commands:
        #getdistributionqcode(commands["format"])

    releaseyear = ""
    if (finnarecord != None):
        releaseyear = finnarecord.getyear()
    
    if "released" in commands and releaseyear == "":
        releaseyear = commands["released"]
    if (releaseyear != "" and releaseyear != None):
        final.year = releaseyear


    # TODO: may have multiple artists in some cases
    # if finna record is given, try to find by name
    artist_qcode = ""
    if "artistqid" in commands:
        # override given in commands? (name is ambigious?)
        artist_qcode = commands["artistqid"]
        
        artistitem = getitembyqcode(repo, artist_qcode)
        if (isArtistItem(artistitem) == False):
            print("skipping item as not proper artist instance:", artist_qcode)
        else:
            # avoid duplicates, catch errors
            addtolist(final.artists, artist_qcode)

    if (artist_qcode == "" and finnarecord != None):

        # if we have asteri-id from finnarecord,
        # try to find qid by asteri id.
        # note that the id may be still missing in wikidata so it should be fixed
        for fas in finnarecord.presenterasteri:

            print("searching for artist with asteri:", fas)

            # use kanto-property for asteri-id: should give only one match
            faslist = searchbySparqlPropValue(repo, "P8980", fas)
            for item in faslist:
                #item = getitembyqcode(repo, aq)
                # must be a humand or a band
                if (isArtistItem(item) == False):
                    print("skipping item as not proper artist instance:", item.getID())
                    continue

                print("DEBUG: found artist qcode:", item.getID(), "for asteri:", fas)
                
                # avoid duplicates, catch errors
                addtolist(final.artists, item.getID())


        # try to find artist by sparql,
        # allow override by command as this may be ambigious to resolve automatically
        # so only search if qcode is not given.
        #
        # use only as fallback now
        if (len(finnarecord.presenterasteri) == 0 and len(finnarecord.artistname) > 0):

            # note: finna names might be "lastname, firstname" or "band (yhtye)"
            # so they might not be usable without further parsing..
            for fan in finnarecord.artistname:
                acodes = searchItembySparql(repo, fan, False, True, False, 'fi')
                if (len(acodes) == 0):
                    print("note, no qcode for artist:", fan)

                for item in acodes:
                    #item = getitembyqcode(repo, aq)
                    # must be a humand or a band
                    if (isArtistItem(item) == False):
                        print("skipping item as not suitable artist instance:", item.getID())
                        continue

                    #print("DEBUG: found artist qcode:", aq, "for name:", fan)
                    
                    # avoid duplicates, catch errors
                    addtolist(final.artists, item.getID())


    sourceurl = ""
    if (finnarecord != None):
        sourceurl = finnarecord.sourceref

    if "source" in commands and sourceurl == "":
        sourceurl = commands['source']
    
    if (sourceurl != ""):
        final.sourceurl = sourceurl

    # if genre was given manually
    if "genre" in commands:
        print("looking for genre:", commands["genre"])

        gcodes = searchItembySparql(repo, commands["genre"], True, True, False, 'fi')
        if (len(gcodes) == 0):
            print("note, no qcode for genre name:", commands["genre"])

        for item in gcodes:
            #item = getitembyqcode(repo, gq)
            if (isGenreItem(item) == False):
                print("skipping item as not proper genre instance:", item.getID())
                continue
            # avoid duplicates, catch errors
            addtolist(final.genres, item.getID())

    # if publisher was given manually
    if "muslabel" in commands:
        print("looking for publisher:", commands["muslabel"])

        pqcodes = searchItembySparql(repo, commands["muslabel"], True, False, False, 'fi')
        if (len(pqcodes) == 0):
            print("note, no qcode for publisher:", commands["muslabel"])
            
            # note: should try with different language as well?
            # 'Q18127' tai  'Q2442401'

            # try without language schema
            pqcodes = searchItembySparql(repo, commands["muslabel"], True, False, False, 'en', 'Q18127')

        for item in pqcodes:
            #item = getitembyqcode(repo, pq)
            # must be record label or record company
            if (isRecordLabel(item) == False):
                print("skipping item as not proper record label instance:", item.getID())
                continue
            # avoid duplicates, catch errors
            addtolist(final.publishers, item.getID())

    # try to fetch qcodes by record (if given)
    if (finnarecord == None):
        return final

    # if we have detected some format(s)..
    for relform in finnarecord.releaseformat:
        rformcode = getdistributionqcode(relform)
        if (rformcode != ""):
            addtolist(final.releaseformat, rformcode)

    # might be EP or something else too or tag may be missing:
    # only mark as single if high confidence (explicit tag found)
    if (finnarecord.issingle() == True):
        final.issingle = True
        final.instancetype = 'Q134556' # single
        print("album is single", final.instancetype)
    elif (finnarecord.iscompilation() == True):
        final.instancetype = 'Q482994' # music album
        print("album is compilation", final.instancetype)
    else:
        final.instancetype = 'Q482994' # music album
        print("album is album", final.instancetype)
    
    # use duration when explicitly given
    if (finnarecord.duration != None):
        final.duration = finnarecord.duration

    # may be a list
    albumlangs = finnarecord.getlang()
    for alang in albumlangs:
        langqcode = getlanguageqcode(alang)
        if (langqcode != ""):
            # avoid duplicates, catch errors
            addtolist(final.languages, langqcode)

    # find qid by asteri-id: needs federated sparql?
    # or try with kanto-id property first?
    for prodast in finnarecord.producerasteri:
        # search from kanto-property by asteri-id
        prodlist = searchbySparqlPropValue(repo, "P8980", prodast)
        if (len(prodlist) == 0):
            print("note, no qcode for asteri-id:", prodast)
            continue
        for item in prodlist:
            #item = getitembyqcode(repo, prodq)
            #if (item == None):
            #    print("skipping item as not found:", prodq)
            #    continue
            #if (isDisambiguation(item) == True):
            #    continue
            # should be human?

            print("DEBUG: found producer qcode:", item.getID(), "for asteri:", prodast)

            # avoid duplicates, catch errors
            addtolist(final.producers, item.getID())


    # may have multiple genres:
    # genres are complicated and overlapping aliases
    for gname in finnarecord.genres:
        
        # cleanup
        if (endswith(gname, ";") == True):
            gname = removelastchar(gname)
            gname = gname.strip()

        print("DEBUG: looking for genre name:", gname)
        
        # might give too wide results..
        gcodes = searchItembySparql(repo, gname, True, True, False, 'fi')
        if (len(gcodes) == 0):
            print("note, no qcode for genre name:", gname)
            continue
        for item in gcodes:
            #item = getitembyqcode(repo, gq)
            if (isGenreItem(item) == False):
                print("skipping item as not proper genre instance:", item.getID())
                continue
            # avoid duplicates, catch errors
            addtolist(final.genres, item.getID())

    # publisher name: record label or record company
    for pname in finnarecord.publishernames:

        if (endswith(pname, ";") == True):
            pname = removelastchar(pname)
            pname = pname.strip()

        print("DEBUG: looking for publisher:", pname)

        pqcodes = searchItembySparql(repo, pname, False, False, False, 'fi')
        if (len(pqcodes) == 0):
            print("note, no qcode for publisher:", pname)

            # try with alias first
            pqcodes = searchItembySparql(repo, pname, True, False, True, 'fi')
            if (len(pqcodes) == 0):
                # we should use 'mul' as fallback but many have english label instead still
                # try again
                # 'Q18127' tai  'Q2442401'
                # also try without language schema
                pqcodes = searchItembySparql(repo, pname, False, False, False, 'en', 'Q18127')
                if (len(pqcodes) == 0):
                    pqcodes = searchItembySparql(repo, pname, True, False, True, 'en', 'Q18127')

        # check also that publisher from query is in same country as publisher in finna data:
        # different publishers with same name can exist in different countries (for example, LeBaron Music),
        # finna data has often publishing city so try to match that to location of headquarters as well

        # TODO: also try to prioritize if there is both a record label and a record company in results..
        # don't link to both though qcodes might be different but names same
        
        for item in pqcodes:
            #item = getitembyqcode(repo, pq)
            # must be record label or record company
            if (isRecordLabel(item) == False):
                print("skipping item as not proper record label instance:", item.getID())
                continue
            
            # we could try to get country code from name of location,
            # but there are cities with same name in different countries..
            
            # name of location(s) of hq for this publisher (for country match) as finna gives city
            hqplaces = getlabelofpropbylangfromitem(repo, item, 'P159', 'fi')
            if (len(hqplaces) == 0):
                # should use 'mul' as fallback but try english for now
                hqplaces = getlabelofpropbylangfromitem(repo, item, 'P159', 'en')
            print("DEBUG: hq-list", hqplaces)
            
            if (len(finnarecord.publishingplaces) > 0 and len(hqplaces) > 0):
                for ppname in finnarecord.publishingplaces:
                    if ppname in hqplaces:
                        # ok, match: keep qcode of this publisher
                        addtolist(final.publishers, item.getID())
                    else:
                        print("DEBUG: place", ppname ,"not found in hq-list")
            else:
                # we don't have publishing places to check so keep the qcode of publisher
                addtolist(final.publishers, item.getID())

    # label identifier ("brand"): in case publisher was not given?
    if (len(final.publishers) == 0 and len(finnarecord.labelnames) > 0):
        for lblname in finnarecord.labelnames:
            # try to search only from levymerkki (Q18127)
            lblcodes = searchItembySparql(repo, pname, False, False, False, 'fi', 'Q18127')
            if (len(lblcodes) == 0):
                lblcodes = searchItembySparql(repo, pname, True, False, True, 'fi', 'Q18127')

            for item in lblcodes:
                addtolist(final.publishers, item.getID())


    # publishing location/area
    for plname in finnarecord.publishingplaces:
        
        if (endswith(plname, ":") == True):
            plname = removelastchar(plname)
            plname = plname.strip()
        # place names might have brackets around, remove before lookup
        if (isinbrackets(plname) == True):
            plname = removefirstlastbracket(plname)

        # TODO: if we can get YSO-identifier from data, search by that?

        # we could shortcut some
        #if (plname == "maailmanlaajuinen"):
        #if (plname == "Eurooppa"):
        #if (plname == "Suomi"):

        # skip for now, needs better way to determine usable places..
        pqcodes = list()
        #pqcodes = searchItembySparql(repo, plname, True, True, False, 'fi')
        if (len(pqcodes) == 0):
            print("note, no qcode for place:", plname)
            continue
        
        for item in pqcodes:
            # must be city or country ?
            #kaupunki (Q515)
            #valtio (Q7275)
            #itsenäinen valtio (Q3624078)
            #maa (Q6256)

            #item = getitembyqcode(repo, pq)
            if (isItemInstanceOf(item, 'Q515') == False 
                and isItemInstanceOf(item, 'Q7275') == False 
                and isItemInstanceOf(item, 'Q6256') == False):
                print("skipping item as not proper place instance:", item.getID())
                continue
            # avoid duplicates, catch errors
            addtolist(final.places, item.getID())

    # publishing location/area, if we have yso-id try that first
    if (len(finnarecord.locationyso) > 0):
        for locyso in finnarecord.locationyso:
            # search from yso-property by yso-id
            loclist = searchbySparqlPropValue(repo, "P2347", locyso)
            if (len(loclist) == 0):
                print("note, no qcode for yso-id:", locyso)
                continue
            for item in loclist:
                # check it is a location we can use, if we have yso it should be ok?
                if (isItemInstanceOf(item, 'Q515') == False 
                    and isItemInstanceOf(item, 'Q7275') == False 
                    and isItemInstanceOf(item, 'Q6256') == False):
                    print("skipping item as not proper place instance:", item.getID())
                    continue

                print("DEBUG: found location qcode:", item.getID(), "for yso-id:", locyso)

                # avoid duplicates, catch errors
                addtolist(final.location, item.getID())
                
    # not found by yso or not it was not given
    if (len(finnarecord.locationyso) == 0 or len(final.location) == 0):
        for locname in finnarecord.location:
            
            # we could shortcut some
            #if (plname == "maailmanlaajuinen"):
            #if (plname == "Eurooppa"):
            #if (plname == "Suomi"):
            
            # TODO: if we can get YSO-identifier from data, search by that?

            # should be country name
            locqcodes = searchItembySparql(repo, locname, True, False, False, 'fi', 'Q3624078')
            if (len(locqcodes) == 0):
                print("note, no qcode for location:", locname)
                continue
            
            for item in locqcodes:
                # must be city or country ?
                #kaupunki (Q515)
                #valtio (Q7275)
                #itsenäinen valtio (Q3624078)
                #maa (Q6256)

                # itsenäinen valtio (Q3624078)
                # yhtenäisvaltio (Q179164)
                #item = getitembyqcode(repo, locq)
                if (isItemInstanceOf(item, 'Q515') == False 
                    and isItemInstanceOf(item, 'Q7275') == False 
                    and isItemInstanceOf(item, 'Q6256') == False):
                    print("skipping item as not proper place instance:", item.getID())
                    continue
                # avoid duplicates, catch errors
                addtolist(final.location, item.getID())

    # recording studio
    for recstudio in finnarecord.recordedat:
        print("DEBUG: looking for studio name:", recstudio)
        
        reccodes = searchItembySparql(repo, recstudio, False, False, False, 'fi')
        if (len(reccodes) == 0):
            print("note, no qcode for studio name:", recstudio)
            
            # try alias
            reccodes = searchItembySparql(repo, recstudio, False, False, True, 'fi')

        for item in reccodes:
            #item = getitembyqcode(repo, rcq)
            if (isStudioItem(item) == False):
                print("skipping item as not proper studio instance:", item.getID())
                continue
            # avoid duplicates, catch errors
            addtolist(final.recordedat, item.getID())

    # nothing to do, use as-is
    for catident in finnarecord.catalogidentifiers:
        addtolist(final.catalogidentifiers, catident)

    return final

def create_album_item(repo, final, artistlabel):

    if (final.albumtitle == None):
        return None
    if (artistlabel == None):
        return None

    # album needs artist and album name since there can be 
    # multiple albums from different artists or even same artist
    #if (check_if_album_exists(repo, commands) == True):
    #    print('Album exists, skipping')
    #    return None

    # TOOD: if we have type == Q208569, 
    # then use descrption "studio album by..",
    # also check cases for live albums etc. 

    albumtype = ""
    if (final.issingle == True):
        albumtype = "single"
    else:
        albumtype = "album"

    album_desc_en = albumtype + " by " + artistlabel
    #album_desc_fi = artistlabel + " albumi"
    album_desc_sv = albumtype + " av " + artistlabel
    album_desc_fr = albumtype + " de " + artistlabel # de/des

    #album_desc_de = albumtype + " von " + artistlabel # Album
    #album_desc_es = albumtype + " de " + artistlabel # álbum
    #album_desc_it = albumtype + " dei " + artistlabel # degli/dei/di
    #album_desc_pt = albumtype + " de " + artistlabel # álbum

    # more accurate date? parse to year
    if (len(final.year) > 0):
        # only year for now, add support for date
        year = str(final.year)
        album_desc_en = year + " " + album_desc_en
    #    album_desc_fi = album_desc_fi + " vuodelta " + year
        album_desc_sv = album_desc_sv + " från " + year
        album_desc_fr = album_desc_fr + " sorti en " + year
        #album_desc_fr = album_desc_fr + ", sorti en " + year
        
        #album_desc_de = album_desc_de + " (" + year + ")"
        #album_desc_es = album_desc_es + " de " + year
        #album_desc_it = album_desc_it + " del " + year
        #album_desc_pt = album_desc_pt + " de " + year
    
    data = {"labels": {"en": final.albumtitle, "fi": final.albumtitle, "sv": final.albumtitle, "fr": final.albumtitle, "mul": final.albumtitle},
    "descriptions": {"en": album_desc_en, "sv": album_desc_sv, "fr": album_desc_fr}}


    print('Creating a new album item for', final.albumtitle)

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
    if (wtitle == "" or wtitle == None):
        print("no label given, trying english")
        wtitle = getlabelbylangfromitem(item, 'en')
    if (wtitle == "" or wtitle == None):
        print("no label given, trying finnish")
        wtitle = getlabelbylangfromitem(item, 'fi')
    if (wtitle == "" or wtitle == None):
        print("no label given, trying mul")
        wtitle = getlabelbylangfromitem(item, 'mul')

    if (wtitle == "" or wtitle == None):
        print("no label found for item")
        return False


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
    supportedLangs = "en", "fi", "mul"
    for lang in supportedLangs:
        if lang not in item.labels:
            # example: "fi": "Virtanen"
            copy_labels[lang] = wtitle
    if (len(copy_labels) > 0):
        item.editLabels(labels=copy_labels, summary="Adding missing labels.")
        modifiedItem = True

    if (modifiedItem == True):
        item.get()
    return modifiedItem

def add_album(commands, finnarecord = None):

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()

    # parse finna items to qcodes, lookups by asteri-id or name(s),
    # use commandline parameters if given
    final = recordstoparams(repo, commands, finnarecord)
    
    # updating existing album?
    albumqid = ""
    if "albumqid" in commands:
        albumqid = commands['albumqid']

    if (len(final.albumtitle) == 0 and len(albumqid) == 0):
        print('WARN: cannot create or update, album name and qid missing')
        return None

    album_item = {}
    if (len(albumqid) == 0):
        
        # just check given parameter makes sense,
        # if we are just updating an album this might not be necessary,
        # but we should validate it if we are adding it to an album..
        artistlabel = get_artist_label(repo, final)
        if (artistlabel == None or artistlabel == ""):
            print('WARN: cannot create, artist unknown')
            return None
        
        # create new item by given name:
        # add description with artist and year
        #
        album_item = create_album_item(repo, final, artistlabel)
    else:
        # update/expand existing album
        album_item = getitembyqcode(repo, albumqid)
        if (isAlbumItem(album_item) == False):
            print('WARN: qid is not for album', albumqid)
            return None
        # check if item needs label fixing
        check_and_add_labels(album_item, final.albumtitle)

    # only add given properties
    print('Adding properties...')
    add_album_properties(repo, album_item, final)

    # identifiers for other databases and so on
    print('Adding identifiers...')
    add_album_identifiers(repo, album_item, commands)

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
    
    # keep metapage address:
    # could use kansalliskirjasto.finna.fi ?
    frpage = "https://finna.fi/Record/" + finnaid
    fr.sourceref = frpage
    
    if (fr.isalbum() == False):
        print("Not a supported album record with id:", fr.finnaid)
        return None
    
    # TODO: more validation..
    # before starting to write in to wikidata, do more checks here

    # most of the useful data is in the xml for albums
    fr.parseFullRecord()
    
    # try to parse these separately
    fr.parsenonpresenterauthors()
    
    fr.parsepresenters()
    
    # pass both record and extra commands:
    # some we can't parse yet..
    add_album(commands, fr)


support_args = ["album",
                "albumqid",
                #"artist",
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

            #if (val[0] == '"' and val[len(val)-1] == '"'):
            #    val = val[1:len(val)-1]

            val = val.replace('"', "") # remove double quotes from command line
            commands[key] = val
            
        #if (key == "artist"):
        #    if (getartistqcode(commands["artist"]) == ""):
        #        print("WARN: no qcode for artist", commands["artist"])
        #        exit()
        # switch to sparql
        #if (key == "muslabel"):
        #    if (getpublisherqcode(commands["muslabel"]) == ""):
        #        print("WARN: no qcode for label", commands["muslabel"])
        #        exit()
        # switch to sparql
        #if (key == "genre"):
        #    if (getgenreqcode(commands["genre"]) == ""):
        #        print("WARN: no qcode for genre", commands["genre"])
        #        exit()
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


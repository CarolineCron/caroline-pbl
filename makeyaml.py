import yaml
import xml.etree.ElementTree as ET
import xmltodict
import pprint
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup


# LOADING FILES AND BASIC PARSING

def loadXmlFile(filename):
    data = open(filename, 'r').read()
    return data

def deleteTemplates(strng):
    s = re.sub(r'{[^}]*}*', '', strng)
    s = re.sub(r'<[^>]*>*', '', s)
    return s

def getHyperlinks(strng):
    y = re.findall(r'\[\[.*?\]\]', strng)
    return y

def getUrl(lnk):
    # delete [[-prefix and ]]-suffix
    if lnk.startswith("[["):
        lnk = lnk[2:]
    if lnk.endswith("]]"):
        lnk = lnk[:-2]

    name = lnk
    if "|" in lnk:
        pair = lnk.split("|")
        name = pair[0]
        lnk = pair[1]
    lnk = "_".join( lnk.split() )
    url = "https://models.pbl.nl/image/"+lnk
    return (name, url)

def sortHyperlinksAndUrls(lst):
    d = {'references': [],
         'other links': []}
    for ref in lst:
        (name, url) = getUrl(ref)
        if re.search(r'[0-9][0-9][0-9][0-9]', ref):
            d['references'] = d['references'] + [name+": "+url]
        else:
            d['other links'] = d['other links'] + [name+": "+url]
    return d

def getTemplates(strng):
    y = re.findall(r'{{[\s\S]*?}}', strng)
    return y

def parseTemplate(strng):
    # takes a string that is the entirety of a template and parses its name and parameters into a dictionary
    # remove double curly brackets from start and end
    if strng.startswith("{{"):
        strng = strng[2:]
    if strng.endswith("}}"):
        strng = strng[:-2]

    def semicolonSplit(x):
        if ";" in x:
            lst = x.split("; ")
            newlst = []
            for item in lst:
                if ";" in item:
                    sublst = item.split(";")
                    newlst = newlst + sublst
            return newlst
        else:
            return [x]
        
    def equalSplit(x):
        if "=" in x:
            lst = x.split("=")
            return (lst[0], semicolonSplit(lst[1]))
        else:
            return [x]

    def deleteNewLine(item):
        if isinstance(item, str) :
            strng = item.replace('\n', '')
            if (re.search(r'[a-z]|[A-Z]', strng)) == None:
                return()
            return(strng)
        else:
            lst = list(map(lambda i: deleteNewLine(i), item))
            for i in lst:
                if i == ():
                    lst.remove(i)
            return(lst)
        
    d = {}

    # split string by pipes
    lst = strng.split("|")

    tplName = lst[0]
    tplName = tplName.replace("\n", "")
    lst.pop(0)

    rest = []

    # split first by equal, then the second component by semicolon
    for i in lst:
        if "=" in i:
            pair = equalSplit(i)

            linkSections = ['Application','IMAGEComponent', 'KeyReference', 'Reference']

            if (pair[0] in linkSections) and (tplName == 'ComponentTemplate2') :
                nameUrlLst = []
                for lnk in pair[1]:
                    (name, url) = getUrl(lnk)
                    nameUrlLst = nameUrlLst + [name+": "+url]
                d[pair[0]] = nameUrlLst
            # this makes sure that entries that are just "\n" are deleted (needed for the variable pages)
            # TODO: for the variable pages, the VariableTape is parsed correctly but is not what is displayed on the website
            elif pair[1] != ['\n']: 
                #item = (pair[1]).replace('\n', '')
                d[pair[0]] = deleteNewLine(pair[1])
        else:
            item = i.replace('\n', '')
            d[item] = []
            #rest = rest + [i]
        

    if len(rest)!=0:
        pprint.pp(rest)
        raise Exception("The template "+tplName+" might not have been parsed successfully.")
    else:
        ret = {tplName : d}
        return ret


# TREE LEAF PAGES

# get data from XMLs
def getAll(file):
    my_xml = loadXmlFile(file)
    my_dict = xmltodict.parse(my_xml)
    pages = my_dict["mediawiki"]["page"]
    d = {}
    for p in pages:
        title = p["title"]
        if "Template" in title:
            continue
        text = p["revision"]["text"]["#text"]
        tpl = (getTemplates(text))[0]
        tpl = parseTemplate(tpl)
        key = list(tpl)[0]
        d[title] = tpl[key]
    #pprint.pp(d)
    return(d)
# Policy Questions
def getAllKeyPolicyQuestions():
    # returns dict with key policy questions as keys
    return(getAll('IMAGE-KeyPolicyQuestionsAll.xml'))
# Variables
def getAllVariables():
    # returns a dict with variables as keys and subdicts for Label, Description, Dimension, Unit, VariableType
    return(getAll('IMAGE-VariablesAll.xml'))
# Components (this is only the Intro page of each)
def getAllComponents():
    # this only parses and returns the ComponentTemplate2. but it is enough to establish the connections with PQs and Vars
    return(getAll('IMAGE-ComponentsAll.xml'))
# Policy Interventions
def getAllPolicyInterventions():
    # returns dict with policy interventions as keys and subdicts for Component, Description, Reference, EnergyThemeItem, LanduseThemeItem, NatureThemeItem, ClimateThemeItem
    return(getAll('IMAGE-PolicyInterventionsAll.xml'))

# organise data
def getVarOverview():
    # returns df with columns varName, varType (= InputVar, OutputVar or Parameter), component (varName are not unique)
    dict = getAllComponents()
    varTypes = ['InputVar', 'Parameter', 'OutputVar']
    arr = []
    for comp in dict.keys():
        for tpe in varTypes:
            if tpe in dict[comp].keys():
                for var in dict[comp][tpe]:
                    arr.append([var, tpe, comp])
    df = pd.DataFrame(arr)
    df.columns = ['varName', 'varType', 'component']
    print(df)
    return(df)

def getKeyPolicyQuestionyByComp(component):
    # returns the subset of getAllKeyPolicyQuestions() that belongs to the input component
    abbrevToComp = {
        'AB': 'Aquatic biodiversity',
        'ACC': 'Atmospheric composition and climate',
        'AEF': 'Agricultural economy',
        'APEP': 'Air pollution and energy policies',
        'AS': 'Land-use allocation',
        'CG': 'Crops and grass',
        'CP': 'Climate policy',
        'E': 'Emissions',
        'EC': 'Energy conversion',
        'ED': 'Energy demand',
        'EGS': 'Ecosystem services',
        'ES': 'Energy supply',
        'ESD': 'Energy supply and demand',
        'FM': 'Forest management',
        'FR': 'Flood risks',
        'H': 'Water',
        'HD': 'Human development',
        'IF': 'IMAGE framework summary',
        'LBP': 'Land and biodiversity policies',
        'LD': 'Land degradation',
        'LS': 'Livestock systems',
        'N': 'Nutrients',
        'NVCC': 'Carbon cycle and natural vegetation',
        'TB': 'Terrestrial biodiversity',
        'VHA': 'Carbon, vegetation, agriculture and water'}
    comptToAbbrev = {v: k for k, v in abbrevToComp.items()}
    kpqDict = getAllKeyPolicyQuestions()
    abbrev = comptToAbbrev[component]
    kpqOfComp = {}
    for k in kpqDict.keys():
        if abbrev in k:
            kpqOfComp[k] = kpqDict[k]
    return(kpqOfComp)

def getVariableDependencies():
    # takes getAllVariables and adds subkeys for each var: InputVarOf, OutputVarOf, ParameterOf (this info is obtained from getVarOverview())
    variables = getAllVariables()
    varOverview = getVarOverview()
    for var in variables.keys():
        variables[var]['InputVarOf'] = []
        variables[var]['OutputVarOf'] = []
        variables[var]['ParameterOf'] = []
        specVar = varOverview[varOverview['varName'] == var]
        for index, row in specVar.iterrows():
            (variables[var][row['varType']+'Of']).append(row['component'])
    pprint.pp(variables)
    return(variables)


# TESTING START

testi = getAllPolicyInterventions() 
pprint.pp(testi)
#getKeyPolicyQuestionyByComp('Human development')

# TESTING END

def extractTextWebsite(file):
    my_xml = loadXmlFile(file)
    my_dict = xmltodict.parse(my_xml)
    pge = my_dict["mediawiki"]["page"]

    first_page = pge[0]
    ttl = first_page["title"]
    text = first_page["revision"]["text"]["#text"]

    # getting prefix (before <div BLA>) and suffix (after </div>) and the in-between (actual text)
    if "</div>" in text:
        aux1 = text.split("<div class=\"page_standard\">")
        prefix = aux1[0]
        aux2 = aux1[1].split("</div>")
        txt = aux2[0]
        suffix = aux2[1]
        
        # throw error when multiple divs intersect
        if len(aux1) > 2 or len(aux2) > 2:
            raise Exception("Error when splitting the raw text into prefix, text and suffix")
    else:
        prefix = text
        txt = ""
        suffix = ""


    return ttl, txt, prefix, suffix

def aux_getComp2Template(tpls):
    for t in tpls:
        if "ComponentTemplate2" in t:
            #print(t)
            return t
        
def makeInfoBox(introFile):
    (ttl, text, prefix, suffix) = extractTextWebsite(introFile)
    preTpl = getTemplates(prefix)

    t = aux_getComp2Template(preTpl)
    t = parseTemplate(t)
    t = t['ComponentTemplate2']

    dbq = 'DATABASE_QUERY'
    boxHdgToCompOrdered = {'Component is implemented in:': dbq,
                'Related IMAGE components': 'IMAGEComponent',
                'Projects/Applications': 'Application',
                'Models/Databases': 'Model-Database',
                'Key publications': 'KeyReference',
                'References': 'Reference'
                }
    infoBox = {}
    c = 1
    for hdg in boxHdgToCompOrdered.keys():
        if boxHdgToCompOrdered[hdg] == dbq:
             infoBox['box '+str(c)] = {'heading': hdg,
                        'content': dbq}
             c = c+1
        elif boxHdgToCompOrdered[hdg] in t.keys():
            compHdg = boxHdgToCompOrdered[hdg]
            infoBox['box '+str(c)] = {'heading': hdg,
                                      'content': sorted(t[compHdg], key=strng.lower)} # points sorted alphabetically on website
            c = c+1
    d = {'infobox' : infoBox}
    return(d)

# this currently works pretty well for the component pages and their subpages
def buildDict(file):

    def makeSection(heading, text, sectionType, sectionNumberStr):
        sectionDict = {}
        hlnk = sortHyperlinksAndUrls(getHyperlinks(text))
        tpl = getTemplates(text)
        sectionDict[sectionType+ ' ' +sectionNumberStr] = {
            'heading': heading,
            'text' : text ,
            'hyperlinks' : hlnk,
            'figures' : [],
            'in-text templates' : tpl
        }
        return(sectionDict)
        
    def makeSubSections(heading, text, sectionNumberStr):
        subsecDict = {}
        tList = text.split("===", 1)
        
        preText = tList[0]
        s = makeSection(heading, preText, 'section', sectionNumberStr)
        subsecDict.update(s)
        tList.pop(0)

        tList = tList[0].split('===')
        for i in range(0, len(tList)-1):
            if (tList[i].replace('\n', '') == ''):
                tList.pop(0)
    
        c = 1
        while len(tList) > 1:
            s = makeSection(tList[0], tList[1], 'subsection', sectionNumberStr+"."+str(c))
            subsecDict.update(s)
            tList.pop(0)
            tList.pop(0)
            c = c + 1
        
        return(subsecDict)

    (ttl, text, prefix, suffix) = extractTextWebsite(file)

    d = {}

    # title
    d['title'] = ttl


    # go through prefix
    # TODO write parsing fun for other templates as well so that differen prefix templates can be parsed
    preTpl = getTemplates(prefix)

        # parse ComponentTemplate2 when it exists in the prefix
    #comp2 = "missing"
    tpl = {}
    for t in preTpl:
        #if "ComponentTemplate2" in t:
        pt = parseTemplate(t)
        prefix = prefix.replace(t, '') 
        preTpl.remove(t)
        #    break
        tpl.update(pt)
    #d['Component Template 2 (prefix)'] = comp2
    d['prefix templates'] = tpl

    # go through suffix
    sufTpl = getTemplates(suffix)
    d['suffix templates'] = sufTpl

    # end parsing if there is no text
    if text == "":
        pprint.pp(d)
        return(d)
        
    # making sections

    sectionNo = (len(re.findall(r'[^=]==[^=]', text)))/2

    if sectionNo==0:
        if "/" not in ttl:
            if "===" not in text:
                s = makeSection('Introduction', text, 'section', "1")
                d.update(s)
            else:
                s = makeSubSections("Missing Heading", text, "1")
                d.update(s)
        else: 
            if 'ComponentDescriptionTemplate' in d['prefix templates'].keys():
                hdg = "Model Description of "+((ttl.split("/"))[0])
            else:
                hdg = (ttl.split("/"))[1]
            s = makeSubSections(hdg, text, "1")
            #s = makeSection(hdg, text, 'section', 1)
            d.update(s)

    elif sectionNo == 1: 
        textList = text.split('==', 2)
        hdg = textList[1]
        txt = textList[2]

        if "===" not in txt:
            s = makeSection(hdg, txt, 'section', "1")
            d.update(s)
        else:
            s = makeSubSections(hdg, txt, "1")
            d.update(s)

    else:
        # TODO
        #hdg = (ttl.split("/"))[1]

        c = 1

        if "/" not in ttl:
            hdg = "Text before first heading"
        else: 
            hdg = (ttl.split("/"))[1]


        textList = text.split("==")

        #for i in range(0, len(textList)-1):
        #    if (textList[i].replace('\n', '') == ''):
        #        textList.pop(0)

        preText = textList[0]
        if preText != "":
            s = makeSection(hdg, preText, 'section', str(c))
            d.update(s)
            c = c + 1
        textList.pop(0)

        while len(textList) > 1:
            if "===" in textList[1]:
                s = makeSubSections(textList[0], textList[1], str(c))
            else:
                s = makeSection(textList[0], textList[1], 'section', str(c))
            d.update(s)
            textList.pop(0)
            textList.pop(0)
            c = c+1

    pprint.pp(d)
    return(d)


# TEST FILES

testfile_easy = 'test.xml' 
testfile_1 = 'IMAGE-Agricultural economy.xml'
testfile_2 = 'IMAGE-Energy conversion.xml'
testfile_3 = 'IMAGE-Agricultural economy - Policy issues.xml'
testfile_4 = 'IMAGE-Agricultural economy - Description.xml'
testfile_5 = 'IMAGE-Agricultural economy - Data uncertainties limiations.xml'
testfile_var1 = 'IMAGE-Land supply (variable).xml'
testfile_var2 = 'IMAGE-Income and price elasticities (variable).xml'
testfile_cleaned = 'cleaned_response.xml'


#buildDict(testfile_var2)

#makeInfoBox(testfile_1)



def trashFromBuildDict():

    # if "/" is not in the title, this must be an intro page
    if "/" not in ttl:
        s = makeSection('Introduction', text, 'section', 1)
        d.update(s)

    # DONE DONE DONE

    # case: no section headings are given in '=='
    elif not (bool(re.search('[^=]==[^=]', text))):
        hdg = (ttl.split("/"))[1]

        textList = text.split("===", 1)
        preText = textList[0]
        
        s = makeSection(hdg, preText, 'section', 1)
        d.update(s)

        textList.pop(0)
        textList = textList[0].split('===')

        print(len(textList))

        for i in range(0, len(textList)-1):
            if (textList[i].replace('\n', '') == ''):
                textList.pop(0)
        
        c = 1
        while len(textList) > 1:
            s = makeSection(textList[0], textList[1], 'subsection', c)
            d.update(s)
            textList.pop(0)
            textList.pop(0)
            c = c+1
     # DONE DONE DONE
    # case: sections headings are given in '=='
    else:
        textList = text.split(r'[^=]==[^=]')
        #textList = text.split(r'[\n^=]==[\n^=]')
        #pprint.pp(textList)
        #pprint.pp(len(textList))
        #textList = text.split('==')

        #breakpoint

        # delete all elements that are just new lines
        for i in range(0, len(textList)-1):
            if (textList[i].replace('\n', '') == ''):
                textList.pop(0)
            
        c = 1
        while len(textList) > 1:

            s = makeSection(textList[0], textList[1], 'section', c)
            d.update(s)

            textList.pop(0)
            textList.pop(0)

            c = c+1

        if False: #len(textList) != 0:
            print("\n\nTHERE HAS BEEN AN ERROR\n\n")
            print("this is the state of the dictionary:\n")
            pprint.pp(d)

            print("this is the unparsed bit:\n")
            pprint.pp(textList)
            #raise Exception("The text might not have been parsed successfully.")

def moreTrash():
    def ooUgetKeyPolicyQuestions(url): # not in use atm
        website = requests.get(url)
        text = website.text 
        soup = BeautifulSoup(text)
        #print(soup)
        list = []
        for l in soup.find_all('a'):
            list.append(str(l.get("href")))
        list = [x for x in list if x is not None]
        list = [x for x in list if "PQ" in x]
        urlList = []
        for l in list:
            urlList.append("https://models.pbl.nl/"+l)
        return(urlList)
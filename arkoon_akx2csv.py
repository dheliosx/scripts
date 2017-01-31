# coding: utf8

__script__ = 'Script de fortage xml 2 csv arkoon'
__author__ = 'Karim, Xavier Meunier'
__version__ = '2.0'
__copyright__ = "Copyright 2015, TGS EPI"
__status__ = "Devel"

#!/usr/bin/python

from io import StringIO
import argparse
import sys
from datetime import datetime

try:
	import cElementTree as ET
except:
	import xml.etree.cElementTree as ET

HEADER = '\033[95m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'

objecttypes = ('./ListHost/Host','./ListNetwork/Network','./ListFast360/Fast360', \
		'./ListCluster/Cluster','./ListServiceSystemTcp/ServiceSystemTcp', \
		'./ListServiceSystemUdp/ServiceSystemUdp','./ListServiceSystemIcmp/ServiceSystemIcmp', \
		'./ListServiceSystemOther/ServiceSystemOther','./ListServiceUserTcp/ServiceUserTcp', \
		'./ListServiceUserUdp/ServiceUserUdp','./ListServiceUserIcmp/ServiceUserIcmp', \
		'./ListServiceUserOther/ServiceUserOther', './ListGroupService/GroupService', './ListGroupNetObject/GroupNetObject')
grouptypes = ('./ListGroupService/GroupService', './ListGroupNetObject/GroupNetObject')

objects = {} 
outrules = {}


def init_opt():
    """
    INPUT: 
    OUTPUT: options de la ligne de commande parsee et renseignee (valeur par defaut, etc)
    """
    
    parser = argparse.ArgumentParser(description="Script de formatage des confs JunOs XML en CSV")

    parser.add_argument("xmlfile", 
            help="fichier xml a parser", metavar="xmlfile")
    parser.add_argument("hostname", 
            help="hostname a specifier", metavar="hostname")
    
    options = parser.parse_args()
    
    if options.hostname is None:
        parser.error(FAIL+'Veuillez entrer un hostname'+ENDC)
        sys.exit()
               
    return options

    
def explodegroup(group):
	for ref in igroups[group]:
		if ref in groups:
			explodegroup(ref)
		else:
			if not group in groups:
				groups[group] = []
			groups[group].append(ref)

            
def getobjects(root):
	for objtype in objecttypes:
		objlist = root.findall(objtype)
		for obj in objlist:
			objects[obj.attrib['Guid']] = obj.attrib['Name']

            
def getobjectname(obj):
    if obj in objects:
        return objects[obj]
    else:
        return 'Unknown Object'


def main():    
    options = init_opt()     
    nbServices = 0
    
    if len(sys.argv) < 2:
        print FAIL+"Please enter filename"+ENDC
        sys.exit(1)

    print HEADER+'Loading file'+ENDC,
    sys.stdout.flush()
    try:
        tree = ET.parse(options.xmlfile)
    except:
        print FAIL+"[failed]"+ENDC
        sys.exit(1)
    print OKGREEN+'[done]'+ENDC

    print HEADER+'Creating database...'+ENDC,
    sys.stdout.flush()
    root = tree.getroot()
    getobjects(root)
    print OKGREEN+str(len(objects))+' objects [done]'+ENDC

    maintenant = datetime.now()
    csvfile = options.hostname+"_"+str(maintenant.year)+str('{:02d}'.format(maintenant.month))+str('{:02d}'.format(maintenant.day))+"_arkoon_RULES.csv"
    outputfilename = csvfile
    print HEADER+'Creating output file ' + outputfilename + ENDC,

    rules = root.findall('./ListRule/Rule')
    for rule in rules:
        sourcesGuid = rule.findall('./Criteria/ListSource/Source')
        destsGuid = rule.findall('./Criteria/ListDestination/Destination')
        servicesGuid = rule.findall('./Criteria/ListService/Service')
        General = rule.find('./General')
        Id = General.find('./SeqNum')
        Log = General.find('./Log')
        Block = rule.find('./Action/Block')
        Reject = rule.find('./Action/Reject')
        Accept = rule.find('./Action/Accept')
        SourceTranslation = rule.find('./Action/Accept/ListTranslation/RuleTranslation/SourceTranslation')
        DestinationTranslation = rule.find('./Action/Accept/ListTranslation/RuleTranslation/DestinationTranslation')

        if Block.attrib['Selected'] == 'true':
            Action = 'Block'
        elif Reject.attrib['Selected'] == 'true':
            Action = 'Reject'
        else:
            Action = 'Accept'

        Activated = General.attrib['Activated']
        if General.attrib['Activated'] == '1':
            Activated = 'true'
        if General.attrib['Activated'] == '0':
            Activated = 'false'

        if not SourceTranslation is None:
            NAT=SourceTranslation.attrib['Enabled']
        else:
            NAT='false'
        if not DestinationTranslation is None:
            PAT=DestinationTranslation.attrib['Enabled']
        else:
            PAT='false'

        sources = set() 
        dests = set() 
        services = set()
        
        nbServices = 0
        nbDestinations = 0
        nbSources = 0
        
        for sourceGuid in sourcesGuid:
            nbSources += 1
            sources.add(getobjectname(sourceGuid.attrib['Ref']))
        for destGuid in destsGuid:
            nbDestinations += 1
            dests.add(getobjectname(destGuid.attrib['Ref']))
        for serviceGuid in servicesGuid:
            nbServices += 1
            services.add(getobjectname(serviceGuid.attrib['Ref']))

        if nbServices == 0:
            services.add("Any")
        if nbSources == 0:
            sources.add("Any")
        if nbDestinations == 0:
            dests.add("Any")
            
        outrules[int(Id.text)] = { 'Sources': sources, 'Destinations': dests, 'Services':services, \
                'Action':Action, 'Name':rule.attrib['Name'], 'Description':rule.attrib['Desc'], \
                'Enabled':Activated,'Log':Log.text,'NAT':NAT,'PAT':PAT}


    outputfile = open(outputfilename, 'w')
    if outputfile is None:
        print FAIL,'Cannot open file',outputfile,ENDC
    sep = ';'
    header = sep.join(('Id','Enabled','Name','Description','Sources','Destinations','Services',\
            'Action','Log','Source Translation','Destination Translation'))+'\n'
    outputfile.write(header)
    for key in sorted(outrules.iterkeys()):
        line = sep.join((str(key), outrules[key]['Enabled'], outrules[key]['Name'], \
            outrules[key]['Description'], ' '.join(outrules[key]['Sources']),
            ' '.join(outrules[key]['Destinations']), ' '.join(outrules[key]['Services']), \
            outrules[key]['Action'], outrules[key]['Log'],outrules[key]['NAT'], outrules[key]['PAT']))+'\n'
        outputfile.write(line.encode('latin_1'))
    outputfile.close()
    if len(outrules) == 0:
        exit(1)
    print OKGREEN+str(len(outrules))+' rules [done]'+ENDC

if __name__ == "__main__":
        main()      
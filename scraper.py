#!/usr/bin/env python
import os, imghdr, urllib, urllib2, sys, argparse, zlib, unicodedata, re, time
import difflib
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement
from PIL import Image

SCUMMVM = False

parser = argparse.ArgumentParser(description='ES-scraper, a scraper for EmulationStation')
parser.add_argument("-w", metavar="value", help="defines a maximum width (in pixels) for boxarts (anything above that will be resized to that value)", type=int)
parser.add_argument("-noimg", help="disables boxart downloading", action='store_true')
parser.add_argument("-v", help="verbose output", action='store_true')
parser.add_argument("-f", help="force re-scraping (ignores and overwrites the current gamelist)", action='store_true')
parser.add_argument("-crc", help="CRC scraping", action='store_true')
parser.add_argument("-p", help="partial scraping (per console)", action='store_true')
parser.add_argument("-m", help="manual mode (choose from multiple results)", action='store_true')
parser.add_argument('-newpath', help="gamelist & boxart are written in $HOME/.emulationstation/%%NAME%%/", action='store_true')
parser.add_argument('-fix', help="temporary thegamesdb missing platform fix", action='store_true')
args = parser.parse_args()

def normalize(s):
   return ''.join((c for c in unicodedata.normalize('NFKD', unicode(s)) if unicodedata.category(c) != 'Mn'))

def fixExtension(file):    
    newfile="%s.%s" % (os.path.splitext(file)[0],imghdr.what(file))
    os.rename(file, newfile)
    return newfile

def readConfig(file):
    systems=[]
    config = ET.parse(file)
    configroot = config.getroot()
    for child in configroot:
        name = child.find('name').text
        path = child.find('path').text
        ext = child.find('extension').text
        pid = child.find('platformid').text
        if not pid:
            continue
        else:
            system=(name,path,ext,pid)
            systems.append(system)
            print name, path, ext, pid
    return systems

def crc(fileName):
    prev = 0
    for eachLine in open(fileName,"rb"):
        prev = zlib.crc32(eachLine, prev)
    return "%X"%(prev & 0xFFFFFFFF)

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def getPlatformName(id):
    url = "http://thegamesdb.net/api/GetPlatform.php"
    req = urllib2.Request(url, urllib.urlencode({'id':id}), headers={'User-Agent' : "RetroPie Scraper Browser"})
    data = urllib2.urlopen( req )
    platform_data = ET.parse(data)
    return platform_data.find('Platform/Platform').text

def exportList(gamelist):
    if gamelistExists and args.f is False:
        for game in gamelist.iter("game"):
            existinglist.getroot().append(game)

        indent(existinglist.getroot())
        ET.ElementTree(existinglist.getroot()).write("gamelist.xml")
        print "Done! %s updated." % os.getcwd()+"/gamelist.xml"
    else:
        indent(gamelist)
        ET.ElementTree(gamelist).write("gamelist.xml")
        print "Done! List saved on %s" % os.getcwd()+"/gamelist.xml"

def getFiles(base):
    dict=set([])
    for files in sorted(os.listdir(base)):
        if files.endswith(tuple(ES_systems[var][2].split(' '))):
            filepath=os.path.abspath(os.path.join(base, files))
            dict.add(filepath)
    return dict

def getGameInfo(file,platformID):
    title=re.sub(r'\[.*?\]|\(.*?\)', '', os.path.splitext(os.path.basename(file))[0]).strip()
    if args.crc:
        crcvalue=crc(file)
        if args.v:
            try:
                print "CRC for %s: %s" % (os.path.basename(file), crcvalue)
            except zlib.error as e:
                print e.strerror
        URL = "http://api.archive.vg/2.0/Game.getInfoByCRC/xml/7TTRM4MNTIKR2NNAGASURHJOZJ3QXQC5/%s" % crcvalue
        values={}
    else:
        URL = "http://thegamesdb.net/api/GetGame.php"
        platform = getPlatformName(platformID)
        if SCUMMVM: 
            title = getScummvmTitle(title)
            args.fix = True #Scummvm doesn't have a proper platformID so we search all
        if platform == "Arcade" or platform == "NeoGeo": title = getRealArcadeTitle(title)		
        
        if args.fix:
            try:                
                fixreq = urllib2.Request("http://thegamesdb.net/api/GetGamesList.php", urllib.urlencode({'name' : title, 'platform' : platform}), headers={'User-Agent' : "RetroPie Scraper Browser"})
                fixdata=ET.parse(urllib2.urlopen(fixreq)).getroot()
                if fixdata.find("Game") is not None:        

                    #values={ 'id': fixdata.findall("Game/id")[chooseResult(fixdata)].text if args.m else fixdata.find("Game/id").text }
                    values={ 'id': fixdata.findall("Game/id")[chooseResult(fixdata)].text if args.m else fixdata.findall("Game/id")[autoChooseBestResult(fixdata,title)].text }
					
            except:
                return None
        else:
            values={'name':title,'platform':platform}

    try:
        req = urllib2.Request(URL,urllib.urlencode(values), headers={'User-Agent' : "RetroPie Scraper Browser"})
        remotedata = urllib2.urlopen( req )
        data=ET.parse(remotedata).getroot()
    except ET.ParseError:
        print "Malformed XML found, skipping game.. (source: {%s})" % URL
        return None

    try:
        if args.crc:
            result = data.find("games/game")
            if result is not None and result.find("title").text is not None:
                return result
        elif data.find("Game") is not None:
            return data.findall("Game")[chooseResult(data)] if args.m else data.findall("Game")[autoChooseBestResult(data,title)]
        else:
            return None
    except Exception, err:
        print "Skipping game..(%s)" % str(err)
        return None

def getText(node):
    return normalize(node.text) if node is not None else None

def getTitle(nodes):
    if args.crc:
        return getText(nodes.find("title"))
    else:
        return getText(nodes.find("GameTitle"))

def getGamePlatform(nodes):
    if args.crc:
        return getText(nodes.find("system_title"))
    else:
        return getText(nodes.find("Platform"))
		
def getScummvmTitle(title):
    print "Fetching real title for %s from scummvm.org" % title
    URL  = "http://scummvm.org/compatibility/DEV/%s" % title.split("-")[0]
    data = "".join(urllib2.urlopen(URL).readlines())
    m    = re.search('<td>(.*)</td>', data)
    if m:
       print "Found real title %s for %s on scummvm.org" % (m.group(1), title)
       return m.groups()[0]
    else:
       print "No title found for %s on scummvm.org" % title
       return title		

def getRealArcadeTitle(title):
    print "Fetching real title for %s from mamedb.com" % title
    URL  = "http://www.mamedb.com/game/%s" % title
    data = "".join(urllib2.urlopen(URL).readlines())
    m    = re.search('<b>Name:.*</b>(.+) .*<br/><b>Year', data)
    if m:
       print "Found real title %s for %s on mamedb.com" % (m.group(1), title)
       return m.group(1)
    else:
       print "No title found for %s on mamedb.com" % title
       return title

def getDescription(nodes):
    if args.crc:
        return getText(nodes.find("description"))
    else:
        return getText(nodes.find("Overview"))

def getImage(nodes):
    if args.crc:
        return getText(nodes.find("box_front"))
    else:
        return getText(nodes.find("Images/boxart[@side='front']"))

def getTGDBImgBase(nodes):
    return nodes.find("baseImgUrl").text

def getRelDate(nodes):
    if args.crc:
        return None
    else:
        return getText(nodes.find("ReleaseDate"))

def getRating(nodes):
    if args.crc:
        return None
    else:
        return getText(nodes.find("Rating"))

def getPlayers(nodes):
    if args.crc:
        return None
    else:
        return getText(nodes.find("Players"))

def getPublisher(nodes):
    if args.crc:
        return None
    else:
        return getText(nodes.find("Publisher"))

def getDeveloper(nodes):
    if args.crc:
        return getText(nodes.find("developer"))
    else:
        return getText(nodes.find("Developer"))

def getGenres(nodes):
    genres=[]
    if args.crc and nodes.find("genre") is not None:
        for item in getText(nodes.find("genre")).split('>'):
            genres.append(item)
    elif nodes.find("Genres") is not None:
        for item in nodes.find("Genres").iter("genre"):
            genres.append(item.text)

    return genres if len(genres)>0 else None

def resizeImage(img,output):
    maxWidth= args.w
    if (img.size[0]>maxWidth):
        print "Boxart over %spx. Resizing boxart.." % maxWidth
        height = int((float(img.size[1])*float(maxWidth/float(img.size[0]))))
        img.resize((maxWidth,height), Image.ANTIALIAS).save(output)

def downloadBoxart(path,output):
    if args.crc:
        os.system("wget -q %s --output-document=\"%s\"" % (path,output))
    else:
        os.system("wget -q http://thegamesdb.net/banners/%s --output-document=\"%s\"" % (path,output))

def skipGame(list, filepath):
    for game in list.iter("game"):
        if game.findtext("path")==filepath:
            if args.v:
                print "Game \"%s\" already in gamelist. Skipping.." % os.path.basename(filepath)
            return True

def chooseResult(nodes):
    results=nodes.findall('Game')
    if len(results) > 1:
        for i,v in enumerate(results):
            try:
                print "[%s] %s | %s" % (i,getTitle(v), getGamePlatform(v))
            except Exception as e:
                print "Exception! %s %s %s" % (e, getTitle(v), getGamePlatform(v))

        return int(raw_input("Select a result (or press Enter to skip): "))
    else:
        return 0
        
def ToXMLDate(d):
	if d is not None:
		if len(d) == 10 :
			return time.strftime('%Y%m%dT%H%M%S', time.strptime(d, '%m/%d/%Y'))
		elif len(d) == 4:
			return time.strftime('%Y%m%dT%H%M%S', time.strptime('01/01/' + d, '%m/%d/%Y'))
		else:
			return None
	else:
		return None
		
		
def autoChooseBestResult(nodes,t):
    results=nodes.findall('Game')
    t = t.split('(', 1)[0]
    if len(results) > 1:

        sep = ' |' # remove platform name
        lista = []
        listb = []
        listc = []
        for i,v in enumerate(results): # Do it backwards to eliminate false positives
            a = (str(getTitle(v).split(sep, 1)[0]).split('(', 1)[0])
            lista.append(a)
            listb.append(i)
        listc = list(lista)
        listc.sort(key = len)
        x = 0
        for n in reversed(listc):
            s = difflib.SequenceMatcher(None, t, lista[lista.index(n)]).ratio()
            if s > x:
                x = s
                xx = lista.index(n)
        ss = int(x * 100)
        print "Game Title Found  " + str(ss) + "% Chance : " + lista[xx]
        return xx
    else:
        return 0

def scanFiles(SystemInfo):
    name=SystemInfo[0]
    if name == "scummvm":
        global SCUMMVM
        SCUMMVM = True
    folderRoms=SystemInfo[1]
    extension=SystemInfo[2]
    platformID=SystemInfo[3]

    global gamelistExists
    global existinglist
    gamelistExists = False

    gamelist = Element('gameList')
    folderRoms = os.path.expanduser(folderRoms)

    if args.newpath is False:
        destinationFolder = folderRoms;
    else:
        destinationFolder = os.environ['HOME']+"/.emulationstation/%s/" % name
    try:
        os.chdir(destinationFolder)
    except OSError as e:
        print "%s : %s" % (destinationFolder, e.strerror)
        return

    print "Scanning folder..(%s)" % folderRoms

    if os.path.exists("gamelist.xml"):
        try:
            existinglist=ET.parse("gamelist.xml")
            gamelistExists=True
            if args.v:
                print "Gamelist already exists: %s" % os.path.abspath("gamelist.xml")
        except:
            gamelistExists=False
            print "There was an error parsing the list or file is empty"

    for root, dirs, allfiles in os.walk(folderRoms, followlinks=True):
        allfiles.sort()
        for files in allfiles:
            if files.endswith(tuple(extension.split(' '))):
                try:
                    filepath=os.path.abspath(os.path.join(root, files))
                    filename = os.path.splitext(files)[0]
    
                    if gamelistExists and not args.f:
                        if skipGame(existinglist,filepath):
                            continue
    
                    print "Trying to identify %s.." % files
    
                    data=getGameInfo(filepath, platformID)
     
                    if data is None:
                        continue
                    else:
                        result=data
    
                    str_title=getTitle(result)
                    str_des=getDescription(result)
                    str_img=getImage(result)
                    str_rating=getRating(result)
                    str_rd=ToXMLDate(getRelDate(result))
                    str_pub=getPublisher(result)
                    str_dev=getDeveloper(result)
                    lst_genres=getGenres(result)
                    str_players=getPlayers(result)
    
                    if str_title is not None:
                        game = SubElement(gamelist, 'game')
                        path = SubElement(game, 'path')
                        name = SubElement(game, 'name')
                        desc = SubElement(game, 'desc')
                        image = SubElement(game, 'image')
                        releasedate = SubElement(game, 'releasedate')
                        rating = SubElement(game, 'rating')
                        publisher=SubElement(game, 'publisher')
                        developer=SubElement(game, 'developer')
                        #genres=SubElement(game, 'genres')
                        players=SubElement(game, 'players')
    
                        path.text=filepath
                        name.text=str_title
                        print "Game Found: %s" % str_title
    
                    if str_des is not None:
                        desc.text=str_des
    
                    if str_img is not None and args.noimg is False:
                        if args.newpath is True:
                            imgpath="./" + filename+os.path.splitext(str_img)[1]
                        else:
                            imgpath=os.path.abspath(os.path.join(root, filename+os.path.splitext(str_img)[1]))
    
                        print "Downloading boxart.."
    
                        downloadBoxart(str_img,imgpath)
                        imgpath=fixExtension(imgpath)
                        image.text=imgpath
    
                        if args.w:
                            try:
                                resizeImage(Image.open(imgpath),imgpath)
                            except:
                                print "Image resize error"
    
                    	
                    if str_rating is not None:
                        flt_rating = float(str_rating) / 10.0
                        rating.text = "%.6f" % flt_rating
                    else:
                        rating.text = "0.000000"
    
                    if str_rd is not None:
                        
                        releasedate.text=str_rd
    
                    if str_pub is not None:
                        publisher.text=str_pub
    
                    if str_dev is not None:
                        developer.text=str_dev

                    if str_players is not None:
                        players.text=str_players
    
                    if lst_genres is not None:
                        for genre in lst_genres:
                            newgenre = SubElement(game, 'genre')
                            newgenre.text=genre.strip()
                            break;
                except KeyboardInterrupt:
                    print "Ctrl+C detected. Closing work now..."
                except Exception as e:
                    print "Exception caught! %s" % e

    if gamelist.find("game") is None:
        print "No new games added."
    else:
        print "{} games added.".format(len(gamelist))
        exportList(gamelist)

try:
    if os.getuid()==0:
        os.environ['HOME']="/home/"+os.getenv("SUDO_USER")
    config=open(os.environ['HOME']+"/.emulationstation/es_systems.cfg")
except IOError as e:
    sys.exit("Error when reading config file: %s \nExiting.." % e.strerror)

ES_systems=readConfig(config)
print parser.description

if args.w:
    print "Max width set: %spx." % str(args.w)
if args.noimg:
    print "Boxart downloading disabled."
if args.f:
    print "Re-scraping all games.."
if args.v:
    print "Verbose mode enabled."
if args.crc:
    print "CRC scraping enabled."
if args.p:
    print "Partial scraping enabled. Systems found:"
    for i,v in enumerate(ES_systems):
        print "[%s] %s" % (i,v[0])
    try:
        var = int(raw_input("System ID: "))
        scanFiles(ES_systems[var])
    except:
        sys.exit()
else:
    for i,v in enumerate(ES_systems):
        scanFiles(ES_systems[i])

print "All done!"
import argparse
import datetime
import os
import sys
import requests
from tqdm import tqdm



class bcolors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


parser = argparse.ArgumentParser()
parser.add_argument("command", nargs='?', default='false', help="type of command")
parser.add_argument("-s", "--scene", help="satellite scene id")
parser.add_argument("-p", "--path", help="satellite scene path and row")
parser.add_argument("-b", "--bands", help="satellite bands")
parser.add_argument("-d", "--date", help="satellite date")
parser.add_argument("-c", "--clouds", help="prc of clouds")
args = parser.parse_args()


class Landsat:
    'Generates attributes for Landsat images'

    def __init__(self, scene, path):
      if scene != None:
        self.scene = scene
        self.path = scene[3:6]
        self.row = scene[6:9]
        self.band_url = "http://landsat-pds.s3.amazonaws.com/L8/" + self.path + "/" + self.row + "/" + self.scene + "/" + self.scene 

      elif scene == None:
        path = path.split(',')
        self.path = path[0]
        self.row = path[1]
        self.api_url = "https://api.developmentseed.org/satellites?search=satellite_name:landsat-8+AND+((path:" + self.path + "+AND+row:" + self.row + "))&limit=2000"
  
    def get_tile_folder(self):
        return ["_B1.TIF", "_B2.TIF", "_B3.TIF", "_B4.TIF", "_B5.TIF", "_B6.TIF", "_B7.TIF", "_B8.TIF", "_B9.TIF", "_B10.TIF", "_B11.TIF", "_BQA.TIF", "_MTL.txt"]


class Sentinel:
    'Generates attributes for Sentinel images'

    def __init__(self, scene, path):
      if scene != None:
        self.scene = scene
        self.utm_code = scene[18:20]
        self.lat_band = scene[20]
        self.square = scene[21:23]
        self.year = scene[9:13]
        self.month = scene[13:15]
        self.day =  scene[15:17]
        self.sequence = scene[-1]
        if self.month[0] == "0": #check for zeroes
            self.month = self.month[1]
        if self.day[0] == "0":
            self.day = self.day[1]
        self.band_url = "http://sentinel-s2-l1c.s3.amazonaws.com/tiles/" + self.utm_code + "/" + self.lat_band + "/" + self.square + "/" + self.year + "/" + self.month + "/" + self.day + "/" + self.sequence + "/"

      elif scene == None:
        self.utm_code = path[0:2]
        self.lat_band = path[2]
        self.square = path[3:5]
        self.api_url = "https://api.developmentseed.org/satellites?search=satellite_name:sentinel-2+AND+((grid_square:" + self.square + "+AND+latitude_band:" + self.lat_band + "+AND+utm_zone:" + self.utm_code + "))&limit=2000"
  
    def get_tile_folder(self):
        return ["B01.jp2", "B02.jp2", "B03.jp2", "B04.jp2", "B05.jp2", "B06.jp2", "B07.jp2", "B08.jp2", "B09.jp2", "B10.jp2", "B11.jp2", "B12.jp2", "productInfo.json"]


command = args.command.lower() #type of command
scene = args.scene
input_path = args.path
urls = []
bulk_ids = []


def get_list(pic):
    api_url = getattr(pic, 'api_url')
    r = requests.get(api_url)
    status = r.status_code
    if status == 200: 
        return r.json()
    else: 
        sys.exit(bcolors.FAIL + str(status) + " ERROR. Please check later." + bcolors.ENDC)


def create_directory(pic):
    home = os.path.expanduser("~")
    pictures_directory = home + "/openasat/"
    if not os.path.exists(pictures_directory):
        os.mkdir(os.path.expanduser(pictures_directory))

    satellite_directory = pictures_directory + satellite
    if not os.path.exists(satellite_directory):
        os.mkdir(os.path.expanduser(satellite_directory))

    scene_directory = satellite_directory + "/" + getattr(pic, 'scene') 
    if not os.path.exists(scene_directory):
        os.mkdir(os.path.expanduser(scene_directory))

    return scene_directory


def scene_links(pic):
    band_url = getattr(pic, 'band_url')

    if args.bands == None:  #download all files
        tile_folder = pic.get_tile_folder()
        for tile in tile_folder:
            urls.append( band_url + tile)

    else:  #download seperate bands
        bands = args.bands.split(',')
        for band in bands:
            if satellite == "landsat":
                url = band_url + "_B" + band + ".TIF"
                urls.append(url)
            else:
                if len(band) == 1:
                    band = band.zfill(2)
                url = band_url + "B" + band + ".jp2"
                urls.append(url)


def download(pic):
    dowloaded_path = create_directory(pic)
    for url in urls:
        local_filename = url.split('/')[-1]
        check = os.path.isfile(dowloaded_path + "/" + local_filename)
        if check == True:
            print bcolors.WARNING + local_filename + " is already downloaded" + bcolors.ENDC 
        else: 
            print "Downloading " + local_filename
            response = requests.get(url, stream=True, timeout=120)
            local_filename = url.split('/')[-1]
            file_chunk_size = int(response.headers['content-length'])/99
            with open(dowloaded_path + "/" + local_filename, 'wb') as f:
                for chunk in tqdm(response.iter_content(chunk_size = file_chunk_size), unit='%'):
                    f.write(chunk)
            print bcolors.OKGREEN + "Success! " + local_filename + " is downloaded!" + bcolors.ENDC 
            print "This file is saved to " + dowloaded_path
            print " "


def bulk_objects():
    for  val in bulk_ids:
        if satellite == "landsat":
            val = Landsat(val, None)
        elif satellite == "sentinel":
            val = Sentinel(val,None)
        scene_links(val)
        download(val)


def query_yes_no(question):
  
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}

    sys.stdout.write(bcolors.WARNING + question + bcolors.ENDC)
    choice = raw_input().lower()
    if choice in valid:
        if valid[choice] == True:
            print "Downloading collection of scenes..."
            bulk_objects()
    else:
        sys.stdout.write(bcolors.FAIL + "Invalid answer. Please respond with 'yes' or 'no'.\n" + bcolors.ENDC)

cloud_cases = 0
max_cloud = 0
min_cloud = 100 

def search_results(pic):
    search = get_list(pic)
    print bcolors.OKGREEN + "===== List of scenes: =====" + bcolors.ENDC
    print " "


    def print_match():
        global cloud_cases, max_cloud, min_cloud
        cloud_cases += 1
        if scene["cloud_coverage"] > max_cloud: max_cloud = scene["cloud_coverage"]
        if scene["cloud_coverage"] < min_cloud: min_cloud = scene["cloud_coverage"]
        bulk_ids.append(scene["scene_id"])
        print "scene id: " + bcolors.OKGREEN + scene["scene_id"] + bcolors.ENDC
        print "date:", scene["date"]
        print "cloud coverage:", str(scene["cloud_coverage"]) + "%"
        print "preview:", scene["thumbnail"]
        print " "

    def print_summary():
        print " "
        print "======= SEARCH SUMMARY ======= "
        if cloud_cases > 0:
            print bcolors.OKGREEN + str(cloud_cases) + " scenes were found for the search area" + bcolors.ENDC
            print bcolors.OKGREEN + "The min cloud coverage is " + str(min_cloud) + "%" + bcolors.ENDC
            print bcolors.OKGREEN + "The max cloud coverage is "  +  str(max_cloud) + "%" + bcolors.ENDC
            query_yes_no("Do you want to download all "+ str(cloud_cases) + " scenes? " + "[y/n]")
        else:
            print bcolors.FAIL + "No results were found" + bcolors.ENDC


    if args.clouds != None: #check for clouds condition
        clouds = float(args.clouds)
        for scene in search["results"]: 
            if scene["cloud_coverage"] <= clouds:
                print_match()
        print_summary()

    elif args.date != None: #check for date condition
        date = args.date.split(",")
        date_start = datetime.datetime.strptime(date[0], "%Y-%m-%d")
        date_end = datetime.datetime.strptime(date[1], "%Y-%m-%d")
        for scene in search["results"]: 
            data_scene = datetime.datetime.strptime(scene["date"], "%Y-%m-%d")
            if (data_scene < date_end) & (data_scene > date_start):
                print_match()
        print_summary()

    elif (args.clouds != None) & (args.date != None): #check for cloud and date conditions
        clouds = float(args.clouds)
        date = args.date.split(",")
        date_start = datetime.datetime.strptime(date[0], "%Y-%m-%d")
        date_end = datetime.datetime.strptime(date[1], "%Y-%m-%d")
        for scene in search["results"]: 
            data_scene = datetime.datetime.strptime(scene["date"], "%Y-%m-%d")
            if (data_scene < date_end) & (data_scene > date_start) & scene["cloud_coverage"] <= clouds:
                print_match()
        print_summary()
             
    else: # print all scenes
        for scene in search["results"]:
            print_match()
        print_summary()


if scene == None and input_path != None:
    if "," in input_path:
        satellite = "landsat"
        picture = Landsat(None, input_path)
    elif "," not in input_path:
        satellite = "sentinel"
        picture = Sentinel(None, input_path) 


if command == "search":
    search_results(picture)


elif command == "download":
    if scene != None and scene[0] == "L": # Check satellite and type of command 
        satellite = "landsat"
        picture = Landsat(scene, None)
    if scene != None and scene[0] == "S":
        satellite = "sentinel"
        picture = Sentinel(scene, None)
    scene_links(picture)
    download(picture)

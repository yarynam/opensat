import argparse
import datetime
import os
import requests
import sys
from tqdm import tqdm
from processing import *
from mask import *



parser = argparse.ArgumentParser()
parser.add_argument("command", nargs='?', default='false', help="type of command")
parser.add_argument("-s", "--scene", help="satellite scene id")
parser.add_argument("-l", "--location", help="satellite scene path and row")
parser.add_argument("-b", "--bands", help="satellite bands")
parser.add_argument("-d", "--date", help="satellite date")
parser.add_argument("-c", "--clouds", help="prc of clouds")
parser.add_argument("-p", "--processing", help="prc of clouds")
parser.add_argument("-m", "--mask", help="prc of clouds")
args = parser.parse_args()


class bcolors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


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

    def get_all_bands(self):
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

    def get_all_bands(self):
        return ["B01.jp2", "B02.jp2", "B03.jp2", "B04.jp2", "B05.jp2", "B06.jp2", "B07.jp2", "B08.jp2", "B09.jp2", "B10.jp2", "B11.jp2", "B12.jp2", "tileInfo.json"]



command = args.command.lower()   #type of command
scene = args.scene  #scene ID
location = args.location  #scene path
processing_bands = args.processing
mask = args.mask
search_matches = []  #list of bands IDs


def get_list(pic):  #get json from developmentseed API
    api_url = getattr(pic, 'api_url')
    print api_url
    r = requests.get(api_url)
    status = r.status_code
    if status == 200:
        return r.json()
    else:
        sys.exit(bcolors.FAIL + str(status) + " ERROR. Please check later." + bcolors.ENDC)


def create_directory(pic): #check if directory exists and craete if needed
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


def scene_links(pic): #create links for particular scene
    band_url = getattr(pic, 'band_url')
    all_bands = pic.get_all_bands()
    if args.bands == None:  #download all files
        urls = [band_url + band for band in all_bands]
    else:  #download seperate bands
        bands = args.bands.split(',')
        if satellite == "landsat":
            urls = [band_url + "_B" + band + ".TIF" for band in bands]
            urls.append(band_url + "_MTL.txt")
        else:
            bands = [band.zfill(2) if len(band) == 1 else band for band in bands]
            urls = [band_url + "B" + band + ".jp2" for band in bands]
            urls.append(band_url + "tileInfo.json")
    return urls


def download(pic):
    dowloaded_path = create_directory(pic)
    urls = scene_links(pic)
    for url in urls:
        local_filename = url.split('/')[-1]
        check = os.path.isfile(dowloaded_path + "/" + local_filename)
        if check == True:
            print local_filename + " is already downloaded"
        else:
            for i in range(10):
                try:
                    response = requests.get(url, stream=True)
                    # response = requests.get(url, stream=True, timeout=240)
                    local_filename = url.split('/')[-1]
                    headers = response.headers
                    if "content-length" not in headers:
                        print bcolors.FAIL + "Ooops... SERVER ERROR. Looks like " + local_filename + " doesn't exist" + bcolors.ENDC
                    else:
                        print "Downloading " + local_filename
                        file_chunk_size = int(headers['content-length'])/99
                        with open(dowloaded_path + "/" + local_filename, 'wb') as f:
                            for chunk in tqdm(response.iter_content(chunk_size = file_chunk_size), unit='%'):
                                f.write(chunk)
                        print bcolors.OKGREEN + "Success! " + local_filename + " is downloaded!" + bcolors.ENDC
                        print "This file is saved to " + dowloaded_path + "\n"
                except requests.exceptions.Timeout:
                    continue
                break
    # is_processing()


def processing(bands):
    if satellite == "landsat" and "8" in bands:
        process = PanSharpen(scene, bands, satellite)
        process.run()
    else:
        if command == "search":
            for match in search_matches:
                process = Processing(match['id'], bands, satellite)
                process.run()
        elif command == "download":
            process = Processing(scene, bands, satellite)
            process.run()
    if mask != None:
        mask_img = Mask(process.output_file, mask)
        mask_img.run()



def bulk_objects(): # download multiple scenes
    for match in search_matches:
        if satellite == "landsat":
            scene_d = Landsat(match["id"], None)
        elif satellite == "sentinel":
            scene_d = Sentinel(match["id"],None)
        download(scene_d)
    if processing_bands != None:
        processing(processing_bands)




def download_yes_no(question): #bulk download prompt
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


def search_results(pic):  #print search results
    search = get_list(pic)
    print bcolors.OKGREEN + "===== List of scenes: =====" + bcolors.ENDC + "\n"

    def print_match():
        search_matches.append({'id': scene["scene_id"], 'clouds': scene["cloud_coverage"]})
        print "scene id: " + bcolors.OKGREEN + scene["scene_id"] + bcolors.ENDC
        print "date:", scene["date"]
        print "cloud coverage:", str(scene["cloud_coverage"]) + "%"
        print "preview:", scene["thumbnail"] + "\n"

    def print_summary():
        match_cases = len(search_matches)
        min_cloud = min(search_match['clouds'] for search_match in search_matches)
        max_cloud = max(search_match['clouds'] for search_match in search_matches)
        print "\n======= SEARCH SUMMARY ======="
        if match_cases > 0:
            print bcolors.OKGREEN + str(match_cases) + " scenes were found for the search area" + bcolors.ENDC
            print bcolors.OKGREEN + "The min cloud coverage is " + str(min_cloud) + "%" + bcolors.ENDC
            print bcolors.OKGREEN + "The max cloud coverage is "  +  str(max_cloud) + "%" + bcolors.ENDC
            download_yes_no("Do you want to download all scenes? " + "[y/n]")
        else:
            print bcolors.FAIL + "No results were found" + bcolors.ENDC


    if (args.clouds != None) & (args.date != None): #check for cloud and date conditions
        clouds = float(args.clouds)
        date = args.date.split(",")
        date_start = datetime.datetime.strptime(date[0], "%Y-%m-%d")
        date_end = datetime.datetime.strptime(date[1], "%Y-%m-%d")
        for scene in search["results"]:
            data_scene = datetime.datetime.strptime(scene["date"], "%Y-%m-%d")
            if (data_scene < date_end) & (data_scene > date_start) & (scene["cloud_coverage"] <= clouds):
                print_match()
        print_summary()

    elif args.clouds != None: #check for clouds condition
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

    else: # print all scenes
        for scene in search["results"]:
            print_match()
        print_summary()


if scene == None and location != None:
    if "," in location:
        satellite = "landsat"
        picture = Landsat(None, location)
    elif "," not in location:
        satellite = "sentinel"
        picture = Sentinel(None, location)


if command == "search":
    search_results(picture)


elif command == "download":
    if scene != None and scene[0] == "L": # Check satellite and type of command
        satellite = "landsat"
        picture = Landsat(scene, None)
    if scene != None and scene[0] == "S":
        satellite = "sentinel"
        picture = Sentinel(scene, None)
    download(picture)
    if processing_bands != None:
        processing(processing_bands)

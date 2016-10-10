import argparse
import os
import requests
from tqdm import tqdm

class bcolors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


parser = argparse.ArgumentParser()
parser.add_argument("command", help="type of command")
parser.add_argument("-s", "--scene", help="satellite scene id")
parser.add_argument("-p", "--path", help="satellite scene path and row")
parser.add_argument("-b", "--bands", help="satellite bands")
parser.add_argument("-d", "--date", help="satellite date")
parser.add_argument("-c", "--clouds", help="prc of clouds")
parser.add_argument('download', nargs='?', default='false')
args = parser.parse_args()


# LC80020262016269LGN00
# "20161005_18TYM_0"
command = args.command.lower() #type of command
scene = args.scene


if args.scene != None and scene[0] == "L":
    satellite = "landsat"
    path = scene[3:6]
    row = scene[6:9]

elif args.scene != None and scene[0] == "S":
    satellite = "sentinel"
    utm_code = scene[18:20]
    lat_band = scene[20]
    square = scene[21:23]
    year = scene[9:13]
    month = scene[13:15]
    day =  scene[15:18]
    sequence = scene[-1]

    if month[0] == "0": #check for zeroes
        month = month[1]
    if day[0] == "0":
        day = day[1]

    sentinel_path = utm_code + "/" + lat_band + "/" + square + "/" + year + "/" + month + "/" + day + "/" + sequence + "/"

elif args.scene == None and "," in args.path:
    satellite = "landsat"
    path = args.path[0]
    row = args.path[1]

elif args.scene == None and "," not in args.path:
    satellite = "sentinel"
    utm_code = args.path[0:2]
    lat_band = args.path[2]
    square = args.path[3:5]

urls = []

def get_list():
    if satellite == "landsat":
        api_url = "https://api.developmentseed.org/satellites?search=satellite_name:landsat-8+AND+((path:" + path + "+AND+row:" + row + "))&limit=2000"
    else:
        api_url = "https://api.developmentseed.org/satellites?search=satellite_name:sentinel-2+AND+((grid_square:" + square + "+AND+latitude_band:" + lat_band + "+AND+utm_zone:" + utm_code + "))&limit=2000"
    r = requests.get(api_url)
    return r.json()


def search_results():
    search = get_list()
    print bcolors.OKGREEN + str(len(search['results'])) + " scenes were found for the search area" + bcolors.ENDC
    print bcolors.WARNING + "The min cloud coverage is " + str(min(scene["cloud_coverage"] for scene in search['results'])) + "%" + bcolors.ENDC
    print bcolors.WARNING + "The max cloud coverage is "  +  str(max(scene["cloud_coverage"] for scene in search['results'])) + "%" + bcolors.ENDC
    print " "
    print bcolors.OKGREEN + "===== List of scenes: =====" + bcolors.ENDC
    print " "
    for scene in search["results"]:
        print "scene id: " + bcolors.OKGREEN + scene["scene_id"] + bcolors.ENDC
        print "date:", scene["date"]
        print "cloud coverage:", str(scene["cloud_coverage"]) + "%"
        print "preview:", scene["thumbnail"]
        print " "


def create_directory():
    satellite_directory = satellite
    if not os.path.exists(satellite_directory):
        os.makedirs(satellite_directory)

    scene_directory = satellite + "/" + scene
    if not os.path.exists(scene_directory):
        os.makedirs(scene_directory)


def scene_links():
    if args.bands == None:  #download all files
        if satellite == "landsat":
            urls.append("https://s3.amazonaws.com/geotrellis-sample-datasets/landsat/" + scene + ".tar.bz")
        elif satellite == "sentinel":
            tile_folder = ["B01.jp2", "B02.jp2", "B03.jp2"]
            for pic in tile_folder:
                urls.append("http://sentinel-s2-l1c.s3.amazonaws.com/tiles/" + sentinel_path + pic)

    else:  #download seperate bands
        bands = list(args.bands)
        for band in bands:
            if satellite == "landsat":
                url = "http://landsat-pds.s3.amazonaws.com/L8/" + path + "/" + row + "/" + scene + "/" + scene + "_B" + band + ".TIF"
                urls.append(url)


def download():
    create_directory()
    for url in urls:
        local_filename = url.split('/')[-1]
        print "Downloading " + local_filename
        response = requests.get(url, stream=True)
        local_filename = url.split('/')[-1]
        file_chunk_size = int(response.headers['content-length'])/99
        with open( satellite + "/" + scene + "/" + local_filename, 'wb') as f:
            for chunk in tqdm(response.iter_content(chunk_size = file_chunk_size), unit='%'):
                f.write(chunk)

        print bcolors.OKGREEN + "Success! " + local_filename + " is downloaded!" + bcolors.ENDC


if args.command == "search":
    search_results()
else:
     scene_links()
     download()

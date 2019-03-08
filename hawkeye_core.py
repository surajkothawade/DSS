# constants
ESUN = [1853.76, 1589.78, 1094.4, 237.03]
Lmin = [0, 0, 0, 0]
Lmax = [52.00, 47.00, 31.5, 8.00]
months = ['', 'jan', 'Feb', 'Mar', 'Apr', 'may',
          'jun', 'jul', 'aug', 'Sep', 'Oct', 'nov', 'dec']
# SparseFeature_Water = {} # Format: #SparseFeature_Water{"FolderName" : [((featureIndex),(featureVec))]}

#global made_dir
# imports
from pymongo import MongoClient
import timeit
from bs4 import BeautifulSoup
import urllib2
from math import cos, sin, acos
import datetime
from datetime import date
import glob
import os
import sys
import numpy as np
from math import ceil
#from matplotlib import pyplot as plt
from PIL import Image
import multiprocessing
folder_for_output = ""
get_date_for_name = ""
get_tile_for_name = ""

client = MongoClient("mongodb://localhost:27017")

# db=client.water_burnt_perc #database created

db1 = client.sparsefeatures_water  # database created


def store_water_in_database(folder_name, index, b2, b3, b4, b5, NDVI, BRT, color):
    # collections=db1.collection_names()
    dbentry = {
        'index': index,
        'b2': b2,
        'b3': b3,
        'b4': b4,
        'b5': b5,
        'NDVI': NDVI,
        'BRT': BRT,
        'color': color
    }
    dbresult = db1[folder_name].insert_one(dbentry)


db2 = client.sparsefeatures_burnt  # database created


def store_burnt_in_database(folder_name, index, b2, b3, b4, b5, NDVI, BRT, BAIM, color):
    # collections=db2.collection_names()
    dbentry = {
        'index': index,
        'b2': b2,
        'b3': b3,
        'b4': b4,
        'b5': b5,
        'NDVI': NDVI,
        'BRT': BRT,
        'BAIM': BAIM,
        'color': color
    }
    dbresult = db2[folder_name].insert_one(dbentry)


db = client.image_output


def store_in_database(folder_name, water, burnt):
    # collections=db.collection_names()
    dbentry = {
        'folder_name': folder_name,
        'water_percentage': water,
        'burnt_area_percentage': burnt
    }
    dbresult = db.image_output.insert_one(dbentry)


#	***functions***
#	11] day_of_year is a function used to calculate the difference of two dates, 1-Jan-1900 is the start date where days are calculated in between...(it is used in calculation of Solar Zenith Angle)
def day_of_year(d, m, y):
    d = int(d)
    m = int(m)
    y = int(y)
#	12] given_date is the date given on that file
    given_date = datetime.date(y, m, d)
#	13] reference_date is 1-jan-1900, constant value
    reference_date = datetime.date(1900, 1, 1)
    delta = given_date - reference_date
#	14] this excludes those 2 days, but for calculation, those 2 days are taken for the count in the formula
    return (delta.days + 2)

#	15] Function to find TOA for a particular Band of a particular date


def get_TOA(my_string, j, my_longitude, my_latitude):  # j is the index considered for bands
    print multiprocessing.current_process().name, " Working on : " + my_string
    image_name = my_string.split("/")[-1]
    date = image_name[17:24]  # i) for above function used viz day_of_year
    # ii) for getting Solar-earth dist in astronomical units from required_dict below
    date2 = image_name[17:22]
    index = 0
    # iii) index is used to get value of dist from that matched date
    d = required_dict[date2.lower()]
    d = float(d)
    dd = date[:2]
    month = date[2:5]
    yy = date[5:7]
    mm = 0
    dd = int(dd)
    for index in range(len(months)):
        if (month.lower() == months[index].lower()):
            # This converts (month as a character) into (month as a number) e.g. (mar -> 3), (sep -> 9)
            mm = int(index)
    # just for converting the given format of year in the format as 20xx, e.g : year 13 -> 2013.
    yy = int('20' + yy)
    # iv) formula given in xlsx file for calculation of solar zenith angle
    doy = day_of_year(dd, mm, yy) - 39447
    # Gamma is fractional year w.r.t. year
    gamma = float(float((2 * 3.14159) * float(doy - 1)) / 365)
    eqtime = 229.18 * (0.000075 + 0.001868 * cos(gamma) - 0.032077 *
                       sin(gamma) - 0.014615 * cos(2 * gamma) - 0.040849 * sin(2 * gamma))
    decl = 0.006918 - 0.399912 * cos(gamma) + 0.070257 * sin(gamma) - 0.006758 * cos(2 * gamma) + 0.000907 * sin(
        2 * gamma) - 0.002697 * cos(3 * gamma) + 0.00148 * sin(3 * gamma)  # declination angle
    time_offset = eqtime - 4 * my_longitude + 60 * 5.5  # longitude is in degrees
    tst = 12 * 60 + time_offset  # true solar time
    ha = ((tst / 4) - 180) * 3.14159 / 180  # hour angle
    lat_in_rad = (my_latitude * 3.14159 / 180)  # converting to radians
    sz = 180 * (acos((sin(lat_in_rad) * sin(decl)) + (cos(lat_in_rad) *
                                                      cos(decl) * cos(ha)))) / 3.14159  # sz - Solar Zenith Angle in radians
    sz = 3.14159 * sz / 180		# converting back to degrees
    cos_of_sz = cos(sz)		# cos(Solar Zenith Angle)
    List_of_Pixel = []		# List of all the pixel in an image
    img = Image.open(my_string)
    arr = np.array(img)
    img.close()
    TOA_refl = []
    for each_row in arr:
        TOA_each_row = []
        for each_pixel in each_row:
            if(each_pixel != 0):
                L_rad = float(Lmax[j] * float(each_pixel) / ((2**12) - 1))
            # TOA reflectance is the required output for current image
            TOA = (3.14159 * L_rad * d * d) / (ESUN[j] * cos_of_sz)
            TOA_each_row.append(TOA)
        TOA_refl.append(TOA_each_row)
    return TOA_refl


#	1] Getting the Solar-Earth Distance data file ***esd.txt***
fp = open('esd.txt')
lines = fp.read().split("\n")
data = [[]]
for each_line in lines:
    each_word = each_line.split(" ")
    data.append(each_word)
data = data[1:367]  # for removing extra first empty list_item
#	2] Finding day number, date, and Solar-Earth Distance data for all 1 - 366 days and storing them in their individual lists
#index_list_of_day = []
dist = []
date = []
for x in data:
    #	index_list_of_day.append(x[0])
    dist.append(x[1])
    date.append(x[2])
dist = map(float, dist)
#index_list_of_day = map(int,index_list_of_day)
#	3] Finding the date in proper format by removing '/' such that list will be like [[4,7,2012],[5,9,2012]].i.e. sub_date is list format of date
sub_date = []
for each_date in date:
    value = each_date.split('/')
    sub_date.append(value)
#	4] Proper date is nothing but just like the date used in the names_folderwise of images for extracting distance on that date
#	e.g. 04Oct , 09Mar, 25nov for all 366 days, as year is not necessary for distance calculation in esd.txt file

proper_date = []
for each_list_of_subdate in sub_date:
    month_in_numbers = int(each_list_of_subdate[1])
    file_name_like_date = str(
        each_list_of_subdate[0] + months[month_in_numbers])
    if(len(file_name_like_date) == 5):
        proper_date.append(file_name_like_date)
    else:
        file_name_like_date = str(0) + file_name_like_date
        proper_date.append(file_name_like_date)
proper_date = [p.lower() for p in proper_date]
#	5] required_dict is merging of proper_date with dist, so that for a particular image, just matching the date will be enough to find the distance on that index only,  e.g. [['05sep', '12Oct', '01jan'],[1.0080019, 0.9977524, 0.9833098]]
# Code Review Suraj: We should make required_dict as a dictionary
required_dict = dict(zip(proper_date, dist))
#	6] list_of_names is List of Names of all the files in Folder containing all your data files (The code is in the same Folder Duh.)
# list_of_names = []
# for file in glob.glob("*.tif"):
# 	list_of_names.append(file)
# list_of_names.sort()


def get_longitude(string_name):
    infile = open(string_name, "r")
    contents = infile.read()
    soup = BeautifulSoup(contents, 'lxml')
    titles = soup.find_all('upper_left')
    longitude = titles[0].text
    longitude = longitude[4:7]
    l1 = longitude
    if ('N' or 'S' in longitude):
        longitude = int(l1[0:2])
    else:
        longitude = int(l1)
    return longitude


def get_latitude(string_name):
    infile = open(string_name, "r")
    contents = infile.read()
    soup = BeautifulSoup(contents, 'xml')
    titles = soup.find_all('upper_left')
    if(len(titles) == 0):  # Handling the First Character Error bs4 had
        titles = soup.find_all('Upper_left')
    latitude = titles[0].text
    latitude = latitude[13:16]
    l2 = latitude
    if ('E' or 'W' in latitude):
        latitude = int(l2[0:2])
    else:
        latitude = int(l2)
    return latitude

#	7] ndvi_list is a list of values formed by the calculation of bands of a particular image
#		e.g : for date 05Sep2013, for tile H44B, By calculating TOA reflectance of B2,B3,B4,B5 and using formula:
#		NDVI = (B2-B4)/(B2+B4) we'll get that date's NDVI of that Tile,  so it is a list of such values
#	8] Same is the case for brt_list, it is summation of TOA reflectance values of all 4 bands, and brt_list is brightness, i.e. sum(b2,b3,b4,b5)
###ndvi_list = []
###brt_list = []
#	9] Names_folderwise is a list of names of those files, but it has sub-list like [['12oct13-Band2.tiff','12oct13-Band3.tiff','12oct13-Band4.tiff','12oct13-Band5.tiff'],['09Sep13-Band2.tiff','09Sep-Band3.tiff','09Sep-Band4.tiff','09Sep-Band5.tiff'],...[],...[]] such 29 sub-lists e.g.

# Commented by Suraj - Uncomment to restore
# names_folderwise = [list_of_names[i:i+4] for i in range(0, len(list_of_names), 4)]
# print "Names_folderwise is ", names_folderwise

#	10] toa_of_all_folders is a list of sub-lists of toa of bands given on that specific date of that specific tile
#		e.g : [[value(09oct12_b2_toa),value(09oct12_b3_toa),value(09oct12_b4_toa),value(09oct12_b5_toa)],	[value(05sep13_b2_toa),value(05sep13_b3_toa),value(05sep13_b4_toa),value(05sep13_b5_toa)]...[]] 29 such sub-lists
#my_toa = get_TOA(names_folderwise[0][0],0)
#a = np.array(my_toa)
#img = Image.fromarray(np.uint16(a) , 'L')
# img.show()


def save_image_water(np_arr, its_name):
    result = Image.fromarray(np_arr)
    result.save("output_water/" + its_name)


def save_image_burnt(np_arr, its_name):
    result = Image.fromarray(np_arr)
    result.save("output_burnt/" + its_name)


waterbody_outputs = []
burntarea_outputs = []
water_percentage = []
#ndvi_all = []
#brt_all = []
#toa_of_all_folders = []
# Creating function for iterating through the folders


def process_folder(folder_path):
    start = timeit.default_timer()
    folder_name = folder_path.split("/")[-1]
    #SparseFeature_Water[folder_name] = []
#	print multiprocessing.current_process().name ," Currently working on folder ", folder_path
    files = os.listdir(folder_path)
    each_folder = []
    for file in files:
        if(file.endswith(".tif")):
            each_folder.append(file)
    each_folder.sort()
#	print multiprocessing.current_process().name ," Currently working on image ", each_folder
#	print("Task assigned to Process: {}".format(multiprocessing.current_process().name))
#	print("ID of process running task 1: {}".format(os.getpid()))
    get_date_for_name = each_folder[0][17:24]
    get_tile_for_name = each_folder[0][3:8]
    folder_name = get_tile_for_name + "_" + get_date_for_name
    my_xml = each_folder[0].replace('-BAND2.tif', '.xml')
    my_xml = folder_path + "/" + my_xml
    longitude = get_longitude(my_xml)
    latitude = get_latitude(my_xml)
#	print longitude,latitude
    toa_of_each_folder = []
    for i in range(len(each_folder)):
        toa_of_each_folder.append(
            get_TOA(folder_path + "/" + each_folder[i], i, longitude, latitude))
    # toa_of_all_folders.append(toa_of_each_folder)
    waterbody_image = []
    burned_area_image = []
    non_water_pixel_count = 0.0
    water_pixel_count = 0.0
    burnt_pixel_count = 0.0
    non_burnt_pixel_count = 0.0
    for row in range(len(toa_of_each_folder[0])):
        waterbody_row = []
        burned_area_row = []
        for each_pixel in range(len(toa_of_each_folder[0][row])):
            b2 = toa_of_each_folder[0][row][each_pixel]
            b3 = toa_of_each_folder[1][row][each_pixel]
            b4 = toa_of_each_folder[2][row][each_pixel]
            b5 = toa_of_each_folder[3][row][each_pixel]
            NDVI = -(b3 - b4) / (b3 + b4)
            BRT = b2 + b3 + b4 + b5
            baim = 1 / ((0.05 - b4)**2 + (0.02 - b5)**2)
            if(BRT < 0.075 and (b3 - b2 != 0)):
                if((b2 > b3) and ((b2 > b4) or (b2 > b5))):
                    if((b3 > b4) and (b2 > b4)):
                        water_pixel_count += 1.0
                        waterbody_row.append(255.0)  # make water as white
                        #SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 255.0))
                        store_water_in_database(
                            folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 255.0)
                    else:
                        if((b2 > b5) and (NDVI < 0.05) and (b3 > (0.9 * b2)) and (b4 < (1.1 * b2)) and ((b5 > (0.92 * b4)) or (b5 > (0.92 * b2)))):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)
                            #SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        elif((b2 > (0.8 * b3)) and (NDVI < 0.03) and ((b2 > b4) and ((0.7 * b2) > b5))):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)  # make water as white
                            #SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        elif((b2 > (0.9 * b4)) and (b3 > (0.9 * b5)) and (NDVI < 0.0325)):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)  # make water as white
                            #SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        elif((0.0325 < BRT < 0.05) and (NDVI < 0.05) and (b5 < (0.85 * b2)) and (b4 < (1.1 * b5)) and ((b3 > (0.75 * b2))) or (b2 > b4)):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)  # make water as white
                            #SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        elif((b2 > b4) and (b5 < (0.8 * b2)) and (b3 > (0.9 * b2)) and (NDVI < 0.05)):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)  # make water as white
                            #SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        elif((BRT < 0.05) and (NDVI < 0.05) and (b2 > (0.9 * b5)) and (b2 > b4) and (b4 > (1.3 * b5))):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)  # make water as white
                            #SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        else:
                            non_water_pixel_count += 1.0
                            waterbody_row.append(0.0)
                else:
                    non_water_pixel_count += 1.0
                    waterbody_row.append(0.0)
            elif(0.075 < BRT <= 0.10):
                if((b2 > 1.4 * b5) and (b3 > 1.6 * b5)):
                    if((b2 > 0.8 * b4) and (b3 > 1.1 * b4)):
                        water_pixel_count += 1.0
                        waterbody_row.append(63.0)  # make water as white
                        #SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 63.0))
                        store_water_in_database(
                            folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 63.0)
                    else:
                        non_water_pixel_count += 1.0
                        waterbody_row.append(0.0)
                elif((BRT < 0.1075) and (1.1 * b2 > b3) and((b2 > b4) or (b2 > b5))):
                    if((b3 > b4) and (b2 > b5)):
                        water_pixel_count += 1.0
                        waterbody_row.append(63.0)  # make water as white
                        #SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 63.0))
                        store_water_in_database(
                            folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 63.0)
                    else:
                        non_water_pixel_count += 1.0
                        waterbody_row.append(0.0)
                elif((BRT < 0.1) and (b2 > 1.6 * b5) and (b3 > 1.1 * b4)):
                    if((b2 > 0.7 * b4) and (b3 > 1.1 * b4)):
                        water_pixel_count += 1.0
                        waterbody_row.append(63.0)
                        #SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 63.0))
                        store_water_in_database(
                            folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 63.0)
                    else:
                        non_water_pixel_count += 1.0
                        waterbody_row.append(0.0)
                else:
                    non_water_pixel_count += 1.0
                    waterbody_row.append(0.0)
            else:
                non_water_pixel_count += 1.0
                waterbody_row.append(0.0)
            if((0.0086 < b2 < 0.011) and (0.005 < b3 < 0.0092) and (0.010 < b4 < 0.01739) and (0.010 < b5 < 0.0135)):
                if((586.0 <= baim <= 920.0) and (0.1 <= NDVI <= 0.43) and(0.036 <= BRT <= 0.0497)):
                    if((0.0000141 < abs(b5 - b4) < 0.0002423) and (0.0017 < abs(b5 - b3) < 0.00788) and (0.00001153 < abs(b5 - b2) < 0.00564) and (0.0019 < abs(b4 - b3) < 0.00562) and (0.000182 < abs(b4 - b2) < 0.003383) and (0.00085 < abs(b3 - b2) < 0.004431)):
                        burnt_pixel_count += 1.0
                        burned_area_row.append(255.0)
                        store_burnt_in_database(
                            folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, baim, 255.0)
                    else:
                        non_burnt_pixel_count += 1.0
                        burned_area_row.append(0.0)
                else:
                    non_burnt_pixel_count += 1.0
                    burned_area_row.append(0.0)
            else:
                non_burnt_pixel_count += 1.0
                burned_area_row.append(0.0)
            # print "Status of #SparseFeature_Water after the ", each_pixel, " is ", #SparseFeature_Water
        burned_area_image.append(burned_area_row)
        waterbody_image.append(waterbody_row)
    my_output_image1 = np.array(waterbody_image, dtype=np.uint8)
    my_output_image2 = np.array(burned_area_image, dtype=np.uint8)
    water_body_percentage = float(
        (water_pixel_count / (water_pixel_count + non_water_pixel_count)) * 100)
    burnt_area_percentage = float(
        (burnt_pixel_count / (burnt_pixel_count + non_burnt_pixel_count)) * 100)
    store_in_database(folder_name, water_body_percentage,
                      burnt_area_percentage)  # call to store in Mongodb
    Water_op_file_name = "WAT-" + folder_name + ".tif"
    Burnt_op_file_name = "BNT-" + folder_name + ".tif"
    op1 = Water_op_file_name + " - " + str(water_body_percentage)
    op2 = Burnt_op_file_name + " - " + str(burnt_area_percentage)
    waterbody_outputs.append(op1)
    burntarea_outputs.append(op2)
    save_image_water(my_output_image1, Water_op_file_name)
    save_image_burnt(my_output_image2, Burnt_op_file_name)
    water_percentage.append(water_body_percentage)
    stop_time = timeit.default_timer()
    print "Total Time: ", stop_time - start
#print water_percentage


def execute_Processes(dataset_folder, pivot):
    # Creating Processs
    try:
        p1 = multiprocessing.Process(target=process_folder, name='Process 1', args=(
            str(dataset_folder + "/" + dataset[pivot]),))
    except:
        print "Unable to Create Process 1"
    try:
        p2 = multiprocessing.Process(target=process_folder, name='Process 2', args=(
            str(dataset_folder + "/" + dataset[pivot + 1]),))
    except:
        print "Unable to Create Process 2"
    try:
        p3 = multiprocessing.Process(target=process_folder, name='Process 3', args=(
            str(dataset_folder + "/" + dataset[pivot + 2]),))
    except:
        print "Unable to Create Process 3"
    try:
        p4 = multiprocessing.Process(target=process_folder, name='Process 4', args=(
            str(dataset_folder + "/" + dataset[pivot + 3]),))
    except:
        print "Unable to Create Process 4"
    # try:
    # 	p5 = multiprocessing.Process(target = process_folder, name = 'Process 5', args = (str(dataset_folder + "/" + dataset[pivot + 4]),))
    # except:
    # 	print "Unable to Create Process 5"
    # try:
    # 	p6 = multiprocessing.Process(target = process_folder, name = 'Process 6', args = (str(dataset_folder + "/" + dataset[pivot + 5]),))
    # except:
    # 	print "Unable to Create Process 6"
    # try:
    # 	p7 = multiprocessing.Process(target = process_folder, name = 'Process 7', args = (str(dataset_folder + "/" + dataset[pivot + 6]),))
    # except:
    # 	print "Unable to Create Process 7"
    # try:
    # 	p8 = multiprocessing.Process(target = process_folder, name = 'Process 8', args = (str(dataset_folder + "/" + dataset[pivot + 7]),))
    # except:
    # 	print "Unable to Create Process 8"

    # starting Processs
    p1.start()
    p2.start()
    p3.start()
    p4.start()
    # p5.start()
    # p6.start()
    # p7.start()
    # p8.start()

    # wait until all Processs finish
    p1.join()
    p2.join()
    p3.join()
    p4.join()
    # p5.join()
    # p6.join()
    # p7.join()
    # p8.join()


if __name__ == "__main__":
    start_main = timeit.default_timer()
    dataset_folder = sys.argv[1]
#	print "Dataset folder is ", dataset_folder
    folder_for_output = dataset_folder
    dataset = os.listdir(dataset_folder)
    os.system("mkdir output_water")
    os.system("mkdir output_burnt")
    #print "Dataset has : ", dataset
    dataset.sort()
    pivot = 0
#	print "Length of dataset is: ", len(dataset), " ", dataset
    for i in range(int(ceil((len(dataset) / 4.0)))):
        # print ID of current process
        #		print("ID of process running main program: {}".format(os.getpid()))
        try:
            execute_Processes(dataset_folder, pivot)
        except:
            print "ERROR! UNABLE TO START execute_Processes"
        pivot += 4
    print "Exiting Main Process"
    stop_main = timeit.default_timer()
    print "Overall Time: ", stop_main - start_main
    t = float((stop_main - start_main) / 60)
    print "Overall time in minutes : ", t

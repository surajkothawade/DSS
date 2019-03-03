# Script for Computing Similarity based on SparseFeature Vector
# Usage : python Similarity.py path_to_reference_image folder
from pymongo import MongoClient
import pandas as pd
import numpy as np
import os
import sys
import timeit
from SparseFeature_woIndex_mongo import get_longitude, get_latitude, get_TOA

client = MongoClient("mongodb://localhost:27017/")
db = client.sparsefeatures_water
collections = db.collection_names()

if(len(sys.argv) != 2):
    print "Error! Similarity.py expects two scripts."
    print "Please refer to the usage below"
    print "Usage: python Similarity.py path_to_reference_image folder"

# Taking referece image folder
reference_image = sys.argv[1]


def check_tile_availabilty(tile_no):
    similar_tiles = []
    for tile in collections:
        ext_tile = str((tile.split('_')[0]))
        print ext_tile, tile_no
        print type(ext_tile), type(tile_no)
        if (tile_no == ext_tile):
            similar_tiles.append(str(tile))
            print "Appended"
    return similar_tiles


def binary_search_xy(indices, index_dict):
    index_x = indices[0]
    index_y = index[1]
    for tile_name, stored_indices in index_dict.iteritems():
        # stored_indices = stored_indices.tolist()
        print "Tile name is", tile_name
        print "Stored indices are ", stored_indices


def process_similarity_folder(folder_path):
    start = timeit.default_timer()
    folder_name = folder_path.split("/")[-1]
    # SparseFeature_Water[folder_name] = []
    #	print multiprocessing.current_process().name ," Currently working on folder ", folder_path
    files = os.listdir(folder_path)
    each_folder = []
    for file in files:
        if(file.endswith(".tif")):
            each_folder.append(file)
    each_folder.sort()
    tile_no = (each_folder[0].split('-'))[1]
    similar_tiles = check_tile_availabilty(tile_no)
    print "Similar tiles are : ", similar_tiles
    tile_available = True
    if(len(similar_tiles) == 0):
        print "WARNING: Data for Similar Tiles is not Available!"
        print "Comparing tile based on Percentage Feature"
        tile_available = False
    else:
        df_tiles = {}
        for tile in similar_tiles:
            df = pd.DataFrame(list(db[tile].find({}, {'index': 1, '_id': 0})))
            df_tiles[tile] = df['index'].tolist()
        #print "Similar tiles found are: ", df_tiles
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
                        # Binary Search Function for Similarity goes here
                        binary_search_xy([row, each_pixel], df_tiles)
                        # SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 255.0))
                        store_water_in_database(
                            folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 255.0)
                    else:
                        if((b2 > b5) and (NDVI < 0.05) and (b3 > (0.9 * b2)) and (b4 < (1.1 * b2)) and ((b5 > (0.92 * b4)) or (b5 > (0.92 * b2)))):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)
                            # SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        elif((b2 > (0.8 * b3)) and (NDVI < 0.03) and ((b2 > b4) and ((0.7 * b2) > b5))):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)  # make water as white
                            # SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        elif((b2 > (0.9 * b4)) and (b3 > (0.9 * b5)) and (NDVI < 0.0325)):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)  # make water as white
                            # SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        elif((0.0325 < BRT < 0.05) and (NDVI < 0.05) and (b5 < (0.85 * b2)) and (b4 < (1.1 * b5)) and ((b3 > (0.75 * b2))) or (b2 > b4)):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)  # make water as white
                            # SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        elif((b2 > b4) and (b5 < (0.8 * b2)) and (b3 > (0.9 * b2)) and (NDVI < 0.05)):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)  # make water as white
                            # SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
                            store_water_in_database(
                                folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 127.0)
                        elif((BRT < 0.05) and (NDVI < 0.05) and (b2 > (0.9 * b5)) and (b2 > b4) and (b4 > (1.3 * b5))):
                            water_pixel_count += 1.0
                            waterbody_row.append(127.0)  # make water as white
                            # SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 127.0))
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
                        # SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 63.0))
                        store_water_in_database(
                            folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 63.0)
                    else:
                        non_water_pixel_count += 1.0
                        waterbody_row.append(0.0)
                elif((BRT < 0.1075) and (1.1 * b2 > b3) and((b2 > b4) or (b2 > b5))):
                    if((b3 > b4) and (b2 > b5)):
                        water_pixel_count += 1.0
                        waterbody_row.append(63.0)  # make water as white
                        # SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 63.0))
                        store_water_in_database(
                            folder_name, (row, each_pixel), b2, b3, b4, b5, NDVI, BRT, 63.0)
                    else:
                        non_water_pixel_count += 1.0
                        waterbody_row.append(0.0)
                elif((BRT < 0.1) and (b2 > 1.6 * b5) and (b3 > 1.1 * b4)):
                    if((b2 > 0.7 * b4) and (b3 > 1.1 * b4)):
                        water_pixel_count += 1.0
                        waterbody_row.append(63.0)
                        # SparseFeature_Water[folder_name].append((b2, b3, b4, b5, NDVI, BRT, 63.0))
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


process_similarity_folder(reference_image)

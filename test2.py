#!/usr/bin/env python
# -*- coding: UTF-8

from __future__ import absolute_import, print_function, division

import binascii      # for binascii.hexlify()
from functools import reduce  # pylint: disable=redefined-builtin
import getopt        # for getopt.getopt(), to parse CLI options
import operator      # for or_
import os            # for os.environ
import socket        # for socket.error
import stat          # for stat.S_ISBLK()
import struct        # for pack()
import sys
import time
import datetime
import argparse
import math
import gpxpy.gpx

from ubxtool import ubx

PROG_NAME = 'ubx2gpx'


try:
    import gps
except ImportError:
    # PEP8 says local imports last
    sys.stderr.write("%s: failed to import gps, check PYTHON_PATH\n" %
                     PROG_NAME)
    sys.exit(2)

gps_version = '3.19-dev'
if gps.__version__ != gps_version:
    sys.stderr.write("%s: ERROR: need gps module version %s, got %s\n" %
                     (PROG_NAME, gps_version, gps.__version__))
    sys.exit(1)

def arg_parse():

    parser = argparse.ArgumentParser(description="Script to convert ubx file to gpx")
    parser.add_argument('--version', action='version', version='0.1')
    parser.add_argument("input", help="ubx file path")

    parser.add_argument("--output", help="gpx out file")
    args = parser.parse_args()
    if args.output == None:
        args.output = args.input + ".gpx"
    print(args)
    #import ipdb; ipdb.set_trace()
    return args
    
            
def ubx_read_generator(ubx_file_path, type_filter=None):

    # buffer to hold read data
    out = b''

    # open the input: device, file, or gpsd
    if ubx_file_path is not None:
        # check if input file is a file or device
        try:
            mode = os.stat(ubx_file_path).st_mode
        except OSError:
            sys.stderr.write('%s: failed to open input file %s\n' %
                             (PROG_NAME, ubx_file_path))
            sys.exit(1)

    # Read from a plain file of UBX messages
    try:
        ubx_file = open(ubx_file_path, 'rb')
    except IOError:
        sys.stderr.write('%s: failed to open input %s\n' %
                         (PROG_NAME, ubx_file_path))
        sys.exit(1)

    try:
        # ordinary file, so all read at once
        out += ubx_file.read()
        start = 0
        consumed = 0
        while True:
            start = start + consumed
            #print("début à : ", start)
            #consumed, data = gps_model.decode_msg(out[:2000])
            consumed, data = gps_model.decode_msg(out[start:start+8192])
            #out = out[consumed:]
            if type_filter is None:
                yield data
            elif type_filter is not None and isinstance(data, dict) and data['type'] in type_filter:
                yield data
                
            if 0 >= consumed:
                print(time.time())
                print("time elapsed to read ubx: ", time.time() - start_time)
                break
                    

    except IOError:
        # This happens on a good device name, but gpsd already running.
        # or if USB device unplugged
        sys.stderr.write('%s: failed to read %s\n'
                         % (PROG_NAME, read_ubx_file_path,
                            PROG_NAME))
        return 1


def iTow_group_generator(ubx_file_path, type_filter=None):

    mon_generateur = ubx_read_generator(ubx_file_path, type_filter)
    
    #Catch first iTow
    timestamp = 0
    sentences_group = {}
    for sentence in mon_generateur:
        new_iTow = sentence['msg'].get('iTow')
        
        if new_iTow is not None:
            timestamp = new_iTow
            sentences_group['iTow'] = new_iTow
            sentences_group[sentence['type']] = sentence['msg']
            break
            
    for sentence in mon_generateur:
        new_iTow = sentence['msg'].get('iTow')
        if new_iTow is None or new_iTow == timestamp:
            sentences_group[sentence['type']] = sentence['msg']

        elif new_iTow != timestamp:
            timestamp = new_iTow
            # send sentences_group to function
            yield sentences_group
            # Emptying the dict
            sentences_group.clear()
            
            sentences_group['iTow'] = new_iTow
            sentences_group[sentence['type']] = sentence['msg']

if __name__ == '__main__':
    start_time = time.time()
    gps_model = ubx()
    args = arg_parse()
    #input_file_name = 'c:/Users/Stéphane/Documents/RTK/data/COM12_190514_154853.ubx'
    #input_file_name = 'c:/Users/Stéphane/Documents/RTK/data/rover_2019-05-14.16-51-07.ubx'
    #output_file_name = 'c:/Users/Stéphane/Documents/RTK/data/rover.gpx'
    
    new_gpx = gpxpy.gpx.GPX()
    # Create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    new_gpx.tracks.append(gpx_track)
    # Create first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    
    iTow_group = iTow_group_generator(args.input, ('UBX-NAV-PVT', 'UBX-NAV-HPPOSLLH'))
    for group in iTow_group:
        
        try:
            
            # Check fix
            if group['UBX-NAV-PVT'].get('fixType') == None or group['UBX-NAV-PVT'].get('fixType') == 0:
                continue
            
            # Create fix type 
            fix_type = {'0':'none', '2':'2d', '3':'3d'}.get(str(group['UBX-NAV-PVT']['fixType']))
            
            
            #Compute real second
            complete_second=group['UBX-NAV-PVT']['second'] + group['UBX-NAV-PVT']['nano']*1E-9
            # Create datetime object        
            gpx_time = datetime.datetime (year=group['UBX-NAV-PVT']['year'],
                            month=group['UBX-NAV-PVT']['month'],
                            day=group['UBX-NAV-PVT']['day'],
                            hour=group['UBX-NAV-PVT']['hour'],
                            minute=group['UBX-NAV-PVT']['minute'],
                            second=int(complete_second // 1),
                            microsecond=round((complete_second % 1)*1E6))
                            
            
            # Create points:
            new_point = gpxpy.gpx.GPXTrackPoint(
                longitude = group['UBX-NAV-HPPOSLLH']['prec_lon'],
                latitude = group['UBX-NAV-HPPOSLLH']['prec_lat'],
                elevation = group['UBX-NAV-HPPOSLLH']['prec_height'],
                time = gpx_time,
                
                )
            new_point.type_of_gpx_fix = fix_type
            new_point.satellites = group['UBX-NAV-PVT']['numSV']
            new_point.position_dilution = group['UBX-NAV-PVT']['pDOP']
            
            gpx_segment.points.append(new_point)
        
        except Exception as e:
            print(e, "point :", new_point)
            print("gpx time: ", gpx_time)
                     
    
    """
    mon_generateur = ubx_read_generator(input_file_name, ('UBX-NAV-PVT'))
    for i, sent in enumerate(mon_generateur):
        if i == 0:
            print(sent['msg']['iTow'])
    print("nombre de groupe", i)
    print(sent['msg']['iTow'])
    """
            
            
    
        
    
    """
    for sentence in mon_generateur:
        print(sentence['type'], sentence['msg']['iTow'], '\n')
        timestamp = sentence['msg']['iTow'] if sentence['msg'].get('iTow') else None
    """    
        
    with open(args.input + ".gpx", "w") as gpx_file:
        gpx_file.write(new_gpx.to_xml())
    #print('Created GPX:', new_gpx.to_xml())
    print("Converting to gpx in {} seconds".format(time.time() - start_time)
    
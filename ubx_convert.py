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
PROG_VERSION = '0.2'


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

    parser = argparse.ArgumentParser(description="Script to convert a ubx file to a gpx or pos file")
    parser.add_argument('--version', action='version', version='%(prog)s' + PROG_VERSION)
    parser.add_argument(
        "ubx",
        help="Path to the ubx file",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-p",
        "--pos",
        action="store_true",
        help="Convert to pos file",
    )
    group.add_argument(
        "-g",
        "--gpx",
        action="store_true",
        help="Convert to gpx file",
    )
    parser.add_argument(
        "-o",
        "--output",
        nargs="?",
        default=sys.stdout,
        help="Path to the output file",
    )
    args = parser.parse_args()
    args.prog = parser.prog
    #if args.output == None:
    #    args.output = args.input.replace(".ubx", ".gpx")

    print("% {}".format(args))
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
                # print(time.time())
                print("% Reading ubx in {:.3f} seconds".format(time.time() - start_time))
                break
                    

    except IOError:
        # This happens on a good device name, but gpsd already running.
        # or if USB device unplugged
        sys.stderr.write('%s: failed to read %s\n'
                         % (PROG_NAME, ubx_file_path,
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

def convert_to_pos_line(point_group, point_time):
    # round microsecond to millisecond 
    if point_time.microsecond > 999499 :
        point_time = point_time + datetime.timedelta(seconds=1, microseconds = - point_time.microsecond)
    else:
        point_time = point_time.replace(microsecond = round(point_time.microsecond/1000))

    sol_type = {False: 5, 'Float': 2, 'Fixed': 1}.get(group['UBX-NAV-PVT']['carrSoln'])
    pos_time = '{0:%Y}/{0:%m}/{0:%d} {0:%H}:{0:%M}:{0:%S}.{0:%f}'.format(point_time)
    pos_line = ('{} {:14.9f} {:14.9f} {:10.4f} {:3d} {:3d} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:4.2f} {:6.1f} \n'.format(
        pos_time,
        point_group['UBX-NAV-HPPOSLLH']['prec_lat'],
        point_group['UBX-NAV-HPPOSLLH']['prec_lon'],
        point_group['UBX-NAV-HPPOSLLH']['prec_height'],
        sol_type,
        point_group['UBX-NAV-PVT']['numSV'],
        point_group['UBX-NAV-HPPOSLLH']['hAcc']/10000.0,   # sdn(m)
        point_group['UBX-NAV-HPPOSLLH']['hAcc']/10000.0,   # sde(m)
        point_group['UBX-NAV-HPPOSLLH']['vAcc']/10000.0,   # sdu(m)
        0.0,
        0.0,
        0.0,
        0.0,    # age
        0.0     # ratio
    ))

    return pos_line

if __name__ == '__main__':
    start_time = time.time()
    gps_model = ubx()
    args = arg_parse()
    new_gpx = gpxpy.gpx.GPX()
    # Create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    new_gpx.tracks.append(gpx_track)
    # Create first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    
    if args.pos:
        pos_lines=[]
    if args.gpx:
        pass

    iTow_group = iTow_group_generator(args.ubx, ('UBX-NAV-PVT', 'UBX-NAV-HPPOSLLH'))
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
            point_time = datetime.datetime (year=group['UBX-NAV-PVT']['year'],
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
                time = point_time,
                #position_dilution=group['UBX-NAV-PVT']['pDOP'],
                horizontal_dilution=group['UBX-NAV-PVT']['pDOP'],
                )
            new_point.type_of_gpx_fix = fix_type
            new_point.satellites = group['UBX-NAV-PVT']['numSV']
            #new_point.position_dilution = group['UBX-NAV-PVT']['pDOP']
            
            if args.gpx:
                gpx_segment.points.append(new_point)
            if args.pos:
                pos_lines.append(convert_to_pos_line(group, point_time))     
        
        except Exception as e:
            print("%", group['iTow'], "Error :", e)

    if args.pos:
        with open(args.output, "w", encoding="utf-8") as output_file:
            output_file.write("% program   : {}\n".format(args.prog + PROG_VERSION))
            output_file.write("% (lat/lon/height=WGS84/ellipsoidal,Q=1:fix,2:float,3:sbas,4:dgps,5:single,6:ppp,ns=# of satellites)\n")
            output_file.write("%  DateTime                  latitude(deg) longitude(deg)  height(m)   Q  ns   sdn(m)   sde(m)   sdu(m)  sdne(m)  sdeu(m)  sdun(m) age(s)  ratio\n")
            output_file.writelines(pos_lines)
    if args.gpx:    
        with open(args.output, "w", encoding="utf-8") as gpx_file:
            gpx_file.write(new_gpx.to_xml())

    print("% Convertion done in {:.3f} seconds".format(time.time() - start_time))
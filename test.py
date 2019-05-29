#!/usr/bin/env python
# -*- coding: UTF-8

from ubxtool import *

def ubx_read(ubx_file_path):

    out = b''
    ser = None
    input_is_device = False

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
        #if raw is not None:
            # save to raw file
        #    raw.write(self.out)

        gnss_data = []
        while True:
            consumed, data = gps_model.decode_msg(out)
            gnss_data.append(data)
            out = out[consumed:]
            if 0 >= consumed:
                return gnss_data
                    

    except IOError:
        # This happens on a good device name, but gpsd already running.
        # or if USB device unplugged
        sys.stderr.write('%s: failed to read %s\n'
                         '%s: Is gpsd already holding the port?\n'
                         % (PROG_NAME, read_ubx_file_path,
                            PROG_NAME))
        return 1

if __name__ == '__main__':
    gps_model = ubx()
    input_file_name = 'c:/Users/Stéphane/Documents/RTK/data/rover_2019-05-10.16-38-09.ubx'
    data = ubx_read(input_file_name)
    print(data)
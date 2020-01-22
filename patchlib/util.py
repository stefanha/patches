#
# patches - QEMU Patch Tracking System
#
# Copyright IBM, Corp. 2013
#
# Authors:
#  Anthony Liguori <aliguori@us.ibm.com>
#
# This work is licensed under the terms of the GNU GPLv2 or later.
# See the COPYING file in the top-level directory.
#

from subprocess import Popen, PIPE, STDOUT
import os, sys

def call_teed_output(args, **kwds):
    p = Popen(args, stdout=PIPE, stderr=STDOUT, universal_newlines=True, **kwds)
    out = ''
    for line in iter(p.stdout.readline, ''):
        sys.stdout.write(line)
        out += line
    return p.wait(), out

def backup_file(filename):
    backup = "%s~" % filename
    if filename.find('/') != -1:
        parts = filename.split('/')
        parts[-1] = '.#' + parts[-1]
        tmp_filename = '/'.join(parts)
    else:
        tmp_filename = ".#%s" % filename

    try:
        with open(filename, 'r') as infp:
            with open(backup, 'w') as outfp:
                outfp.write(infp.read())
    except Exception as e:
        pass

    return tmp_filename

def replace_cfg(filename, ini):
    tmp_filename = backup_file(filename)

    with open(tmp_filename, 'wb') as fp:
        ini.write(fp)

    os.rename(tmp_filename, filename)

def replace_file(filename, data):
    tmp_filename = backup_file(filename)

    with open(tmp_filename, 'wb') as fp:
        fp.write(data)

    os.rename(tmp_filename, filename)

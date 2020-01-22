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

import os
from configparser import RawConfigParser
from . import fetch, config

def main(args):
    filename = os.getcwd() + '/.patchesrc'

    if os.access(filename, os.R_OK):
        raise Exception('Configuration file %s already exists' % filename)

    ini = RawConfigParser()

    if args.url:
        ini.add_section('fetch')
        ini.set('fetch', 'url', args.url[0])

    with open(filename, 'w') as fp:
        ini.write(fp)

    if args.url:
        config.setup(filename)
        return fetch.fetch()

    return 0

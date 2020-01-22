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

from subprocess import check_call
from . import config

def invoke(name):
    command = config.get_hook(name)
    if command:
        check_call(command, shell=True)

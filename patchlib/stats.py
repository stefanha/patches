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

import sys
from . import data

def is_reviewed(patch):
    for tag in patch['tags']:
        if tag.startswith('Reviewed-by: '):
            return True
    return False

patches = data.parse_json(sys.stdin.read())

total_series = 0
total_patches = 0
total_reviews = 0
total_obsolete = 0
total_broken = 0
total_committed = 0
total_not_builds = 0
total_not_applies = 0
total_unreviewed = 0

for series in patches:
    total_series += 1

    is_broken = "broken" in series and series["broken"]
    is_obsolete = False
    builds = not ("builds" in series and not series["builds"])
    applies = not ("applies" in series and not series["applies"])

    for patch in series["messages"]:
        if is_broken:
            pass
        elif "obsolete" in patch and patch["obsolete"]:
            is_obsolete = True

        if "cover" in patch and patch["cover"]:
            continue

        total_patches += 1

        if "commit" in patch:
            total_committed += 1
        elif not applies:
            total_not_applies += 1
        elif not builds:
            total_not_builds += 1
        elif is_broken:
            total_broken += 1
        elif is_obsolete:
            total_obsolete += 1
        elif is_reviewed(patch):
            total_reviews += 1
        else:
            total_unreviewed += 1

print("Total Series,", total_series)
print("Total Patches,", total_patches)
print("Total Reviews,", total_reviews)
print("Total Obsolete,", total_obsolete)
print("Total Broken,", total_broken)
print("Total Committed,", total_committed)
print("Total Not Builds,", total_not_builds)
print("Total Not Applies,", total_not_applies)
print("Total Unreviewed,", total_unreviewed)

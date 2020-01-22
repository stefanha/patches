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

from . import config, mbox, gitcmd, data
from .list import find_subseries
from .series import *
from subprocess import call, check_output
from .util import call_teed_output
import os

def apply_patch(pathname, **kwds):
    opts = [ '--3way' ]
    if 'signed-off-by' in kwds:
        opts.append('-s')
        del kwds['signed-off-by']
    if 'interactive' in kwds:
        opts.append('-i')
        del kwds['interactive']
    opts.append(pathname)
    return call_teed_output(['git', 'am'] + opts, **kwds)

def apply_pull_request(msg, **kwds):
    pull_request = msg['pull-request']
    uri = pull_request['uri'].encode('ascii', errors='ignore')
    refspec = pull_request['refspec'].encode('ascii', errors='ignore')
    remotes = gitcmd.get_remotes(**kwds)
    sob = None

    if 'signed-off-by' in kwds:
        del kwds['signed-off-by']
        name = check_output(['git', 'config', 'user.name'], **kwds).strip()
        email = check_output(['git', 'config', 'user.email'], **kwds).strip()
        sob = '%s <%s>' % (name, email)

    if 'interactive' in kwds:
        del kwds['interactive']

    if uri not in remotes:
        raise Exception('%s is not setup as a remote, please add a remote manually' % pull_request['uri'])

    remote = remotes[uri]

    s, o = call_teed_output(['git', 'fetch', remote], **kwds)
    if s != 0:
        return s, o

    s, o = call_teed_output(['git', 'merge', '--no-ff', '%s/%s' % (remote, refspec)], **kwds)
    if s != 0:
        return s, o

    # I am not proud of this but I don't see any other option
    if o.strip() == 'Already up-to-date.':
        return 0, o

    o = check_output(['git', 'log', '-1', '--format=%B', 'HEAD'], **kwds)
    o += '\n'
    o += 'Message-id: %s\n' % msg['message-id']
    if sob:
        o += 'Signed-off-by: %s\n' % sob

    return call_teed_output(['git', 'commit', '--amend', '-m', o], **kwds)

def apply_series(series, **kwds):
   if is_pull_request(series):
       return apply_pull_request(series['messages'][0], **kwds)
   elif is_broken(series):
       raise Exception('Cannot apply series: series is either incomplete or improperly threaded.')
   elif not 'mbox_path' in series:
       raise Exception('Cannot apply series: missing mbox')
   return apply_patch(mbox.get_real_path(series['mbox_path']), **kwds)

def main(args):
    with open(config.get_json_path(), 'rb') as fp:
        patches = data.parse_json(fp.read())

    kwds = {}
    if args.git_dir:
        kwds['cwd'] = args.git_dir
    if args.s:
        kwds['signed-off-by'] = True
    if args.interactive:
        kwds['interactive'] = True

    for series in find_subseries(patches, args):
        try:
            s, _ = apply_series(series, **kwds)
            if s:
                return s
        except Exception as e:
            print(str(e))
            return 1

    return 0
            

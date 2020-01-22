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

import nntplib, email, datetime, notmuch, mailbox, os, sys
from configparser import RawConfigParser
from subprocess import check_call
from . import config, util

def fetch_msg(self, num):
    _, _, _, head = self.head(str(num))
    _, _, _, body = self.body(str(num))
    return email.message_from_string('\n'.join(head + body))

def setup(args):
    maildir = config.get_notmuch_dir()
    git_dir = config.get_git_dir()

    try:
        os.makedirs(git_dir.rsplit('/', 1)[0])
    except Exception as e:
        pass

    git = ['git', '--git-dir=%s' % git_dir]

    check_call(git + ['init', '--bare'])
    check_call(git + ['remote', 'add', 'origin', args.url])

    try:
        os.makedirs(maildir.rsplit('/', 1)[0])
    except Exception as e:
        pass

    mdir = mailbox.Maildir(maildir, create=True)
    db = notmuch.Database(maildir, create=True)

    srv = nntplib.NNTP(args.server)
    _, _, first, last, _ = srv.group(args.group)

    first_fetch = max(int(first), int(last) - args.max_msgs)
    util.replace_file('%s/.last' % maildir, str(first_fetch))

    ini = RawConfigParser()
    ini.read([config.config_filename])

    ini.add_section('nntp')
    ini.set('nntp', 'server', args.server)
    ini.set('nntp', 'group', args.group)

    ini.add_section('scan')
    if args.list_tag:
        ini.set('scan', 'list_tag', args.list_tag)
    if args.search_days:
        ini.set('scan', 'search_days', str(args.search_days))
    util.replace_cfg(config.config_filename, ini)

    return 0

def refresh(args):
    maildir = config.get_notmuch_dir()

    with open('%s/.last' % maildir, 'r') as fp:
        last_msg = int(fp.read())

    mdir = mailbox.Maildir(maildir)
    db = notmuch.Database(maildir, mode=notmuch.Database.MODE.READ_WRITE)

    srv = nntplib.NNTP(config.get_nntp_server())
    _, _, first, last, _ = srv.group(config.get_nntp_group())

    last = int(last)

    clear = False
    for msgno in range(last_msg + 1, last + 1):
        msg = fetch_msg(srv, str(msgno))
        filename = maildir + '/new/' + mdir.add(msg)

        db.begin_atomic()
        try:
            msg, status = db.add_message(filename)
        finally:
            db.end_atomic()

        util.replace_file('%s/.last' % maildir, str(msgno))

        sys.stdout.write('\rFetching message %4d of %4d...    ' % (msgno - last_msg, last - last_msg))
        clear = True
        sys.stdout.flush()

    if clear:
        sys.stdout.write('\n')

    return 0
    

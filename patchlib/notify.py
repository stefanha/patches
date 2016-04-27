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

import email.message, email.utils
import os, smtplib, time
import config, data
from series import *
from email.header import Header
from list import search_subseries
from UserDict import UserDict
from message import escape_message_id

def format_addr(addr):
    name = addr['name']

    # This seems like a python bug to me...
    if name.encode('ascii', errors='replace') != name:
        name = str(Header().append(addr['name']))

    return email.utils.formataddr((name, addr['email']))

def encode_address_list(addrs):
    return ', '.join(map(format_addr, addrs))

def try_to_send(args, notified_dir, sender, message, payload):
    mid = escape_message_id(message['message-id'])
    if os.access(notified_dir + '/mid/' + mid, os.F_OK):
        return

    msg = email.message.Message()

    receipents = [ message['from'] ]
    receipents += message['to']
    receipents += message['cc']
    receipents = map(format_addr, receipents)

    msg['From'] = sender
    msg['Subject'] = 'Re: %s' % message['subject']
    msg['Cc'] = encode_address_list(message['cc'])
    msg['To'] = encode_address_list([ message['from'] ] + message['to'])
    msg['In-Reply-To'] = '<%s>' % message['message-id']
    msg['Date'] = email.utils.formatdate()

    lines = payload.split('\n')
    if len(lines) > 1024:
        lines = lines[0:1024] + ['[Output truncated]']
    payload = '\n'.join(lines)
    msg.set_payload(payload.encode('ascii', errors='replace'))

    txt_msg = msg.as_string().encode('ascii', errors='replace')

    if not args.dry_run and not args.fake:
        sent = False
        for i in range(10):
            try:
                s = smtplib.SMTP(config.get_smtp_server())
                s.sendmail(sender, receipents, txt_msg)
                s.quit()
                sent = True
                break
            except:
                time.sleep(1)

        if not sent:
            raise

    if not args.dry_run:
        f = open(notified_dir + '/mid/' + mid, 'w')
        f.flush()
        f.close()

    print txt_msg
    print '-' * 80

class SeriesDict(UserDict):
    def __init__(self, series):
        UserDict.__init__(self)
        self.series = series

    def __getitem__(self, item):
        if item.find('/') != -1:
            parts = item.split('/')
        else:
            parts = [item]

        value = self.series
        for part in parts:
            if part[0] in '0123456789':
                value = value[int(part)]
            else:
                value = value[part]

        return value

def notify(args, patches, notified_dir, query, template):
    sender = config.get_default_sender()
    for series in search_subseries(patches, query):
        sd = SeriesDict(series)
        try_to_send(args, notified_dir, sender, series['messages'][0], template % sd)

def main(args):
    import config

    notified_dir = config.get_notified_dir()

    try:
        os.makedirs(notified_dir + '/mid')
    except Exception, e:
        pass

    if args.smtp_server != None:
        config.set('notify', 'smtp_server', args.smtp_server)
    if args.sender != None:
        config.set('notify', 'default_sender', args.sender)

    with open(config.get_json_path(), 'rb') as fp:
        patches = data.parse_json(fp.read())

    nots = []
    if args.labels:
        print args.labels
        def fn(x):
            return (x, config.get_notification(x))
        nots = map(fn, args.labels)
    else:
        nots = config.get_notifications()

    for label, filename in nots:
        with open(filename, 'rb') as fp:
            template = fp.read()
        
        notify(args, patches, notified_dir, 'label:%s' % label, template)

    return 0

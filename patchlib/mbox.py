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

import shutil, os, mailbox, hashlib
import config
from message import get_payload, merge_tags, parse_tag, escape_message_id

def setup_mboxes():
    try:
        os.makedirs(config.get_mbox_path())
    except Exception, e:
        pass

def add_tags(message, tags):
    lines = []
    payload = get_payload(message)

    in_sob = False
    done = False
    whitespace = []
    for line in payload.split('\n'):
        # if we've added our tags, we're done
        if done:
            lines.append(line)
            continue

        # is this line a tag
        tag = parse_tag(line, config.get_email_tags())
        if not in_sob and tag:
            in_sob = True

        if in_sob:
            # if it's a blank line, queue it for now
            if not line.strip():
                whitespace.append(line)
                continue

            if tag:
                key = tag.keys()[0]
                value = tag[key]

                # always drop message-id tags
                if key == 'Message-id':
                    continue

                # if we hit a tag and there's whitespace before the tag, preserve it
                if whitespace:
                    lines += whitespace
                    whitespace = []
                lines.append(line)

                # Don't duplicate tags
                if key in tags and value[0] in tags[key]:
                    tags[key] = list(set(tags[key]) - set(value))
            else:
                # we hit a non-blank line that isn't a tag
                done = True
                in_sob = False

                # append our tags before this line
                for key in tags:
                    for val in tags[key]:
                        if val:
                            lines.append('%s: %s' % (key, val))

                mid = message.get_message_id()
                if mid:
                    lines.append('Message-id: %s' % mid)

                # but before any whitespace preceeding this line
                if whitespace:
                    lines += whitespace
                    whitespace = []
                lines.append(line)
        else:
            lines.append(line)


    return '\n'.join(lines)

def generate_mbox(messages, full_tags):
    mbox_dir = config.get_mbox_path()
    mid = escape_message_id(messages[0][0].get_message_id())

    tmp_mbox_path = '%s/tmp-%s' % (mbox_dir, mid)
    mbox_path = '%s/mbox-%s' % (mbox_dir, mid)

    mbox = mailbox.mbox(tmp_mbox_path, create=True)
    for message, tags in messages:
        new_payload = add_tags(message, merge_tags(full_tags, tags))

        msg = message.get_message_parts()[0]

        # Drop content transfer encoding so msg.set_payload() will re-encode
        if 'content-transfer-encoding' in msg:
            del msg['content-transfer-encoding']

        # Change charset to UTF-8 to guarantee that we can represent all
        # characters.  Think about the case where the patch email was ASCII and
        # a reviewer with a non-ASCII name replied with a Reviewed-by tag, now
        # the patch can no longer be represented by ASCII.
        msg.set_payload(new_payload.encode('utf-8'), 'utf-8')
        mbox.add(msg)
    mbox.flush()
    mbox.close()

    os.rename(tmp_mbox_path, mbox_path)

    return config.get_mbox_prefix() + ('mbox-%s' % mid)

def get_real_path(mbox_path):
    return '%s/%s' % (config.get_mbox_path(), mbox_path[len(config.get_mbox_prefix()):])

def get_hash(mbox_path):
    real_path = get_real_path(mbox_path)
    if not os.access(real_path, os.R_OK):
        return None

    with open(real_path, 'r') as fp:
        data = fp.read()

    # The first line of each message contains a date from the mailer which
    # changes whenever the mbox is regenerated.  Drop it from the hash
    # calculation
    def fn(line):
        return not line.startswith('From MAILER-DAEMON ')
    data = '\n'.join(filter(fn, data.split('\n')))

    h = hashlib.sha1()
    h.update(data)
    return h.hexdigest()

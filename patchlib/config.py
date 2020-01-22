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

from configparser import RawConfigParser
import os.path, email.utils, os

ini = RawConfigParser()
config_filename = None

def setup(filename):
    global config_filename

    if not filename:
        dirs = os.getcwd().split('/')
        for i in range(0, len(dirs)):
            if i:
                path = '/'.join(dirs[0:-i])
            else:
                path = '/'.join(dirs)

            path += '/.patchesrc'

            if os.access(path, os.R_OK):
                filename = path
                break

        if not filename:
            filename = os.path.expanduser('~/.patchesrc')
    elif filename[0] != '/':
        filename = os.getcwd() + '/' + filename

    config_filename = filename
    ini.read(filename)

def parse_list(value):
    if value == None:
        return []
    elif value.find(';') == -1:
        return [value]
    return value.split(';')

def option(key):
    def getter():
        return get(key)
    return getter

def get_trees():
    trees = {}
    for branch, uri in ini.items('trees'):
        trees[branch] = uri
    return trees

def get_hook(name):
    return get('hooks.%s' % name)

def get_buildbot(name):
    steps = parse_list(ini.get('buildbot "%s"' % name, 'steps'))
    ret = []
    for step in steps:
        cmd = ini.get('buildbot "%s"' % name, step)
        ret.append((step, cmd))
    return ret

def get_buildbot_json(name):
    ret = get('buildbot "%s".json' % name)
    if not ret:
        ret = get_patches_dir() + '/buildbot-%s.json' % name
    return ret

def get_buildbot_owner(name):
    ret = get('buildbot "%s".owner' % name)
    if not ret:
        ret = get_default_sender()
    return ret

def get_buildbot_query(name):
    return get('buildbot "%s".query' % name)

def get_links():
    ret = {}
    if ini.has_section('links'):
        for item, value in ini.items('links'):
            ret[item] = value
    return ret

def get_label(label):
    return get('labels.%s' % label)

def get_notification(label):
    return ini.get('notifications', label)

def get_notifications():
    ret = []
    for item, value in ini.items('notifications'):
        ret.append((item, value))
    return ret

def get(key):
    if key.find('.') == -1:
        section, item = 'options', key
        key = '%s.%s' % (section, item)
    else:
        section, item = key.split('.', 1)

    if ini.has_option(section, item):
        value = ini.get(section, item)
    elif key == 'options.email-tags':
        value = ';'.join(['Reviewed-by', 'Tested-by', 'Acked-by', 'Nacked-by',
                          'Reported-by', 'Signed-off-by', 'Rejected-by'])
    elif key == 'apply.mbox_prefix':
        value = 'patches/'
    elif key == 'apply.mbox_path':
        value = get_patches_dir() + '/public/patches'
    elif key == 'build.working_dir':
        value = get_patches_dir() + '/git-working'
    elif key == 'build.cache_dir':
        value = get_patches_dir() + '/build-cache'
    elif key == 'notify.whitelist':
        value = email.utils.parseaddr(get_default_sender())[0]
    elif key == 'scan.list_tag':
        value = ''
    elif key == 'scan.git_dir':
        value = get_patches_dir() + '/git'
    elif key == 'scan.notmuch_dir':
        value = get_patches_dir() + '/notmuch'
    elif key == 'options.notified_dir':
        value = get_patches_dir() + '/notified'
    elif key == 'options.patches_dir':
        value = config_filename.rsplit('/', 1)[0] + '/.patches'
    elif key == 'options.json_path':
        value = get_patches_dir() + '/public/patches.json'
    elif key == 'scan.mail_query':
        value = ''
    elif key == 'scan.search_days':
        value = '30'
    elif key == 'labels.__list__':
        value = ('not status:broken not status:obsolete ' +
                 'not status:pull-request not status:rfc not status:committed)')
    else:
        value = None

    if key in ['options.email-tags', 'notify.events', 'buildbots.bots']:
        value = parse_list(value)
    elif key in ['scan.search_days']:
        value = int(value)

    return value

def set(section, item, value):
    if not ini.has_section(section):
        ini.add_section(section)
    ini.set(section, item, value)

get_list_tag = option('scan.list_tag')
get_git_dir = option('scan.git_dir')
get_master_branch = option('scan.master_branch')
get_notmuch_dir = option('scan.notmuch_dir')
get_notified_dir = option('options.notified_dir')
get_patches_dir = option('options.patches_dir')
get_json_path = option('options.json_path')
get_mail_query = option('scan.mail_query')
get_search_days = option('scan.search_days')
get_smtp_server = option('notify.smtp_server')
get_default_sender = option('notify.default_sender')
get_working_dir = option('build.working_dir')
get_cache_dir = option('build.cache_dir')
get_committer_whitelist = option('notify.whitelist')
get_mbox_path = option('apply.mbox_path')
get_mbox_prefix = option('apply.mbox_prefix')
get_notify_events = option('notify.events')
get_fetch_url = option('fetch.url')
get_email_tags = option('options.email-tags')
get_nntp_server = option('nntp.server')
get_nntp_group = option('nntp.group')
get_buildbots = option('buildbots.bots')

def main(args):
    value = get(args.key)
    if value == None:
        return 1
    elif type(value) == list:
        print(';'.join(value))
    elif value:
        print(value)
    return 0

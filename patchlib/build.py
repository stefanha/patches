from . import config, mbox, data, apply, list, gitcmd, util
import shutil, errno, os, sys, json
from subprocess import check_call
from .util import call_teed_output
from .series import *

def try_rmtree(path):
    try:
        shutil.rmtree(path)
    except OSError as xxx_todo_changeme:
        (num, msg) = xxx_todo_changeme.args
        if num != errno.ENOENT:
            raise

def try_to_build(series, working_dir, commit, bot):
    try_rmtree(working_dir)

    check_call(['git', 'clone', '-sn', config.get_git_dir(), working_dir])
    check_call(['cp', config.get_git_dir() + '/config', working_dir + '/.git'])
    check_call(['git', 'checkout', commit], cwd=working_dir)
    check_call(['git', 'tag', 'BUILD_HEAD'], cwd=working_dir)

    steps = []

    s, o = apply.apply_series(series, cwd=working_dir)
    steps.append(('apply', s, o))
    if s != 0:
        return s, steps

    cmds = config.get_buildbot(bot)
    for step, cmd in cmds:
        s, o = call_teed_output(['/bin/sh', '-c', cmd], cwd=working_dir)
        steps.append((step, s, o))
        if s != 0:
            return s, steps

    steps = [(name_s_o[0], name_s_o[1], '') for name_s_o in steps]

    return 0, steps

def run_bot(patches, working_dir, commit, bot, query):
    results = []

    for series in list.search_subseries(patches, query):
        if not is_pull_request(series) and 'mbox_path' not in series:
            continue

        result = series
        s, steps = try_to_build(series, working_dir, commit, bot)
        result['buildbot'] = { 'status': s, 'steps': steps }
        results.append(result)

    results = { 'patches': results,
                'version': data.VERSION,
                'owner': config.get_buildbot_owner(bot) }

    try_rmtree(working_dir)
    util.replace_file(config.get_buildbot_json(bot),
                      json.dumps(results, indent=2,
                                 separators=(',', ': '),
                                 encoding='iso-8859-1'))

def main(args):
    with open(config.get_json_path(), 'rb') as fp:
        patches = data.parse_json(fp.read())

    working_dir = config.get_working_dir()
    commit = gitcmd.get_sha1(config.get_master_branch())

    bots = args.bots
    if not bots:
        bots = config.get_buildbots()

    for bot in bots:
        q = config.get_buildbot_query(bot)
        run_bot(patches, working_dir, commit, bot, q)

            
    

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

from . import config
from subprocess import getstatusoutput
from subprocess import check_output

def git(*args, **kwds):
    if 'git_dir' not in kwds:
        git_dir = config.get_git_dir()
    else:
        git_dir = kwds['git_dir']
    
    if git_dir == None:
        git_dir = ''
    else:
        git_dir = ' --git-dir="%s"' % git_dir

    s, o = getstatusoutput('git%s %s' % (git_dir, ' '.join(['"%s"' % x for x in args])))
    if s != 0:
        raise Exception(o)
    return o

def get_sha1(refspec):
    s, o = getstatusoutput('git --git-dir="%s" log -n 1 --format="%%H" %s' % (config.get_git_dir(), refspec))
    if s != 0:
        raise Exception(o)
    return o

def get_remotes(cwd=None, **kwds):
    o = check_output(['git', 'remote', 'show'], cwd=cwd)

    remotes = {}

    for remote in o.split('\n'):
        if not remote:
            continue

        uri = check_output(['git', 'config', 'remote.%s.url' % remote], cwd=cwd)
        remotes[uri.strip()] = remote

    return remotes

def get_merges(since):
    refspec = config.get_master_branch()
    o = git('log', '--merges', '--first-parent',
            '--pretty=format:%H\n%P\n%cn\n%ce', '--since=%s' % since, refspec)

    merged_heads = {}
    lines = o.split('\n')
    for i in range(0, len(lines), 4):
        if (i + 4) >= len(lines):
            continue

        commit = lines[i]
        heads = lines[i + 1].split()
        for head in heads:
            merged_heads[head] = { 'commit': commit,
                                   'committer': { 'name': lines[i + 2],
                                                  'email': lines[i + 3] } }

    return merged_heads

def get_commits(since, trees):
    mapping = {}

    git_dir = config.get_git_dir()
    master_branch = config.get_master_branch()

    for branch in trees:
        if branch == master_branch:
            refspec = branch
        else:
            refspec = '%s..%s' % (master_branch, branch)

        pairs = []
        o = git('log', '--pretty=format:%H\n%s\n%cn\n%ce', '--since=%s' % since, refspec)
        lines = o.split('\n')
        for i in range(0, len(lines), 4):
            if (i + 3) >= len(lines):
                continue

            pairs.append({ 'hexsha': lines[i],
                           'summary': lines[i + 1],
                           'branch': branch,
                           'committer': { 'name': lines[i + 2],
                                          'email': lines[i + 3] } })

        for commit in pairs:
            s = commit['summary']
            if s in mapping:
                hsh = mapping[s]
                if type(hsh) != list:
                    mapping[s] = [commit]
                mapping[s].append(commit)
            else:
                mapping[s] = commit

    return mapping


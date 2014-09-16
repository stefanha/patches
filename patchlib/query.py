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

import config, message, email.utils
from series import *

def match_flat_email_address(lhs, rhs):
    val = {}
    val['name'], val['email'] = email.utils.parseaddr(lhs)
    return match_email_address(val, rhs)

def match_email_address(lhs, rhs):
    lhs_name = lhs['name'].lower()
    lhs_email = lhs['email'].lower()

    rhs = rhs.lower()
    if lhs_name and lhs_name.find(rhs) != -1:
        return True

    if lhs_email and lhs_email.find(rhs) != -1:
        return True

    return False

def tokenize_query(query):
    terms = []

    i = 0
    term = ''
    while i < len(query):
        if query[i] == '"':
            start = i
            i += 1
            while i < len(query) and query[i] != '"':
                i += 1

            if i == len(query):
                raise Exception("Unterminated string '%s'" % query[start:])

            term += query[(start + 1):i]
        elif query[i] in ' \t()':
            if term:
                terms.append(term)
                term = ''

            if query[i] in '()':
                terms.append(query[i])
        else:
            term += query[i]
        i += 1

    if term:
        terms.append(term)
        term = ''

    return terms

def parse_query_unary(terms):
    if type(terms) == list:
        if terms[0] == '(':
            query, rest = parse_query(terms[1:])
            if rest[0] != ')':
                raise Exception('Expected paranthesis, got %s' % rest[0])
            return ['quote', query], rest[1:]
        elif terms[0] in ['any', 'all', 'not']:
            query, rest = parse_query_unary(terms[1:])
            return [terms[0], query], rest
        else:
            return parse_query(terms[0])[0], terms[1:]
    else:
        return ['term', terms ], None

def parse_query_binop(terms):
    lhs, rest = parse_query_unary(terms)
    if not rest or rest[0] == ')':
        return lhs, rest

    if rest[0] in ['and', 'or']:
        rhs, rest_ = parse_query_binop(rest[1:])
        if rhs == []:
            return lhs, rest_
        return [rest[0], lhs, rhs], rest_
    else:
        rhs, rest = parse_query_binop(rest)
        if rhs == []:
            return lhs, rest
        return ['and', lhs, rhs], rest

def parse_query(terms):
    return parse_query_binop(terms)

def eval_messages(series, fn, scope, cover=True):
    ret = None
    first = True
    for msg in series['messages']:
        if not cover and message.is_cover(msg):
            continue

        res = fn(msg)
        if first:
            ret = res
            first = False
        elif scope == 'any':
            ret = ret or res
            if ret:
                break
        else:
            ret = ret and res
            if not ret:
                break

    return ret

def eval_query_term(series, term, scope):
    if term.find(':') != -1:
        command, args = term.split(':', 1)
    else:
        command = None

    if command == 'status':
        status = args.lower()

        if status == 'broken':
            return is_broken(series)
        elif status == 'obsolete':
            return is_obsolete(series)
        elif status == 'pull-request':
            return is_pull_request(series)
        elif status == 'rfc':
            return is_rfc(series)
        elif status == 'unapplied':
            return not (is_broken(series) or
                       is_obsolete(series) or
                       is_pull_request(series) or
                       is_rfc(series) or
                       is_committed(series) or
                       is_applied(series))
        elif status == 'committed':
            return is_committed(series)
        elif status == 'reviewed':
            return is_reviewed(series)
        elif status == 'applied':
            return is_applied(series)
        else:
            raise Exception("Unknown status `%s'" % status)
    elif command == 'label':
        txt = config.get_label(args)
        if txt == None:
            raise Exception('Invalid label %s' % args)
        tks = tokenize_query(txt)
        t, _ = parse_query(tks)
        return eval_query(series, t, scope)
    elif command == 'from':
        def fn(msg):
            return match_email_address(msg['from'], args)
        return eval_messages(series, fn, scope)
    elif command == 'committer':
        def fn(msg):
            if 'pull-request' in msg and 'commit' in msg['pull-request']:
                ret = match_email_address(msg['pull-request']['commit']['committer'], args)
                return ret
            elif 'committer' in msg:
                return match_email_address(msg['committer'], args)
            return False
        return eval_messages(series, fn, scope, cover=False)
    elif command == 'to':
        def fn(msg):
            for to in msg['to'] + msg['cc']:
                if match_email_address(to, args):
                    return True
            return False
        return eval_messages(series, fn, scope)
    elif command == 'id':
        def fn(msg):
            return msg['message-id'] == args
        return eval_messages(series, fn, scope)
    elif command == 'tag':
        def fn(msg):
            if not args:
                return 'subject-tags' in msg
            return 'subject-tags' in msg and args.upper() in msg['subject-tags']
        return eval_messages(series, fn, scope)
    elif command == 'release':
        def fn(msg):
            return 'for-release' in msg and msg['for-release'] == args
        return eval_messages(series, fn, scope)
    elif command and command.startswith('buildbot['):
        name = command[9:].split(']', 1)[0]
        if 'buildbots' in series and name in series['buildbots']:
            bot = series['buildbots'][name]
            steps = bot['steps']

            item = args
            fail = False
            if item[0] == '+':
                item = item[1:]
            elif item[0] == '-':
                item = item[1:]
                fail = True

            if item == 'status':
                if fail:
                    return bool(bot['status'])
                else:
                    return bool(not bot['status'])

            for step, status, output in steps:
                if step == item:
                    if fail:
                        return bool(status)
                    else:
                        return bool(not status)
            return False
    elif command != None:
        command = message.format_tag_name(command)
        email_tags = config.get_email_tags()

        def fn(msg):
            if command not in msg['tags']:
                return False
            if not args:
                return True
            if command in email_tags:
                for addr in msg['tags'][command]:
                    if match_flat_email_address(addr, args):
                        return True
                return False
            return args in msg['tags'][command]
        return eval_messages(series, fn, scope, cover=False)
    else:
        def fn(msg):
            return msg['subject'].lower().find(term.lower()) != -1
        return eval_messages(series, fn, scope)

def eval_query(series, terms, scope='any'):
    if terms[0] == 'and':
        return eval_query(series, terms[1], scope) and eval_query(series, terms[2], scope)
    elif terms[0] == 'or':
        return eval_query(series, terms[1], scope) or eval_query(series, terms[2], scope)
    elif terms[0] == 'quote':
        return eval_query(series, terms[1], scope)
    elif terms[0] in ['any', 'all']:
        return eval_query(series, terms[1], terms[0])
    elif terms[0] == 'not':
        return not eval_query(series, terms[1], scope)
    elif terms[0] == 'term':
        return eval_query_term(series, terms[1], scope)
    else:
        raise Exception('Unexpected node type')

if __name__ == '__main__':
    a = '(status:foo or status:bar)'
    t = tokenize_query(a)
    print t
    print parse_query(t)
    a = 'not (status:foo or status:bar)'
    t = tokenize_query(a)
    print t
    print parse_query(t)
    a = 'not status:foo or status:bar'
    t = tokenize_query(a)
    print t
    print parse_query(t)

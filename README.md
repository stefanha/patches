patches Patch Tracking System
=============================

About
-----

patches is a patch tracking system.  It consists of two parts: a set of
commands that build a database of patches from a mailing list and then a set
of commands that can search that database.  It supports the following features:

- Tracking patch status by determining which patches are already committed,
  have newer versions posted, are RFC, etc.

- Applying patches or pull requests with a single command.

- Searching for patches using a rich query language.

Install
-------

    $ python setup.py install

There are no dependencies if you are working with an existing database.  To
build a new database, you need python-notmuch.

Quick Start
-----------

To get started with the QEMU project:

    $ patches fetch http://wiki.qemu.org/patches/patches.json
    $ patches list
    Message-id: 1357498122-1129-1-git-send-email-afaerber@suse.de
    From: Andreas Färber <afaerber@suse.de>
       [0/2] QOM realize, device-only
       [1/2] qdev: Fold state enum into bool realized
       [2/2] qdev: Prepare "realized" property
    
    Message-id: 1357497091-30013-1-git-send-email-afaerber@suse.de
    From: Andreas Färber <afaerber@suse.de>
       [0/2] PowerPCCPU subclasses
       [1/2] target-ppc: Slim conversion of model definitions to QOM subcl..
       [2/2] target-ppc: Error out for -cpu host on unknown PVR
    ...
    $ patches apply id:1357498122-1129-1-git-send-email-afaerber@suse.de
    Applying: qdev: Fold state enum into bool realized
    Applying: qdev: Prepare "realized" property

The `fetch` command should be run whenever you want to refresh the patch
database; it will download any new patches that have arrived since the
last time you did a fetch.

If you only use patches with one project you can set the default fetch
URL by creating a `~/.patchesrc` file with the following contents:

    [fetch]
    # Default URL to use if 'patches fetch' is not given an argument:
    url=http://wiki.qemu.org/patches/patches.json

Search Language
---------------

The query language supported by patches supports boolean operators: "and" and
"or", and unary operators: "not", "any", and "all".  Parentheses and string
quotation are also supported.  Terms are matched using substring search within
the subject.

The "any" and "all" operators change whether the search term applies to at least
one of the messages in a thread or all messages in a thread.

Special terms have a prefix and can be used to search against other parameters
than subject text.  The following prefixes are supported:

- `status:broken` show broken series (malformed or missing patches)
- `status:obsolete` show series that have newer versions available
- `status:pull-request` show pull requests
- `status:rfc` show RFC postings
- `status:committed` show committed series
- `status:applied` show series with a "Thanks, applied" reply
- `status:unapplied` short hand for `not (status:broken or status:obsolete or status:pull-request or status:rfc or status:committed or status:applied)`
- `status:reviewed` show series where every patch has at least one Reviewed-by
- `to:ADDRESS` show series where `ADDRESS` is on the receipent list
- `from:ADDRESS` show series where `ADDRESS` is the sender
- `reviewed-by:ADDRESS` show series if a patch has a Reviewed-by by `ADDRESS`
- `tested-by:ADDRESS` show series if a patch has a Tested-by by `ADDRESS`
- `nacked-by:ADDRESS` show series if a patch has a Nacked-by by `ADDRESS`
- `acked-by:ADDRESS` show series if a patch has a Acked-by by `ADDRESS`

Query Examples
--------------

Show unapplied patches where 'Anthony Liguori' was CC'd:

    $ patches list 'to:"Anthony Liguori" status:unapplied'

Note that the whole query is wrapped in single quotes.  This is necessary to
avoid having conflicts between shell quote interpretation and patches.

Limit the search to only patches that haven't been reviewed yet:

    $ patches list 'to:"Anthony Liguori" status:unapplied not status:reviewed'

Integration with Notmuch
------------------------

patches is not meant to be a tool to review patches directly.  Instead, it is
designed to integrate with mail clients for displaying patches.

The `list` command can be passed `--format=notmuch` which will cause
patches to output a notmuch search query instead of a stylized output.

Applying Patches and Pull Requests
----------------------------------

Given a message-id of any patch within a series, patches can apply a patch
series or pull request.  This is meant to allow integration with mail clients
that can call out to a external program to process a mail.

`patches apply` takes a query string, so you usually want to provide a search
string with an `id:` function.

Notifying on Commits
--------------------

To use the `notify` command, you need to add the following stanzas to your
`~/.patchesrc` file:

    [notify]
    default_sender=Your Name <your@email.com>
    smtp_server=your.smtp.server.com
    events=pulled;committed

This will send out notifications when patches detects that you have committed
a patch or pulled a pull request.

There are two very important options when using the notify command.  The
`--dry-run` option will show you the mail you are about to send without
taking any real action.  You should always run with `--dry-run` before
sending notifies!

Since patches is looking at a 30 day history, the first time you run it, it
will want to send a very large number of notifications.

To setup the database and avoid these notifications, you should run with the
`--fake` option for the first time.  This will pretend that the emails are
being sent without actually sending them.

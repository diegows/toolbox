#!/usr/bin/python
#
# delete-email.py - Delete email based on some criteria.
#
# Tested on Cyrus IMAP.
#
# Diego Woitasen - diego@woitasen.com.ar
#

import imaplib
import sys
import email

from optparse import OptionParser

usage = "usage: %s" % (sys.argv[0])
parser = OptionParser(usage)

parser.add_option("--from", dest = "sender",
                    help = "Sender address.")

parser.add_option("--subject", dest = "subject",
                    help = "Subject.")

parser.add_option("--imap", dest = "imap",
                    help = "IMAP Server.")

parser.add_option("--user", dest = "user",
                    help = "User. (Could be an admin user if you want to" + \
                             " delete mails on all folders of every user.")

parser.add_option("--pass", dest = "passw",
                    help = "User pass.")

parser.add_option("--unseen", action = "store_true", dest = 'unseen',
                    default = False,
                    help = "Delete mail only with the unseen flag.")

parser.add_option("--expunge", action = "store_true", dest = 'expunge',
                    default = False,
                    help = "Expunge after delete.")

(options, args) = parser.parse_args()

for option in [ 'sender', 'subject', 'imap', 'user', 'passw' ]:
    if not getattr(options, option):
        print option + ' is required '
        print parser.format_help()
        sys.exit(-1)

imap = imaplib.IMAP4_SSL(options.imap)
print imap.login(options.user, options.passw)

deleted = 0
for mbox in imap.list()[1]:
    try:
        print mbox
        mbox = mbox.split()[2].strip('"')
        res = imap.select(mbox)
        if res[0] != 'OK':
            continue
        filter = '(FROM "%s" SUBJECT "%s"' % \
                        (options.sender, options.subject)

        if options.unseen:
            filter += ' UNSEEN'

        filter += ')'

        print filter
        typ, newmsgs = imap.search(None, filter)

        print newmsgs
        for num in newmsgs[0].split():
            if num != '':
                typ, data = imap.fetch(num, '(RFC822)')
                msg = email.message_from_string(data[0][1])
                print msg['subject']
                print imap.store(num, '+FLAGS', '\\Deleted')
                deleted += 1

        if options.expunge:
            print imap.expunge()
    except imap.error, e:
        print 'IMAP error:', e
        continue

print deleted, 'mail deleted.'

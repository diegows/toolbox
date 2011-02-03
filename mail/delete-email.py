#!/usr/bin/python
import imaplib
import sys
import email

#CONFIG
superuser = 'manager'
superpass = 'xtech'
imap_filter = '(FROM "diegows@xtech.com.ar")'
dry_run = True
###

imap = imaplib.IMAP4()
print imap.login(superuser, superpass)

deleted = 0
for mbox in imap.list()[1]:
    try:
        mbox = mbox.split()[2].strip('"')
        res = imap.select(mbox)
        if res[0] != 'OK':
            continue
        typ, newmsgs = imap.search(None, imap_filter)

        for num in newmsgs[0].split():
            if num != '':
                typ, data = imap.fetch(num, '(RFC822)')
                msg = email.message_from_string(data[0][1])
                print mbox, msg['subject']
                if not dry_run:
                    print imap.store(num, '+FLAGS', '\\Deleted')
                    deleted += 1
    except imap.error:
        print 'ERROR', mbox
        continue


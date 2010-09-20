#!/usr/bin/python

import email
import sys

def die(msg):
    print msg
    sys.exit(-1)

try:
    mail_file_path = sys.argv[1]
    prefix = sys.argv[2]
    mail_file = open(mail_file_path)
except IndexError:
    die('I need a prefix!. For example: /tmp/parts, parts.')
except IOError, e:
    die("I can't open the file. " + str(e))

msg = email.message_from_file(mail_file)

if not msg.is_multipart():
    die('This messages is not a multipart message.')

i = 0
for payload in msg.get_payload():
    output_file = prefix + str(i)
    i += 1
    open(output_file, 'w').write(payload.get_payload())


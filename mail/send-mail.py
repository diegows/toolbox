#!/usr/bin/python
#
# Send an email with an attached file. Based on the example of Python doc.
#
# Diego Woitasen <diego@woitasen.com.ar>
#

# Import smtplib for the actual sending function
import smtplib

# Here are the email package modules we'll need
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mimetypes

from optparse import OptionParser
import sys
import os

COMMASPACE = ', '

usage = "usage: %s" % (sys.argv[0])
parser = OptionParser(usage)

parser.add_option("--smtp", dest = "smtp",
                     help = "SMTP server.")

parser.add_option("--from", dest = "sender",
                     help = "Sender address.")

parser.add_option("--to", dest = "recipients",
                     help = "Recipients address (separated by comma).")

parser.add_option("--subject", dest = "subject",
                     help = "Subject.")

parser.add_option("--body", dest = "body",
                     help = "Body (string or file path.")

parser.add_option("--attach", dest = "attach",
                     help = "File(s) to attach (separated by comma).")

(options, args) = parser.parse_args()

for option in [ 'smtp', 'sender', 'recipients', 'subject', 'body' ]:
    if not getattr(options, option):
        print option + ' is required '
        print parser.format_help()
        sys.exit(-1)

# Create the container (outer) email message.
msg = MIMEMultipart()
msg['Subject'] = options.subject
# me == the sender's email address
# family = the list of all recipients' email addresses
msg['From'] = options.sender
msg['To'] = options.recipients

if os.path.exists(options.body):
	msg.preamble = open(options.body).read()
else:
	msg.preamble = options.body

# Assume we know that the image files are all in PNG format
if options.attach:
    for file in options.attach.split(','):
        file = file.strip()
        ctype, encoding = mimetypes.guess_type(file)
        if ctype is None or encoding is not None:
            # No guess could be made, or the file is encoded (compressed), so
            # use a generic bag-of-bits type.
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        if maintype == 'text':
            fp = open(file)
            # Note: we should handle calculating the charset
            part = MIMEText(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'image':
            fp = open(file, 'rb')
            part = MIMEImage(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'audio':
            fp = open(file, 'rb')
            part = MIMEAudio(fp.read(), _subtype=subtype)
            fp.close()
        else:
            fp = open(file, 'rb')
            part = MIMEBase(maintype, subtype)
            part.set_payload(fp.read())
            fp.close()
            # Encode the payload using Base64
            encoders.encode_base64(part)
        # Set the filename parameter
        filename = os.path.basename(file)
        part.add_header('Content-Disposition', 'attachment', filename = filename)
        msg.attach(part)


# Send the email via our own SMTP server.
s = smtplib.SMTP(options.smtp)
s.sendmail(options.sender, options.recipients, msg.as_string())
s.quit()


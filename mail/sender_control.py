#!/usr/bin/python -u 
#
# Sender control for Kolab
# 
# Modifies From:, Sender: and Reply-To: headers to get the 
# "send on behalf of"/"send as" behavior of Microsoft Exchange on Kolab.
#
# Example configuration in master.cf
#sender_control     unix  -       n       n       -       20       pipe user=kolab-n null_sender= argv=/usr/local/bin/sender_control.py
#	--sender=${sender}
#	--recipient=${recipient}
#	--user=${sasl_username}
#        --ldapuri=ldap://127.0.0.1
#        --binddn=cn=nobody,cn=internal,dc=bancocredicoop,dc=coop
#        --bindpw=RUdj9xXIIV7296Bgw1ctuTmJAvMafyu0pqhhYVCb
#        --ldapbase=dc=bancocredicoop,dc=coop
#	--altermime=/kolab/bin/altermime
#	--disclaimer=/kolab/etc/postfix/disclaimer.txt
#	--tmpdir=/var/spool/filter
#	--smtp=localhost
#	--smtpport=10025
#

import sys
import os
import atexit
import shutil
import uuid

import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

from optparse import OptionParser
from smtplib import SMTP, CRLF
from tempfile import NamedTemporaryFile
from subprocess import PIPE, Popen
from syslog import openlog, syslog, LOG_MAIL
from email.utils import parseaddr, formataddr
from twisted.mail.smtp import sendmail
from twisted.internet import reactor

import ldap
import re

FROM = 'from'
SENDER = 'sender'
REPLY_TO = 'reply-to'
MAIL = 'mail'
CN = 'cn'
UID = 'uid'
KOLABDELEGATE = 'kolabDelegate'
SENDAS = 'sendas-'
CALENDAR_REGEX = 'content-type.*text/calendar'

#arguments that are not required
opts = [ 'user', 'sender' ]

def die(msg = 'Internal error', errcode = 421):
    errcode = str(errcode)
    if len(errcode) != 3:
        errcode = '421'
    errcode = '%c.%c.%c ' % tuple(errcode)
    msg = errcode + msg
    syslog(msg)
    print msg
    sys.exit(-1)


def parse_opts():
    usage = "usage: %s" % (sys.argv[0])
    parser = OptionParser(usage)

    parser.add_option("--sender", dest = "sender",
                     help = "Envelope sender.")

    parser.add_option("--recipient", dest = "recipient", action = "append",
                        help = "Envelope recipient.")

    parser.add_option("--user", dest = "user",
                        help = "Autenticated user.")

    parser.add_option("--ldapuri", dest = "ldapuri",
                        help = "LDAP uri.")

    parser.add_option("--ldapbase", dest = "ldapbase",
                        help = "LDAP base.")

    parser.add_option("--binddn", dest = "binddn",
                        help = "LDAP bind dn.")

    parser.add_option("--bindpw", dest = "bindpw",
                        help = "LDAP bind password.")

    parser.add_option("--smtp", dest = "smtp",
                        help = "SMTP address.")

    parser.add_option("--smtpport", dest = "smtpport",
                        help = "SMTP port.")

    parser.add_option("--tmpdir", dest = "tmpdir", default = '/tmp',
                        help = "TMP directory.")

    parser.add_option("--altermime", dest = "altermime",
                        help = "Envelope sender.")

    parser.add_option("--disclaimer", dest = "disclaimer",
                        help = "Envelope sender.")

    (options, args) = parser.parse_args()

    syslog(str(options))

    for opt in parser.option_list:
        if opt.dest and opt.dest not in opts:
            if not getattr(options, str(opt.dest)):
                die('Missing argument: ' + opt.dest)

    return options



class Message:
    def __init__(self, options):
        self.options = options
	try:
        	self.ldap = ldap.initialize(options.ldapuri)
        	self.ldap.bind(options.binddn, options.bindpw)
	except ldap.LDAPError, e:
		die('LDAP Connection error')

    def __del__(self):
        os.unlink(self.msg_tempfile)
        #shutil.move(self.msg_tempfile, self.options.tmpdir + '/SENT-' + \
        #            uuid.uuid1().hex)
        pass

    def save_mail(self):
        """
        Read the mail from stdin and fix From:, Sender: and Reply-to: headers.
        """
        self.msg = NamedTemporaryFile(dir = self.options.tmpdir, delete = False)
        self.msg_tempfile = self.msg.name

        self.from_hdr = False
        self.sender_hdr = False
        self.reply_to_hdr = False
        self.calendar_fwd = False

        #null sender => MAILER-DAEMON
        if self.options.user and self.options.sender:
            headers = True
        else:
            headers = False
        while True:
            line = sys.stdin.readline()
            if not line:
                break

            if headers:
                lc_line = line.lower()
                if lc_line.startswith(FROM + ':'):
                    self.from_hdr = line
                    continue
                elif lc_line.startswith(SENDER + ':'):
                    self.sender_hdr = line
                    continue
                elif lc_line.startswith(REPLY_TO + ':'):
                    self.reply_to_hdr = line
                    continue
                if re.match(CALENDAR_REGEX, lc_line, re.IGNORECASE):
                    self.calendar_fwd = True
                elif line.strip() == '':
                    self.fix_headers()
                    headers = False

            self.msg.write(line)

        self.msg.close()

        return self.msg_tempfile


    def fix_headers(self):
        syslog('From ' + str(self.from_hdr))
        syslog('Sender ' + str(self.sender_hdr))
        syslog('Reply-to ' + str(self.reply_to_hdr))

        user = self.options.user.split('@')[0]
        user_info = self.get_info(UID, user)
        if not user_info:
            die("FATAL: user %s doesn't exists or is duplicated." % \
                    (user))

        if (not self.sender_hdr and not self.reply_to_hdr) or not self.from_hdr:
            self.write_hdr(FROM, user_info[CN], user_info[MAIL])
            if self.reply_to_hdr:
                self.msg.write(self.reply_to_hdr)
            return

        from_hdr = parseaddr(self.from_hdr)

        if self.sender_hdr:
            sender_hdr = parseaddr(self.sender_hdr)
            if sender_hdr[1] == from_hdr[1]:
                self.write_hdr(FROM, user_info[CN], user_info[MAIL])
                return
            if self.reply_to_hdr:
                self.msg.write(self.reply_to_hdr)
        elif self.reply_to_hdr:
            reply_to_hdr = parseaddr(self.reply_to_hdr)
            if reply_to_hdr[1] == from_hdr[1]:
                self.write_hdr(REPLY_TO, *reply_to_hdr)
                self.write_hdr(FROM, user_info[CN], user_info[MAIL])
                return
            from_hdr = reply_to_hdr
            sender_hdr = from_hdr

        from_info = self.get_info(MAIL, from_hdr[1],
                        [ CN, MAIL ] , [ KOLABDELEGATE ])

        delegate = False 

        #Calendar, allow send on behalf of
        if self.calendar_fwd:
            delegate = user_info[MAIL]

        if not delegate and from_info and from_info.has_key(KOLABDELEGATE):
            for i in from_info[KOLABDELEGATE]:
                if i in [ user_info[MAIL], SENDAS + user_info[MAIL] ]:
                    delegate = i
                    break

        if not delegate:
            die("Permission denied: you don't have permission on %s" % \
                (from_hdr[1]), 544)

        if delegate and delegate.startswith(SENDAS):
            self.write_hdr(FROM, from_info[CN], from_info[MAIL])
            return

        self.write_hdr(SENDER, user_info[CN], user_info[MAIL])
        self.write_hdr(FROM, from_info[CN], from_info[MAIL])


    def get_info(self, attr, value, req_attrs = [ CN, MAIL ], opt_attrs = []): 
        try:
            res = self.ldap.search_s(self.options.ldapbase, ldap.SCOPE_SUBTREE,
                    '%s=%s' % (attr, value),
                    req_attrs + opt_attrs)
        except ldap.LDAPError, e:
            die('LDAP search ERROR (%s). That means a config option is wrong.' \
                    % (e))
	
        if len(res) != 1:
            return False

        attrs = res[0][1]
        ret_attrs = {}

        for req_attr in req_attrs:
            if not req_attr in attrs.keys():
                die("FATAL: invalid %s=%s object doesn't have %s attr in LDAP" %
                    (req_attr))

            ret_attrs[req_attr] = attrs[req_attr][0]

        for opt_attr in opt_attrs:
            if opt_attr in attrs.keys():
                ret_attrs[opt_attr] = attrs[opt_attr]

        return ret_attrs


    def write_hdr(self, hdr, info, mail):
        hdr_line = '%s: %s' % \
            (hdr.capitalize(), formataddr((info, mail)))
        self.msg.write(hdr_line + CRLF)


    def send_mail(self):
        msg_fd = open(self.msg_tempfile)
        dfr = sendmail(self.options.smtp, self.options.sender,
                        self.options.recipient,
                        msg_fd, port = int(self.options.smtpport))

        def success(r):
            reactor.stop()

        def error(e):
            reactor.stop()

        dfr.addCallback(success)
        dfr.addErrback(error)
        reactor.run()


    def add_disclaimer(self):
        altermime_cmd = "%s --input=%s --disclaimer=%s "
        altermime_cmd += "--disclaimer-html=%s "
        altermime_cmd += " > /dev/null 2>&1" 
        altermime_cmd = altermime_cmd % \
                            (self.options.altermime, self.msg_tempfile,
                            self.options.disclaimer, self.options.disclaimer)

        ret = os.system(altermime_cmd)
        if ret != 0:
            syslog('WARNING: "%s" execution failure (rc = %s).' % \
                (altermime_cmd, ret))


def main():
    openlog('sender_control.py', 0, LOG_MAIL)

    options = parse_opts()

    msg = Message(options)
    msg.save_mail()
    #msg.add_disclaimer()
    msg.send_mail()


#I know, we must not do this... but I have to ensure that the emails are
#deferred if something goes wrong.
try:
    main()
except Exception, e:
    die('Internal error: ' + str(e))


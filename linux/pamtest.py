#!/usr/bin/env python
#
# Dummy script to test pam module from command line. It's the original example
# of the Python module with a few changes.
#
# Diego Woitasen - <diego@woitasen.com.ar>
#

import sys
import PAM
from getpass import getpass

def pam_conv(auth, query_list, userData):

	resp = []

	for i in range(len(query_list)):
		query, type = query_list[i]
		if type == PAM.PAM_PROMPT_ECHO_ON:
			val = raw_input(query)
			resp.append((val, 0))
		elif type == PAM.PAM_PROMPT_ECHO_OFF:
			val = getpass(query)
			resp.append((val, 0))
		elif type == PAM.PAM_PROMPT_ERROR_MSG or type == PAM.PAM_PROMPT_TEXT_INFO:
			print query
			resp.append(('', 0))
		else:
			return None

	return resp

if len(sys.argv) < 3:
    print "server and user required!. example: %s imap username" % \
        sys.argv[0]

service = sys.argv[1]
user = sys.argv[2]

auth = PAM.pam()
auth.start(service)
if user != None:
	auth.set_item(PAM.PAM_USER, user)
auth.set_item(PAM.PAM_CONV, pam_conv)
try:
	auth.authenticate()
	auth.acct_mgmt()
except PAM.error, resp:
	print 'Go away! (%s)' % resp
except:
	print 'Internal error'
else:
	print 'Good to go!'

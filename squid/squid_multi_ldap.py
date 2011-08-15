#!/usr/bin/python -u
#
# Squid Multi LDAP Helper.
#
# Diego Woitasen - <diego@woitasen.com.ar>
#

import sys,re,ldap,syslog

###############CONFIG#########################################################
ldap1 = { 
		'uri'		: 'ldaps://1.2.3.4', 
		'binddn'	: 'cn=squid,ou=users,o=company1',
		'bindpw'	: 'squid',
		'bases'		: ( 'o=company1' ),
		'filter'	: '(&(objectClass=person)(mail=%s))',
		'suffix'	: '@company1.com.ar' }

ldap2 = { 
		'uri'		: 'ldaps://5.6.7.8', 
		'binddn'	: 'cn=squid,ou=users,o=company2',
		'bindpw'	: 'squid',
		'bases'		: ( 'o=company2' ),
		'filter'	: '(&(objectClass=person)(cn=%s))', 
		'suffix'	: '' }

ldapses = (ldap1, ldap2)

##############################################################################

required_keys = ('uri', 'binddn', 'bindpw', 'bases', 'filter', 'suffix')

def err():
	#print "ERR"
	sys.stdout.write('ERR\n')
	sys.stdout.flush()

def ok():
	#print "OK"
	sys.stdout.write('OK\n')
	sys.stdout.flush()

def logger(str):
	syslog.syslog('squid_multi_ldap: ' + str)
	#print str

def config_check():
	for i in ldapses:
		for key in required_keys:
			if not i.has_key(key):
				logger('Configuration error: ' + key + 
						' required')
				sys.exit(-1)

def ldap_connect(uri, binddn, bindpw):
	try:
		conn = ldap.initialize(uri) 
		conn.protocol_version = ldap.VERSION3
		conn.simple_bind_s(binddn, bindpw)

	except ldap.LDAPError, err:
		logger('LDAP Error conn: %s' % (str(err)))
		return False

	return conn

def ldap_auth(ldap_info, user, passw):

	conn = ldap_connect(ldap_info["uri"], ldap_info["binddn"], 
				ldap_info["bindpw"])
	if not conn:
		return False

	userdn = ''
	for base in ldap_info["bases"]:
		if not base: continue
		filter = ldap_info["filter"] % (user)
		try:
			res = conn.search(base, ldap.SCOPE_SUBTREE, filter)
		except ldap.LDAPError, err:
			logger('LDAP Error Search: %s' % (str(err)))
			return False
		type, data = conn.result(res, 0)
		if data != []:
			userdn = data[0][0]
			break

	if not userdn:
		return False

	authtest = ldap_connect(ldap_info["uri"], userdn, passw)
	if not authtest:
		return False
	
	return True

class squid_auth:
	def __init__(self):
		self._buffer = False
		self.in_format = re.compile("^\S+\s+\S+");

	def process(self):
		self.readline()
		if not self.line:
			return False

		self.line = self.line[:-1]
		if not self.in_format.match(self.line):
			err()
			return True

		user, passw = self.line.split()

		for i in ldapses:
			if not i["suffix"] or user.find(i["suffix"]) != -1:
				ldap_info = i
				break

		if not ldap_auth(ldap_info, user, passw):
			err()
		else:
			ok()
		return True

	def readline(self):
		self.line = sys.stdin.readline()

#main()
config_check()
multi_ldap = squid_auth()
while multi_ldap.process(): pass


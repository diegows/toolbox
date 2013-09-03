#!/usr/bin/python
#
# Script to delete objects from LDAP using a filter.
# Use with caution :)
#
# Diego Woitasen <diego@woitasen.com.ar>
#

import ldap
from optparse import OptionParser

parser = OptionParser()
parser.add_option('--ldapuri')
parser.add_option('--ldapbinddn')
parser.add_option('--ldapbindpw')
parser.add_option('--searchbase')
parser.add_option('--filter')
(options, args) = parser.parse_args()

new_ldap = ldap.initialize(options.ldapuri)
new_ldap.bind_s(options.ldapbinddn, options.ldapbindpw)
objs = new_ldap.search_s(options.searchbase, ldap.SCOPE_SUBTREE, options.filter)

for obj in objs:
    dn = obj[0]
    print dn
    #new_ldap.delete_s(dn)

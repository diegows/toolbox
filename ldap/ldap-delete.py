#!/usr/bin/python
#
# Script to delete objects from LDAP using a filter.
# Use with caution :)
#
# Diego Woitasen <diego@woitasen.com.ar>
#

import ldap
import argparse

parser = argparse.ArgumentParser(description='LDAP delete by filter.')
parser.add_argument('--ldapuri', required=True)
parser.add_argument('--ldapbinddn', required=True)
parser.add_argument('--ldapbindpw', required=True)
parser.add_argument('--searchbase', required=True)
parser.add_argument('--filter', required=True)
args = parser.parse_args()

new_ldap = ldap.initialize(args.ldapuri)
new_ldap.bind_s(args.ldapbinddn, args.ldapbindpw)
objs = new_ldap.search_s(args.searchbase, ldap.SCOPE_SUBTREE, args.filter)

for obj in objs:
    dn = obj[0]
    print dn
    new_ldap.delete_s(dn)

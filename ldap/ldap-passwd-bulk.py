#!/usr/bin/python
#
# Script to change LDAP password for more than one user at a time.
#
# Example:
# ldap-passwd-bulk.py --ldapuri ldaps://localhost:636 \
#   --ldapbinddn "cn=manager,dc=example,dc=com" \
#   --ldapbindpw "123456" \
#   --searchbase "dc=example,dc=ar" \
#   --filter "uid=johndoe" \
#   --newpass xxxxxx
#

import ldap
import argparse

parser = argparse.ArgumentParser(description='Director control cmd tool.')
parser.add_argument('--ldapuri', required=True)
parser.add_argument('--ldapbinddn', required=True)
parser.add_argument('--ldapbindpw', required=True)
parser.add_argument('--searchbase', required=True)
parser.add_argument('--filter', required=True)
parser.add_argument('--newpass', required=True)
args = parser.parse_args()

new_ldap = ldap.initialize(args.ldapuri)
new_ldap.bind_s(args.ldapbinddn, args.ldapbindpw)
users = new_ldap.search_s(args.searchbase, ldap.SCOPE_SUBTREE, args.filter)

for user in users:
    dn = user[0]
    print dn
    new_ldap.passwd_s(dn, None, args.newpass)


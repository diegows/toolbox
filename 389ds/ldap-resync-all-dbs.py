#!/usr/bin/python
#
# Script to re-synchronize the replication of 389 DS databases.
#
# Without any argument, it performs re-sync of all database of all agreements.
# If you have a FQDN as argument, it performs re-sync of all database of the specified 
# host
#
# Diego Woitasen <diego@woitasen.com.ar>
# http://www.woitasen.com.ar
#


import ldap
from getpass import getpass
from time import sleep
import sys

bind_dn = "cn=directory manager"
host = "localhost"
base = "cn=config"

ldap_c = ldap.init(host)
ldap_c.start_tls_s()
ldap_c.bind_s(bind_dn, getpass('Ingrese password del manager: '))

if len(sys.argv) > 1:
    print base
    print '(&(objectClass=nsDS5ReplicationAgreement)(nsDS5ReplicaHost=%s))' % \
                sys.argv[1]
    results = ldap_c.search_s(base, 
                ldap.SCOPE_SUBTREE,
                '(&(objectClass=nsDS5ReplicationAgreement)(nsDS5ReplicaHost=%s))' % \
                sys.argv[1])
else:
    results = ldap_c.search_s(base, 
                            ldap.SCOPE_SUBTREE,
                            'objectClass=nsDS5ReplicationAgreement')

for obj in results:
    dn = obj[0]
    print dn
    modlist = [ (ldap.MOD_ADD, 'nsDS5BeginReplicaRefresh', 'start') ]
    ldap_c.modify_s(dn, modlist)
    #Wait before continue. If not and you have a lof of agreements 
    #(I have 300+) the current server will die :)
    sleep(10)


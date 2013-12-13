#!/usr/bin/env python
#
# Export/Import DNS zone from a Cloud provider.
#
# Usage:
# cloud-dns.py --provider rs-myaccount --zone test.com --export > myzone.txt
# Edit your records and then
# cloud-dns.py --provider rs-myaccount --zone test.com --import < myzone.txt
#
# code@vhgroup.net
# VHGroup - www.vhgroup.net
#

import os
import sys
import argparse
import json
from ConfigParser import ConfigParser, NoSectionError, NoOptionError

from libcloud.compute.providers import get_driver as get_compute_driver
from libcloud.dns.types import Provider as DNSProvider, RecordType
from libcloud.dns.providers import get_driver as get_dns_driver

cfg = ConfigParser()
cfg.read(os.path.expanduser('~/.libcloud.conf'))

config_example = """
[rs-myaccount]
provider = rackspace
user = YOUR_USER
apikey = YOUR_KEY

Right now only Rackspace is supported!

"""

parser = argparse.ArgumentParser()
parser.add_argument("--provider", required=True,
        help="Provider name from config file")
parser.add_argument("--zone", required=True)
parser.add_argument("--email")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--export", action="store_true")
group.add_argument("--import", action="store_true")

args = parser.parse_args()

try:
    provider_user = cfg.get(args.provider, "user")
    provider_apikey = cfg.get(args.provider, "apikey")
except (NoSectionError, NoOptionError):
    print "Wrong configuration. Create the file ~/.libcloud.conf with:"
    print config_example
    sys.exit(-1)

Cls = get_dns_driver(DNSProvider.RACKSPACE)
dns_driver = Cls(provider_user, provider_apikey)

rr_type_map = {}
for t in dns_driver.list_record_types():
    rr_type_map[t] = getattr(RecordType, t)

def export_zone(zone):
    for record in zone.list_records():
        print '%s;%s;%s;%s' % \
                (record.name, record.type, record.data,
                        json.dumps(record.extra))

def import_zone(zone):
    if zone:
        dns_driver.delete_zone(zone)
    zone = dns_driver.create_zone(args.zone, extra=dict(email=args.email))

    records = {}
    for line in sys.stdin:
        fields = line.split(';')
        fields = map(lambda x: x.strip(), fields)

        rr = records.setdefault(fields[0], list())
        rr.append(fields)

    for name, values in records.iteritems():
        for value in values:
            if value[1] == 'NS':
                continue 
            elif value[1] == 'MX':
                name = ''

            try:
                rr_type = rr_type_map[value[1]]
            except KeyError:
                print "RR TYPE not supported:", value[1]
                sys.exit(-1)

            extra = json.loads(value[3])
            dns_driver.create_record(name, zone, rr_type, value[2], extra)

if getattr(args, "import") and not args.email:
    print '--email is required for import operation.'
    sys.exit(-1)

zone = None
for i in dns_driver.list_zones():
    if i.domain == args.zone:
        zone = i

if args.export:
    export_zone(zone)
else:
    import_zone(zone)


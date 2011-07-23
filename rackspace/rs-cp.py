#!/usr/bin/python

import cloudfiles
import sys
import os
import ConfigParser

if len(sys.argv) != 3:
    print "Usage: rs-cp.py container/file dst_container"
    sys.exit(-1)

config = ConfigParser.ConfigParser()
cfg_path = os.path.expanduser('~/.rackspace.cfg')
if not os.path.exists(cfg_path):
    print "Config file missing: " + cfg_path
    print """File format:
[main]
user = USER
apikey = APIKEY
"""
    sys.exit(-1)

config.read(cfg_path)

src = sys.argv[1]
dst = sys.argv[2]

conn = cloudfiles.get_connection(config.get('main', 'user'),
                    config.get('main', 'apikey'),
                    timeout = 300)
container, obj_name = src.split('/')

print container + "/" + obj_name, "->",  dst
print conn[container][obj_name].size, "bytes"

conn[container][obj_name].copy_to(dst, obj_name)
print conn[dst][obj_name].public_ssl_uri()


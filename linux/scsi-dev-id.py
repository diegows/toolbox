#!/usr/bin/python
#
# Script to list SCSI id/wwn/wwid of the specified devices
#
# Diego Woitasen - <diego@woitasen.com.ar>
#

import sys

import pyudev
import re

def show_device(dev):
    print dev.device_node,
    print dev.get('ID_SERIAL', '-'), 
    print dev.get('ID_MODEL', '-'),
    print dev.get('ID_VENDOR', '-'),
    print

context = pyudev.Context()
dev_re = re.compile(sys.argv[1])

for dev in context.list_devices():
    if dev.device_node is not None and dev_re.match(dev.device_node):
        show_device(dev)

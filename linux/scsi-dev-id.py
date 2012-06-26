#!/usr/bin/python
#
# Script to list SCSI id/wwn/wwid of the specified devices
#
# Diego Woitasen - <diego@woitasen.com.ar>
#

from subprocess import Popen, PIPE
from os import stat
from stat import S_ISBLK
import sys

import pyudev
import re

def show_device(dev):
    print dev.device_node, dev['ID_WWN']

context = pyudev.Context()
dev_re = re.compile(sys.argv[1])

for dev in context.list_devices():
    if dev.device_node is not None and dev_re.match(dev.device_node):
        show_device(dev)

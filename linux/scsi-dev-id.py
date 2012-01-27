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

if len(sys.argv) == 1:
    print "Device(s) path required."
    sys.exit(-1)

def get_id(device):
    scsi_id_cmd = "/lib/udev/scsi_id --whitelisted --device="  + device
    scsi_id = Popen(scsi_id_cmd.split(), stdout=PIPE)
    return scsi_id.stdout.readline().strip()

def is_block(device):
    dev_info = stat(device)
    return S_ISBLK(dev_info.st_mode)

for device in sys.argv[1:]:
    if not is_block(device):
        print "Device %s is not a block device." % (device)
        sys.exit(-1)
    print device, get_id(device)


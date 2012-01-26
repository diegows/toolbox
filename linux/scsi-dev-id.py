#!/usr/bin/python
#
# Script to list SCSI id/wwn/wwid of the specified devices
#
# Diego Woitasen - <diego@woitasen.com.ar>
#

from subprocess import Popen, PIPE
import sys

if len(sys.argv) == 1:
    print "Device(s) path required."
    sys.exit(-1)

def get_id(device):
    scsi_id_cmd = "/lib/udev/scsi_id --whitelisted --device="  + device
    scsi_id = Popen(scsi_id_cmd.split(), stdout=PIPE)
    return scsi_id.stdout.readline().strip()

for device in sys.argv[1:]:
    print device, get_id(device)



import os

from ConfigParser import ConfigParser

from novaclient.v1_1 import client
import boto.ec2

cfg = ConfigParser()
cfg.read(os.path.expanduser("~/.list-ips.cfg"))

def rackspace_ips(rack_cfg):
    nt = client.Client(rack_cfg.get("user"), rack_cfg.get("pass"), 
            rack_cfg.get("tenant"),
            rack_cfg.get("url"), 
            region_name=rack_cfg.get("region"))

    addrs = []
    for server in nt.servers.list():
        for addr in server.addresses["public"]:
            if addr["version"] == 4:
                addrs.append(addr["addr"])

    return addrs

def ec2_ips(ec2_cfg):
    conn = boto.ec2.connect_to_region(ec2_cfg["region"],
            aws_access_key_id=ec2_cfg["key"],
            aws_secret_access_key=ec2_cfg["secret"])

    addrs = []
    reservations = conn.get_all_reservations()
    for reservation in reservations:
        for instance in reservation.instances:
            addrs.append(instance.ip_address)

    return addrs


cloud_addrs = []

for section in cfg.sections():
    provider_cfg = {}
    for option, value in cfg.items(section):
        provider_cfg[option] = value

    if provider_cfg["type"] == "rackspace":
        cloud_addrs += rackspace_ips(provider_cfg)

    if provider_cfg["type"] == "ec2":
        cloud_addrs += ec2_ips(provider_cfg)

for addr in cloud_addrs:
    print addr


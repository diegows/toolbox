#!/usr/bin/env python
#
# Virtual Machine clonner and configurer !? 
#
# It uses libvirt and Fabric to clone VMs and configure them.
# Have a look at this post for more information:
# http://www.woitasen.com.ar/2013/09/making-vm-cloning-easier-with-libvirt-fabric-and-dnsmasq/
#
# Diego Woitasen - <diego@woitasen.com.ar>
#

import sys
import socket

from ConfigParser import ConfigParser
from StringIO import StringIO
from time import sleep
from xml.dom.minidom import parseString

import libvirt
from fabric.api import run, local, put, env, execute
from fabric.network import disconnect_all


try:
    template = sys.argv[1]
    clones = sys.argv[2:]
except IndexError:
    print "Syntax error, my-virt-clone.py template clone1 clone2 ... clone N"
    sys.exit(-1)


def wait_guest(hostname):
    for i in range(60):
        try:
            sock = socket.socket()
            sock.settimeout(3)
            sock.connect((hostname, 22))
            if sock.recv(3) == "SSH":
                return
        except socket.error:
            pass
        sleep(2)

    raise Exception("Guest timeout: " + hostname)

def domain_set_bridge(domain):
    domain = virt_conn.lookupByName(domain)
    domain_xml = domain.XMLDesc(0)

    doc = parseString(domain_xml)
    iface = doc.getElementsByTagName("interface")[0]
    source = iface.getElementsByTagName("source")[0]
    if source.hasAttribute("network"):
        source.source.removeAttribute("network")
    source.setAttribute("bridge", "virbr0")

    virt_conn.defineXML(doc.toxml())

def config_guest(**kwargs):
    template = kwargs["template"]
    guest = kwargs["guest"]
    guest_info = dict(hostname=guest, ip=socket.gethostbyname(template))
    etc_hosts = etc_hosts_tmpl % guest_info
    etc_hosts = StringIO(etc_hosts)

    if template[:6] in [ 'centos', 'fedora', 'redhat' ]:
        hostname_tmpl = sysconfig_hostname_tmpl
        hostname_path = "/etc/sysconfig/network"
    else:
        hostname_tmpl = etc_hostname_tmpl
        hostname_path = "/etc/hostname"

    hostname = hostname_tmpl % (guest)
    hostname = StringIO(hostname)

    put(etc_hosts, "/etc/hosts")
    put(hostname, hostname_path)
    run("reboot")

img_path_tmpl = "/var/lib/libvirt/images/%s.qcow2"
clone_cmd_tmpl = "sudo virt-clone -o %s -n %s -f %s"

etc_hosts_tmpl = """
127.0.0.1 localhost.localdomain localhost
%(ip)s %(hostname)s.woitasen.local %(hostname)s

# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
"""

etc_hostname_tmpl = """%s
"""

sysconfig_hostname_tmpl = """NETWORKING=yes
HOSTNAME=%s
"""

env.user = 'root'

virt_conn = libvirt.open("qemu:///system")

for clone in clones:
    img_path = img_path_tmpl % (clone)
    clone_cmd = clone_cmd_tmpl % (template, clone, img_path)

    local(clone_cmd)
    domain_set_bridge(clone)
    local("virsh start " + clone)

    wait_guest(template)

    execute(config_guest, host=template, template=template, guest=clone)
    #Because Fabric caches connection using template name, but must be sure
    #that they are close at the end of this loop.
    disconnect_all()
    sleep(5)

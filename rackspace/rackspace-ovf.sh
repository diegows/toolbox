#!/bin/bash
#
# Convert Rackspace Cloudserver backups to a OVA file.
#
# Diego Woitasen <diego@woitasen.com.ar>
#
# Requires virtualbox-vdfuse package (Debian, Ubuntu). No idea on others,
# the tool vdfuse and Virtualbox is required.
#
# Tested with Debian 6 based images.
#
# Usage: $0 rackspace.tgz dstname dstdir
#
# Inside the image while it's running on Rackspace, you MUST RUN this first:
# grub-install /dev/xvda1
#

TMPDIR=$(mktemp -d)
VHDMNTDIR=${TMPDIR}/mnt
ROOTMNTDIR=${TMPDIR}/root
IMAGE=$1
DSTNAME=$2
DSTDIR=$3

cd $TMPDIR
mkdir -p $VHDMNTDIR $ROOTMNTDIR

tar xfz $IMAGE
vdfuse -f image/image.vhd $VHDMNTDIR

install-mbr ${VHDMNTDIR}/EntireDisk

mount -o loop,rw ${VHDMNTDIR}/Partition1 $ROOTMNTDIR

cat << EOF > ${ROOTMNTDIR}/etc/network/interfaces

auto lo
iface lo inet loopback

auto eth0 
iface eth0 inet dhcp

EOF

sed -i s/xvda1/sda1/g ${ROOTMNTDIR}/boot/grub/menu.lst

#Disable getty at hvc0
sed -i s/^8:/#8:/g ${ROOTMNTDIR}/etc/inittab

chroot ${ROOTMNTDIR} /sbin/insserv -r nova-agent
rm ${ROOTMNTDIR}/etc/init.d/nova-agent

umount $ROOTMNTDIR $VHDMNTDIR

#Create the VirtualBOX VM to export it as OVA
VBoxManage unregistervm $DSTNAME --delete > /dev/null 2>&1
VBoxManage createvm -name $DSTNAME -register
VBoxManage modifyvm $DSTNAME --memory 1024 --acpi on --nic1 nat
VBoxManage storagectl $DSTNAME \
	--name ide0 \
	--add ide
#Vbox supports VHD, but exporting from a VHD fails. From VMDK works.
vboxmanage clonehd image/image.vhd image.vmdk --format VMDK
VBoxManage storageattach $DSTNAME \
	--storagectl ide0 \
	--type hdd \
	--port 0 --device 0 \
	--medium image.vmdk
VBoxManage export $DSTNAME -o ${DSTDIR}/${DSTNAME}.ova --manifest \
	--vsys 0 \
	--product "VisualApps" \
	--vendorurl "http://www.visualhosting.com.ar"
VBoxManage unregistervm $DSTNAME --delete

rm -fR $TMPDIR


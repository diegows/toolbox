#!/usr/bin/python -u
#
# Zimbra message archiving for the Open Source edition
#
# Tested on Zimbra Open Source Edition 6.0.8.
#
# Requires Python 2.6.x and Sqlalchemy 0.5.8.
#
# zimbra-archive.py config.cfg
#
# Config example: ##########################
# [archiving]
# #Keep only msgs from the last days
# days = 60
# #Volumen name for archiving
# volume = store2
# #Set this to false if you want to do the archiving.
# dry_run = true
# #Archiving only this mailbox ids (optional)
# #mailboxes = 1,2,3,4
# #Post archive command.
# #command = /usr/local/bin/restart-zimbra.sh
# #Finish the archiving in "time" seconds"
# time=14400
# [db]
# user = zimbra
# pass = db_pass
# unix_socket = /opt/zimbra/db/mysql.sock
#
############################################
#
# Diego Woitasen
# diego@woitasen.com.ar
#

import sqlalchemy
from sqlalchemy import and_
from sqlalchemy.ext.sqlsoup import SqlSoup
from sqlalchemy.orm.exc import NoResultFound
from ConfigParser import ConfigParser
from time import time
from datetime import datetime

import gzip
import email
import os
import shutil
import pwd
import sys
import re

config = ConfigParser()

config.read(sys.argv[1])

db_user = config.get('db', 'user')
db_pass = config.get('db', 'pass')
db_socket = config.get('db', 'unix_socket')
days = config.get('archiving', 'days')
archive_vol_name = config.get('archiving', 'volume')
dry_run = config.getboolean('archiving', 'dry_run')
command = config.get('archiving', 'command')
xtime = config.getint('archiving', 'time')

if config.has_option('archiving', 'mailboxes'):
    mailboxes = config.get('archiving', 'mailboxes')
    mailboxes = re.split('\s*,\s*', mailboxes)
    for i in mailboxes:
        if not i.isdigit():
            print 'Mailboxes ids must be numbers.'
            sys.exit(-1)
else:
    mailboxes = []

if not os.path.exists(command):
    print "ERROR: command %s doesn't exists" % (command)
    sys.exit(-1)

if not (db_user and db_pass and db_socket and days):
    print 'Config error!'
    sys.exit(-1)

if not days.isdigit():
    print 'Config file error, days must be a number'
    sys.exit(-1)

date = int(time()) - (86400 * int(days))

mysql_uri = "mysql://%s:%s@localhost/%%s?unix_socket=%s" % \
                (db_user, db_pass, db_socket)

zimbra_uri = mysql_uri % ('zimbra')
zimbra_db = SqlSoup(zimbra_uri)

zimbra_user = pwd.getpwnam('zimbra')
zimbra_uid = zimbra_user.pw_uid
zimbra_gid = zimbra_user.pw_gid

volume = False

def get_volume(volume_id):
    global volume
    if not volume or volume.id != volume_id:
        volume = zimbra_db.volume.filter(zimbra_db.volume.id == volume_id).one()
    return volume

def message_path(mail_item, volume):
    subfolder1 = mail_item.mailbox_id >> volume.mailbox_bits
    subfolder2 = mail_item.id >> volume.file_bits

    msg_path = '%s/%s/%d/msg/%d/%d-%d.msg' % \
                (volume.path, subfolder1, mail_item.mailbox_id, subfolder2,
                    mail_item.id, mail_item.mod_content)

    return msg_path

def mk_dir(dir_path):
    directories = dir_path.split('/')
    dir_path = '/'
    for directory in directories[1:]:
        dir_path += directory + '/'
        if not os.path.exists(dir_path):
            os.mkdir(dir_path, 0750)
            os.chown(dir_path, zimbra_uid, zimbra_gid)

def copy_compress(src, dst):
    dst_gzip = gzip.open(dst, 'wb')
    src_fd = open(src)
    dst_gzip.write(src_fd.read())
    os.unlink(src)

def set_perm(file_path):
    os.chown(file_path, zimbra_uid, zimbra_gid)
    os.chmod(file_path, 0640)


try:
    archive_vol = zimbra_db.volume.\
                filter(zimbra_db.volume.name == archive_vol_name).one()
except sqlalchemy.orm.exc.NoResultFound:
    print "Archive volume doesn't exist"
    sys.exit(-1)

start_time = datetime.now()

for i in range(1, 101):
    mboxgroup_uri = mysql_uri % ('mboxgroup' + str(i))
    mboxgroup_db = SqlSoup(mboxgroup_uri)

    msg_filter = and_(mboxgroup_db.mail_item.volume_id != None,
                        mboxgroup_db.mail_item.volume_id != archive_vol.id,
                        mboxgroup_db.mail_item.date < date)

    if len(mailboxes) > 0:
        msg_filter = and_(msg_filter,
                        mboxgroup_db.mail_item.mailbox_id.in_(mailboxes))

    try:
        mail_items = mboxgroup_db.mail_item.filter(msg_filter).yield_per(100)
    except NoResultFound:
        print 'No items in mboxgroup' + str(i)
        continue

    for mail_item in mail_items:
        volume = get_volume(mail_item.volume_id)

        if volume.compress_blobs == 1:
            print 'Skiping', mail_item.id,
            print 'I don\'t support compressed volumes as source'
            continue

        msg_path = message_path(mail_item, volume)
        msg_archive_path = message_path(mail_item, archive_vol)

        print mail_item.id, mail_item.mailbox_id, msg_path, msg_archive_path,
        if dry_run:
            print 'OK'
            continue

        try:
            archive_dir_path = os.path.dirname(msg_archive_path)
            if not os.path.exists(archive_dir_path):
                mk_dir(archive_dir_path)

            if archive_vol.compress_blobs == 1 and \
                    mail_item.size > archive_vol.compression_threshold:
                copy_compress(msg_path, msg_archive_path)
                print 'zipped',
            else:
                shutil.move(msg_path, msg_archive_path)

            set_perm(msg_archive_path)

            mail_item.volume_id = archive_vol.id
            mboxgroup_db.commit()

        except IOError, e:
            print 'ERROR:', e
            continue

        print 'OK'
        current_time = datetime.now()
        diff_time = current_time - start_time
        if diff_time.seconds > xtime:
            print "Stopping archiving, time excedded."
            break


#Run command after archiving
os.system(command)



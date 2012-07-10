#!/usr/bin/python
#
# Script to organize fotos and discard duplicates.
#
# Diego Woitasen <diego@woitasen.com.ar>
#

import os
import sys
import hashlib
import pyexiv2
import mimetypes
import shutil

src = sys.argv[1]
dst = sys.argv[2]

file_shas = []

def move_file2(file_src, file_dst):
    i = 0
    dir_path, xfile = os.path.split(file_dst)
    while os.path.exists(file_dst):
        xfile = str(i) + "-" + xfile
        file_dst = os.path.join(dir_path, xfile)

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    print file_src, file_dst
    try:
        shutil.move(file_src, file_dst)
    except:
        print "WARN5:", file_src, file_dst

def move_jpeg(file_path):
    try:
        metadata = pyexiv2.ImageMetadata(file_path)
        metadata.read()
        date_time = metadata["Exif.Image.DateTime"].value
        dst_file = os.path.join(dst, 
                str(date_time.year), 
                str(date_time.month), 
                str(date_time.day),
                os.path.basename(file_path) )
    except:
        print "WARN4:", file_path, "exif info not found"
        dst_file = os.path.join(dst, "no-date", os.path.basename(file_path))

    move_file2(file_path, dst_file)

def for_each_file(xdir, func):
    for i in os.walk(xdir):
        files = i[2]
        f_path = i[0]
        if len(files) == 0:
            continue

        for f in files:
            file_path = os.path.join(f_path, f)
            func(file_path)

def shacalc(xfile):
    sha = hashlib.sha1()
    sha.update(open(xfile).read())
    return sha.hexdigest()

def load_sha_list(xfile):
    global file_shas
    digest = shacalc(xfile)
    if digest in file_shas:
        print "WARN:" , xfile, "exists"
    else:
        file_shas.append(digest)

def move_file(xfile):
    global file_shas
    digest = shacalc(xfile)
    if digest in file_shas:
        print "WARN2: ", xfile, "exists"
        return

    file_shas.append(digest)

    file_type = mimetypes.guess_type(xfile)[0]
    if file_type == 'image/jpeg':
        move_jpeg(xfile)
    else:
        print "WARN3:", xfile, "unknown type"


for_each_file(dst, load_sha_list)
for_each_file(src, move_file)


#!/usr/bin/python
#
# Script to extract HTTP headers and bodies from flows/session extracted from 
# pcap files. I usually use Chaosreader to extract the flows/sessions from
# pcap and then this script to extract the HTTP data.
#
# Example:
# chaosread -r data.pcap
# pcap-http.py *raw1
# and you'll see files with .body.NUMBER suffix
#
# Diego Woitasen <diego@woitasen.com.ar>
# http://www.woitasen.com.ar
#

import sys
import os
from httplib import HTTPResponse

#HTTPResponde class expects a socket but it does a makefile() to get a file
#pointer. We are giving a fp to HTTPResponse so we have emulate makefile()
class MyFile(file):
    def makefile(self, *kw):
        return self

#We don't close the fp because the may be read from a pipeline
class MyHTTPResponse(HTTPResponse):
    def close(self):
        pass

def extract_http(flow):
    flow_fd = MyFile(flow)
    size = os.stat(flow).st_size
    serial = 0
    while size > flow_fd.tell():
        try:
            http_response = MyHTTPResponse(flow_fd)
            http_response.begin()
            output_fd = open(flow + '.body.' + str(serial), 'w+')
            output_fd.write(http_response.read())
            serial += 1
        except httplib.IncompleteRead, e:
            #XXX: I haven't look the reason of this, may be broken connections.
            print 'XXX', flow, e


for flow in sys.argv[1:]:
    extract_http(flow)


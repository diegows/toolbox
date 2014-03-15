#!/usr/bin/python
#
# Scan OpenLDAP (389ds?) log an report all the search filters and attrs 
# requested
#
# Diego Woitasen <diego@woitasen.com.ar>
# http://www.woitasen.com.ar
# https://github.com/diegows
#

import sys
import re

search_r = re.compile('.*SRCH.*filter="([^ ]*)"')
attrs_r = re.compile('.*SRCH attr=(.*)')

out = ''
for line in sys.stdin:
    line = line.strip()

    search_m = search_r.match(line)
    if search_m:
        if out is None:
            out = search_m.group(1)
        else:
            print search_m.group(1)

    attrs_m = attrs_r.match(line)
    if attrs_m:
        print "'%s' %s" % (out, attrs_m.group(1))
        out = None

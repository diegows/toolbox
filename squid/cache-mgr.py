import httplib
from datetime import date

class CacheMgr():
    def __init__(self, host_port):
        self.host_port = host_port
        self.http_conn = httplib.HTTPConnection(self.host_port)

    def get(self, name):
        url = "cache_object://%s/%s" % (self.host_port, name)
        self.http_conn.request("GET", url)
        response = self.http_conn.getresponse()
        return response.read()

    def get_counters(self):
        counters = self.get('counters')
        counters = counters.split('\n')
        counters_d = {}
        for counter in counters:
            if len(counter) == 0:
                continue
            counter_nv = counter.split('=')
            counter_name = counter_nv[0].strip()
            counter_value = counter_nv[1].strip()
            if counter_value.isdigit():
                counter_value = int(counter_value)
            counters_d[counter_name] = counter_value

        return counters_d

    def get_hit_ratios(self):
        info = self.get('info')
        info = info.split('\n')
        hit_ratios = {}
        for i in info:
            i = i.strip()
            if i.startswith('Request Hit Ratios'):
                request_hit = i.split()[4]
                request_hit = request_hit.strip('%,')
                hit_ratios['request'] = float(request_hit)
            elif i.startswith('Byte Hit Ratios'):
                byte_hit = i.split()[4]
                byte_hit = byte_hit.strip('%,')
                hit_ratios['byte'] = float(byte_hit)

        return hit_ratios

    def client_list(self):
        client_list = self.get('client_list')
        print client_list

if __name__ == "__main__":
    mgr = CacheMgr('localhost:8080')
    print mgr.client_list()


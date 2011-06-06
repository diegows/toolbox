import socket
from base64 import b64encode
 
class simplesieve:
    fd = ''
    sock = ''
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.fd = self.sock.makefile('w')
        self.wait_resp()

    def cmd(self, command):
        print command
        self.fd.write(command + '\r\n')
        self.fd.flush()

    def wait_resp(self):
        line = self.fd.readline()
        ret = []
        while line:
            ret.append(line)
            if line[:2] == 'OK':
                print ret
                return ret
            if line[:2] == 'NO':
                print ret
                raise 'Command error'
            line = self.fd.readline()

        raise 'Command error'

    def cmdresp(self, command):
        self.cmd(command)
        self.wait_resp()

    def authplain(self, user, passw, authz):
        b64auth = b64encode('%s\0%s\0%s' % (authz, user, passw))
        authlines = 'AUTHENTICATE "PLAIN" {%d+}\r\n' % (len(b64auth))
        authlines += b64auth
        self.cmdresp(authlines)

    def putscript(self, name, script):
        putscript = 'PUTSCRIPT "%s" {%d+}\r\n%s' % (name, len(script),
                        script)
        self.cmdresp(putscript)
        self.cmdresp('SETACTIVE "%s"' % name)

    def __del__(self):
        self.cmdresp('LOGOUT')


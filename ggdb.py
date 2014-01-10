#!/usr/bin/python
import sys
import struct
import socket
from socket import htonl
from socket import ntohl

#static const char hexchars[] = "0123456789abcdef";

def hex(ch):
    if ch >= 'a' and ch <= 'f':
        return ord(ch) - ord('a') + 10
    if ch >= '0' and ch <= '9':
        return ord(ch) - ord('0')
    if ch >= 'A' and ch <= 'F':
        return ord(ch) - ord('A') + 10
    return -1

# scan for the sequence $<data>#<checksum>
class Protocol():

    def __init__(self):
        pass

    def run(self):
        self.svc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print "sd=%s" % self.svc
        self.svc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.svc.bind(("localhost",5000))
        self.svc.listen(5)
        self.sd, self.peer = self.svc.accept()
        print "New connection from", self.peer
        while True:
            p = gdb.getpacket()
            if Protocol.cmds.has_key(p[0]):
                r = Protocol.cmds[p[0]](p)
                gdb.putpacket(r)
            elif p == "k":
                break
            else:
                gdb.putpacket("")

    def getchar(self):
        return self.sd.recv(1)

    def putchar(self, ch):
        self.sd.send(ch)

    def puts(self, buf):
        self.sd.send(buf)

    def wait_for(self, ch):
        while True:
            ch = self.getchar()
            if ch == -1:
                return False
            if ch == '$':
                return True

    def getpacket(self):
        checksum = 0
        buf = ""

        self.wait_for('$')
        while True:
            ch = self.getchar()
            if ch == '$':
                return None
            if ch == '#':
                break
            checksum = checksum + ord(ch);
            buf += ch

        ch = self.getchar()
        xmitcsum = int(ch,16) << 4;
        ch = self.getchar()
        xmitcsum += int(ch,16)

        if (checksum  & 0xff) != xmitcsum:
            print "gdb: bad checksum. mine=0x%x, theirs=0x%x. buf=%s\n" % (checksum, xmitcsum, buf)
            self.putchar('-')
            return None

        self.putchar('+')

        if len(buf) > 2 and buf[2] == ':':
            self.putchar(buf[0])
            self.putchar(buf[1])
            buf = buf[2:]

        print "< %s" % buf
        return buf

    def putpacket(self, buf):
        checksum = 0
        for i in range(len(buf)):
            checksum += ord(buf[i])
        pkt = "$" + buf + "#" + "%02x" % (checksum & 0xff)
        print "> %s" % pkt
        self.puts(pkt)
        ch = self.getchar()
        if ch == None:
            print "gdb: EOF\n"
        if ch != '+':
            print "gdb: No ACK\n"

    def cmd_query(p):
        if p == "qSupported":
            return "PacketSize=%d;QStartNoAckMode?;QNonStop?" % 1024
        return ""

    def reply_ok(p):
        return "OK"

    def cmd_status(p):
        reply = "T"
        reply += "%02x:%08x;" % (13, htonl(0x55004400))
        reply += "%02x:%08x;" % (14, htonl(0x12340000))
        reply += "%02x:%08x;" % (15, htonl(0xc0000050))
        return reply

    def cmd_getregs(p):
        reply = ""
        for r in range(16):
            reply += "%08x" % htonl(r)
        return reply

    cmds = {
        'q' : cmd_query,
        '!' : reply_ok,
        '?' : cmd_status,
        'g' : cmd_getregs,
    }
# Protocol


gdb = Protocol()
gdb.run()


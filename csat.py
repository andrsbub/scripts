#!/usr/bin/env python
import sys
import re
import string
import readline
import pexpect

class CSAT:
	prompt = '%>'

        class Error(Exception):
            def __init__(self, msg):
                Exception.__init__(self, msg)

	def __init__(self):
		self.c = pexpect.spawn('csat', timeout=3)
		self.c.expect(CSAT.prompt)
                self.last_error = None
		self.seg = 0

	def cmd(self, cmd, verbose=False):
		if verbose: print ">>> %s" % cmd
		self.c.sendline(cmd)
		self.c.expect_exact(cmd)
		self.c.expect(CSAT.prompt)
		result = []
                self.last_err = None
		for line in self.c.before.split('\n'):
                        line = line.strip()
			if verbose: print "<<< %s" % line
                        if len(line) > 0:
                            result.append(line)
                            if 'EMUERR_' in line:
                                self.last_err = "%s: %s" % (cmd, line)
		return result

        def check_err(self):
            if self.last_err:
                print self.last_err
            return not self.last_err

        def connect(self, url):
		out = self.cmd('con TCP:swsds01')
                for l in out: print l
		self.cmd('chain dev=ARMCS-DP clk=1000000')
                self.cmd('dvo 0')
                return self.check_err()

	def readmem(self, addr, length):
		result = ""
		while length > 0:
			n = min(512, length)
			words = self.readwords(addr, (n + 3) / 4)
			for w in words:
				for i in range(4):
					result += chr(w & 0xff)
					w >>= 8
			length -= n
			addr += n
		return result

	def select_segment(self, addr):
		if addr >> 32 != self.seg:
			self.seg = addr >> 32
			self.cmd("drw ap0.2 %#x" % self.seg)
		return addr & 0xffffffff

	def writeword(self, addr, value):
		self.writewords(addr, [value])
		return self.readword(addr)

	def writewords(self, addr, values):
		addr = self.select_segment(addr)
		cmd = "dmw 0 %#x " % addr
		for w in values: cmd += "%#x" % w
		self.cmd(cmd)

	def readword(self, addr):
		x = self.readwords(addr, 1)
		if len(x) != 1:
			print "Excpected one-word-list got: %s" % x
		return x[0]

	def readwords(self, addr, num):
		result = []
		addr = self.select_segment(addr)
		buf = self.cmd("dmr 0 %#x %u" % (addr, num))
		for line in buf:
			if not re.match("0x[0-9a-fA-F]+ : ", line):
				raise CSAT.Error(line)
			pfx,data = line.strip().split(':')
			values = data.split()
			for i in xrange(len(values)):
				result.append(int(values[i],0))
		return result

	def close(self):
		self.c.sendline('exit\r')
		self.c.expect('CSAT exiting')

class csat_cli:

    def __init__(self, csat):
        self.csat = csat
        self.cmds = {
            'poke' : self.cmd_poke,
            'x'    : self.cmd_dump,
        }

    @staticmethod
    def printable(c):
            if ord(c) >= 32 and c in string.printable:
                    return c
            else:
		return '.'

    def hexdump(self, buf, group=1, endian='e'):
        hbuf = ""
        abuf = ""
        colw = 0
        for i in xrange(0, len(buf), group):
                word = 0
                rng = xrange(group)
                if endian == 'e':
                    rng = reversed(rng)
                for j in rng:
                    abuf += "%c" % csat_cli.printable(buf[i+j])
                    word <<= 8
                    word |= ord(buf[i+j])
                hbuf += "%0*x " % (group*2, word)
                if len(abuf) >= 16:
                    print "%04x: %-*s %s" % (i&~0xf, colw, hbuf, abuf)
                    colw = len(hbuf)
                    hbuf = ""
                    abuf = ""
        if len(abuf) > 0:
            print "%04x: %-*s %s" % (i&~0xf, colw, hbuf, abuf)

    def cmd_dump(self, args):
        if args[0][0] == '/':
            groups = { 'w':4, 'h':2, 'b':1 }
            grouping = 4
            endian = 'e'
            fmt = args.pop(0)
            m = re.match("/([0-9]+)([whb]?)([eE]?)", fmt)
            if not m:
                print "Bad format %s" % fmt
                return False
            if len(m.group(2)) > 0:
                grouping = groups[m.group(2)]
            if len(m.group(3)) > 0:
                endian = m.group(3)
            length = int(m.group(1), 0)
        addr = int(args[0], 0)
        buf = csat.readmem(addr, length)
        self.hexdump(buf, group=grouping, endian=endian)

    def cmd_poke(self, args):
        try:
            if len(args) == 1:
                x = csat.readword(int(args[0],0))
                print "%#x" % x
            else:
                print "%#x" % csat.writeword(int(args[0],0), int(args[1],0))
        except CSAT.Error, e:
            print "%s" % e.message

    def run(self):
	while True:
		try:
			x = raw_input("%s> " % host)
		except EOFError, e:
			print "Exiting"
			break
		w = x.split()
                if '/' in w[0]:
                    cmd = w[0][:w[0].index('/')]
                    args = [ w[0][w[0].index('/'):] ]
                else:
                    cmd = w[0]
                    args = []
                args += w[1:]
		if len(cmd) == 0:
			break
                if not self.cmds.has_key(cmd):
			print "Unknown command: %s" % cmd
                        continue

                self.cmds[cmd](args)

if __name__ == "__main__":
	host = 'TCP:swsds01'
	csat = CSAT()
        if not csat.connect(host):
            sys.exit(1)
        try:
            cli = csat_cli(csat)
            cli.run()
            csat.close()
        except Exception, e:
            csat.close()
            raise

#!/usr/bin/python
import re
import sys
import struct
import subprocess
import getopt
import pexpect

logsize   = (64<<10)
blocksize = 1024
hex_exp   = re.compile("([0-9a-f_]+)[\t ]+((?:[0-9a-f]{2} )+).*")
word_exp  = re.compile("([0-9a-f_]+)[\t ]+((?:[0-9a-f]{8} )+).*")
sym_exp   = re.compile("\s+\d+:\s+([\da-f]+)\s+(\d+)\s(\S+)\s+\S+\s+\S+\s+\d+\s+(\S+).*")

class Symbols:
    def __init__(self, filename):
        self.filename = filename
	self.by_name = {}	
        self.by_addr = []
	s = subprocess.Popen("arm-linux-gnueabi-readelf -s %s" % filename, shell=True, stdout=subprocess.PIPE)
	for line in s.stdout:
		m = sym_exp.match(line)
		if not m: continue
		addr = int(m.group(1),16)
                size = int(m.group(2))
                kind = m.group(3)
		name = m.group(4)
                if kind != "NOTYPE":
                    self.by_name[name] = (addr,size,kind)
                    self.by_addr.append((addr,size,kind,name))
        print "%d symbols from %s" % (len(self.by_addr), filename)
        self.by_addr = sorted(self.by_addr, cmp=lambda x,y:x[0]-y[0])

    def dump(self):
        for x in self.by_addr:
            print "%08x %5d %12s %s" % (x[0],x[1],x[2],x[3])

    def addr_of(self, name):
        return self.by_name[name][0]

    def name_of(self, addr):
        for x in self.by_addr:
            if addr >= x[0] and addr < x[0]+x[1]:
                return x[3]
        return "%#x" % addr

def tochar(x):
	x = ord(x)
	if x > 0 and x < 255:
		return chr(x)
	return '<%#x>' % x


class ghprobe:

	def __init__(self, host, vmlinux):
		self.host    = host
		self.vmlinux = vmlinux
		self.c       = None
		self.prompt  = re.compile("([a-zA-Z0-9]+)\[(\d+),(\S)\] % ")
		self.debug   = False
                self.regs    = {}

	def addr2func(self, addr):
		s = subprocess.Popen("arm-linux-gnueabi-addr2line -f -e %s %#x" % (self.vmlinux, addr), shell=True, stdout=subprocess.PIPE)
		output = s.stdout.read()
		line = output.strip().split('\n')
		s.wait()
		if len(line) != 2:
			return output
		return "%s" % line[0]

	def addr2line(self, addr):
		s = subprocess.Popen("arm-linux-gnueabi-addr2line -f -e %s %#x" % (self.vmlinux, addr), shell=True, stdout=subprocess.PIPE)
		output = s.stdout.read()
		line = output.strip().split('\n')
		s.wait()
		if len(line) != 2:
			return output
		return "%s (%s)" % (line[0], line[1])

	def connect(self):
		self.c = pexpect.spawn("telnet ghprobe20410", timeout=3)
		self.banner = self.wait_prompt()

	def close(self):
		self.c.sendline("exit\r")
		self.c.expect("Connection closed by foreign host.")
		self.c.close()

	def wait_prompt(self):
		self.c.expect(self.prompt)
		self.what = self.c.match.group(1)
		self.target = self.c.match.group(2)
		self.state = self.c.match.group(3)
		if self.debug:
			for l in self.c.before.split('\n'):
				print "< %s" % l
		return self.c.before

	def do_command(self, cmd):
		self.c.sendline(cmd + "\r")
		self.c.expect(cmd)
		if self.debug: print "> %s" % cmd
		output = self.wait_prompt()
		return output.strip()

	def jtag_reset(self):
		self.do_command("jr")

	def run(self):
		self.do_command("tc")

	def halt(self):
		self.do_command("halt")
                self.update_regs()

	def select(self, core):
		output = self.do_command("t %u" % core)
		m = re.match("Selected core (\d+).", output)
		if not m or int(m.group(1)) != core:
			print "ERROR: %s" % output
			raise Exception("Failed to select target %u" % core)

        def update_regs(self):
            if self.state != 'h':
                print "core%s: Not halted (state=%s)" % (self.target, self.state)
                return
            output = self.do_command("rr")
            for field in output.split():
                try:
                    reg,value = field.split('=')
                    self.regs[reg] = int(value,0)
                except ValueError, e:
                    print "Bad field: %s" % field

	def getreg(self, reg):
            if not self.regs.has_key(reg):
                raise Exception("Bad register name: %s" % reg)
            return self.regs[reg]

        def run_all(self):
            for core in xrange(16):
                self.select(core)
                if self.state == "h":
                    print "Resume core%d" % core
                    self.run()
                else:
                    print "core%s: ignoring in state %s" % self.state

        def read_word(self, addr):
                result = None
                output = self.do_command("md s4 %#x 4" % addr) 
                for line in output.split("\n"):
                        m = word_exp.match(line)
                        if not m: continue
                        result = int(m.group(2),16)
                        break
                if result == None:
                        print "read_word: Failed\n%s\n" % output
                return result

        def read_block(self, addr, n):
                result = ""
                output = self.do_command("md s1 %#x %u" % (addr, n)) 
                for line in output.split("\n"):
                        m = hex_exp.match(line)
                        if not m: continue
                        for x in m.group(2).split():
                                result += chr(int(x,16))
                return result

	def status_all(self):
		for core in xrange(16):
			self.select(core)
                        if self.state == "?":
                            break
			self.halt()
			pc = self.getreg('pc')
			lr = self.getreg('lr')
                        r2 = self.getreg('r2')
                        r3 = self.getreg('r3')
                        r4 = self.getreg('r4')
                        r11 = self.getreg('r11')
                        r12 = self.getreg('r12')
                        if r4 > 0xc0000000 and r4 < 0xd0000000:
                            w = self.read_word(r4)
                            ts = self.read_word(r4+8) + (self.read_word(r4+12) << 32)
                            cpu = self.read_word(r4+16)
                        else:
                            w = 0
                            ts = 0
                            cpu = -1
			print "core%d: pc=%s lr=0x%08x r2=0x%08x r3=0x%08x r4=%s r11=0x%08x r12=0x%08x ts=0x%08x cpu=%#x [r4]=0x%08x" % (core,self.addr2func(pc),lr,r2,r3,syms.name_of(r4),r11,r12,ts, cpu, w)
                        if False:
                            print "   %s" % self.addr2line(pc)
                            print "   %s" % self.addr2line(lr)

#===========================================================================
# MAIN
#===========================================================================

probe   = "ghprobe20410"
vmlinux = "/home/aberg/git/lsigithub/vmlinux"

long_opts = [
        'host=',
        'kernel=',
    ]

opts, args = getopt.getopt(sys.argv[1:], None, long_opts)
for opt, optarg in opts:
    if opt == '--kernel':
        vmlinux = optarg
    elif opt == '-probe':
        probe = optarg

if len(args) == 0:
    print "No command specified"
    sys.exit(1)

print "Loading symbols from %s" % vmlinux
syms = Symbols(vmlinux)

print "Connecting to probe %s" % probe
gh = ghprobe("ghprobe20410", vmlinux)
gh.connect()
gh.jtag_reset()
gh.halt()

if len(args) == 3 and args[0] == 'q':
	addr_ring = int(args[1], 0)
	addr_q    = int(args[2], 0)
	ring = []

	buf = gh.read_block(addr_q, 128)
	if False:
		hw_tail, tail, head, size, phys = struct.unpack("<5I", buf);
	else:
		hw_tail, = struct.unpack("<I", buf[0:4]);
		tail, head, size, phys = struct.unpack("<4I", buf[64:64+16]);
	print "hw_tail = %#x" % hw_tail
	print "tail    = %#x" % tail
	print "head    = %#x" % head
	print "size    = %#x" % size
	print "phys    = %#x" % phys
	buf = gh.read_block(addr_ring, 128*16)
	for i in range(0,128*16,16):
		x = struct.unpack("<IHHII", buf[i:i+16])
		ptrs = ""
		if i == (hw_tail & 0xfffff): ptrs += "<-hw_tail "
		if i == (tail & 0xfffff): ptrs += "<-tail "
		if i == (head & 0xfffff): ptrs += "<-head "
		print "[%05x] %08x %4u/%4u %08x %08x %s" % ((addr_ring+i)&0xfffff, x[0],x[1],x[2],x[3],x[4], ptrs)
		ring.append(x)
elif args[0] == "run":
        gh.run_all()
elif args[0] == "status":
	gh.status_all()
elif args[0] == "dmesg":
	i=gh.read_word(syms.addr_of('log_first_idx'))
        iend=gh.read_word(syms.addr_of('log_next_idx'))
	print "first=%u last=%u" % (i,iend)
	if i == iend:
		print "No log"
		sys.exit(0)
	if i == 0:
		n = iend
	else:
		n = logsize
	addr = syms.addr_of('__log_buf')
	buf = ""
	for offset in range(0,n,blocksize):
		buf += gh.read_block(addr+offset, blocksize)
		sys.stdout.write("%5d%%\r" % (100*offset/logsize))
		sys.stdout.flush()
	print "__log_buf: %d bytes" % len(buf)
	dmesg = ""
	while i != iend:
		ts, rlen, tlen, dlen, fac, flags = struct.unpack("<QHHHBB", buf[i:i+16])
		if True:
			print "[%u] ts=%u rlen=%u tlen=%u dlen=%u fac=%u flags=%#x" % (i, ts, rlen, tlen, dlen, fac, flags)
		if rlen > 0:
			text = ''.join(map(tochar, buf[i+16:i+16+tlen]))
			dmesg += "[%u.%06u] %s\n" % (ts/1000000000, (ts % 1000000000)/1000, text)
			i += rlen
			i &= (logsize-1)
		else:
			i=0
	print dmesg
else:
    print "Invalid command"

gh.close()

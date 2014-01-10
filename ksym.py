#!/usr/bin/env python
import sys

class kallsyms:
    def __init__(self, filename):
        self.syms = []
        for line in open(filename, "r"):
            x = line.split()
            self.syms.append([int(x[0],16),x[1],x[2]])
        print "Loaded %d symbols" % len(self.syms)

    def lookup(self, addr, typ='t'):
        match = None
        for s in self.syms:
            if s[0] > addr:
                break
            match = s
        return match


addr = int(sys.argv[2],16)
ksyms = kallsyms(sys.argv[1])
s = ksyms.lookup(addr)
if s:
    offset = addr - s[0]
    print "%#x %s %s + %#x" % (s[0], s[1], s[2], offset)
else:
    print "No match"

            

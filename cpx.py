#!/usr/bin/python
import sys
import socket
import time

class CPX:
    MAX_MSG = 128
    NUM_CH  = 2

    def __init__(self):
        self.debug = False
        self.socket = None
        self.errmsg = "OK"

    def connect(self, host='t-cpx-126200'):
        try:
            self.sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sd.connect((host, 9221))
            self.sd.settimeout(3.0)
            self.instrument_id = self.identify()
        except socket.error, e:
            self.errmsg = str(e)
            return False
        return True

    def close(self):
        self.unlock()
        self.local()
        self.sd.close()

    def send_cmd(self, cmd):
        if self.debug: print ">>> %s" % cmd
        self.sd.send(cmd + '\n')

    def recv_rsp(self):
        rsp = self.sd.recv(CPX.MAX_MSG)
        if self.debug: print "<<< %s" % rsp.strip()
        return rsp.strip()

    def do_cmd(self, cmd):
        self.send_cmd(cmd)
        return self.recv_rsp()

    def identify(self):
        return self.do_cmd("*IDN?")

    def get_output(self, chan):
        rsp = self.do_cmd("OP%d?" % chan)
        return int(rsp)

    def set_output(self, chan, onoff):
        self.send_cmd("OP%d %d" % (chan, onoff))
        return self.get_output(chan) == onoff

    def get_voltage(self, chan):
        rsp = self.do_cmd("V%d?" % chan)
        return float(rsp[3:])

    def get_current(self, chan):
        rsp = self.do_cmd("I%d?" % chan)
        return float(rsp[3:])

    def get_readback_voltage(self, chan):
        rsp = self.do_cmd("V%dO?" % chan)
        return float(rsp.strip('V'))

    def get_readback_current(self, chan):
        rsp = self.do_cmd("I%dO?" % chan)
        return float(rsp.strip('A'))

    def lock(self):
        rsp = self.do_cmd("IFLOCK")
        return int(rsp) == 1

    def unlock(self):
        rsp = self.do_cmd("IFUNLOCK")
        return int(rsp) == 0

    def local(self):
        self.send_cmd("LOCAL")
# CPX

usage = """cpx.py [option] [--on | --off | --cycle]
options:
    --host <hostname>   Hostname or IP address of instrument
    --channel <1..2>    Output channel to operate on
    --on                Turn output on (requires --channel)
    --off               Turn output off (requires --channel)
    --cycle             Power cycle output (requires --channel)
    --delay <seconds>   Delay in seconds for power cycle
"""

if __name__ == "__main__":
    args = sys.argv
    opt_cycle = False
    opt_off = False
    opt_on = False
    opt_delay = 3.0
    opt_channel = None
    opt_host = 't-cpx-126200'

    while len(args) > 0:
        opt = args.pop(0)
        if opt == '--help':
            print usage
            sys.exit(0)
        elif opt == '--on':
            opt_on = True
        elif opt == '--off':
            opt_off = True
        elif opt == '--cycle':
            opt_cycle = True
        elif opt == '--channel':
            if len(args) == 0:
                print "Missing arguments for --channel"
                print usage
                sys.exit(1)
            else:
                opt_channel = int(args.pop(0))
        elif opt == '--delay':
            if len(args) == 0:
                print "Missing arguments for --delay"
                print usage
                sys.exit(1)
            else:
                opt_delay = float(args.pop(0))
        elif opt == '--host':
            if len(args) == 0:
                print "Missing arguments for --host"
                print usage
                sys.exit(1)
            else:
                opt_host = args.pop(0)

    cpx = CPX()
    if not cpx.connect(opt_host):
        print "Failed to connect to instrument %s: %s" % (opt_host, cpx.errmsg)
        sys.exit(1)

    if opt_on and opt_channel:
        cpx.set_output(opt_channel, 1)
    elif opt_off and opt_channel:
        cpx.set_output(opt_channel, 0)
    elif opt_cycle and opt_channel:
        cpx.set_output(opt_channel, 0)
        time.sleep(opt_delay)
        cpx.set_output(opt_channel, 1)
    else:
        if not opt_channel: chs = [1,2]
	else: chs = [opt_channel]
	for opt_channel in chs:
	    print "---------[CHANNEL %d]--------" % opt_channel
	    print "Instrument:  %s" % cpx.identify()
	    print "Output:      %d" % cpx.get_output(opt_channel)
	    print "Max Voltage: %.2f" % cpx.get_voltage(opt_channel)
	    print "Max Current: %.2f" % cpx.get_current(opt_channel)
	    print "Voltage:     %.3f" % cpx.get_readback_voltage(opt_channel)
	    print "Current:     %.3f" % cpx.get_readback_current(opt_channel)
    cpx.close()

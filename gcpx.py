#!/usr/bin/python
import sys
import socket
import time
from gi.repository import Gtk
from gi.repository import GObject

class Limit:
    def __init__(self, x):
        self.limit = x

    def set(self, limit):
        self.limit = limit

    def __int__(self):
        return self.limit

    def __float__(self):
        return self.limit

class ChannelDisplay:

    def __init__(self, ch):
        self.ch      = ch
        self.output  = False
        self.v_meas  = Limit(59.4)
        self.a_meas  = Limit(3.3)
        self.frame   = Gtk.Frame()
        self.vbox    = Gtk.VBox()
        self.draw    = Gtk.DrawingArea()
        self.v_max   = Gtk.HScale()
        self.a_max   = Gtk.HScale()
        self.onoff   = Gtk.Button(label="On/Off")
        self.frame.add(self.vbox)
        self.vbox.add(self.draw)
        if False:
            self.vbox.add(self.v_max)
            self.vbox.add(self.a_max)
        self.vbox.add(self.onoff)
        self.v_max.set_range(0,60.0)
        self.a_max.set_range(0,8.0)
        self.frame.set_label("Channel %d" % ch)
        self.draw.connect("configure_event", self.on_configure)
        self.draw.connect("draw", self.on_draw)
        self.v_max.connect("value-changed", self.on_value_changed)
        self.a_max.connect("value-changed", self.on_value_changed)
        self.draw.set_size_request(160,100)

    def get_widget(self):
        return self.frame

    def get_button(self):
        return self.onoff

    def on_configure(self, widget, data):
        pass

    def on_value_changed(self, widget):
        self.redraw()

    def on_draw(self, widget, cr):
        if self.output:
            row_v = "%2.02f V" % float(self.v_meas)
            row_a = "%2.02f A" % float(self.a_meas)
        else:
            row_v = "%2.02f V" % self.v_max.get_value()
            row_a = "%2.02f A" % self.a_max.get_value()

        a = widget.get_allocation()
        cr.set_font_size(24)
        e = cr.text_extents(row_v)
        cr.move_to(10, 10+e[3])
        cr.show_text(row_v)
        cr.move_to(10, 20+2*e[3])
        cr.show_text(row_a)
        cr.set_source_rgb(1.0,0,0)
        cr.set_line_width(1.0)
        cr.rectangle(a.width-15, 1, 10, 10)
        if self.output:
            cr.fill()
        else:
            cr.stroke()

    def redraw(self):
        self.draw.queue_draw()

    def set_v_max(self, v_max):
        self.v_max.set_value(v_max)
        self.redraw()

    def set_a_max(self, a_max):
        self.a_max.set_value(a_max)
        self.redraw()

    def set_measured(self, v_meas, a_meas):
        self.v_meas = v_meas
        self.a_meas = a_meas
        self.redraw()

    def get_output(self):
        return self.output

    def set_output(self, onoff):
        self.output = onoff
        if onoff: self.onoff.set_label("Off")
        else: self.onoff.set_label("On")
        self.redraw()
        return self.output

class MainWindow(Gtk.Window):

    def __init__(self, cpx):
        Gtk.Window.__init__(self, title="CPX400DP")
        self.connect("delete-event", self.on_quit)
        self.ch = []
        self.hbox = Gtk.HBox()
        for i in [1,2]:
            w = ChannelDisplay(i)
            self.ch.append(w)
            self.hbox.add(w.get_widget())
            w.get_button().connect("clicked", self.on_button_clicked, w)
        self.add(self.hbox)
        if False:
            GObject.timeout_add(2000, self.on_update)
        self.cpx = cpx
        self.on_update()

    def on_quit(self, wnd, event):
        print "QUIT"
        self.cpx.close()
        Gtk.main_quit()

    def on_update(self):
        for chan in [1,2]:
            v_max = self.cpx.get_voltage(chan)
            i_max = self.cpx.get_current(chan)
            v_cur = self.cpx.get_readback_voltage(chan)
            i_cur = self.cpx.get_readback_current(chan)
            onoff = self.cpx.get_output(chan)
            self.ch[chan-1].set_v_max(v_max)
            self.ch[chan-1].set_a_max(i_max)
            self.ch[chan-1].set_measured(v_cur, i_cur);
            self.ch[chan-1].set_output(onoff)
        return True

    def on_button_clicked(self, widget, ch):
        onoff = ch.set_output(not ch.get_output())
        self.cpx.set_output(ch.ch, onoff)

# MainWindow

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

usage = """gcpx.py [option]
options:
    --host <hostname>   Hostname or IP address of instrument
"""

if __name__ == "__main__":
    args = sys.argv
    opt_host = 't-cpx-126200'

    while len(args) > 0:
        opt = args.pop(0)

        if opt == '--help':
            print usage
            sys.exit(0)
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

    win = MainWindow(cpx)
    win.show_all()
    Gtk.main()
    sys.exit(0)

#!/usr/bin/env python
import time
import inotify.adapters
import os, os.path
from threading import Timer, Lock
from datetime import datetime
from send_client import SendClient
from pathlib import Path

import logging, logging.handlers
script_dir = os.path.dirname(os.path.realpath(__file__))
log = logging.getLogger()
log.setLevel(logging.DEBUG)
logHandler = logging.handlers.TimedRotatingFileHandler(os.path.join(script_dir, 'logs', 'sms_receiver.log'), 'D', 1, 5)
logFormat = logging.Formatter('%(levelname)-5s - %(filename)s:%(lineno)d - %(message)s')
logHandler.setFormatter(logFormat)
logHandler.setLevel(logging.DEBUG)
log.addHandler(logHandler)


#from pdb_clone import pdb
#pdb.set_trace_remote()

class IncomingSMSProcesser:
    def __init__(self, inbox):
        self.inbox = inbox
        self.partfiles = []
        self.lock = Lock()
        self.nexttime = self.current_time()
        self.client = SendClient()
        self.syncfile = os.path.join(Path.home(), '.sms_last')
        self.delay = 2.0
        self.date_last = '19000101'
        self.time_last = '000000'

    def current_time(self):
        return int(round(time.time() * 1000))

    def watch(self):
        with self.lock:
            self.check_sync()

        i = inotify.adapters.Inotify()
        i.add_watch(self.inbox)
        log.info("watcher starting")

        for event in i.event_gen(yield_nones=False):
            (_, type_names, path, filename) = event
            if 'IN_CLOSE_WRITE' in type_names:
                log.debug("found new file %s" % filename)
                with self.lock:
                    self.nexttime = self.current_time() + 1000 # after one second
                    self.partfiles.append(filename)
                    job = Timer(self.delay, self.process)
                    job.start()

    def process(self):
        with self.lock:
            now = self.current_time()
            if now < self.nexttime:
                return
            self.process_sms()
            self.partfiles.clear()

    def process_sms(self):
        sms_pool = {}
        for f in self.partfiles:
            # IN20181226_062921_00_106913161015355_00.txt
            try:
                date_, time_, serial, sender, seq = f[2:].split('.')[0].split('_')
            except:
                pass
            sms_pool.setdefault((serial, sender), [date_, time_]).append(f)
            if date_ > self.date_last or (date_ == self.date_last and time_ > self.time_last):
                self.date_last = date_
                self.time_last = time_

        for tup, seqs in sms_pool.items():
            date_, time_ = seqs[:2]
            seqs = seqs[2:]
            seqs.sort()
            text = ''
            mms = False
            for f in seqs:
                if f.endswith('.bin'):
                    mms = True
                    break
                with open(os.path.join(self.inbox, f)) as input:
                    try:
                        text += input.read()
                    except UnicodeDecodeError:
                        log.error("cannot read unicode from %s" % f)

                    
            serial, sender = tup
            #print("Got message from " + sender + ", '" + text + "'")
            log.debug("sending message from %s" % sender)
            dt = datetime.strptime(date_ + time_, '%Y%m%d%H%M%S')
            time_str = datetime.strftime(dt, '%Y/%m/%d %H:%M:%S')

            while True:
                try:
                    if mms:
                        self.client.send("_Incoming MMS from %s at %s_" % (sender, time_str), parse_mode="markdown")
                    else:
                        self.client.send("_Incoming SMS from %s at %s_" % (sender, time_str), parse_mode="markdown")
                        self.client.send(text, parse_mode="plaintext")
                    log.debug("message from %s sent" % sender)
                    break
                except:
                    log.error("send fail, will retry")
                    time.sleep(30)

        if self.date_last != '19000101':
            self.update_sync(self.date_last, self.time_last)


    def check_sync(self):
        log.info("check sync status")
        try:
            with open(self.syncfile) as input:
                last_ts = input.read().strip()
                log.debug("found last time %s" % last_ts)
        except:
            log.error("no sync file found, all file need to be parsed")
            last_ts = "19000101000000"

        found_unread = False

        for f in os.listdir(self.inbox):
            try:
                date_, time_, serial, sender, seq = f[2:].split('.')[0].split('_')
            except:
                continue

            if date_ + time_ > last_ts: # new file
                self.partfiles.append(f)
                log.debug("found unread message file %s" % f)
                found_unread = True

        if found_unread:
            job = Timer(1.0, self.process)
            job.start()

    def update_sync(self, date_, time_):
        with open(self.syncfile, "w") as output:
            output.write(date_ + time_)
            output.flush()
            os.fsync(output.fileno())
            log.debug("update sync mark to %s:%s" % (date_, time_))


if __name__ == '__main__':
    smsp = IncomingSMSProcesser('/var/spool/gammu/inbox')
    smsp.watch()


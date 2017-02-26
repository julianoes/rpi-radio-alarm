#!/usr/bin/env python

import subprocess
import time
import datetime
import falcon
import json
import threading

"""Simple radio alarm using a Raspberry Pi.

This plays internet radio using mplayer and provides some RESTful API
using gunicorn.

Author: Julian Oes <julian@oes.ch>

Published under 3-Clause BSD License.
"""


class Radio(object):

    def __init__(self):
        self.process = None

    def __del__(self):
        self.stop_playing()

    def start_playing(self):
        if not self.is_playing():
            self.process = subprocess.Popen(
                ["mplayer", "http://stream.srg-ssr.ch/m/drs3/mp3_128"])

    def stop_playing(self):
        if self.is_playing():
            self.process.terminate()

    def is_playing(self):
        # poll() returns None if not exited yet
        return self.process is not None and self.process.poll() is None


class RadioResource(object):

    def __init__(self, radio):
        self.radio = radio

    def on_get(self, req, resp, action):
        """Handles GET requests"""

        if action == "start":
            if self.radio.is_playing():
                result = {"status": "already started"}
            else:
                result = {"status": "ok let's start this"}
                self.radio.start_playing()
        elif action == "stop":
            if self.radio.is_playing():
                result = {"status": "ok let's stop this"}
                self.radio.stop_playing()
            else:
                result = {"status": "already stopped"}
        elif action == "status":
            if self.radio.is_playing():
                result = {"status": "started"}
            else:
                result = {"status": "stopped"}
        else:
            result = {"status": "not sure what to do with this"}

        resp.status = falcon.HTTP_200
        resp.body = json.dumps(result)


class AlarmResource(object):

    def __init__(self, radio):
        self.last_should_be_playing = False
        self.on = False
        self.wake_hour = 6
        self.wake_min = 55

        self.radio = radio
        self.thread_should_exit = False
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def __del__(self):
        self.thread_should_exit = True
        self.thread.join()

    def run(self):
        while not self.thread_should_exit:
            if self.on:
                self.check_time()
            time.sleep(1)

    def check_time(self):

        now = datetime.datetime.now().time()
        start = datetime.time(self.wake_hour, self.wake_min)
        end = datetime.time(self.wake_hour+1, self.wake_min)
        radio_should_be_playing = (start <= now <= end)
        if radio_should_be_playing and not self.last_should_be_playing:
            self.radio.start_playing()
            self.last_should_be_playing = radio_should_be_playing
        elif not radio_should_be_playing and self.last_should_be_playing:
            self.radio.stop_playing()
            self.last_should_be_playing = radio_should_be_playing

    def on_get(self, req, resp, action):
        """Handles GET requests"""

        # import pprint
        # pp = PrettyPrinter(indent=4)
        # pp.pprint(req)

        if action == "on":
            if self.on:
                result = {"status": "alarm already on"}
            else:
                result = {"status": "ok, set alarm on"}
                self.on = True

        elif action == "off":
            if self.on:
                result = {"status": "ok, set alarm off"}
                self.on = False
            else:
                result = {"status": "alarm already off"}
        elif action == "status":
            if self.on:
                result = {"status": "on"}
            else:
                result = {"status": "off"}
        else:
            result = {"status": "not sure what to do with this"}

        resp.status = falcon.HTTP_200
        resp.body = json.dumps(result)

api = falcon.API()

radio = Radio()

radio_resource = RadioResource(radio)
alarm_resource = AlarmResource(radio)

api.add_route('/radio/{action}', radio_resource)
api.add_route('/alarm/{action}', alarm_resource)

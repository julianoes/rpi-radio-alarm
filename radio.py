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


class PersistentConfig(object):
    CONFIG_FILENAME = 'radio-config.json'
    DEFAULT_CONFIG = {"alarm": {"on": False},
                      "radio": {"playing": False}}

    def __init__(self):
        try:
            with open(self.CONFIG_FILENAME, 'r') as f:
                self._config = json.load(f)
        except:
            self._config = None

        if self._config is None:
            self._config = self.DEFAULT_CONFIG
        self.save()

    def save(self):
        print("saving config:\n %s" % self._config)
        with open(self.CONFIG_FILENAME, 'w') as f:
            json.dump(self._config, f, indent=4)

    def set(self, key, value):
        key_parts = key.split("/")
        old_value = self._config
        # We don't need the last value but the second last,
        # so the "reference pointing to the last one."
        for key_part in key_parts[:-1]:
            old_value = old_value[key_part]
        old_value[key_parts[-1]] = value
        self.save()

    def get(self, key):
        key_parts = key.split("/")
        ret_value = self._config
        for key_part in key_parts:
            ret_value = ret_value[key_part]
        return ret_value


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

    def __init__(self, radio, config):
        self.radio = radio
        self.config = config
        if self.config.get('radio/playing'):
            self.radio.start_playing()

    def on_get(self, req, resp, action):
        """Handles GET requests"""

        if action == "start":
            if self.radio.is_playing():
                result = {"status": "already started"}
            else:
                result = {"status": "ok let's start this"}
                self.radio.start_playing()
            self.config.set('radio/playing', True)
        elif action == "stop":
            if self.radio.is_playing():
                result = {"status": "ok let's stop this"}
                self.radio.stop_playing()
            else:
                result = {"status": "already stopped"}
            self.config.set('radio/playing', False)
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

    def __init__(self, radio, config):
        self.config = config
        self.last_should_be_playing = False
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
            if self.config.get('alarm/on'):
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
            if self.config.get('alarm/on'):
                result = {"status": "alarm already on"}
            else:
                result = {"status": "ok, set alarm on"}
            self.config.set('alarm/on', True)

        elif action == "off":
            if self.config.get('alarm/on'):
                result = {"status": "ok, set alarm off"}
            else:
                result = {"status": "alarm already off"}
            self.config.set('alarm/on', False)

        elif action == "status":
            if self.config.get('alarm/on'):
                result = {"status": "on"}
            else:
                result = {"status": "off"}
        else:
            result = {"status": "not sure what to do with this"}

        resp.status = falcon.HTTP_200
        resp.body = json.dumps(result)


api = falcon.API()

radio = Radio()

config = PersistentConfig()

radio_resource = RadioResource(radio, config)
alarm_resource = AlarmResource(radio, config)

api.add_route('/radio/{action}', radio_resource)
api.add_route('/alarm/{action}', alarm_resource)


if __name__ == '__main__':
    print("Needs to be run using 'gunicorn -b :80 radio:api'")

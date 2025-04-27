# MIT License
#
# Copyright (c) 2022  Dr. Magnus Christ (mc0110)
#
# This is part of the wifimanager package
#
#
# Functionalities: The module establishes a Wifi connection.
# This is done either via an STA connection or if no credentials are available,
# via an AP connection on 192.168.4.1.
# It is possible to establish both connections in parallel.
#
# Further functionalities:
#     Reading / writing a json file for the credentials
#     Wifi-network scan
#     Reading / writing encrypted credentials from / to file

import os
import sys
import logging
import configparser
from mqtt_async2 import MQTTClient, MQTTConfig
from tools import PIN_MAPS, PIN_MAP

log = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FN    = "etc/inetbox2mqtt"

class Connect():
    client      = None
    config      = None
    mqtt_config = None
    platform    = ""
    python      = ""
    rel_no      = ""
    appname     = ""
    mqtt_flg    = ""

    def __init__(self, hw=None, fn=None):
        if hw == None: hw = "RPi"

        log = logging.getLogger(__name__)

        self.pin_map = hw
        self.client = None
        self.p = PIN_MAP(PIN_MAPS[hw])

        if fn != None:
            self.config_fn = fn
        else:
            self.config_fn = CONFIG_FN


        self.platform = str(sys.platform)
        self.platform_name = str(self.pin_map) + " " + str(sys.platform)
        self.python = '{} {}'.format(sys.implementation.name,'.'.join(str(s) for s in sys.implementation.version))

        log.info("Detected " + self.python + " on port: " + self.platform)

        self.mqtt_config = MQTTConfig()

        self.mqtt_config.subs_cb = self.c_subscripted
        self.mqtt_config.connect_coro = self.c_connected


    async def c_subscripted(self, topic, msg, retained, qos):
        log.debug("Received topic:" + str(topic) + " > payload: " + str(msg) + "qos: " + str(qos))
        if self.subscripted != None:
            await self.subscripted(topic, msg, retained, qos)


    # Initialze the connect-funct
    # define subscriptions
    async def c_connected(self, client):
        log.info("MQTT connected")
        if self.connected != None:
            await self.connected(client)


    def set_proc(self, connect = None, subscript = None):
        self.connected   = connect
        self.subscripted = subscript


    def read_config(self):
        file = f"{PROJECT_ROOT}/{self.config_fn}"
        try:
            self.config = configparser.ConfigParser()
            self.config.read(file)
            return self.config
        except:
            log.error(f"Failed to open config file: {file}")
            return None


    def connect(self, mqtt_debug=False):
        return self.set_mqtt(mqtt_debug=mqtt_debug)


    def set_mqtt(self, mqtt_debug):
        log.debug("Try to open mqtt connection")
        cfg = self.read_config()
        if cfg:
            mqtt_debug = cfg.getboolean("logging", "mqtt_debug")
            if mqtt_debug:
                log.setLevel(level=logging.DEBUG)
                log.info("MQTT debug log enabled")
            self.mqtt_config.server   = cfg["mqtt"]["server"]
            self.mqtt_config.user     = cfg["mqtt"]["user"]
            self.mqtt_config.password = cfg["mqtt"]["password"]
            port = 1883
            if cfg["mqtt"]["port"] != "":
                port = int(cfg["mqtt"]["port"])
                log.info(f"MQTT Port is switched to port: {port}")
            self.mqtt_config.clean     = True
            self.mqtt_config.keepalive = 60  # last will after 60sec off
            #self.mqtt_config.set_last_will("service/truma/control_status/alive", "OFF", retain=True, qos=0)  # last will is important
            self.client = MQTTClient(self.mqtt_config, mqtt_debug)


    def run_mode(self):
        return 1





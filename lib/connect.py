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
from crypto_keys import fn_crypto as crypt
from mqtt_async2 import MQTTClient, MQTTConfig
from tools import PIN_MAPS, PIN_MAP

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

    def __init__(self, hw=None, fn=None, debuglog=False):
        if hw == None: hw = "RPi"

        self.log = logging.getLogger(__name__)

        if debuglog:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)

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

        self.log.info("Detected " + self.python + " on port: " + self.platform)

        self.mqtt_config = MQTTConfig()

        self.mqtt_config.subs_cb = self.c_subscripted
        self.mqtt_config.connect_coro = self.c_connected


    async def c_subscripted(self, topic, msg, retained, qos):
        self.log.debug("Received topic:" + str(topic) + " > payload: " + str(msg) + "qos: " + str(qos))
        if self.subscripted != None: await self.subscripted(topic, msg, retained, qos)


    # Initialze the connect-funct
    # define subscriptions
    async def c_connected(self, client):
        self.log.info("MQTT connected")
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
            self.log.error(f"Failed to open config file: {file}")
            return None


    def connect(self):
        return self.set_mqtt()


    def set_mqtt(self):
        self.log.debug("Try to open mqtt connection")
        cfg = self.read_config()
        if cfg:
            self.mqtt_config.server   = cfg["mqtt"]["server"]
            self.mqtt_config.user     = cfg["mqtt"]["user"]
            self.mqtt_config.password = cfg["mqtt"]["password"]
            port = 1883
            if cfg["mqtt"]["port"] != "":
                port = int(cfg["mqtt"]["port"])
                self.log.info(f"MQTT Port is switched to port: {port}")
            self.mqtt_config.clean     = True
            self.mqtt_config.keepalive = 60  # last will after 60sek off
            # self.mqtt_config.set_last_will("test/alive", "OFF", retain=True, qos=0)  # last will is important for clean connect
            self.mqtt_config.set_last_will("service/truma/control_status/alive", "OFF", retain=True, qos=0)  # last will is important
            self.client = MQTTClient(self.mqtt_config)


    def run_mode(self):
        return 1





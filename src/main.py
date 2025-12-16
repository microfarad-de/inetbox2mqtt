# MIT License
#
# Copyright (c) 2022  Dr. Magnus Christ (mc0110)
# Copyright (c) 2023  Dr. Magnus Christ (mc0110)
# Copyright (c) 2025  Karim Hraibi
#
# TRUMA-inetbox-simulation
#
# Credentials and MQTT-server-adress must be filled
# If the mqtt-server needs authentification, this can also filled
#
# The communication with the CPplus uses a FT232RL USB to serial converter
#
#
#
# Version: 3.0.0
#
# change_log:
# 0.8.2 HA_autoConfig für den status error_code, clock ergänzt
# 0.8.3 encrypted credentials, including duo_control, improve the MQTT-detection
# 0.8.4 Tested with RP pico w R2040 - only UART-definition must be changed
# 0.8.5 Added support for MPU6050 implementing a 2D-spiritlevel, added board-based autoconfig for UART,
#       added config variables for activating duoControl and spirit-level features
# 0.8.6 added board-based autoconfig for I2C bus definition
# 1.0.0 web-frontend implementation
# 1.0.1 using mqtt-commands for reboot, ota, OS-run
# 1.5.x chance browser behavior
# 2.0.x chance connect and integrate mqtt-logic
# 3.0.x Simplified version ported to CPython for running on a Venus OS enabled Raspberry Pi (by Karim Hraibi)
#

import os
import sys
import logging
import asyncio
from lin import Lin
import serial as pyserial

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_PATH = os.path.join(PROJECT_ROOT, "lib")
sys.path.insert(0, os.path.abspath(LIB_PATH))


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    stream=sys.stdout  # Direct logs to stdout
)

log = logging.getLogger(__name__)


# Global objects
connect = None
lin     = None
lock    = None


# Release number
REL_NO = "3.0.0"


# Change the following configs to suit your environment
TOPIC_ROOT = 'truma'
SET_PREFIX = 'service/' + TOPIC_ROOT + '/set/'
STA_PREFIX = 'service/' + TOPIC_ROOT + '/control_status/'



# Universal callback function for all subscriptions
async def callback(topic, msg, retained, qos):
    global connect
    global lock

    log.debug(f"received: {topic}: {msg}")
    topic = str(topic)
    topic = topic[2:-1]
    msg = str(msg)
    msg = msg[2:-1]
    # Command received from broker
    if topic.startswith(SET_PREFIX):
        topic = topic[len(SET_PREFIX):]
        if topic in lin.app.status.keys():
            log.info("inet-key:"+str(topic)+" value:"+str(msg))
            async with lock:
                try:
                    lin.app.set_status(topic, msg)
                except Exception as e:
                    log.debug(Exception(e))
        else:
            log.debug("key is unknown")


# Initialze the subscripted topics
async def conn_callback(client):
    log.debug("Set subscription")
    # inetbox_set_commands
    await connect.client.subscribe(SET_PREFIX+"#", 1)



# Write a key-value pair to a file in the tmp folder for use by other scripts
def write_to_file(key, value):
    dir_path = "/tmp/truma"
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, key)
    with open(file_path, 'w') as f:
        f.write(str(value) + '\n')



# main publisher-loop
async def main():
    global connect
    global lock

    log.debug("main-loop is running")

    i = 0
    wd = False
    while True:
        await asyncio.sleep(8)      # Set the update interval (seconds)
        async with lock:
            await asyncio.sleep(2)  # Wait to ensure the status buffer has been updated
            s = lin.app.get_all(True)

        for key in s.keys():
            log.debug(f'publish {key}:{s[key]}')
            write_to_file(key, s[key])
            try:
                await connect.client.publish(STA_PREFIX+key, str(s[key]), qos=1)
            except:
                log.debug("Error in LIN status publishing")
        if lin.app.status["alive"][0]=="OFF":
            if not(wd):
                log.info("LIN disconnected!")
                #asyncio.create_task(lin.watchdog())
                wd = True
        else:
            if wd:
                log.info("LIN connected")
                wd = False

        i += 1
        if not(i % 6):
            i = 0
            lin.app.status["alive"][1] = True # publish alive-heartbeat every min


# major ctrl loop for inetbox-communication
async def lin_loop():
    global lin
    await asyncio.sleep(1) # Delay at begin
    log.info("lin-loop is running")
    while True:
        await lin.loop_serial()
        if not(lin.stop_async): # full performance to send buffer
            await asyncio.sleep(0.001)


async def ctrl_loop():
    global lock
    lock = asyncio.Lock()

    a=asyncio.create_task(main())
    b=asyncio.create_task(lin_loop())

    # Delay to ensure successful MQTT connect after boot
    await asyncio.sleep(20)
    asyncio.create_task(connect.client.connect())

    while True:
        await asyncio.sleep(10)
        if a.done():
            log.info("Restart main_loop")
            a=asyncio.create_task(main())
        if b.done():
            log.info("Restart lin_loop")
            b=asyncio.create_task(lin_loop())


def run(w, lin_debug=False, inet_debug=False, mqtt_debug=False):
    global TOPIC_ROOT
    global connect
    global lin
    connect = w

    lin_debug  = connect.config.getboolean("logging", "lin_debug")
    inet_debug = connect.config.getboolean("logging", "inet_debug")
    mqtt_debug = connect.config.getboolean("logging", "mqtt_debug")

    if mqtt_debug:
        log.setLevel(logging.DEBUG)
        log.info("MQTT debug log enabled")

    log.info(f"HW-Check {w.platform_name}")

    port = connect.config["serial"]["device"]
    log.info(f"device = {port}")

    if port == "dummy":
        serial = pyserial.serial_for_url('loop://', baudrate=9600)
    else:
        serial = pyserial.Serial(
            port=port,
            baudrate=9600,
            bytesize=pyserial.EIGHTBITS,
            parity=pyserial.PARITY_NONE,
            stopbits=pyserial.STOPBITS_ONE,
            timeout=3
        )

    # Initialize the lin-object
    lin = Lin(serial, w.p, lin_debug, inet_debug)
    if connect.config["mqtt"]["topic"] != "":
        TOPIC_ROOT = connect.options["mqtt"]["topic"]

    log.info(f"prefix: '{TOPIC_ROOT}' set: '{SET_PREFIX}' status: '{STA_PREFIX}'")

    connect.set_proc(connect=conn_callback, subscript=callback)

    asyncio.run(ctrl_loop())


if __name__ == "__main__":

    import connect
    w = connect.Connect()
    w.rel_no = REL_NO
    w.connect()
    run(w)

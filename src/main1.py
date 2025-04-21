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
# The communication with the CPplus uses ESP32-UART2 - connect (tx:GPIO17, rx:GPIO16)
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
# 3.0.0 Simplified version ported to CPython for running on a Venus OS enabled Raspberry Pi
#

import os
import sys
import logging
import asyncio
from lin import Lin
from duocontrol import duo_ctrl
import serial as pyserial

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_PATH = os.path.join(PROJECT_ROOT, "lib")
sys.path.insert(0, os.path.abspath(LIB_PATH))


REL_NO = "3.0.0"

log = logging.getLogger(__name__)

# define global objects - important for processing
connect = None
lin = None
dc = None
sl = None

# Change the following configs to suit your environment
TOPIC_ROOT    = 'truma'
S_TOPIC_1     = ''
S_TOPIC_2     = ''
PUB_PREFIX    = ''
HA_STOPIC     = ''
HA_CTOPIC     = ''
HA_CONFIG     = ''



def set_prefix(topic):
    global TOPIC_ROOT
    global S_TOPIC_1
    global S_TOPIC_2
    global PUB_PREFIX
    global HA_STOPIC
    global HA_CTOPIC
    global HA_CONFIG

    TOPIC_ROOT = topic
    S_TOPIC_1       = 'service/' + TOPIC_ROOT + '/set/'
    S_TOPIC_2       = 'homeassistant/status'
    PUB_PREFIX      = 'service/' + TOPIC_ROOT + '/control_status/'

    # Auto-discovery-function of home-assistant (HA)
    HA_MODEL  = 'inetbox'
    HA_SWV    = 'V03'
    HA_STOPIC = 'service/' + TOPIC_ROOT + '/control_status/'
    HA_CTOPIC = 'service/' + TOPIC_ROOT + '/set/'

    HA_CONFIG = {
        "alive":                 ['homeassistant/binary_sensor/' + TOPIC_ROOT + '/alive/config', '{"name": "' + TOPIC_ROOT + '_alive", "model": "' + HA_MODEL + '", "sw_version": "' + HA_SWV + '", "device_class": "running", "state_topic": "' + HA_STOPIC + 'alive"}'],
        "release":               ['homeassistant/sensor/release/config', '{"name": "' + TOPIC_ROOT + '_release", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "state_topic": "' + HA_STOPIC + 'release"}'],
        "current_temp_room":     ['homeassistant/sensor/current_temp_room/config', '{"name": "' + TOPIC_ROOT + '_current_temp_room", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "device_class": "temperature", "unit_of_measurement": "°C", "state_topic": "' + HA_STOPIC + 'current_temp_room"}'],
        "current_temp_water":    ['homeassistant/sensor/current_temp_water/config', '{"name": "' + TOPIC_ROOT + '_current_temp_water", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "device_class": "temperature", "unit_of_measurement": "°C", "state_topic": "' + HA_STOPIC + 'current_temp_water"}'],
        "target_temp_room":      ['homeassistant/sensor/target_temp_room/config', '{"name": "' + TOPIC_ROOT + '_target_temp_room", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "device_class": "temperature", "unit_of_measurement": "°C", "state_topic": "' + HA_STOPIC + 'target_temp_room"}'],
        "target_temp_aircon":    ['homeassistant/sensor/target_temp_aircon/config', '{"name": "' + TOPIC_ROOT + '_target_temp_aircon", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "device_class": "temperature", "unit_of_measurement": "°C", "state_topic": "' + HA_STOPIC + 'target_temp_aircon"}'],
        "target_temp_water":     ['homeassistant/sensor/target_temp_water/config', '{"name": "' + TOPIC_ROOT + '_target_temp_water", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "device_class": "temperature", "unit_of_measurement": "°C", "state_topic": "' + HA_STOPIC + 'target_temp_water"}'],
        "energy_mix":            ['homeassistant/sensor/energy_mix/config', '{"name": "' + TOPIC_ROOT + '_energy_mix", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "state_topic": "' + HA_STOPIC + 'energy_mix"}'],
        "el_power_level":        ['homeassistant/sensor/el_level/config', '{"name": "' + TOPIC_ROOT + '_el_power_level", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "state_topic": "' + HA_STOPIC + 'el_power_level"}'],
        "heating_mode":          ['homeassistant/sensor/heating_mode/config', '{"name": "' + TOPIC_ROOT + '_heating_mode", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "state_topic": "' + HA_STOPIC + 'heating_mode"}'],
        "operating_status":      ['homeassistant/sensor/operating_status/config', '{"name": "' + TOPIC_ROOT + '_operating_status", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "state_topic": "' + HA_STOPIC + 'operating_status"}'],
        "aircon_operating_mode": ['homeassistant/sensor/aircon_operating_mode/config', '{"name": "' + TOPIC_ROOT + '_aircon_operating_mode", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "state_topic": "' + HA_STOPIC + 'aircon_operating_mode"}'],
        "aircon_vent_mode":      ['homeassistant/sensor/aircon_vent_mode/config', '{"name": "' + TOPIC_ROOT + '_aircon_vent_mode", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "state_topic": "' + HA_STOPIC + 'aircon_vent_mode"}'],
        "operating_status":      ['homeassistant/sensor/operating_status/config', '{"name": "' + TOPIC_ROOT + '_operating_status", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "state_topic": "' + HA_STOPIC + 'operating_status"}'],
        "error_code":            ['homeassistant/sensor/error_code/config', '{"name": "' + TOPIC_ROOT + '_error_code", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "state_topic": "' + HA_STOPIC + 'error_code"}'],
        "clock":                 ['homeassistant/sensor/clock/config', '{"name": "' + TOPIC_ROOT + '_clock", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "state_topic": "' + HA_STOPIC + 'clock"}'],
        "set_target_temp_room":  ['homeassistant/select/target_temp_room/config', '{"name": "' + TOPIC_ROOT + '_set_roomtemp", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'target_temp_room", "options": ["0", "10", "15", "18", "20", "21", "22"] }'],
        "set_target_temp_aircon":['homeassistant/select/target_temp_aircon/config', '{"name": "' + TOPIC_ROOT + '_set_aircontemp", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'target_temp_aircon", "options": ["16", "18", "20", "22", "24", "26", "28"] }'],
        "set_target_temp_water": ['homeassistant/select/target_temp_water/config', '{"name": "' + TOPIC_ROOT + '_set_warmwater", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'target_temp_water", "options": ["0", "40", "60", "200"] }'],
        "set_heating_mode":      ['homeassistant/select/heating_mode/config', '{"name": "' + TOPIC_ROOT + '_set_heating_mode", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'heating_mode", "options": ["off", "eco", "high"] }'],
        "set_aircon_mode":       ['homeassistant/select/aircon_mode/config', '{"name": "' + TOPIC_ROOT + '_set_aircon_mode", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'aircon_operating_mode", "options": ["off", "vent", "cool", "hot", "auto"] }'],
        "set_vent_mode":         ['homeassistant/select/vent_mode/config', '{"name": "' + TOPIC_ROOT + '_set_vent_mode", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'aircon_vent_mode", "options": ["low", "mid", "high", "night", "auto"] }'],
        "set_energy_mix":        ['homeassistant/select/energy_mix/config', '{"name": "' + TOPIC_ROOT + '_set_energy_mix", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'energy_mix", "options": ["none", "gas", "electricity", "mix"] }'],
        "set_el_power_level":    ['homeassistant/select/el_power_level/config', '{"name": "' + TOPIC_ROOT + '_set_el_power_level", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'el_power_level", "options": ["0", "900", "1800"] }'],
        "set_reboot":            ['homeassistant/select/set_reboot/config', '{"name": "' + TOPIC_ROOT + '_set_reboot", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'reboot", "options": ["0", "1"] }'],
        "set_os_run":            ['homeassistant/select/set_os_run/config', '{"name": "' + TOPIC_ROOT + '_set_os_run", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'os_run", "options": ["0", "1"] }'],
        "ota_update":            ['homeassistant/select/ota_update/config', '{"name": "' + TOPIC_ROOT + '_ota_update", "model": "' + HA_MODEL + '", "sw_version":"' + HA_SWV + '", "command_topic": "' + HA_CTOPIC + 'ota_update", "options": ["0", "1"] }'],
    }

# Universal callback function for all subscriptions
def callback(topic, msg, retained, qos):
    global connect
    log.debug(f"received: {topic}: {msg}")
    topic = str(topic)
    topic = topic[2:-1]
    msg = str(msg)
    msg = msg[2:-1]
    # Command received from broker
    if topic.startswith(S_TOPIC_1):
        topic = topic[len(S_TOPIC_1):]
#       log.info("Received command: "+str(topic)+" payload: "+str(msg))
        if topic in lin.app.status.keys():
            log.info("inet-key:"+str(topic)+" value: "+str(msg))
            try:
                lin.app.set_status(topic, msg)
            except Exception as e:
                log.debug(Exception(e))
                # send via mqtt
        elif not(dc == None):
            if topic in dc.status.keys():
                log.info("dc-key:"+str(topic)+" value: "+str(msg))
                try:
                    dc.set_status(topic, msg)
                except Exception as e:
                    log.debug(Exception(e))
                    # send via mqtt
            else:
                log.debug("key incl. dc is unkown")
        else:
            log.debug("key w/o dc is unkown")
    # HA-server send ONLINE message
    if (topic == S_TOPIC_2) and (msg == 'online'):
        log.info("Received HOMEASSISTANT-online message")
        set_ha_autoconfig(connect.client)


# Initialze the subscripted topics
async def conn_callback(client):
    log.debug("Set subscription")
    # inetbox_set_commands
    await connect.client.subscribe(S_TOPIC_1+"#", 1)
    # HA_online_command
    await connect.client.subscribe(S_TOPIC_2, 1)


# HA autodiscovery - delete all entities
async def del_ha_autoconfig(c):
    for i in HA_CONFIG.keys():
        await asyncio.sleep(0) # clean asyncio programming
        try:
            await c.publish(HA_CONFIG[i][0], "{}", qos=1)
        except:
            log.debug("Publishing error in del_ha_autoconfig")
    log.info("del ha_autoconfig completed")

# HA auto discovery: define all auto config entities
async def set_ha_autoconfig(c):
    global connect
    for i in HA_CONFIG.keys():
        await asyncio.sleep(0) # clean asyncio programming
        try:
            await c.publish(HA_CONFIG[i][0], HA_CONFIG[i][1], qos=1)
#            print(i,": [" + HA_CONFIG[i][0] + "payload: " + HA_CONFIG[i][1] + "]")
        except:
            log.debug("Publishing error in set_ha_autoconfig")
    await c.publish(PUB_PREFIX + "release", connect.rel_no, qos=1)
    log.info("set ha_autoconfig completed")

# main publisher-loop
async def main():
    global repo_update
    global connect
    global file
    log.debug("main-loop is running")

    await del_ha_autoconfig(connect.client)
    await set_ha_autoconfig(connect.client)
    log.info("Initializing completed")

    i = 0
    wd = False
    while True:
        await asyncio.sleep(10) # Update every 10sec
        if file: logging._stream.flush()
        s = lin.app.get_all(True)
        for key in s.keys():
            log.debug(f'publish {key}:{s[key]}')
            try:
                await connect.client.publish(PUB_PREFIX+key, str(s[key]), qos=1)
            except:
                log.debug("Error in LIN status publishing")
        if lin.app.status["alive"][0]=="OFF":
            if not(wd):
                asyncio.create_task(lin.watchdog())
                wd = True
        else: wd = False
        if not(dc == None):
            s = dc.get_all(True)
            for key in s.keys():
                log.debug(f'publish {key}:{s[key]}')
                try:
                    await connect.client.publish(PUB_PREFIX+key, str(s[key]), qos=1)
                except:
                    log.debug("Error in duo_ctrl status publishing")

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


# major ctrl loop for duo_ctrl_check
async def dc_loop():
    await asyncio.sleep(30) # Delay at begin
    log.info("duo_ctrl-loop is running")
    while True:
        dc.loop()
        await asyncio.sleep(10)

async def sl_loop():
    await asyncio.sleep(5) # Delay at begin
    log.info("spirit-level-loop is running")
    while True:
        sl.loop()
        #print("Angle X: " + str(sl.get_roll()) + "      Angle Y: " +str(sl.get_pitch()) )
        await asyncio.sleep(0.1)

async def ctrl_loop():
    loop = asyncio.get_event_loop()
    a=asyncio.create_task(main())
    b=asyncio.create_task(lin_loop())
    c=asyncio.create_task(connect.client.connect())
    if not(dc == None):
        d=asyncio.create_task(dc_loop())
    while True:
        await asyncio.sleep(10)
        if a.done():
            log.info("Restart main_loop")
            a=asyncio.create_task(main())
        if b.done():
            log.info("Restart lin_loop")
            b=asyncio.create_task(lin_loop())
        if c.done():
            log.info("Restart MQTT clinet connect looop")
            c=asyncio.create_task(connect.client.connect())


def run(w, lin_debug=False, inet_debug=False, mqtt_debug=False, logfile=False):
    global TOPIC_ROOT
    global connect
    global lin
    global dc
    global sl
    global file
    connect = w

    file = logfile
    activate_duoControl  = (connect.config["options"]["duo_control"] == "1")

    if mqtt_debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    if lin_debug: log.info("LIN-LOG defined")
    if inet_debug: log.info("INET-LOG defined")
    if mqtt_debug: log.info("MQTT-LOG defined")

    log.info(f"HW-Check {w.platform_name}")

    port = connect.config["serial"]["device"]

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

    #if activate_duoControl:
    #    log.info("Activate duoControl set to true, using GPIO 18,19 as input, 22,23 as output")
    #    dc = duo_ctrl()
    #else:
    #    dc = None

    # Initialize the lin-object
    lin = Lin(serial, w.p, lin_debug, inet_debug)
    if connect.config["mqtt"]["topic"] != "":
        TOPIC_ROOT = connect.options["mqtt"]["topic"]

    set_prefix(TOPIC_ROOT)
    log.info(f"prefix: '{TOPIC_ROOT}' set: {S_TOPIC_1} rec: {PUB_PREFIX}")
    connect.mqtt_config.set_last_will("service/" + TOPIC_ROOT + "/control_status/alive", "OFF", retain=True, qos=0)  # last will is important
    connect.set_proc(subscript = callback, connect = conn_callback)

    if not(dc == None):
        HA_CONFIG.update(dc.HA_DC_CONFIG)

    asyncio.run(ctrl_loop())


if __name__ == "__main__":

    log.info(f"Release no: {REL_NO}")

    import connect
    w=connect.Connect()
    w.rel_no = REL_NO
    w.connect()

    run(w)

#!/usr/bin/env python
# Add custom temperature gauges to Victron Venus OS running on Raspberry Pi
#
# Based on https://github.com/TimD1981/RpiTemperature
#
# KHr

from dbus.mainloop.glib import DBusGMainLoop
import sys
if sys.version_info.major == 2:
    import gobject
    from gobject import idle_add
else:
    from gi.repository import GLib as gobject
import dbus
import platform
from threading import Timer
import logging
import os

from pprint import pprint

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-modem'))
from vedbus import VeDbusService, VeDbusItemExport, VeDbusItemImport
from settingsdevice import SettingsDevice  # available in the velib_python repository

dbusservice = None

def update():
     update_temp("cpu",   dbus_cpu_service,   '/sys/devices/virtual/thermal/thermal_zone0/temp', convert=True)
     update_temp("room",  dbus_room_service,  '/tmp/truma/current_temp_room')
     update_temp("water", dbus_water_service, '/tmp/truma/current_temp_water')
     return True


# KHr: Update temperature
def update_temp(name, dbus_service, file, convert=False):
    if not os.path.exists(file):
        if dbus_service['/Connected'] != 0:
            logging.info(f"{name} temperature interface disconnected")
            dbus_service['/Connected'] = 0
    else:
        if dbus_service['/Connected'] != 1:
            logging.info(f"{name} temperature interface connected")
            dbus_service['/Connected'] = 1
        with open(file,'r') as fd:
            content = fd.read().strip()
            if content:
                try:
                    value = float(content)
                except:
                    logging.warning(f"Invalid temperature value: {file} {content}")
                    return
            else:
                    logging.warning(f"Temperature file is empty: {file}")
                    return
            if convert:
                value = round(value / 1000.0, 1)
            dbus_service['/Temperature'] = value



# =========================== Start of settings interface ================
#  The settings interface handles the persistent storage of changes to settings
#  This should probably be created as a new class extension to the settingDevice object
#  The complexity is because this python service handles temperature and humidity
#  Data for about 6 different service paths so we need different dBusObjects for each device
#
newSettings = {}     # Used to gather new settings to create/check as each dBus object is created
settingObjects = {}  # Used to identify the dBus object and path for each setting
                     # settingsObjects = {setting: [path,object],}
                     # each setting is the complete string e.g. /Settings/Temperature/4/Scale

settingDefaults = {'/Offset': [0, -10, 10],
                   '/Scale'  : [1.0, -5, 5],
                   '/TemperatureType'   : [2, 0, 3],
                   '/CustomName'        : ['', 0, 0]}

# Values changed in the GUI need to be updated in the settings
# Without this changes made through the GUI change the dBusObject but not the persistent setting
# (as tested in venus OS 2.54 August 2020)
def handle_changed_value(setting, path, value):
    global settings
    print("some value changed")
    # The callback to the handle value changes has been modified by using an anonymouse function (lambda)
    # the callback is declared each time a path is added see example here
    # self.add_path(path, 0, writeable=True, onchangecallback = lambda x,y: handle_changed_value(setting,x,y) )
    logging.info(" ".join(("Storing change to setting", setting+path, str(value) )) )
    settings[setting+path] = value
    return True

# Changes made to settings need to be reflected in the GUI and in the running service
def handle_changed_setting(setting, oldvalue, newvalue):
    logging.info('Setting changed, setting: %s, old: %s, new: %s' % (setting, oldvalue, newvalue))
    [path, object] = settingObjects[setting]
    object[path] = newvalue
    return True

# Add setting is called each time a new service path is created that needs a persistent setting
# If the setting already exists the existing recored is unchanged
# If the setting does not exist it is created when the serviceDevice object is created
def addSetting(base, path, dBusObject):
    global settingObjects
    global newSettings
    global settingDefaults
    setting = base + path
    logging.info(" ".join(("Add setting", setting, str(settingDefaults[path]) )) )
    settingObjects[setting] = [path, dBusObject]             # Record the dBus Object and path for this setting
    newSettings[setting] = [setting] + settingDefaults[path] # Add the setting to the list to be created

# initSettings is called when all the required settings have been added
def initSettings(newSettings):
    global settings

#   settingsDevice is the library class that handles the reading and setting of persistent settings
    settings = SettingsDevice(
        bus=dbus.SystemBus() if (platform.machine() == 'armv7l') else dbus.SessionBus(),
        supportedSettings = newSettings,
        eventCallback     = handle_changed_setting)

# readSettings is called after init settings to read all the stored settings and
# set the initial values of each of the service object paths
# Note you can not read or set a setting if it has not be included in the newSettings
#      list passed to create the new settingsDevice class object

def readSettings(list):
    global settings
    logging.info("reading")
    for setting in list:
        [path, object] = list[setting]
        logging.info(" ".join(("Retreived setting", setting, path, str(settings[setting]))))
        object[path] = settings[setting]

# =========================== end of settings interface ======================

class SystemBus(dbus.bus.BusConnection):
    def __new__(cls):
        return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SYSTEM)

class SessionBus(dbus.bus.BusConnection):
    def __new__(cls):
        return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SESSION)

def dbusconnection():
    return SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else SystemBus()


def getrevision():
  # Extract board revision from cpuinfo file
  myrevision = "0000"
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if line[0:8]=='Revision':
        length=len(line)
        myrevision = line[11:length-1]
    f.close()
  except:
    myrevision = "0000"

  return myrevision

# Argument parsing removed from source as never used
class args: pass
args.debug = False
#args.debug = True

# Init logging
logging.basicConfig(level=(logging.DEBUG if args.debug else logging.INFO))
logging.info(__file__ + " is starting up")
logLevel = {0: 'NOTSET', 10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR'}
logging.info('Loglevel set to ' + logLevel[logging.getLogger().getEffectiveLevel()])

# Have a mainloop, so we can send/receive asynchronous calls to and from dbus
DBusGMainLoop(set_as_default=True)

def new_service(base, type, physical, logical, productName, customName, id, instance, settingId = False):
    self =  VeDbusService("{}.{}.{}{:02d}".format(base, type, physical,  id), dbusconnection())
    # physical is the physical connection
    # logical is the logical connection to allign with the numbering of the console display
    # Create the management objects, as specified in the ccgx dbus-api document
    self.add_path('/Mgmt/ProcessName', __file__)
    self.add_path('/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
    self.add_path('/Mgmt/Connection', logical)

    # Create the mandatory objects, note these may need to be customised after object creation
    self.add_path('/DeviceInstance', instance)
    self.add_path('/ProductId', 0)
    self.add_path('/ProductName', productName)
    self.add_path('/FirmwareVersion', platform.system())
    self.add_path('/HardwareVersion', getrevision())
    self.add_path('/Connected', 0)  # Mark devices as disconnected until they are confirmed

    # Create device type specific objects set values to empty until connected
    if settingId :
        setting = "/Settings/" + type.capitalize() + "/" + str(settingId)
    else:
        print("no setting required")
        setting = ""
    if type == 'temperature':
        self.add_path('/Temperature', [])
        self.add_path('/Status', 0)
        if settingId:
            addSetting(setting , '/TemperatureType', self)
            addSetting(setting , '/CustomName', self)
        self.add_path('/TemperatureType', 2, writeable=True, onchangecallback = lambda x,y: handle_changed_value(setting,x,y) )
        self.add_path('/CustomName', customName, writeable=True, onchangecallback = lambda x,y: handle_changed_value(setting,x,y) )
        self.add_path('/Function', 1, writeable=True )

    return self

#dbusservice = {} # Dictionary to hold the multiple services

base = 'com.victronenergy'

# service defined by (base*, type*, connection*, logial, id*, instance, settings ID):
# Items marked with a (*) are included in the service name
#

dbus_cpu_service   = new_service(base, 'temperature', 'RpiCpu',     'Raspberry Pi OS', 'Raspberry Pi', 'CPU',    6, 29, 6)
dbus_room_service  = new_service(base, 'temperature', 'TrumaRoom',  'Raspberry Pi OS', 'Truma C4',     'Indoor', 7, 30, 7) # KHr
dbus_water_service = new_service(base, 'temperature', 'TrumaWater', 'Raspberry Pi OS', 'Truma C4',     'Water',  8, 31, 8) # KHr

# Tidy up custom or missing items
#dbus_cpu_service['/ProductName']     = 'RPi CPU Temp'
#dbus_room_service['/ProductName']    = 'Truma Room Temp'   # KHr
#dbus_water_service['/ProductName']   = 'Truma Water Temp'  # KHr

# Persistent settings obejects in settingsDevice will not exist before this is executed
initSettings(newSettings)
# Do something to read the saved settings and apply them to the objects
readSettings(settingObjects)

# Do a first update so that all the readings appear.
update()
# update every 10 seconds - temperature and humidity should move slowly so no need to demand
# too much CPU time
#
gobject.timeout_add(10000, update)

print('Connected to dbus, and switching over to gobject.MainLoop() (= event based)')
mainloop = gobject.MainLoop()
mainloop.run()

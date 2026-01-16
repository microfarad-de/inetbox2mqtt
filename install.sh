#!/bin/bash

# KHr
# Apply all the changes required for running inetbox2mqtt to a fresh Venus OS installation


# Enable classic Bluetooth
sed -i 's|^[[:space:]]*ControllerMode[[:space:]]*=[[:space:]]*le[[:space:]]*$|ControllerMode = dual|' /etc/bluetooth/ble.conf


# Create symbolic links for inetbox2mqtt components
ln -s /data/inetbox2mqtt/service/* /opt/victronenergy/service/
ln -s /data/inetbox2mqtt/etc/udev/rules.d/zz-serial-starter-override.rules /etc/udev/rules.d/
ln -s /data/inetbox2mqtt/etc/inetbox2mqtt /etc/


# Create symbolic links for nastia-server components
ln -s /data/nastia-server/opt/logrotate-3.21.0/logrotate /usr/sbin/
ln -s /data/nastia-server/opt/msmtp-1.8.24/src/msmtp /usr/bin/
ln -s /data/nastia-server/opt/lynx2.9.0/lynx /usr/bin/
ln -s /data/nastia-server/etc/nastia-server.conf /etc/
ln -s /data/nastia-server/etc/cron.d/nastia-server /etc/cron.d/
ln -s /data/nastia-server/etc/logrotate.conf /etc/
ln -s /data/nastia-server/service/* /opt/victronenergy/service/
mkdir /usr/local/etc/
ln -s /data/nastia-server/opt/lynx2.9.0/lynx.cfg /usr/local/etc/


# PySHT40toMQTT

This Python program will:

1. Connect to a SHT40 humidity and temperature sensor.
2. Read settings from a JSON formatted configuration file.
3. Use the settings to connect to a MQTT broker.
4. Publish sensor and client information to the broker on a timer set in the config file.

This was designed for Raspberry Pi devices, and has been tested on a Pi Zero 2 W.

### Installation:

> pip install adafruit-circuitpython-sht4x
> >
> pip install paho-mqtt

#### It can be set to auto-start by editing this file:

> sudo nano /etc/xdg/autostart/display.desktop

#### And setting the contents to this:

> [Desktop Entry]
> 
> Name=PiCounter
> 
> Exec=/usr/bin/python /home/pi/Source/PySHT40toMQTT/PySHT40toMQTT.py /home/pi/Source/PySHT40toMQTT/config.json

It is important to put the full path to all files which are not on the system path.



To use systemd to control execution create this file:
> sudo nano /lib/systemd/system/piWeather.service

In that file, enter this text:

> [Unit]
> Description=Python Weather Service
> After=multi-user.target
>
> [Service]
> Type=idle
> ExecStart=/usr/bin/python /home/pi/Source/PySHT40toMQTT/PySHT40toMQTT.py
> WorkingDirectory=/home/pi/Source/PySHT40toMQTT
> User=pi
>
> [Install]
> WantedBy=multi-user.target

Set the permissions on that file with:

> sudo chmod 644 /lib/systemd/system/piWeather.service

Systemd will need to be restarted with:

> sudo systemctl daemon-reload

Then the service can be enabled with:

> sudo systemctl enable piWeather.service

And it can be disabled with:

> sudo systemctl disable piWeather.service

The status of this service can be 

> sudo systemctl status piWeather.service

That's it!

# This tool will connect to a MQTT broker, and publish simple MQTT messages containing weather data.
# The sole command-line-parameter is the configuration file.
# The configuration file is in JSON format.
# It must contain "brokerAddress", "brokerPort", "brokerQoS", "publishTopic", and "sleepTime".
# https://pypi.org/project/paho-mqtt/

import sys
import json
import time
import socket
import board
import adafruit_sht4x
import datetime
import paho.mqtt.client as mqtt
from uuid import getnode as get_mac
from pathlib import Path

client = mqtt.Client( client_id = "PySHT40toMQTT" )


# The callback for when a connection is made to the server.
def on_connect( client2, userdata, flags, result ):
    if result != 0:
        print( "Bad connection, returned code=", result )


# The callback for when a connection is made to the server.
def on_disconnect():
    print( "Disconnected from broker!" )


def on_publish( client3, userdata, result ):  # create function for callback
    # print( "Published message: \"" + str( result ) + "\"" )
    pass


def get_ip():
    s = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
    s.settimeout( 0 )
    try:
        # This address doesn't need to be reachable.
        s.connect( ( '10.255.255.255', 1 ) )
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def main( argv ):
    config_file_name = "/home/pi/Source/PySHT40toMQTT/config.json"

    try:
        if len( argv ) > 1:
            config_file_name = argv[1]
        print( "Using " + config_file_name + " as the config file." )
        # Read in the configuration file.
        with open( config_file_name, "r" ) as config_file:
            configuration = json.load( config_file )

        host_name = socket.gethostname()
        print( "Hostname: " + host_name )
        timestamp = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
        print( timestamp )
        print( "Using broker address: " + configuration['brokerAddress'] )
        print( "Using broker port: " + configuration['brokerPort'] )
        print( "Publishing to topic: \"" + configuration['publishTopic'] + "\"" )
        print( "Publishing on QoS: " + str( configuration['brokerQoS'] ) )
        print( "Pausing " + str( configuration['sleepTime'] ) + " seconds between polls" )
        i2c = board.I2C()  # uses board.SCL and board.SDA
        sht = adafruit_sht4x.SHT4x( i2c )
        print( "Found SHT4x with serial number", hex( sht.serial_number ) )
        sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
        # Can also set the mode to enable heater
        # sht.mode = adafruit_sht4x.Mode.LOWHEAT_100MS
        print( "Current mode is: ", adafruit_sht4x.Mode.string[sht.mode] )

        # Create the Dictionary to hold results, and set the static components.
        results = json.loads( '{}' )
        results['host'] = host_name
        results['timeStamp'] = timestamp
        if 'notes' in configuration:
            results['notes'] = configuration['notes']
        results['brokerAddress'] = configuration['brokerAddress']
        results['brokerPort'] = configuration['brokerPort']
        results['clientAddress'] = get_ip()
        results['clientMAC'] = ':'.join( ( "%012X" % get_mac() )[i:i+2] for i in range( 0, 12, 2 ) )

        # Define callback functions.
        client.on_connect = on_connect
        client.on_publish = on_publish
        client.on_disconnect = on_disconnect

        # Connect using the details from the configuration file.
        client.connect( configuration['brokerAddress'], int( configuration['brokerPort'] ) )
        
        while True:
            client.loop_start()
            timestamp = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )
            results['timeStamp'] = timestamp
            temperature, relative_humidity = sht.measurements
            results['tempC'] = temperature
            results['humidity'] = relative_humidity
            print( json.dumps( results, indent = '\t' ) )
            info = client.publish( topic = configuration['publishTopic'], payload = json.dumps( results, indent = '\t' ), qos = configuration['brokerQoS'] )
            client.loop_stop()
            time.sleep( configuration['sleepTime'] )

    except KeyboardInterrupt:
        print( "\nKeyboard interrupt detected, exiting...\n" )
    except KeyError as key_error:
        log_string = "Python dictionary key error: %s" % str( key_error )
        print( log_string )
    except ConnectionRefusedError as connection_error:
        print( "Connection error: " + str( connection_error ) )


if __name__ == "__main__":
    main( sys.argv )

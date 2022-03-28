# This tool will connect to a MQTT broker, and publish simple MQTT messages containing weather data.
# The sole command-line-parameter is the configuration file.
# The configuration file is in JSON format.
# It must contain "brokerAddress", "brokerPort", "brokerQoS", "publishTopic", and "sleepTimeSec".
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

client = mqtt.Client( client_id = "PySHT40toMQTT" )
i2c = board.I2C()  # uses board.SCL and board.SDA
sht = adafruit_sht4x.SHT4x( i2c )
results = json.loads( '{}' )
configuration = json.loads( '{}' )


def on_connect( con_client, userdata, flags, result ):
  if result != 0:
    print( "Bad connection, returned code: ", result )
  if result == 2112:  # This should be unreachable.
    print( str( con_client ) )
    print( str( userdata ) )
    print( str( flags ) )


def on_disconnect():
  print( "Disconnected from broker!" )


def on_message( sub_client, userdata, msg ):
  global configuration
  message = json.loads( str( msg.payload.decode( 'utf-8' ) ) )
  print( json.dumps( message, indent = '\t' ) )
  if 'command' in message:
    command = message['command']
    match command.casefold():
      case "publishTelemetry":
        temperature, relative_humidity = read_sht()
        publish_results( temperature, relative_humidity )
      case "changeTelemetryInterval":
        print( "Old publish interval: " + configuration['publishInterval'] )
        configuration['publishInterval'] = message['value']
        print( "New publish interval: " + configuration['publishInterval'] )
      case "changeSeaLevelPressure":
        print( "Old sea level pressure: " + configuration['seaLevelPressure'] )
        configuration['seaLevelPressure'] = message['value']
        print( "New sea level pressure: " + configuration['seaLevelPressure'] )
      case "publishStatus":
        publish_status()
      case "":
        print( str( sub_client ) )
        print( str( userdata ) )
      case _:
        return "No match found for " + str( message['command'] )


def on_publish( pub_client, userdata, result ):
  print( json.dumps( result, indent = '\t' ) )
  if result == 2112:  # This should be unreachable.
    print( str( pub_client ) )
    print( str( userdata ) )


def get_ip():
  sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
  sock.settimeout( 0 )
  try:
    # This address doesn't need to be reachable.
    sock.connect( ('10.255.255.255', 1) )
    ip = sock.getsockname()[0]
  except InterruptedError:
    ip = '127.0.0.1'
  finally:
    sock.close()
  return ip


def read_sht():
  global sht
  return sht.measurements


def get_timestamp():
  return datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )


def publish_results( temperature, relative_humidity ):
  results['timeStamp'] = get_timestamp()
  results['tempC'] = temperature
  results['humidity'] = relative_humidity
  client.publish( topic = configuration['publishTopic'], payload = json.dumps( results, indent = '\t' ), qos = configuration['brokerQoS'] )


def publish_status():
  status = results
  status['timeStamp'] = get_timestamp()
  status.pop( 'temperature', None )
  print( json.dumps( results, indent = '\t' ) )
  client.publish( topic = configuration['publishTopic'], payload = json.dumps( status, indent = '\t' ), qos = configuration['brokerQoS'] )


def main( argv ):
  global configuration
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
    timestamp = get_timestamp()
    print( timestamp )
    print( "Using broker address: " + configuration['brokerAddress'] )
    print( "Using broker port: " + configuration['brokerPort'] )
    print( "Publishing to topic: \"" + configuration['publishTopic'] + "\"" )
    print( "Publishing on QoS: " + str( configuration['brokerQoS'] ) )
    print( "Pausing " + str( configuration['sleepTimeSec'] ) + " seconds between publishes." )

    print( "Found SHT4x with serial number " + hex( sht.serial_number ) )
    sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION  # noqa
    # Can also set the mode to enable heater
    # sht.mode = adafruit_sht4x.Mode.LOWHEAT_100MS
    print( "Current mode is: ", adafruit_sht4x.Mode.string[sht.mode] )  # noqa

    # Create the Dictionary to hold results, and set the static components.
    results['host'] = host_name
    results['timeStamp'] = timestamp
    if 'notes' in configuration:
      results['notes'] = configuration['notes']
    results['brokerAddress'] = configuration['brokerAddress']
    results['brokerPort'] = configuration['brokerPort']
    results['clientAddress'] = get_ip()
    results['clientMAC'] = ':'.join( ("%012X" % get_mac())[i:i + 2] for i in range( 0, 12, 2 ) )

    # Define callback functions.
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # Connect using the details from the configuration file.
    client.connect( configuration['brokerAddress'], int( configuration['brokerPort'] ) )
    # Subscribe to the control topic.
    client.subscribe( configuration['controlTopic'], configuration['brokerQoS'] )

    while True:
      # ToDo: Determine if client.loop_start() and loop_stop() should be in this while loop.
      client.loop_start()
      temperature, relative_humidity = read_sht()
      publish_results( temperature, relative_humidity )
      client.loop_stop()
      time.sleep( configuration['sleepTimeSec'] )

  except KeyboardInterrupt:
    print( "\nKeyboard interrupt detected, exiting...\n" )
    client.unsubscribe( configuration['controlTopic'] )
    client.disconnect()
  except KeyError as key_error:
    log_string = "Python dictionary key error: %s" % str( key_error )
    print( log_string )
  except ConnectionRefusedError as connection_error:
    print( "Connection error: " + str( connection_error ) )


if __name__ == "__main__":
  main( sys.argv )

# This tool will connect to a MQTT broker, and publish simple MQTT messages containing weather data.
# The sole command-line-parameter is the configuration file.
# The configuration file is in JSON format.
# It must contain "brokerAddress", "brokerPort", "brokerQoS", "publishTopic", and "publishInterval".
# https://pypi.org/project/paho-mqtt/
# This requires Python version 3.10 or higher.

import sys
import json
import time
import socket
import board
import adafruit_sht4x
import datetime
import gpiozero as gz
import paho.mqtt.client as mqtt
from uuid import getnode as get_mac

client = mqtt.Client( client_id = "PySHT40toMQTT" )
i2c = board.I2C()  # Uses board.SCL and board.SDA
sht = adafruit_sht4x.SHT4x( i2c )
results = json.loads( '{}' )
configuration = json.loads( '{}' )
config_file_name = "/home/pi/Source/PySHT40toMQTT/config.json"
last_publish = 0
cpu_temperature = 0


def on_connect( con_client, userdata, flags, result ):
  if result != 0:
    print( "Bad connection, returned code: ", result )
  if result == 2112:  # This should be unreachable, and should not cause problems if it is reached.
    print( str( con_client ) )
    print( str( userdata ) )
    print( str( flags ) )


def on_disconnect():
  print( "Disconnected from broker!" )


def on_message( sub_client, userdata, msg ):
  global configuration
  global last_publish
  message = json.loads( str( msg.payload.decode( 'utf-8' ) ) )
  print( json.dumps( message, indent = '\t' ) )
  if 'command' in message:
    command = message['command']
    print( "Processing command \"" + command + "\"" )
    match command.casefold():
      case "publishTelemetry":
        temperature, relative_humidity = read_sht()
        publish_results( temperature, relative_humidity, cpu_temperature )
        last_publish = epoch_time()
      case "changeTelemetryInterval":
        old_value = configuration['publishInterval']
        new_value = message['value']
        if old_value != new_value and new_value > 4:
          print( "Old publish interval: " + old_value )
          configuration['publishInterval'] = new_value
          print( "New publish interval: " + configuration['publishInterval'] )
        else:
          print( "Not changing the telemetry publish interval." )
      case "changeSeaLevelPressure":
        old_value = configuration['seaLevelPressure']
        new_value = message['value']
        if old_value != new_value and 100 < new_value < 10000:
          print( "Old sea level pressure: " + old_value )
          configuration['seaLevelPressure'] = new_value
          print( "New sea level pressure: " + configuration['seaLevelPressure'] )
        else:
          print( "Not changing the sea level pressure." )
      case "publishStatus":
        publish_status()
      case "debug":
        print( str( sub_client ) )
        print( str( userdata ) )
      case _:
        print( "The command \"" + str( command ) + "\" is not recognized." )
        print( "Currently recognized commands are:\n\tpublishTelemetry\n\tchangeTelemetryInterval\n\tchangeSeaLevelPressure\n\tpublishStatus" )
  else:
    print( "Message did not contain a command property." )


def on_publish( pub_client, userdata, result ):
  if result == 2112.2112:  # This should be unreachable, and should not cause problems if it is reached.
    print( str( pub_client ) )
    print( str( userdata ) )
    print( str( result ) )


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


def epoch_time():
  # Returns the time in seconds since Unix Epoch, rounded to an integer.
  return round( time.time() )


def get_timestamp():
  # Returns the current date and time in ISO-8601 format.
  return datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" )


def publish_results( temperature, relative_humidity, cpu_temp ):
  results['timeStamp'] = get_timestamp()
  results['tempC'] = temperature
  results['humidity'] = relative_humidity
  results['cpuTemp'] = cpu_temp
  client.publish( topic = configuration['publishTopic'], payload = json.dumps( results, indent = '\t' ), qos = configuration['brokerQoS'] )
  print( json.dumps( results, indent = 3 ) )


def publish_status():
  status = results
  status['timeStamp'] = get_timestamp()
  status.pop( 'temperature', None )
  client.publish( topic = configuration['publishTopic'], payload = json.dumps( status, indent = '\t' ), qos = configuration['brokerQoS'] )
  print( json.dumps( results, indent = 3 ) )


def main( argv ):
  global configuration
  global config_file_name
  global last_publish
  global cpu_temperature

  try:
    if len( argv ) > 1:
      config_file_name = argv[1]
    print( "Using " + config_file_name + " as the config file." )
    # Read in the configuration file.
    with open( config_file_name, "r" ) as config_file:
      configuration = json.load( config_file )

    host_name = socket.gethostname()
    print( "Hostname: " + host_name )
    print( "Current time: " + get_timestamp() )
    print( "Using broker address: " + configuration['brokerAddress'] )
    print( "Using broker port: " + configuration['brokerPort'] )
    print( "Publishing to the telemetry topic: \"" + configuration['publishTopic'] + "\"" )
    print( "Subscribing to the control topic: \"" + configuration['controlTopic'] + "\"" )
    print( "Publishing and subscribing using QoS: " + str( configuration['brokerQoS'] ) )
    print( "Waiting " + str( configuration['publishInterval'] ) + " seconds between publishes (non-blocking)." )

    print( "Found SHT4x with serial number " + hex( sht.serial_number ) )
    sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION  # noqa
    # Can also set the mode to enable heater like this: sht.mode = adafruit_sht4x.Mode.LOWHEAT_100MS
    print( "Current mode is: ", adafruit_sht4x.Mode.string[sht.mode] )  # noqa

    # Create the Dictionary to hold results, and set the static components.
    results['host'] = host_name
    results['timeStamp'] = get_timestamp()
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
    # client.on_disconnect = on_disconnect  # This is throwing: "TypeError: on_disconnect() takes 0 positional arguments but 3 were given" when the program closes.

    # Connect using the details from the configuration file.
    client.connect( configuration['brokerAddress'], int( configuration['brokerPort'] ) )
    # Subscribe to the control topic.
    result_tuple = client.subscribe( configuration['controlTopic'], configuration['brokerQoS'] )
    if result_tuple[0] == 0:
      print( "Successfully subscribed to the control topic: \"" + configuration['controlTopic'] + "\"" )

    client.loop_start()
    while True:
      if not client.is_connected():
        client.reconnect()
      current_time = epoch_time()
      interval = configuration['publishInterval']
      if current_time - interval > last_publish:
        temperature, relative_humidity = read_sht()
        cpu_temperature = gz.CPUTemperature().temperature
        publish_results( temperature, relative_humidity, cpu_temperature )
        last_publish = epoch_time()

  except KeyboardInterrupt:
    print( "\nKeyboard interrupt detected, exiting...\n" )
    client.loop_stop()
    client.unsubscribe( configuration['controlTopic'] )
    client.disconnect()
  except KeyError as key_error:
    log_string = "Python dictionary key error: %s" % str( key_error )
    print( log_string )
  except ConnectionRefusedError as connection_error:
    print( "Connection error: " + str( connection_error ) )


if __name__ == "__main__":
  main( sys.argv )

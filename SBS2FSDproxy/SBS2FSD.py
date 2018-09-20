"""
Converts ADS-B and MLAT position and velocity data from a provider like ADSBX
to conform to the SBS protocol, which can then be streamed to an FSD proxy for
display in Euroscope, the ICAO hex address is also linked to aircraft model and
registration. You can modify Latitude, longitude and distance variables to suit
your needs its currently centred around NZ domestic FIR. Press disconnect in the FSD
proxy first to save data before closing the python program.

Author: Callum Riddington
Python: 3.7
Requirements: pip3 install requests
"""
import os
import socket
import sys
import time
import requests

LATITUDE, LONGITUDE, DISTANCE = -41.627144, 173.853380, 2100
REQUEST_ALL = True
PROVIDER = 'https://public-api.adsbexchange.com/VirtualRadar/AircraftList.json'
if not REQUEST_ALL:
    PROVIDER += ('?lat={}&lng={}&fDstL=0&fDstU={}'.format(LATITUDE, LONGITUDE, DISTANCE))

os.chdir(sys.path[0])
with open('icao24.txt', 'r') as icao_file:
    icao = set([l for l in icao_file])
icao_file.close()
with open('aircrafts.txt', 'r') as aircrafts_file:
    aircrafts = set([l for l in aircrafts_file])
aircrafts_file.close()

SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
SERVER_ADDRESS = ('127.0.0.1', 30003)
print('Connect FSD to {} on port {}.'.format(*SERVER_ADDRESS))
SOCK.bind(SERVER_ADDRESS)
SOCK.listen(1)

def save_data():
    print('Saving data...')
    icao_dict = {k:v for k, v in (x.split('\t') for x in icao)}
    with open('icao24.txt', 'w') as icao_file:
        for k, v in sorted(icao_dict.items()):
            icao_file.write('{}\t{}'.format(k, v))
    icao_file.close()
    aircrafts_dict = {k:v for k, v in (x.split('\t\t') for x in aircrafts)}
    with open('aircrafts.txt', 'w') as aircrafts_file:
        for k, v in sorted(aircrafts_dict.items()):
            aircrafts_file.write('{}\t\t{}'.format(k, v))
    aircrafts_file.close()

def convert_to_sbs(plane):
    sbs = 'MSG,3,{session_id},{aircraft_id},{hex_ident},{flight_id},,,,,\
    {callsign},{altitude},{ground_speed},{track},{Lat},{Long},{vertical_rate},{squawk},0,0,0,0\n'
    return(sbs.format(session_id=plane.get('Id', ""), aircraft_id=plane.get('Id', ""),
                      hex_ident=plane.get('Icao', ""), flight_id=plane.get('Id', ""),
                      callsign=plane.get('Call', ""), altitude=plane.get('Alt', ""),
                      ground_speed=plane.get('Spd', ""), track=plane.get('Trak', ""),
                      Lat=plane.get('Lat', ""), Long=plane.get('Long', ""),
                      vertical_rate=plane.get('Vsi', ""), squawk=plane.get('Sqk', "")))

while 1:
    print('Waiting for FSD proxy.')
    connection, client_address = SOCK.accept()
    print('Connection from FSD proxy', connection, client_address)
    try:
        while 1:
            data = requests.get(PROVIDER)
            if data.ok:
                data = data.json()
                for plane in data['acList']:
                    connection.sendall(str.encode(convert_to_sbs(plane)))
                    plane_Icao, plane_reg, = plane.get('Icao', ""), plane.get('Reg', ""),
                    if plane_Icao and plane_reg:
                        if not '{}\t{}\n'.format(plane_Icao, plane_reg) in icao:
                            icao.add('{}\t{}\n'.format(plane_Icao, plane_reg))
                    plane_type = plane.get('Type', "")
                    if plane_reg and plane_type:
                        if not '{}\t\t{}\n'.format(plane_reg, plane_type) in aircrafts:
                            aircrafts.add('{}\t\t{}\n'.format(plane_reg, plane_type))
                print('Total Aircraft Requested >>>', len(data['acList']))
                time.sleep(4)
            else:
                print('Got Bad Response\n', data, '\n')
                time.sleep(10)
    except ConnectionAbortedError:
        print("The FSD proxy closed the connection, reconnect to continue.")
    finally:
        save_data()
        connection.close()

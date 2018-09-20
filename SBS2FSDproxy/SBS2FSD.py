"""
Converts ADS-B and MLAT position and velocity data from a provider like ADSBX
to conform to the SBS protocol, which can then be streamed to an FSD proxy for
display in Euroscope, the ICAO hex address is also linked to aircraft model and
registration. You can modify latitude, longitude and distance variables to suit
your needs its currently centred around NZ domestic FIR. Press disconnect in the FSD
proxy first to save data before closing the python program.

Author: Callum Riddington
Python: 3.7
Requirements: pip3 install requests
"""
import os
import json
import socket
import sys
import time
import requests
latitude = -41.627144
longitude = 173.853380
distance = 2100

with open('icao24.txt', 'r') as icaofile:
    icao = set([l for l in icaofile])
icaofile.close()
with open('aircrafts.txt', 'r') as aircraftsfile:
    aircrafts = set([l for l in aircraftsfile])
aircraftsfile.close()
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('127.0.0.1', 30003)
print('Connect FSD to {} on port {}.'.format(*server_address))
sock.bind(server_address)
sock.listen(1)


def save_data():
    print('Saving data...')
    icao_dict = {k:v for k,v in (x.split('\t') for x in icao)}
    with open('icao24.txt', 'w') as icaofile:
        for k,v in sorted(icao_dict.items()):
            icaofile.write('{}\t{}'.format(k, v))
    icaofile.close()
    aircrafts_dict = {k:v for k,v in (x.split('\t\t') for x in aircrafts)}
    with open('aircrafts.txt', 'w') as aircraftsfile:
        for k,v in sorted(aircrafts_dict.items()):
            aircraftsfile.write('{}\t\t{}'.format(k, v))
    aircraftsfile.close()

while 1:
    print('Waiting for FSD proxy.')
    connection, client_address = sock.accept()
    try:
        print('Connection from FSD proxy', connection, client_address)
        while 1:
            data = requests.get('https://public-api.adsbexchange.com/VirtualRadar/AircraftList.json?lat={}&lng={}&fDstL=0&fDstU={}'.format(latitude, longitude, distance))
            if data.ok:
                data = json.loads(data.text)
                for plane in data['acList']:
                    sbs = 'MSG,3,{session_id},{aircraft_id},{hex_ident},{flight_id},,,,,{callsign},{altitude},{ground_speed},{track},{Lat},{Long},{vertical_rate},{squawk},0,0,0,0\n'
                    sbs = sbs.format(session_id=plane.get('Id', ""), aircraft_id=plane.get('Id', ""), hex_ident=plane.get('Icao', ""), flight_id=plane.get('Id', ""),
                                     callsign=plane.get('Call', ""), altitude=plane.get('Alt', ""), ground_speed=plane.get('Spd', ""), track=plane.get('Trak', ""),
                                     Lat=plane.get('Lat', ""), Long=plane.get('Long', ""), vertical_rate=plane.get('Vsi', ""), squawk=plane.get('Sqk', ""))
                    connection.sendall(str.encode(sbs))
                    planeIcao, planeReg = plane.get('Icao', ""), plane.get('Reg', "")
                    if planeIcao and planeReg:
                        if not '{}\t{}\n'.format(planeIcao, planeReg) in icao:
                            print('Adding ICAO Address','{}\t{}'.format(planeIcao, planeReg))
                            icao.add('{}\t{}\n'.format(planeIcao, planeReg))
                    planeType = plane.get('Type', "")
                    if planeReg and planeType:
                        if not '{}\t\t{}\n'.format(planeReg, planeType) in aircrafts:
                            print('Adding Aircraft', '{}\t{}\t{}\t{}'.format(planeReg, planeType, plane.get('Mdl', ""), plane.get('Year', "")))
                            aircrafts.add('{}\t\t{}\n'.format(planeReg, planeType))
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

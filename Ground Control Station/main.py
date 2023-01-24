#!py -3.6

import asyncio
import threading
import websockets
import json
# All functions related to drone movement are in droneActions,
# including drone state as STATUS
from droneActions import *
# STATUS
# -2 -> RADIUS BREACH - Geofence radius breach
# -1 -> ALTITUDE BREACH - Geofence altitude breach
# 0  -> BUSY  - work-in-progress state : will reject all further commands when BUSY
# 1  -> READY - initial state : will accept incoming commands, not armed/not tookoff
# 2  -> DONE  - drone positioned : will accept incoming commands, tookoff

url = 'wss://32226u87yi.execute-api.eu-west-1.amazonaws.com/test_experiment'


# Init and connect to a drone
# either using options provided on cli
# or default simulator if not provided
import argparse  
parser = argparse.ArgumentParser(description='Demonstrates basic mission operations.')
parser.add_argument('--connect', 
                   help="vehicle connection target string. If not specified, SITL automatically started and used.")
args = parser.parse_args()
cstring = args.connect
print(f'{cstring} provided as connection string')
findAndConnect(cstring)
from dk import vehicle

print(f'number of Active threads ==> {threading.active_count()}')

async def conn():
    print(f"connecting to {url}")
    async with websockets.connect(url) as ws:
        print("CONNECTED to WSS")
        while True:
            try:
                # Listening for commands from Alexa
                resp = await ws.recv()
                print(f"🔽 {resp}")
                
                # get real-time live status
                STATUS = getStatus()
                
                # parse request
                body = json.loads(resp)['body']
                type = body['type']

                # Check if target is within geofence for FLY commands
                if type=='fly' and STATUS!=0:
                    dir, dist = body['dir'], body.get('dist')
                    if dist is None: dist = 2
                    # IF geofence breach, modify status accordingly
                    BREACH = checkBreach(dir,float(dist))
                    if(BREACH):
                        STATUS = BREACH
                
                    
                # Sending status and other necessary details from GCS to Alexa
                doc = {"action": "broadcast", "STATUS": STATUS}
                if(type in ['status','launch','takeoff']): doc['mode'] = vehicle.mode.name
                if(type=='status' and STATUS>0):
                    doc['homeDist'] = calcDistToHome(vehicle)
                await ws.send(json.dumps(doc))
                print(f"🔼 {doc}")
                
                # Executing command received from alexa
                # only if drone is in ready(1)/done(2) state and not busy(0)
                if STATUS<=0 or type in ['status', 'launch']: continue
                thread = None
                if(type == 'takeoff' and STATUS==1):
                    thread = threading.Thread(target=arm_and_elevate)
                elif(type == 'rtl' and STATUS==2):
                    thread = threading.Thread(target=returnToLaunch)
                elif(type == 'fly' and STATUS==2):
                    dist = float(dist)
                    if dir in ['higher','lower']:
                        thread = threading.Thread(target=setAltitude, args=[dir,dist])
                    else:
                        thread = threading.Thread(target=moveDrone, args=[dir, dist])
                else: continue
                thread.start()

                print(f'Active Threads ==> {threading.active_count()}')


            except Exception as E:
                print("error ==>> "+str(E))
                # reconnect on connection timeouts/ unexpected disconnections
                print('Reconnecting to wss')
                ws = await websockets.connect(url)
                print('RECONNECTED to WSS')


async def main(loop):
    print("Starting GCS..")
    task = loop.create_task(conn())
    await task

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))

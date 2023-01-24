#!py -3.6

import math
import time
from pymavlink import mavutil
# Import DroneKit-Python
from dronekit import connect, VehicleMode, LocationGlobal, LocationGlobalRelative, Command

vehicle = None
home = None
fence = None

# In case running in a simulator, start sim first
# returns simulator obj
def start_sim():
    print("Starting dronekit-sitl simulator (SITL)")
    import dronekit_sitl
    return dronekit_sitl.start_default()


# Connect to the Drone, times out if not connected in 15 seconds
def connectToDrone(conn_str='/dev/ttyUSB0'):
    print("Connecting to Drone on: %s" % (conn_str,))
    try:
        global vehicle
        vehicle = connect(conn_str, wait_ready=False, baud=57600)
        # Get Vehicle Home location - will be `None` until first set by autopilot
        while not vehicle.home_location:
            cmds = vehicle.commands
            cmds.download()
            cmds.wait_ready()
            if not vehicle.home_location:
                print(" Waiting for home location ...")
        # We have a home location. store it as home
        global home
        home = vehicle.home_location
        print(f'SET HOME ->> {str(home)}')
    except Exception as E:
        print("Error connecting to drone -> "+str(E))


def get_distance_metres(aLocation1, aLocation2):
    """
    Returns the ground distance in metres between two
    LocationGlobal objects.
    This method is an approximation, and will not be accurate over
    large distances and close to the
    earth's poles. It comes from the ArduPilot test code:
    https://github.com/diydrones/ardupilot/blob/master/Tools/autotest/com
    mon.py
    """
    dlat = aLocation2.lat - aLocation1.lat
    dlong = aLocation2.lon - aLocation1.lon
    return math.sqrt((dlat*dlat) + (dlong*dlong)) * 1.113195e5


def get_location_metres(original_location, dNorth, dEast):
    """
    Returns a LocationGlobal object containing the
    latitude/longitude `dNorth` and `dEast` metres from the
    specified `original_location`. The returned LocationGlobal has
    the same `alt` value
    as `original_location`.
    The function is useful when you want to move the vehicle around
    specifying locations relative to
    the current vehicle position.
    The algorithm is relatively accurate over small distances (10m
    within 1km) except close to the poles.
    For more information see:
    http://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters
    """
    earth_radius = 6378137.0 #Radius of "spherical" earth
    #Coordinate offsets in radians
    dLat = dNorth/earth_radius
    dLon = dEast/(earth_radius*math.cos(math.pi*original_location.lat/180))
    #New position in decimal degrees
    newlat = original_location.lat + (dLat * 180/math.pi)
    newlon = original_location.lon + (dLon * 180/math.pi)
    if type(original_location) is LocationGlobal:
        targetlocation=LocationGlobal(newlat,newlon,original_location.alt)
    elif type(original_location) is LocationGlobalRelative:
        targetlocation=LocationGlobalRelative(newlat,newlon,original_location.alt)
    else: 
        raise Exception("Invalid Location object passed")
    return targetlocation


def get_altitude_metres(curr,target):
    # curr and target are locations of drone and final goal respectively
    return abs(target.alt - curr.alt)


class FENCE:
    
    ON = True # Enabled by default

    # Draws a imaginary CYLINDRICAL fence
    def __init__(self,rad=30,alt=15):
        self.RAD = rad # MAX FENCE RADIUS
        self.ALT = alt # MAX FENCE ALTITUDE
    
    # Modifies fence
    def setFence(self, rad, alt):
        self.RAD = rad
        self.ALT = alt
    
    # pass target location as param
    def chkBreach(self, dir, dist):
        # Returns the following
        # 0 - No breach, within fence.
        # 1 - Fence altitude breach
        # 2 - Fence radius breach
        loc = vehicle.location.global_relative_frame # Current location
        
        if dir in ['higher','lower']:
            newAlt = loc.alt + dist
            if newAlt > self.ALT or newAlt < 1:
                return 1
            else: return 0

        dNorth,dEast=0,0
        if dir=='west':
            dEast = -dist
        elif dir=='east':
            dEast = dist
        elif dir=='north':
            dNorth = dist
        elif dir=='south':
            dNorth = -dist
        newLoc = get_location_metres(loc, dNorth, dEast)

        if get_distance_metres(newLoc, home) > self.RAD:
            return 2

        return 0
    
    # enables and disables geofence
    def switch(self, bool=True):
        self.ON = bool


# Instantiate fence
fence = FENCE()


def arm_and_takeoff(aTargetAltitude):
    """
    Arms vehicle and fly to aTargetAltitude.
    """
    print("Basic pre-arm checks")
    # Don't try to arm until autopilot is ready
    while not vehicle.is_armable:
        print (" Waiting for vehicle to initialise...")
        time.sleep(1)

    print ("Arming motors")
    # Copter should arm in GUIDED mode
    vehicle.mode    = VehicleMode("GUIDED")
    vehicle.armed   = True

    # Confirm vehicle armed before attempting to take off
    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(2)

    print ("Taking off!")
    vehicle.simple_takeoff(aTargetAltitude) # Take off to target altitude
    
    # Wait until the vehicle reaches a safe height before processing the goto (otherwise the command
    #  after Vehicle.simple_takeoff will execute immediately).
    while True:
        print(" Altitude: ", vehicle.location.global_relative_frame.alt)
        #Break and return from function just below target altitude.
        if vehicle.location.global_relative_frame.alt>=aTargetAltitude*0.95:
            print("Reached target altitude")
            break
        time.sleep(1)


def move(dir,dist):
    # Return if not in guided mode
    if vehicle.mode.name!="GUIDED": return

    print(f"POSITIONING DRONE {dir} {'@'+str(dist)+'m' if dist else ''}...")
    
    dNorth,dEast,head=0,0,vehicle.heading
    if dir=='west':
        dEast = -dist
    elif dir=='east':
        dEast = dist
    elif dir=='north':
        dNorth = dist
    elif dir=='south':
        dNorth = -dist
    else: return

    # NED coords conversion
    currentLocation = vehicle.location.global_relative_frame
    targetLocation = get_location_metres(currentLocation, dNorth,dEast)
    # targetDistance = get_distance_metres(currentLocation,targetLocation)
    vehicle.simple_goto(targetLocation)

    #Stop action if we are no longer in guided mode.
    while vehicle.mode.name=="GUIDED":
        remainingDistance=get_distance_metres(vehicle.location.global_relative_frame, targetLocation)
        print("Distance to target: ", remainingDistance)
        
        #Just near target,in case of undershoot.
        if remainingDistance<=1:
            time.sleep(1)
            print("Reached target")
            break;
        
        time.sleep(2)


def changeAltitude(newAlt):
    print(f"SETTING ELEVATION to {newAlt}")
    # Sets elevation of drone above if givena alt is positive
    # else below if negative
    loc = vehicle.location.global_relative_frame # current position
    alt = loc.alt + newAlt
    # To avoid crashing
    if(alt<0):
        return

    newLoc = LocationGlobalRelative(loc.lat,loc.lon,alt)
    vehicle.simple_goto(newLoc)

    #Stop action if we are no longer in guided mode.
    while vehicle.mode.name=="GUIDED": 
        remainingAlt=get_altitude_metres(vehicle.location.global_relative_frame, newLoc)
        print("Remaining dist to elevation: ", remainingAlt)
        
        #Just below target,in case of undershoot.
        if remainingAlt<=alt*0.2:
            time.sleep(1)
            print("Reached target")
            break;
        time.sleep(2)


def rtl():
    if vehicle.armed:
        vehicle.parameters['RTL_ALT'] = 0 # maintain current altitude while returning
        vehicle.mode = VehicleMode("RTL")
        print("Returning to Launch...")
        
        while vehicle.armed:
            time.sleep(1)
        print("LANDED")


# EXTRAS
def circle():
    """
    Sketching circular coordinates around the drone,
    and start a CIRCLE mission in AUTO mode with calculated coordinates
    """
    radius = 0.0001
    lat = vehicle.location.global_relative_frame.lat
    lon = vehicle.location.global_relative_frame.lon
    alt = vehicle.location.global_relative_frame.alt

    loops = 1 # do n loops
    points = 30 # total waypoints per circle
    wps = 30 * loops # total number of waypoints for all circle(s) we draw
    coords = []
    for i in range(0, wps):
        degrees = (i/points)*360
        radians = (math.pi/180)*degrees
        x = lat + radius * math.cos(radians)
        y = lon + radius * math.sin(radians)
        coords.append((x,y))

    cmds = vehicle.commands
    cmds.clear()

    for lat,lon in coords:
        # point = LocationGlobalRelative(lat,lon,alt)
        cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, lat, lon, alt))

    cmds.upload()

    vehicle.mode = VehicleMode("AUTO")
    time.sleep(1)

    while True:
        nextwaypoint=vehicle.commands.next
        if(nextwaypoint==wps): break
        time.sleep(1)
    print("Completed CIRCLE mission")

    vehicle.mode = VehicleMode("GUIDED")
    time.sleep(1)
    

# Testing on DroneKit-SITL
if __name__=='__main__':

    sitl = start_sim()

    # Connecting to dronepilot-sitl in this case
    connectToDrone(sitl.connection_string())
    # connectToDrone('tcp:127.0.0.1:5763')

    #Create a message listener for all messages.
    # @vehicle.on_message('*')
    # def listener(self, name, message):
    #     print ('message: %s' % message)

    print("START")
    
    msg = vehicle.message_factory.command_long_encode(
    0, 0,    # target_system, target_component
    mavutil.mavlink.MAV_CMD_DO_FENCE_ENABLE, #command
    0, #confirmation
    vehicle.heading,    # param 1, yaw in degrees
    0,          # param 2, yaw speed deg/s
    1,          # param 3, direction -1 ccw, 1 cw
    0, # param 4, relative offset 1, absolute angle 0
    0, 0, 0)    # param 5 ~ 7 not used
    # send command to vehicle
    vehicle.send_mavlink(msg)

    arm_and_takeoff(5)
    
    print(vehicle.location.local_frame,vehicle.heading)

    move("forward",5)
    print(vehicle.location.global_relative_frame,vehicle.heading)

    move('left',5)
    print(vehicle.location.local_frame,vehicle.heading)

    changeAltitude(5)
    print(vehicle.location.local_frame,vehicle.heading)

    move('backward',5)
    print(vehicle.location.local_frame,vehicle.heading)

    changeAltitude(-5)
    print(vehicle.location.local_frame,vehicle.heading)

    move('right',5)
    print(vehicle.location.local_frame,vehicle.heading)

    rtl()
    print(vehicle.location.local_frame,vehicle.heading)


    print("END")

    # Close vehicle object before exiting script
    vehicle.close()

    # Shut down simulator
    sitl.stop()
    print("Completed")

# # Get some vehicle attributes (state)
# print("Get some vehicle attribute values:")
# print(" GPS: %s" % vehicle.gps_0)
# print(" Battery: %s" % vehicle.battery)
# print(" Last Heartbeat: %s" % vehicle.last_heartbeat)
# print(" Is Armable?: %s" % vehicle.is_armable)
# print(" System status: %s" % vehicle.system_status.state)
# print(" Mode: %s" % vehicle.mode.name)    # settable

# # vehicle is an instance of the Vehicle class
# # Vehicle state and settings
# print ("Autopilot Firmware version: %s" % vehicle.version)
# print ("Autopilot capabilities (supports ftp): %s" % vehicle.capabilities.ftp)
# print ("Global Location: %s" % vehicle.location.global_frame)
# print ("Global Location (relative altitude): %s" % vehicle.location.global_relative_frame)
# print ("Local Location: %s" % vehicle.location.local_frame)    #NED
# print ("Attitude: %s" % vehicle.attitude)
# print ("Velocity: %s" % vehicle.velocity)
# print ("GPS: %s" % vehicle.gps_0)
# print ("Groundspeed: %s" % vehicle.groundspeed)
# print ("Airspeed: %s" % vehicle.airspeed)
# print ("Gimbal status: %s" % vehicle.gimbal)
# print ("Battery: %s" % vehicle.battery)
# print ("EKF OK?: %s" % vehicle.ekf_ok)
# print ("Last Heartbeat: %s" % vehicle.last_heartbeat)
# print ("Rangefinder: %s" % vehicle.rangefinder)
# print ("Rangefinder distance: %s" % vehicle.rangefinder.distance)
# print ("Rangefinder voltage: %s" % vehicle.rangefinder.voltage)
# print ("Heading: %s" % vehicle.heading)
# print ("Is Armable?: %s" % vehicle.is_armable)
# print ("System status: %s" % vehicle.system_status.state)
# print ("Mode: %s" % vehicle.mode.name)    # settable
# print ("Armed: %s" % vehicle.armed)    # settable
from dk import *
# STATUS
# 0 -> BUSY  - work-in-progress state : will reject all further commands when BUSY
# 1 -> READY - initial state : will accept incoming commands
# 2 -> DONE  - drone positioned : will accept incoming commands
# Initial status be 1
STATUS = 1

# Initialise and connect to drone
def findAndConnect(cstring=None):
    # If conn_str provided as cli argument...Maybe the real drone, Use it
    if cstring is not None : 
        conn_str = cstring
    else:
        ########### Starts dronekit-sitl sim 
        # sitl = start_sim()
        # conn_str = sitl.connection_string() # sitl generated cstring
        ############## else use a conn string of already running sim
        conn_str = "tcp:127.0.0.1:5763"
    connectToDrone(conn_str)
    from dk import vehicle
    if vehicle.armed: 
        global STATUS
        STATUS = 2


def checkBreach(dir, dist):
    return -fence.chkBreach(dir,dist)


def arm_and_elevate():
    global STATUS
    STATUS = 0
    arm_and_takeoff(3)
    STATUS = 2


def setAltitude(dir,alt):
    if not alt: alt = 2
    global STATUS
    STATUS = 0
    if dir in ['lower']:
        alt = -1*alt
    changeAltitude(float(alt))
    STATUS = 2


def moveDrone(dir, dist):
    if not dist: dist = 2
    global STATUS
    STATUS = 0
    move(dir,float(dist))
    STATUS = 2


def orbit():
    global STATUS
    STATUS = 0
    circle()
    STATUS = 2

def returnToLaunch():
    global STATUS
    STATUS = 0
    rtl()
    STATUS = 1


def getMode():
    return vehicle.mode.name

def getStatus():
    return STATUS

def calcDistToHome(vehicle):
    rad = get_distance_metres(vehicle.home_location, vehicle.location.global_relative_frame)
    alt = vehicle.location.global_relative_frame.alt
    dist = math.sqrt(rad**2 + alt**2) # third side of a triangle
    return round(dist)

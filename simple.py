"""
simple.py - an unglamorous interactive script for moving the arm and setting its speed

ex on stdin:
m 1 8 0
^- move to x1 y8 z0

s 6000
^- set speed to 6000

'OK' or 'BAD' on stdout when command executed

Control-C to exit
"""

from robotarm.al5x import Al5x, AL5D
from robotarm.controllers import Ssc32
import sys

# these settings are for the macOS Virtual COM port driver
# http://www.ftdichip.com/Drivers/VCP.htm
s = Ssc32('/dev/tty.usbserial-AH05FPDM', baud=9600)

s.trim(2, 0.025)
s.trim(3, -0.025)

r = Al5x(AL5D, 
    servo_controller=s,
    parked_state=dict(pos=[0, 6, -1], gripper_angle=180.0, grip=0.7, wrist_rotate=180.0),
    avg_speed=3000)

def ok():
    print 'OK'
    sys.stdout.flush()

def bad():
    print 'BAD'
    sys.stdout.flush()

while True:

    try:
        line = raw_input()
        cmd = line[:1]

        if cmd == 'm':
            coords = line[1:].split()
            if len(coords) == 3:
                x,y,z = map(float, coords)
                r.move({'pos':[x,y,z]})
                ok()
            else:
                bad()

        elif cmd == 's':
            speed = int(line[1:])
            r.avg_speed = speed
            ok()

        else:
            bad()

    except KeyboardInterrupt:
        exit(0)
    except:
        bad()

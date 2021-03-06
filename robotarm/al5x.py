from vector import Vector, rotate, crossproduct, X, Y, Z, angle
from math import pi, radians, sin, asin, cos, acos, sqrt
from controllers import NullServo
from time import time, sleep


# Robot arm beam vectors:
# base to elbow, elbo to wrist, wrist to gripper_center
# LW: with light-weight wrist rotate
# HD: with heavy-duty wrist rotate
AL5A = ([0.0, 0.0, 3.75],
        [0.0, 4.25, 0.0],
        [0.0, 3.0, 0.0])
AL5A_LW = ([0.0, 0.0, 3.75],
           [0.0, 4.25, 0.0],
           [0.0, 4.13, 0.0])
AL5A_HD = ([0.0, 0.0, 3.75],
           [0.0, 4.25, 0.0],
           [0.0, 3.5,  0.0])
AL5B = ([0.0, 0.0, 4.75],
        [0.0, 5.00, 0.0],
        [0.0, 3.0,  0.0])
AL5B_LW = ([0.0, 0.0, 4.75],
           [0.0, 5.00, 0.0],
           [0.0, 4.13, 0.0])
AL5B_HD = ([0.0, 0.0, 4.75],
           [0.0, 5.00, 0.0],
           [0.0, 3.5,  0.0])
AL5C = ([0.0, 0.0, 6.13],
        [0.0, 6.13, 0.0],
        [0.0, 3.0,  0.0])
AL5C_LW = ([0.0, 0.0, 6.13],
           [0.0, 6.13, 0.0],
           [0.0, 4.13, 0.0])
AL5C_HD = ([0.0, 0.0, 6.13],
           [0.0, 6.13, 0.0],
           [0.0, 3.5,  0.0])
AL5D = ([0.0, 0.0, 5.75],
        [0.0, 7.38, 0.0],
        [0.0, 3.0,  0.0])
AL5D_LW = ([0.0, 0.0, 5.75],
           [0.0, 7.38, 0.0],
           [0.0, 4.13, 0.0])
AL5D_HD = ([0.0, 0.0, 5.75],
           [0.0, 7.38, 0.0],
           [0.0, 3.5,  0.0])

SERVO_MAP = {
        'base': 0,
        'shoulder': 1,
        'elbow': 2,
        'wrist': 3,
        'grip': 4,
        'wrist_rotate': 5,
        }


# hack for python 2.5
sign = lambda x: +(x > 0) or -(x < 0)


def trisss(abc):
    """Calculate the angles of a triangle given 3 sides [a,b,c]"""
    ABC = [0, 0, 0]  # angles
    # find the biggest side/angle to avoid obtuse errors
    l = 0  # index of the longest side
    for i in range(3):
        abc[i] = float(abc[i])  # don't do int division
        if abc[i] > abc[l]:
            l = i
    ABC[l] = acos(  # cosine rule
        (abc[l - 2] ** 2 + abc[l - 1] ** 2 - abc[l] ** 2)
         / (2 * abc[l - 2] * abc[l - 1]))
    ABC[l - 1] = asin(abc[l - 1] * sin(ABC[l]) / abc[l])  # sine rule
    ABC[l - 2] = pi - ABC[l - 1] - ABC[l]
    return ABC


def rad2float(rad):
    """Convert radians to a float between -1 and +1 for servo control"""
    return rad / (pi / 2) - 1


def zip_dicts(lst):
    c = dict()
    for i in lst:
        c.update(i)
    return c


class Al5x(object):
    """Represents an AL5x robot arm from Lynxmotion

    The state of the arm is represented with by a dict with these keys:

        pos: the gripper position in 3-dimensions
        gripper_angle: the grippers angle from horizon in degrees
        grip: the grippers distance between fingers
        wrist_rotate: the angle from center in degrees

    Initiation and usage:

        arm  = Al5x(AL5D, servo_controller=None,
                    parked_state=dict(pos=(0,8,3)), dt=0.010)
        a.move(dict(pos=(-4,6,6), grip_angle=15.0, grip=0.0))
        a.move(dict(pos=(4,4,10), grip_angle=0.0, grip=0.5))
        a.park()

    """
    def __init__(self, beams, servo_controller=None,
                 parked_state=None, servo_map=None, avg_speed=15.0, dt=0.007):
        self.beams = dict(zip(['arm', 'forearm', 'gripper'],
                              map(Vector, beams)))
        if servo_controller is not None:
            self.sc = servo_controller
        else:
            self.sc = NullServo()
        self.current_state = dict()

        # set up parked_state
        p = sum(self.beams.values())
        ga = 0.0
        g = 0.0
        wr = 0.0
        self.parked_state = dict(pos=p, grip_angle=ga,
                                 grip=g, wrist_rotate=wr)

        if parked_state is not None:
            self.parked_state.update(parked_state)

        if servo_map is not None:
            self.servo_map = servo_map
        else:
            self.servo_map = SERVO_MAP

        self.avg_speed = avg_speed
        self.dt = dt

        self.immediate_move(self.parked_state)

    def get_state(self):
        """Return current state"""
        return dict(self.current_state)

    def __zip_state(self, new_state):
        """Returns combined state of current_state and new_state"""
        state = dict(self.current_state)
        state.update(new_state)
        return state

    def immediate_move(self, new_state, time=0):
        """Move arm to new_state without interpolation

        This bypasses the straight-line and accelleration calculations and
        simply finds the servo positions for the new state and steps servos to
        it. This will cause a non-linear gripper movement.

        """
        state = self.__zip_state(new_state)
        servos = dict()
        servos.update(self.calc_pos(state['pos'], state['grip_angle']))
        servos.update(self.calc_grip(state['grip']))
        self.sc.servos(servos, time)
        self.current_state.update(state)

    def park(self):
        """Moves arm to parked state"""
        self.move(self.parked_state)

    def calc_grip(self, val):
        """Calculate grip servo value, returns dict(servo)"""
        return dict({self.servo_map['grip']: val})

    def set_grip(self, val):
        self.sc.servos(self.calc_grip(val))
        self.current_state.update(dict(grip=val))

    def calc_pos(self, pos, grip_angle=0.0):
        """Calculate servo values for arm position, returns dict(servos)"""
        position = Vector(pos)
        grip_angle = float(grip_angle)
        # unit vector translation of position on xy plane
        xy_unit = Vector(position.x, position.y, 0).unit
        # get a grip... vector
        gripper = (xy_unit * self.beams['gripper'].mag)
        # ... and rotate to angle specified
        gripper = rotate(gripper, crossproduct(gripper, Z),
                                       radians(grip_angle))
        # Subtract to get Sub Arm (sum of vectors 0 and 1)
        composite = position - gripper
        # Calculate sub-vectors
        # Get angle betweens
        try:
            arm2compangle = trisss([
                    self.beams['arm'].mag,
                    self.beams['forearm'].mag,
                    composite.mag,
                    ])[1]
        except ValueError, m:
            raise ValueError("Position is beyond range of motion")
        # get arm vector
        arm = composite.unit * self.beams['arm'].mag
        # ... and rotate to calculated angle
        arm = rotate(arm, crossproduct(arm, Z), arm2compangle)
        # the easy part...
        forearm = composite - arm
        # set servo values
        servo_values = dict()
        servo_values[self.servo_map['base']] = rad2float(angle(X, xy_unit))
        servo_values[self.servo_map['shoulder']] = rad2float(
                angle(xy_unit, arm))
        servo_values[self.servo_map['elbow']] = rad2float(angle(arm, forearm))
        servo_values[self.servo_map['wrist']] = rad2float(pi / 2 - angle(
                forearm, gripper) * sign(forearm.unit.z - gripper.unit.z))
        return servo_values

    def genslices(self, dist):
        """Returns generator object and number of slices for given distance

        Slices up the given distance according to cosine, allowing for
        acceleration into and out of the move.

        """
        if dist == 0:
            return iter([None]), 0

        time = float(dist) / self.avg_speed
        ## Fix problem with fast short moves and slow long ones
        time = (time + sqrt(time * 2)) / 2
        time = 2 * sqrt(time) / 3

        num_slices = int(time / self.dt)
        if num_slices == 0:
            #raise ValueError, "dumbass too short"
            return iter([0]), 1
        else:
            return (dist * (1 - cos(pi * float(i) / (num_slices - 1))) / 2
                     for i in range(num_slices)), num_slices

    def move(self, new_state):
        """Moves arm from current state to new state"""
        start_state = self.current_state
        end_state = self.__zip_state(new_state)
        # Position setup
        start_pos = Vector(start_state['pos'])
        end_pos = Vector(end_state['pos'])
        move = end_pos - start_pos
        # Grip angle setup
        start_ga = self.current_state['grip_angle']
        end_ga = end_state['grip_angle']
        delta_ga = end_ga - start_ga
        # Wrist rotate setup
        #start_wr = self.current_state['wrist_rotate']
        #end_wr = end_state['wrist_rotate']
        #delta_wr = end_wr - start_wr
        # Grip setup
        start_g = self.current_state['grip']
        end_g = end_state['grip']
        delta_g = end_g - start_g

        # make positions generator
        g, slices = self.genslices(move.mag)
        move_gen = ((move.unit * d + start_pos)
                     for d in g)

        # make grip angles generator
        ga_gen = (float(s) / (slices - 1) * delta_ga + start_ga
                   for s in range(slices))

        # make wrist rotate generator
        #wr_gen = ( float(s)/(slices-1)*delta_wr + start_wr
        #           for s in range(slices) )

        # make grip val generator
        g_gen = (float(s) / (slices - 1) * delta_g + start_g
                  for s in range(slices))

        # Set Servo values
        the_list = ((self.calc_pos(move_gen.next(), ga_gen.next()),
                      self.calc_grip(g_gen.next()))
                     for x in range(slices))
        next_time = 0.0
        for i in the_list:
            while time() < next_time:
                sleep(0)
            next_time = time() + self.dt
            self.sc.servos(zip_dicts(i))
            self.current_state.update(new_state)

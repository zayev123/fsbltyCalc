from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Tank
from operator import attrgetter
# the jig will always move in the decided pattern. Its the crane that will shift around
# each crane will have a list.
# each element of that list will contain the tank it stops above.
# This list will be working on another list which will be the rack positions list
# that list will be working on the tanks list
# i need a function that tracks the posiion of the rack at any instant of time and then runs calculations on it
# so, there should be a function calling the time function and upon every 0.5 mins, it will rerun the calculations.
# but it should only run these calculations while it has dropped a rack in the tank, not while it is carrying the jig, 
# or picking the jig or dropping the jig
# there needs to be a record of what racks are where
# rack position and time left for rack in that position, a new model
# i need to update the racks list upon each turn

class RackTrack():
    def __init__(self, current_tank_unmber, remaining_tank_time):
        self.current_tank_unmber = current_tank_unmber
        self.remaining_tank_time = remaining_tank_time

class CraneTrack():
    def __init__(self, current_tank_unmber):
        self.tank_unmber = current_tank_unmber

class TankAutomatorView(APIView):

    def calculate_tank_shift_time(self, tank_a_number, tank_b_number):
        crossing_tank_qty = tank_b_number - tank_a_number
        time_for_crossing_mins = crossing_tank_qty * 0.05
        return abs(time_for_crossing_mins)

    rack_pick_time_mins = 0.07
    rack_drop_time_mins = 0.07
    racks = []
    tanks = Tank.objects.all()
    crane = CraneTrack(1)
    # the one added first will be the one most forward

    def find_next_tank(self, tank_a):
        myTanks = self.tanks
        tank_a_number = tank_a.tank_number
        i = 1
        while i < 8:
            tank_b_number = tank_a_number + i
            tank_b = myTanks.get(tank_number = tank_b_number)
            if tank_b.tank_type_number != tank_a.tank_type_number:
                break
        return tank_b

    def calc_rack_shift_time(self, tank_a):
        myTanks = self.tanks
        tank_a_number = tank_a.tank_number
        tank_b = self.find_next_tank(tank_a)
        total_time = self.calculate_tank_shift_time(tank_a.tank_number, tank_b.tank_number) + 2*self.rack_pick_time_mins + 2*self.rack_drop_time_mins
        return total_time

    def get_min_time_left_rack(self, racks):
        min_time_left_rack = min(racks,key=attrgetter('remaining_tank_time'))
        return min_time_left_rack


    def calculate_number_of_parallel_racks(self):
        myTanks = self.tanks
        tanks_list = list(myTanks)
        no_of_tanks = len(tanks_list)

        no_of_racks = len(self.racks)
        new_rack_index = no_of_racks
        self.racks[new_rack_index] = RackTrack(0, tanks_list[0].immersion_time_mins)

        myRacks = self.racks

        new_rack = myRacks[new_rack_index]
        current_tank = myTanks[0]

        total_rack_travel_time = 0.19

        while True:
            # in this while loop, check if it is crashing onto or restricting any other rack as it moves along the line.
            # if it is, the recursively return
            # is less
            mins_available_current_rack = new_rack.remaining_tank_time
            other_rack = self.get_min_time_left_rack(myRacks)
            other_tank = myTanks.get(tank_number = other_rack.current_tank_unmber)
            other_next_tank = self.find_next_tank(other_tank)
            mins_available_other_rack = other_rack.remaining_tank_time
            # first i need to check if getting to the tank will actually be at the right time or before the right time which is the finnish of the rack time
            time_to_get_to_other_tank = self.calculate_tank_shift_time(current_tank.tank_number, other_tank.tank_number)

            time_available_after_getting_to_other_tank_for_other_rack = mins_available_other_rack - time_to_get_to_other_tank
            # if even just getting to other tank without doing any shifting takes too long, then there is no need for further discussion
            # a smarter approach would be to check who has more available time 
            # this below is my base condition
            if time_available_after_getting_to_other_tank_for_other_rack < 0:
                return
            # the one below is fallacy
            time_available_after_getting_to_other_tank_for_current_rack = mins_available_current_rack - time_to_get_to_other_tank
            # should be an and here: And shifting current tank leaves time for other tank
            # after getting to??, no after shifting other tank, what will it acheive by just getting there
            time_left_after_shifting_other_rack_for_current_rack = time_available_after_getting_to_other_tank_for_current_rack - (time_available_after_getting_to_other_tank_for_other_rack + self.calc_rack_shift_time(other_tank) + self.calculate_tank_shift_time(other_next_tank.tank_number, current_tank.tank_number))
            if time_left_after_shifting_other_rack_for_current_rack < 0:
                # it should definetily shift the current rack first, then try
                # so, shift the current rack, and update the remaining times:
                time_taken_to_get_crane_to_current_tank = self.calculate_tank_shift_time(self.crane.tank_unmber, current_tank.tank_number)
                time_taken_to_shift_current_rack = time_taken_to_get_crane_to_current_tank + self.calc_rack_shift_time(current_tank)
                # first just check if the time for the least timed tank is not over run
                # I need to reinstate their initial conditions upon every failed return
                time_left_for_other_rack_after_shifting_current_rack = mins_available_other_rack - time_taken_to_shift_current_rack
                if time_left_for_other_rack_after_shifting_current_rack < 0:
                    return
                else:
                    self.crane.tank_unmber = current_tank.tank_number
                    for rack in self.racks:
                        rack.remaining_tank_time = rack.remaining_tank_time - time_taken_to_shift_current_rack
                pass
                # check then if shifting current tank first solves the problem, i.e both racks get enough time in this new position
                # so shift the tank, and go deeper in the recursive loop
                return
                # else if current rack has time, check if you can afford to shift the other rack
            else:
                # if it is more than zero, you have 2 options: you can still shift the current tank first if you want, or you can actually
                # go ahead with shifting the other tank first. If I choose A, and doesnt work out, I should come back at this point and choose B.
                # if B doesnt work out, then I should return from this point to the previous recurion.
                pass
            # so what then after shifting, lets say you do shift one, then, at one point you shift the other.
            # upon each shift of a rack, i will try to add a new rack to tank one. So, how will it deal with this new rack
            # it will then have to satisfy not one, but 2 racks.
            # but rn, its workking on the one that has the least time available. The process of adding a new rack will automatically reduce the least time,
            # due to travel to the first tank
            # i need to make a crane model aswell


            total_rack_travel_time = total_rack_travel_time + self.calc_rack_shift_time(current_tank)
            if current_tank.tank_number == no_of_tanks - 1:
                break
            current_tank = self.find_next_tank(current_tank)

        total_rack_travel_time = total_rack_travel_time + 0.19
        return total_rack_travel_time


    def post(self, request, *args, **kwargs):
        tanks = list(Tank.objects.all())
        number_of_cranes = 1
        e =self.ca
        pass
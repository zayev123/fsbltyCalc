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
    def __init__(self, tank_unmber, remaining_tank_time, rack_index):
        self.rack_index = rack_index
        self.tank_unmber = tank_unmber
        self.remaining_tank_time = remaining_tank_time

class CraneTrack():
    def __init__(self, tank_unmber):
        self.tank_unmber = tank_unmber

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


    def calculate_racks_and_cranes(self):
        myTanks = self.tanks
        tanks_list = list(myTanks)
        no_of_tanks = len(tanks_list)

        no_of_racks = len(self.racks)
        the_rack_index = no_of_racks
        self.racks[the_rack_index] = RackTrack(0, tanks_list[0].immersion_time_mins, 0)

        myRacks = self.racks

        current_rack = myRacks[the_rack_index]
        current_rack_index = current_rack.rack_index
        current_tank = myTanks[0]
        current_next_tank = self.find_next_tank(current_tank)

        total_rack_travel_time = 0.19

        mins_available_current_rack = current_rack.remaining_tank_time
        other_rack = self.get_min_time_left_rack(myRacks)
        other_rack_index = other_rack.rack_index
        other_tank = myTanks.get(tank_number = other_rack.tank_unmber)
        other_next_tank = self.find_next_tank(other_tank)

        mins_available_other_rack = other_rack.remaining_tank_time
        time_taken_to_get_crane_to_other_tank = self.calculate_tank_shift_time(self.crane.tank_unmber, other_tank.tank_number)
        time_available_for_other_rack_after_getting_crane_to_other_tank = mins_available_other_rack - time_taken_to_get_crane_to_other_tank
        
        if time_available_for_other_rack_after_getting_crane_to_other_tank < 0:
            return False

        time_available_for_current_rack_after_getting_to_other_tank = mins_available_current_rack - time_taken_to_get_crane_to_other_tank
        time_left_for_current_rack_after_shifting_other_rack = time_available_for_current_rack_after_getting_to_other_tank - (time_available_for_other_rack_after_getting_crane_to_other_tank + self.calc_rack_shift_time(other_tank) + self.calculate_tank_shift_time(other_next_tank.tank_number, current_tank.tank_number))

        time_taken_to_get_crane_to_current_tank = self.calculate_tank_shift_time(self.crane.tank_unmber, current_tank.tank_number)
        time_taken_to_shift_current_rack = time_taken_to_get_crane_to_current_tank + self.calc_rack_shift_time(current_tank)
        time_left_for_other_rack_after_shifting_current_rack = mins_available_other_rack - (time_taken_to_shift_current_rack + self.calculate_tank_shift_time(current_next_tank.tank_number, other_tank.tank_number))

        if time_left_for_current_rack_after_shifting_other_rack < 0:
            
            if time_left_for_other_rack_after_shifting_current_rack < 0:
                return False
            else: # shift current tank first
                self.crane.tank_unmber = current_tank.tank_number
                for rack in self.racks:
                    rack.remaining_tank_time = rack.remaining_tank_time - time_taken_to_shift_current_rack
                self.racks[current_rack_index].tank_unmber = current_next_tank.tank_number
                self.racks[current_rack_index].remaining_tank_time = current_next_tank.immersion_time_mins - self.rack_pick_time_mins
                result = self.calculate_racks_and_cranes()
                return result
        else:
            time_taken_to_shift_other_rack = time_taken_to_get_crane_to_other_tank + self.calc_rack_shift_time(other_tank)

            if time_left_for_other_rack_after_shifting_current_rack < 0:
                for rack in self.racks:
                    rack.remaining_tank_time = rack.remaining_tank_time - time_taken_to_shift_other_rack
                self.racks[other_rack_index].tank_unmber = other_next_tank.tank_number
                self.racks[other_rack_index].remaining_tank_time = other_next_tank.immersion_time_mins - self.rack_pick_time_mins
                result = self.calculate_racks_and_cranes()
            else: # shift current tank first
                self.crane.tank_unmber = current_tank.tank_number
                for rack in self.racks:
                    rack.remaining_tank_time = rack.remaining_tank_time - time_taken_to_shift_current_rack
                self.racks[current_rack_index].tank_unmber = current_next_tank.tank_number
                self.racks[current_rack_index].remaining_tank_time = current_next_tank.immersion_time_mins - self.rack_pick_time_mins
                result = self.calculate_racks_and_cranes()
                if not result:
                    for rack in self.racks:
                        rack.remaining_tank_time = rack.remaining_tank_time - time_taken_to_shift_other_rack
                    self.racks[other_rack_index].tank_unmber = other_next_tank.tank_number
                    self.racks[other_rack_index].remaining_tank_time = other_next_tank.immersion_time_mins - self.rack_pick_time_mins
                    result = self.calculate_racks_and_cranes()
                return result
            
            # go with 


        total_rack_travel_time = total_rack_travel_time + self.calc_rack_shift_time(current_tank)
        if current_tank.tank_number == no_of_tanks - 1:
            return
        current_tank = self.find_next_tank(current_tank)

        total_rack_travel_time = total_rack_travel_time + 0.19
        return total_rack_travel_time


    def post(self, request, *args, **kwargs):
        tanks = list(Tank.objects.all())
        number_of_cranes = 1
        e =self.ca
        pass
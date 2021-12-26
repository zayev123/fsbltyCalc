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
# insert crane opertion, and delete crane operation
# make only just enough time shift upon each change
# but the list has already bbeen updated along the recursions, so it should be kept seperate from the racks, 
# and only the last result_map should be stored in the class
# the cranes list should also move along
# for multiple cranes, you'll have to see that by looking at one, it cant look at the other one that 
# requires it more. So you need to check, which rack is more critical for which crane


class RackTrack():
    def __init__(self, rack_index, tank_number, remaining_tank_time, line_entry_added_time_available, entry_time_min_time_tank_number, entry_time_min_time_rack_remainingTimeAvailable):
        self.rack_index = rack_index
        self.tank_number = tank_number
        self.remaining_tank_time = remaining_tank_time
        entry_time_min_time_tank_number = entry_time_min_time_tank_number
        entry_time_min_time_rack_remainingTimeAvailable = entry_time_min_time_rack_remainingTimeAvailable
        line_entry_added_time_available = line_entry_added_time_available
        # shifting this will shift the entire line and hve effects everywhere # inititally, this will be the the same as the min time tank start time
        # so there should be a few other fields:

class CraneTrack():
    def __init__(self, crane_index, tank_number):
        self.crane_index = crane_index
        self.tank_number = tank_number

class CraneOperation():
    def __init__(self, crane_index, tank_number, next_tank_number, rack_index):
        self.crane_index = crane_index
        self.tank_number = tank_number
        self.next_tank_number = next_tank_number
        self.rack_index = rack_index

class TankAutomatorView(APIView):

    tank_cross_time = 0.05

    def calculate_tank_shift_time(self, tank_a_number, tank_b_number):
        crossing_tank_qty = tank_b_number - tank_a_number
        time_for_crossing_mins = crossing_tank_qty * self.tank_cross_time
        return abs(time_for_crossing_mins)

    rack_pick_time_mins = 0.07
    rack_drop_time_mins = 0.07
    tanks = Tank.objects.all()
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

    def get_min_time_left_racks(self, racks):
        min_time_left_racks = racks.sort(key=lambda rack: rack.remaining_tank_time)
        return min_time_left_racks

    def get_sorted_cranes(self, cranes):
        min_time_left_racks = cranes.sort(key=lambda crane: crane.tank_number)
        return min_time_left_racks

    def get_closest_crane(self, cranes, rack):
        sorted_cranes = self.get_sorted_cranes(cranes)
        no_of_cranes = len(sorted_cranes)
        if no_of_cranes == 1 or rack.tank_number < sorted_cranes[0].tank_number:
            return sorted_cranes[0].crane_index
        if rack.tank_number > sorted_cranes[no_of_cranes - 1].tank_number:
            return sorted_cranes[no_of_cranes - 1].crane_index

        i = 0
        while i + 1 < no_of_cranes:
            crane_1 = sorted_cranes[i]
            crane_2 = sorted_cranes[i+1]
            crane_1_tankNumber = crane_1.tank_number
            crane_2_tankNumber = crane_2.tank_number
            rack_tankNumber = rack.tank_number
            is_between = crane_1_tankNumber <= rack_tankNumber <= crane_2_tankNumber
            if is_between: 
                if rack_tankNumber - crane_1_tankNumber < crane_2_tankNumber - rack_tankNumber:
                    return crane_1.crane_index
                else:
                    return crane_2.crane_index

    def check_shift_operations_new_tank(self,current_rack, new_rack, myTanks, myCranes):
        current_rack_index = current_rack.rack_index
        current_tank = myTanks.get(tank_number = current_rack.tank_number)
        current_next_tank = self.find_next_tank(current_tank)
        mins_available_current_rack = current_rack.remaining_tank_time

        new_tank = myTanks.get(tank_number = new_rack.tank_number)
        mins_available_new_rack = new_rack.remaining_tank_time

        myCraneIndex = self.get_closest_crane(myCranes, new_rack)

        time_taken_to_get_crane_to_new_tank = self.calculate_tank_shift_time(myCranes[myCraneIndex].tank_number, new_tank.tank_number) + self.tank_cross_time

        time_available_for_current_rack_after_getting_crane_to_new_tank = mins_available_current_rack - time_taken_to_get_crane_to_new_tank
        
        if time_available_for_current_rack_after_getting_crane_to_new_tank < 0:
            return {'result_id': 0,}
        # what of the crane shift time????
        time_taken_for_shifting_new_rack = self.calc_rack_shift_time(current_tank) + time_taken_to_get_crane_to_new_tank
        time_left_for_current_rack_after_shifting_new_rack = mins_available_current_rack - (mins_available_new_rack + self.calc_rack_shift_time(current_tank) + time_taken_to_get_crane_to_new_tank)
        if time_left_for_current_rack_after_shifting_new_rack < 0:
            return {'result_id': 0,}

        return {'result_id': 1, 'time_taken_for_shifting_new_rack': time_taken_for_shifting_new_rack, 'myCraneIndex': myCraneIndex}


    def check_shift_operations(self,sortedRacks, myTanks, myCranes):
        current_rack = sortedRacks[0]
        current_rack_index = current_rack.rack_index
        current_tank = myTanks.get(tank_number = current_rack.tank_number)
        current_next_tank = self.find_next_tank(current_tank)
        mins_available_current_rack = current_rack.remaining_tank_time

        other_rack = sortedRacks[1]
        other_tank = myTanks.get(tank_number = other_rack.tank_number)
        mins_available_other_rack = other_rack.remaining_tank_time

        myCraneIndex = self.get_closest_crane(myCranes, current_rack)

        time_taken_to_get_crane_to_current_tank = self.calculate_tank_shift_time(myCranes[myCraneIndex].tank_number, current_tank.tank_number)

        time_available_for_current_rack_after_getting_crane_to_current_tank = mins_available_current_rack - time_taken_to_get_crane_to_current_tank
        
        if time_available_for_current_rack_after_getting_crane_to_current_tank < 0:
            return {'result_id': 0,}
            
        time_left_for_other_rack_after_shifting_current_rack = mins_available_other_rack - ((mins_available_current_rack - time_taken_to_get_crane_to_current_tank) + self.calc_rack_shift_time(current_tank) + self.calculate_tank_shift_time(current_next_tank.tank_number, other_tank.tank_number))
        if time_left_for_other_rack_after_shifting_current_rack < 0:
            return {'result_id': 0,}

        return {'result_id': 1, 'time_taken_to_get_crane_to_current_tank': time_taken_to_get_crane_to_current_tank, 'current_tank': current_tank, 'current_rack_index': current_rack_index, 'current_next_tank': current_next_tank, 'myCraneIndex': myCraneIndex}

    def perform_shift_operations(self,sortedRacks, myRacks, myTanks, myCranes):
        ops_resultCheck_map = self.check_shift_operations(self,sortedRacks, myTanks, myCranes)
        if ops_resultCheck_map['result_id'] !=0:
            time_taken_to_get_crane_to_current_tank = ops_resultCheck_map['time_taken_to_get_crane_to_current_tank']
            current_tank = ops_resultCheck_map['current_tank']
            current_rack_index = ops_resultCheck_map['current_rack_index']
            current_next_tank = ops_resultCheck_map['current_next_tank']
            myCraneIndex = ops_resultCheck_map['myCraneIndex']
            crane_old_tank_number = myCranes[myCraneIndex].tank_number

            time_taken_to_shift_current_rack = time_taken_to_get_crane_to_current_tank + self.calc_rack_shift_time(current_tank)
            for rack in myRacks:
                rack.remaining_tank_time = rack.remaining_tank_time - time_taken_to_shift_current_rack

            old_tank_number = myRacks[current_rack_index].tank_number
            myRacks[current_rack_index].tank_number = current_next_tank.tank_number

            old_remaining_time = myRacks[current_rack_index].remaining_tank_time
            myRacks[current_rack_index].remaining_tank_time = current_next_tank.immersion_time_mins - self.rack_pick_time_mins
            
            myCranes[myCraneIndex].tank_number = current_next_tank.tank_number
            result_n = self.calculate_racks_and_cranes(myRacks, myCranes)
            if result_n != 1:
                result_map = {'result_id': -1, 'current_rack_index': current_rack_index, 'time_taken_to_shift_current_rack': time_taken_to_shift_current_rack, 'old_tank_Number': old_tank_number, 'old_remaining_time': old_remaining_time, 'crane_index': myCraneIndex, 'crane_old_tank_number': crane_old_tank_number}
            else:
                result_map = {'result_id': 1, 'current_rack_index': current_rack_index,  'time_taken_to_shift_current_rack': time_taken_to_shift_current_rack, 'old_tank_Number': old_tank_number, 'old_remaining_time': old_remaining_time, 'crane_index': myCraneIndex, 'crane_old_tank_number': crane_old_tank_number}

            return result_map
        else:
            return {'result_id': 0}

    def deUpdateTimesAndPositions(self, result_map, myRacks, myCranes):
        for rack in myRacks:
            rack.remaining_tank_time = rack.remaining_tank_time + result_map['time_taken_to_shift_current_rack']
        myRacks[result_map['current_rack_index']].tank_number = result_map['old_tank_Number']
        myRacks[result_map['current_rack_index']].remaining_tank_time = result_map['old_remaining_time']
        myCranes[result_map['crane_index']].tank_number = result_map['crane_old_tank_number']

        return myRacks

    # jus check if it is in the first tank, if yes, then you can perform in the shift ops
    # if it is not added at the tank start, the i'll have to reupdate the rack_remaining times in the for loop, and see if it is possible all over again
    # but what is the crane time to shift first rack to first tank
    # i need to shift the crane to the first tank, it is separate from the other tank, current tank shiz
    # also, i donot need to get the closest crane, i know that its crane zero
    def calculate_racks_and_cranes(self, myRacks, myCranes):

        myTanks = self.tanks
        tanks_list = list(myTanks)
        no_of_tanks = len(tanks_list)


        no_of_racks = len(myRacks)

        if no_of_racks != 0:
            new_rack_index = no_of_racks
            first_tank = myTanks.get(tank_number = 1)
            new_rack = myRacks[new_rack_index] = RackTrack(new_rack_index, 1, (first_tank.immersion_time_mins - self.rack_pick_time_mins), -1, -1, -1)
            new_next_tank = self.find_next_tank(first_tank)
            new_rack.tank_number = new_next_tank.tank_number
            new_rack.remaining_tank_time = new_next_tank.immersion_time_mins - self.rack_pick_time_mins
            myRacks[new_rack_index] = new_rack
            myCraneIndex = self.get_closest_crane(myCranes, new_rack)
            myCranes[myCraneIndex].tank_number = new_next_tank.tank_number
            result_id = self.calculate_racks_and_cranes(myRacks, myCranes)

            # if it is getting false at the last tank, then i have achieved my purpose
            # what about the initial time
            while result_id !=1:
                firstRack = myRacks[0]
                first_rack_tankNumber = firstRack.tank_number
                the_tank = myTanks.get(tank_number = first_rack_tankNumber)
                the_next_tank = self.find_next_tank(the_tank)
                firstRack.tank_number = the_next_tank.tank_number
                firstRack.remaining_tank_time = the_next_tank.immersion_time_mins - self.rack_pick_time_mins
                myRacks[0] = firstRack
                myCraneIndex = self.get_closest_crane(myCranes, firstRack)
                myCranes[myCraneIndex].tank_number = the_next_tank.tank_number
                result_id = self.calculate_racks_and_cranes(myRacks, myCranes)
            
            return result_id
            # last case scenario, I will just shift the first tank forward

        # first lets try this process by adding a new rack

        else:

            myMinRacks = self.get_min_time_left_racks(myRacks)

            current_rack = myMinRacks[0]

            new_rack_index = no_of_racks
            first_tank = myTanks.get(tank_number = 1)
            line_entry_added_time_available = 0
            #
            myRacks[new_rack_index] = RackTrack(new_rack_index, 1, (first_tank.immersion_time_mins - self.rack_pick_time_mins), current_rack.tank_number, current_rack.remaining_tank_time, line_entry_added_time_available)
            # i need to check if crane 0 can even perform this operation at this stage. this process will have its own update and deupdate stages,
            # I should split the shift op function:
            # i mean if it cant even add it, then i shouldnt even add the rack
            new_result = self.check_shift_operations_new_tank(current_rack, myRacks[new_rack_index], myTanks, myCranes)
            if new_result['result_id'] == 0:
                del myRacks[new_rack_index]
            else:
                # update the times and the crane positions
                # put a flag here to further deupdate
                pass

            sortedRacks = self.get_min_time_left_racks(myRacks)

            result_map = self.perform_shift_operations(sortedRacks, myRacks, myTanks, myCranes)

            if result_map['result_id'] != 1:
                
                myRacks = self.deUpdateTimesAndPositions(result_map, myRacks, myCranes)
                sortedRacks = self.get_min_time_left_racks(myRacks)
                result_map = self.perform_shift_operations(sortedRacks, myRacks, myTanks, myCranes)
            # it needs to be a for loop
            
            return result_map['result_id']
            

    def post(self, request, *args, **kwargs):
        tanks = list(Tank.objects.all())
        number_of_cranes = 1
        e =self.ca
        pass
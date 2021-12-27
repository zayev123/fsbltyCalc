from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Tank
from operator import attrgetter
# now to set the aded times available option
# when the result is returned 1, I can add that data to the list upon each step
# ther is just one extra time and that is when there is time still left for the other tank
 # You also need to accomodate the equals case
 # you need to write a code for accomodating the same type tanks

class RackTrack():
    def __init__(self, rack_index, tank_number, remaining_tank_time, entry_moment_shift_time_available, entry_moment_min_time_tank_number, entry_moment_min_time_rack_remainingTimeAvailable):
        self.rack_index = rack_index
        self.tank_number = tank_number
        self.remaining_tank_time = remaining_tank_time
        self.entry_moment_min_time_tank_number = entry_moment_min_time_tank_number
        self.entry_moment_min_time_rack_remainingTimeAvailable = entry_moment_min_time_rack_remainingTimeAvailable
        self.entry_moment_shift_time_available = entry_moment_shift_time_available
        
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
    # or i can return the least remaining rack time tank then if no same type tank is empty

    def check_occupancy(self, the_tanks, the_racks):
        if len(the_tanks) == 1:
            return the_tanks[0]
        the_racks_list = []
        for tank in the_tanks:
            is_occupied = False
            for rack in the_racks:
                if rack.tank_number == tank.tank_number:
                    the_racks_list.append(rack)
                    is_occupied = True
                    break
            if not is_occupied:
                best_tank = tank
                return best_tank
        # if all tanks are occupied, then:
        min_racks_list = self.get_min_time_left_racks(the_racks_list)
        best_tank = self.tanks.get(tank_number = min_racks_list[0].tank_number)

    def find_next_tank(self, tank_a, z_racks):
        myTanks = self.tanks
        tank_a_number = tank_a.tank_number
        i = 1
        while i < 6:
            tank_b_number = tank_a_number + i
            tank_b = myTanks.get(tank_number = tank_b_number)
            if tank_b.tank_type_number != tank_a.tank_type_number:
                j = 0
                the_tanks = [tank_b]
                tank_x_number = tank_b_number
                while j<5:
                    tank_x_number = tank_x_number +1
                    tank_x = myTanks.get(tank_number = tank_x_number)
                    if tank_x.tank_type_number == tank_b.tank_type_number:
                        the_tanks.append(tank_x)
                    else:
                        break
                best_tank = self.check_occupancy(the_tanks, z_racks)
                return best_tank
            i = i+1
        return -1

        # after finding next tank, it will do +1, +1 till it finds an empty tank of the same type number

    def calc_rack_shift_time(self, tank_a, z_racks):
        tank_b = self.find_next_tank(tank_a, z_racks)
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


    def check_shift_operations_new_tank(self,current_rack, new_rack, myTanks, myFirstCrane):
        current_tank = myTanks.get(tank_number = current_rack.tank_number)
        mins_available_current_rack = current_rack.remaining_tank_time

        new_tank = myTanks.get(tank_number = new_rack.tank_number)


        time_taken_to_get_crane_to_new_tank = self.calculate_tank_shift_time(myFirstCrane.tank_number, new_tank.tank_number) + self.tank_cross_time

        
        time_taken_for_shifting_new_rack = time_taken_to_get_crane_to_new_tank + 2*self.rack_pick_time_mins + 2*self.rack_drop_time_mins + self.tank_cross_time
        time_left_for_current_rack_after_shifting_new_rack = mins_available_current_rack - time_taken_for_shifting_new_rack - self.calculate_tank_shift_time(new_tank.tank_number, current_tank)
        if time_left_for_current_rack_after_shifting_new_rack < 0:
            return {'result_id': 0,}

        return {'result_id': 1, 'time_taken_for_shifting_new_rack': time_taken_for_shifting_new_rack,}

    def perform_shift_operations_new_tank(self,current_rack, myRacks, myTanks, myCranes):
        myFirstCrane = myCranes[0]
        new_rack_index = len(myRacks) - 1
        new_rack = myRacks[new_rack_index]
        ops_resultCheck_map = self.check_shift_operations_new_tank(current_rack, new_rack, myTanks, myFirstCrane)
        
        if ops_resultCheck_map['result_id'] == 1:
            time_taken_for_shifting_new_rack = ops_resultCheck_map['time_taken_for_shifting_new_rack']

            for rack in myRacks:
                rack.remaining_tank_time = rack.remaining_tank_time - time_taken_for_shifting_new_rack

            new_rack.remaining_tank_time = myTanks.get(tank_number = new_rack.tank_number).immersion_time_mins - self.rack_pick_time_mins
            myFirstCrane.tank_number = 1
            myCranes[0] = myFirstCrane

            result_n = self.calculate_racks_and_cranes(myRacks, myCranes)
            return result_n
        else:
            return ops_resultCheck_map
# if that is the case, then i might not need to deupdate
    def check_shift_operations(self,sortedRacks, myTanks, myCranes):
        current_rack = sortedRacks[0]
        current_rack_index = current_rack.rack_index
        current_tank = myTanks.get(tank_number = current_rack.tank_number)
        mins_available_current_rack = current_rack.remaining_tank_time
        myCraneIndex = self.get_closest_crane(myCranes, current_rack)

        time_taken_to_get_crane_to_current_tank = self.calculate_tank_shift_time(myCranes[myCraneIndex].tank_number, current_tank.tank_number)

        time_available_for_current_rack_after_getting_crane_to_current_tank = mins_available_current_rack - time_taken_to_get_crane_to_current_tank
        
        other_rack = sortedRacks[1]
        other_tank = myTanks.get(tank_number = other_rack.tank_number)
        mins_available_other_rack = other_rack.remaining_tank_time

        # if next tank already has a rack in it, then it fails yet again, and this needs to be checked before any other check, and in this case,
        # we can use the entry shift time variable

        if time_available_for_current_rack_after_getting_crane_to_current_tank < 0:
            return {'result_id': 0,}
        
        if current_tank.tank_number == len(myTanks):
            time_left_for_other_rack_after_shifting_current_rack = mins_available_other_rack - ((mins_available_current_rack - time_taken_to_get_crane_to_current_tank) + self.calc_rack_shift_time(current_tank, sortedRacks) + self.calculate_tank_shift_time(current_tank.tank_number, other_tank.tank_number) + 2*self.tank_cross_time)
            if time_left_for_other_rack_after_shifting_current_rack >= 0:
                return {'result_id': 2}
        current_next_tank = self.find_next_tank(current_tank, sortedRacks)

        for rack in sortedRacks:
            # it wont be itself because they dont have the same tank numbers
            # just add the entire shift time for safety reasons
            if rack.tank_number == current_next_tank.tank_number:
                z_tank = myTanks.get(tank_number = rack.tank_number)
                z_next_tank = self.find_next_tank(z_tank, sortedRacks)
                current_rack_time_shift_needed = (rack.remaining_tank_time + self.calc_rack_shift_time(z_tank, sortedRacks) + self.calculate_tank_shift_time(z_next_tank, current_tank)) - current_rack.remaining_tank_time
                return {'result_id': 0, 'current_rack_time_shift_needed': current_rack_time_shift_needed, 'current_rack_index': current_rack_index}
            
        time_left_for_other_rack_after_shifting_current_rack = mins_available_other_rack - ((mins_available_current_rack - time_taken_to_get_crane_to_current_tank) + self.calc_rack_shift_time(current_tank, sortedRacks) + self.calculate_tank_shift_time(current_next_tank.tank_number, other_tank.tank_number))
        if time_left_for_other_rack_after_shifting_current_rack < 0:
            return {'result_id': 0,}

        return {'result_id': 1, 'time_taken_to_get_crane_to_current_tank': time_taken_to_get_crane_to_current_tank, 'current_tank': current_tank, 'current_rack_index': current_rack_index, 'current_next_tank': current_next_tank, 'myCraneIndex': myCraneIndex}

    def perform_shift_operations(self,sortedRacks, myRacks, myTanks, myCranes):
        ops_resultCheck_map = self.check_shift_operations(sortedRacks, myTanks, myCranes)
        if ops_resultCheck_map['result_id'] ==2:
            return ops_resultCheck_map
        if ops_resultCheck_map['result_id'] ==1:
            time_taken_to_get_crane_to_current_tank = ops_resultCheck_map['time_taken_to_get_crane_to_current_tank']
            current_tank = ops_resultCheck_map['current_tank']
            current_rack_index = ops_resultCheck_map['current_rack_index']
            current_next_tank = ops_resultCheck_map['current_next_tank']
            myCraneIndex = ops_resultCheck_map['myCraneIndex']

            time_taken_to_shift_current_rack = time_taken_to_get_crane_to_current_tank + self.calc_rack_shift_time(current_tank, myRacks)
            for rack in myRacks:
                rack.remaining_tank_time = rack.remaining_tank_time - time_taken_to_shift_current_rack

            myRacks[current_rack_index].tank_number = current_next_tank.tank_number

            myRacks[current_rack_index].remaining_tank_time = current_next_tank.immersion_time_mins - self.rack_pick_time_mins
            
            myCranes[myCraneIndex].tank_number = current_next_tank.tank_number
            result_n = self.calculate_racks_and_cranes(myRacks, myCranes)
            return result_n
        else:
            return ops_resultCheck_map

    # for the line shift, you just need to add another clause that if shift bw
    # tank 30 and 31, then add to the crane move time
    # if more than one crane, the times shouldnt be added cumulatively
    # jus be careful of that

    def calculate_racks_and_cranes(self, myRacks, myCranes):

        myTanks = self.tanks
        tanks_list = list(myTanks)
        no_of_tanks = len(tanks_list)


        no_of_racks = len(myRacks)

        if no_of_racks == 0:
            new_rack_index = no_of_racks
            first_tank = myTanks.get(tank_number = 1)
            new_rack = myRacks[new_rack_index] = RackTrack(new_rack_index, 1, (first_tank.immersion_time_mins - self.rack_pick_time_mins), -1, -1, -1)
            new_next_tank = self.find_next_tank(first_tank, myRacks)
            new_rack.tank_number = new_next_tank.tank_number
            new_rack.remaining_tank_time = new_next_tank.immersion_time_mins - self.rack_pick_time_mins
            myRacks[new_rack_index] = new_rack
            myCraneIndex = self.get_closest_crane(myCranes, new_rack)
            myCranes[myCraneIndex].tank_number = new_next_tank.tank_number
            result_Map = self.calculate_racks_and_cranes(myRacks, myCranes)

            # if it is getting false at the last tank, then i have achieved my purpose
            # what about the initial time
            while result_Map['result_id'] !=2:
                firstRack = myRacks[0]
                first_rack_tankNumber = firstRack.tank_number
                the_tank = myTanks.get(tank_number = first_rack_tankNumber)
                the_next_tank = self.find_next_tank(the_tank, myRacks)
                firstRack.tank_number = the_next_tank.tank_number
                firstRack.remaining_tank_time = the_next_tank.immersion_time_mins - self.rack_pick_time_mins
                myRacks[0] = firstRack
                myCraneIndex = self.get_closest_crane(myCranes, firstRack)
                myCranes[myCraneIndex].tank_number = the_next_tank.tank_number
                result_Map = self.calculate_racks_and_cranes(myRacks, myCranes)
                if firstRack.tank_number == no_of_tanks:
                    break
            
            return result_Map
            # last case scenario, I will just shift the first tank forward

        # first lets try this process by adding a new rack

        else:

            myMinRacks = self.get_min_time_left_racks(myRacks)

            current_rack = myMinRacks[0]

            # if the current rack is on the last tank, then delete the current rack
            # the way to add a new rack will be that when a new rack is inserted into the list
            # when there is a missing zero, then you have achieved your result
            is_new_rack_added = False

            if myRacks[no_of_racks - 1].tank_number !=1 :

                new_rack_index = no_of_racks
                first_tank = myTanks.get(tank_number = 1)
                entry_moment_shift_time_available = current_rack.remaining_tank_time - (self.calculate_tank_shift_time(myCranes[0].tank_number, 1) + 2*self.tank_cross_time + 2*self.rack_pick_time_mins + 2*self.rack_drop_time_mins + self.calculate_tank_shift_time(1, current_rack.tank_number))
                entry_moment_shift_time_available_store = entry_moment_shift_time_available

                myRacks[new_rack_index] = RackTrack(new_rack_index, 1, (first_tank.immersion_time_mins - self.rack_pick_time_mins), current_rack.tank_number, current_rack.remaining_tank_time, entry_moment_shift_time_available)
                is_new_rack_added = True
                new_result = self.perform_shift_operations_new_tank(current_rack, myRacks, myTanks, myCranes)

            else:
                sortedRacks = self.get_min_time_left_racks(myRacks)
                new_result = self.perform_shift_operations(sortedRacks, myRacks, myTanks, myCranes)
                is_new_rack_added = False
            
            if new_result['result_id'] != 2:
                if is_new_rack_added:
                    if 'current_rack_time_shift_needed' in new_result and new_result['current_rack_index'] == new_rack_index and new_result['current_rack_time_shift_needed'] > 0 and new_result['current_rack_time_shift_needed'] < myRacks[new_rack_index].entry_moment_shift_time_available:
                        while new_result['current_rack_time_shift_needed'] < myRacks[new_rack_index].entry_moment_shift_time_available:
                            for rack in myRacks:
                                rack.remaining_tank_time = rack.remaining_tank_time - new_result['current_rack_time_shift_needed']
                            myRacks[new_rack_index].entry_moment_shift_time_available = myRacks[new_rack_index].entry_moment_shift_time_available - new_result['current_rack_time_shift_needed']
                            myRacks[new_rack_index].remaining_tank_time = myTanks.get(tank_number = myRacks[new_rack_index].tank_number).immersion_time_mins - self.rack_pick_time_mins
                            sortedRacks = self.get_min_time_left_racks(myRacks)
                            # if it is not a success, then try without the new_rack
                            new_result = self.perform_shift_operations(sortedRacks, myRacks, myTanks, myCranes)
                            if new_result['result_id'] == 2:
                                return new_result
                            if 'current_rack_time_shift_needed' not in new_result:
                                break
                    # it will compare the difference between the store and the current, then add that time to the store
                    # along with the current
                    if 'current_rack_time_shift_needed' not in new_result:
                        if myRacks[new_rack_index].entry_moment_shift_time_available < entry_moment_shift_time_available_store:
                            taken_shift_time = entry_moment_shift_time_available_store - myRacks[new_rack_index]
                            for rack in myRacks:
                                rack.remaining_tank_time = rack.remaining_tank_time + taken_shift_time
                            myRacks[new_rack_index].remaining_tank_time = myTanks.get(tank_number = myRacks[new_rack_index].tank_number).immersion_time_mins - self.rack_pick_time_mins
                            myRacks[new_rack_index].entry_moment_shift_time_available = myRacks[new_rack_index].entry_moment_shift_time_available + taken_shift_time
                        del myRacks[new_rack_index]
                        sortedRacks = self.get_min_time_left_racks(myRacks)
                        # if it is not a success, then try without the new_rack
                        new_result = self.perform_shift_operations(sortedRacks, myRacks, myTanks, myCranes)
                        if new_result['result_id'] == 2:
                            return new_result
                # if it is still not a success, then just return
                    return new_result
            else:
                return new_result        

            

    def post(self, request, *args, **kwargs):
        tanks = list(Tank.objects.all())
        number_of_cranes = 1
        e =self.ca
        pass
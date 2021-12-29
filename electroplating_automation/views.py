import json
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import ElectroEncoder, Tank
import copy
# now to set the aded times available option
# when the result is returned 1, I can add that data to the list upon each step
# ther is just one extra time and that is when there is time still left for the other tank
# You also need to accomodate the equals case
# you need to write a code for accomodating the same type tanks
# it all boils down to which tank i should be deleting.
# I shouldnt be deleting the latest one, but the one causing the problem, and update accordingly

class RackTrack():
    def __init__(self, rack_index, tank_number, remaining_tank_time, entry_moment_shift_time_available, entry_moment_next_rack_number, entry_moment_next_rack_tank_number, entry_moment_next_rack_remainingTankTime):
        self.rack_index = rack_index
        self.tank_number = tank_number
        self.remaining_tank_time = remaining_tank_time
        self.entry_moment_shift_time_available = entry_moment_shift_time_available
        self.entry_moment_next_rack_number = entry_moment_next_rack_number
        self.entry_moment_next_rack_tank_number = entry_moment_next_rack_tank_number
        self.entry_moment_next_rack_remainingTankTime = entry_moment_next_rack_remainingTankTime
        
        # shifting this will shift the entire line and hve effects everywhere # inititally, this will be the the same as the min time tank start time
        # so there should be a few other fields:

class CraneTrack():
    def __init__(self, crane_index, tank_number):
        self.crane_index = crane_index
        self.tank_number = tank_number

class CraneOperation():
    def __init__(self, crane_index, tank_number, rack_tank_number, next_tank_number, rack_index):
        self.crane_index = crane_index
        self.tank_number = tank_number
        self.rack_tank_number = rack_tank_number
        self.next_tank_number = next_tank_number
        self.rack_index = rack_index

class TankAutomatorView(APIView):

    tank_cross_time = 0.05
    final_racks_list = []
    crane_ops = []

    def calculate_tank_shift_time(self, tank_a_number, tank_b_number):
        crossing_tank_qty = tank_b_number - tank_a_number
        time_for_crossing_mins = crossing_tank_qty * self.tank_cross_time
        return abs(time_for_crossing_mins)

    rack_pick_time_mins = 0.07
    rack_drop_time_mins = 0.07
    tanks = Tank.objects.all()
    check_data = []
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
        while i < 5:
            tank_b_number = tank_a_number + i
            tank_b = myTanks.get(tank_number = tank_b_number)
            if tank_b_number >= 56:
                best_tank = tank_b
                return best_tank
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

    final_rack_shift_time = 2*rack_pick_time_mins + 2*rack_drop_time_mins +tank_cross_time

    def get_min_time_left_racks(self, racks):
        min_time_left_racks = sorted(racks, key=lambda rack: rack.remaining_tank_time)
        return min_time_left_racks

    def get_sorted_cranes(self, cranes):
        min_time_left_racks = sorted(cranes, key=lambda crane: crane.tank_number)
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
        time_left_for_current_rack_after_shifting_new_rack = mins_available_current_rack - time_taken_for_shifting_new_rack - self.calculate_tank_shift_time(new_tank.tank_number, current_tank.tank_number)
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

            new_rack.remaining_tank_time = float(myTanks.get(tank_number = new_rack.tank_number).immersion_time_mins) - self.rack_pick_time_mins
            old_tank_number = myCranes[0].tank_number
            myFirstCrane.tank_number = 1
            myCranes[0] = myFirstCrane

            crane_op = CraneOperation(0, old_tank_number, -1, 1, new_rack_index)
            self.crane_ops.append(time_taken_for_shifting_new_rack)
            self.crane_ops.append(crane_op)
            temp_racks_3 = copy.deepcopy(myRacks)
            temp_cranes_3 = copy.deepcopy(myCranes)
            #self.check_data.append(new_rack_index)
            #self.check_data.append(self.serialize_racks(myRacks))
            result_n = self.calculate_racks_and_cranes(temp_racks_3, temp_cranes_3)
            return result_n
        else:
            return ops_resultCheck_map
# if that is the case, then i might not need to deupdate
    def check_shift_operations(self,sortedRacks, myTanks, myCranes):
        if len(sortedRacks) == 1:
            return {'result_id': 0,}
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
        
        current_next_tank = self.find_next_tank(current_tank, sortedRacks)
        

        for rack in sortedRacks:
            if rack.tank_number == current_next_tank.tank_number:
                z_tank = myTanks.get(tank_number = rack.tank_number)
                z_next_tank = self.find_next_tank(z_tank, sortedRacks)
                current_rack_time_shift_needed = (rack.remaining_tank_time + self.calc_rack_shift_time(z_tank, sortedRacks) + self.calculate_tank_shift_time(z_next_tank.tank_number, current_tank.tank_number)) - current_rack.remaining_tank_time
                return {'result_id': 0, 'current_rack_time_shift_needed': current_rack_time_shift_needed, 'current_rack_index': current_rack_index}
            
        time_left_for_other_rack_after_shifting_current_rack = mins_available_other_rack - ((mins_available_current_rack - time_taken_to_get_crane_to_current_tank) + self.calc_rack_shift_time(current_tank, sortedRacks) + self.calculate_tank_shift_time(current_next_tank.tank_number, other_tank.tank_number))
        if time_left_for_other_rack_after_shifting_current_rack < 0:
            return {'result_id': 0,}

        return {'result_id': 1, 'time_taken_to_get_crane_to_current_tank': time_taken_to_get_crane_to_current_tank, 'current_tank': current_tank, 'current_rack_index': current_rack_index, 'current_next_tank': current_next_tank, 'myCraneIndex': myCraneIndex}

    def perform_shift_operations(self,sortedRacks, myRacks, myTanks, myCranes):
        #if myRacks[0].tank_number == 7:
        if myRacks[0].tank_number == len(myTanks):
            # the last tank data will be off because im not putting any checks here
            self.final_racks_list = myRacks
            return {'result_id': 2}
        ops_resultCheck_map = self.check_shift_operations(sortedRacks, myTanks, myCranes)
        if ops_resultCheck_map['result_id'] ==1:
            time_taken_to_get_crane_to_current_tank = ops_resultCheck_map['time_taken_to_get_crane_to_current_tank']
            current_tank = ops_resultCheck_map['current_tank']
            current_rack_index = ops_resultCheck_map['current_rack_index']
            current_next_tank = ops_resultCheck_map['current_next_tank']
            myCraneIndex = ops_resultCheck_map['myCraneIndex']
            self.check_data.append(current_rack_index)
            self.check_data.append(self.serialize_racks(myRacks))
            time_taken_to_shift_current_rack = time_taken_to_get_crane_to_current_tank + self.calc_rack_shift_time(current_tank, myRacks)
            the_remaining_tank_time = myRacks[current_rack_index].remaining_tank_time
            for rack in myRacks:
                rack.remaining_tank_time = rack.remaining_tank_time - (time_taken_to_shift_current_rack + the_remaining_tank_time)

            myRacks[current_rack_index].tank_number = current_next_tank.tank_number
            myRacks[current_rack_index].remaining_tank_time = float(current_next_tank.immersion_time_mins) - self.rack_pick_time_mins
            old_tank_number = myCranes[myCraneIndex].tank_number
            myCranes[myCraneIndex].tank_number = current_next_tank.tank_number
            crane_op = CraneOperation(0, old_tank_number, current_tank.tank_number, current_next_tank.tank_number, current_rack_index)
            self.crane_ops.append(time_taken_to_get_crane_to_current_tank)
            self.crane_ops.append(crane_op)
            temp_racks_2 = copy.deepcopy(myRacks)
            temp_cranes_2 = copy.deepcopy(myCranes)
            self.check_data.append(self.serialize_racks(myRacks))
            result_n = self.calculate_racks_and_cranes(temp_racks_2, temp_cranes_2)
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
            new_rack = RackTrack(new_rack_index, 1, (float(first_tank.immersion_time_mins) - self.rack_pick_time_mins), -1, -1, -1, -1)
            myRacks.append(new_rack)
            new_next_tank = self.find_next_tank(first_tank, myRacks)
            new_rack.tank_number = new_next_tank.tank_number
            new_rack.remaining_tank_time = float(new_next_tank.immersion_time_mins) - self.rack_pick_time_mins
            myRacks[new_rack_index] = new_rack
            myCraneIndex = self.get_closest_crane(myCranes, new_rack)
            myCranes[myCraneIndex].tank_number = new_next_tank.tank_number
            temp_racks_0 = copy.deepcopy(myRacks)
            temp_cranes_0 = copy.deepcopy(myCranes)
            result_Map = self.calculate_racks_and_cranes(temp_racks_0, temp_cranes_0)

            # if it is getting false at the last tank, then i have achieved my purpose
            # what about the initial time
            while result_Map['result_id'] !=2:
                firstRack = myRacks[0]
                first_rack_tankNumber = firstRack.tank_number
                the_tank = myTanks.get(tank_number = first_rack_tankNumber)
                the_next_tank = self.find_next_tank(the_tank, myRacks)
                firstRack.tank_number = the_next_tank.tank_number
                firstRack.remaining_tank_time = float(the_next_tank.immersion_time_mins) - self.rack_pick_time_mins
                myRacks[0] = firstRack
                myCraneIndex = self.get_closest_crane(myCranes, firstRack)
                myCranes[myCraneIndex].tank_number = the_next_tank.tank_number
                temp_racks_1 = copy.deepcopy(myRacks)
                temp_cranes_1 = copy.deepcopy(myCranes)
                result_Map = self.calculate_racks_and_cranes(temp_racks_1, temp_cranes_1)
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
                if entry_moment_shift_time_available >= 0:
                    entry_moment_shift_time_available_store = entry_moment_shift_time_available
                    entry_moment_next_rack_number = no_of_racks - 1
                    entry_moment_next_rack_tank_number = myRacks[no_of_racks - 1].tank_number

                    #sub_new_rack = RackTrack(new_rack_index, 1, (float(first_tank.immersion_time_mins) - self.rack_pick_time_mins), entry_moment_shift_time_available, entry_moment_next_rack_number, entry_moment_next_rack_tank_number, myRacks[no_of_racks - 1].remaining_tank_time)
                    sub_new_rack = RackTrack(new_rack_index, 1, (float(first_tank.immersion_time_mins) - self.rack_pick_time_mins), entry_moment_shift_time_available, current_rack.rack_index, current_rack.tank_number, current_rack.remaining_tank_time)
                    myRacks.append(sub_new_rack)
                    is_new_rack_added = True
                    #self.check_data.append(new_rack_index)
                    #self.check_data.append(self.serialize_racks(myRacks))
                    temp_current_rack_2 = copy.deepcopy(current_rack)
                    temp_racks_2 = copy.deepcopy(myRacks)
                    temp_Tanks_2 = myTanks
                    temp_cranes_2 = copy.deepcopy(myCranes)
                    new_result = self.perform_shift_operations_new_tank(temp_current_rack_2, temp_racks_2, temp_Tanks_2, temp_cranes_2)
                    #self.check_data.append(self.serialize_racks(myRacks))

            if not is_new_rack_added:
                sortedRacks = self.get_min_time_left_racks(myRacks)
                sortedRacks_3 = copy.deepcopy(sortedRacks)
                temp_racks_3 = copy.deepcopy(myRacks)
                temp_Tanks_3 = myTanks
                temp_cranes_3 = copy.deepcopy(myCranes)
                new_result = self.perform_shift_operations(sortedRacks_3, temp_racks_3, temp_Tanks_3, temp_cranes_3)
                is_new_rack_added = False

            shifted_rack_index = -10
            
            if new_result['result_id'] != 2:
                '''
                print(new_result)
                print(is_new_rack_added)
                if is_new_rack_added:
                    print(len(myRacks)-1 == new_rack_index)
                    print(new_rack_index)
                    print(myRacks[new_rack_index].tank_number)
                    if 'current_rack_time_shift_needed' in new_result:
                        print(myRacks[new_rack_index].entry_moment_shift_time_available)
                print('')
                #'''
                if is_new_rack_added and myRacks[new_rack_index].tank_number == 1:
                    # check if this was the depth at which the rack was added for the first time
                    #print(self.serialize_racks(myRacks[new_rack_index]))
                    #print('there')
                    if 'current_rack_time_shift_needed' in new_result and new_result['current_rack_index'] == new_rack_index and new_result['current_rack_time_shift_needed'] > 0 and new_result['current_rack_time_shift_needed'] < myRacks[new_rack_index].entry_moment_shift_time_available:
                        #print('here')
                        while new_result['current_rack_time_shift_needed'] < myRacks[new_rack_index].entry_moment_shift_time_available:
                            for rack in myRacks:
                                rack.remaining_tank_time = rack.remaining_tank_time - new_result['current_rack_time_shift_needed']-0.5
                            myRacks[new_rack_index].entry_moment_shift_time_available = myRacks[new_rack_index].entry_moment_shift_time_available - new_result['current_rack_time_shift_needed']
                            myRacks[new_rack_index].entry_moment_next_rack_remainingTankTime = myRacks[new_rack_index].entry_moment_next_rack_remainingTankTime - new_result['current_rack_time_shift_needed']
                            myRacks[new_rack_index].remaining_tank_time = float(myTanks.get(tank_number = myRacks[new_rack_index].tank_number).immersion_time_mins) - self.rack_pick_time_mins
                            sortedRacks = self.get_min_time_left_racks(myRacks)
                            # if it is not a success, then try without the new_rack
                            shifted_rack_index = new_result['current_rack_index']
                            sortedRacks_4 = copy.deepcopy(sortedRacks)
                            temp_racks_4 = copy.deepcopy(myRacks)
                            temp_Tanks_4 = myTanks
                            temp_cranes_4 = copy.deepcopy(myCranes)
                            new_result = self.perform_shift_operations(sortedRacks_4, temp_racks_4, temp_Tanks_4, temp_cranes_4)
                            if new_result['result_id'] == 2:
                                return new_result
                            if 'current_rack_time_shift_needed' not in new_result:
                                break
                    # it will compare the difference between the store and the current, then add that time to the store
                    # along with the current
                    #self.check_data.append(new_rack_index)
                    #self.check_data.append(self.serialize_racks(myRacks))
                    if 'current_rack_time_shift_needed' not in new_result:
                        del myRacks[new_rack_index]
                        #self.check_data.append(new_rack_index)
                        #self.check_data.append(self.serialize_racks(myRacks))
                        sortedRacks = self.get_min_time_left_racks(myRacks)
                        # if it is not a success, then try without the new_rack
                        sortedRacks_5 = copy.deepcopy(sortedRacks)
                        temp_racks_5 = copy.deepcopy(myRacks)
                        temp_Tanks_5 = myTanks
                        temp_cranes_5 = copy.deepcopy(myCranes)
                        new_result = self.perform_shift_operations(sortedRacks_5, temp_racks_5, temp_Tanks_5, temp_cranes_5)
                        if new_result['result_id'] == 2:
                            return new_result
                # if it is still not a success, then just return
                    return new_result
                else:
                    return new_result
            else:
                return new_result        

            
    # i return false only at the checks
    def get(self, request, *args, **kwargs):
        e_cranes = []
        e_cranes.append(CraneTrack(0, 1))
        e_racks = []
        e_result = self.calculate_racks_and_cranes(e_racks, e_cranes)
        rackJSONData = json.dumps(self.final_racks_list, indent=4, cls=ElectroEncoder)
        rackJSON = json.loads(rackJSONData)
        craneJSONData = json.dumps(self.crane_ops, indent=4, cls=ElectroEncoder)
        craneJSON = json.loads(craneJSONData)
        return Response({'message': 'success', 'rackJSON': rackJSON, 'check_data': self.check_data, 'crane_data': 'craneJSON'})

    def serialize_racks(self, myracks):
        rackJSONData = json.dumps(myracks, indent=4, cls=ElectroEncoder)
        rackJSON = json.loads(rackJSONData)
        return rackJSON
import json
from rest_framework.response import Response
from rest_framework.views import APIView

from electroplating_automation.tank_functions import CraneOperation, CraneTrack, RackTrack, calc_operation_time, calc_rack_shift_time, calculate_tank_shift_time, find_next_tank, get_closest_crane, get_min_time_left_racks, rack_drop_time_mins, crane_2_tanks, crane_2_start_tank_number, tank_cross_time, rack_pick_time_mins
from .models import ElectroEncoder, Tank
import copy
# now to set the aded times available option
# when the result is returned 1, I can add that data to the list upon each step
# ther is just one extra time and that is when there is time still left for the other tank
# You also need to accomodate the equals case
# you need to write a code for accomodating the same type tanks
# it all boils down to which tank i should be deleting.
# I shouldnt be deleting the latest one, but the one causing the problem, and update accordingly
# assume that the crane is always in the down position

# add a rack not at every shift, but at the given time

class CraneTwoView(APIView):

    cycle_x_time_period = 10.48
    cycle_y_time_period = 26.08

    cycle_number = 1

    time_t = 0
    # after each shift, update this time

    myracks = []
    mycranes = []

    crane_ops = []
    check_data = []

    final_rack_shift_time = 2*rack_pick_time_mins + 2*rack_drop_time_mins +tank_cross_time
# the one added first will be the one most forward
# or i can return the least remaining rack time tank then if no same type tank is empty
# the dropped crane is the base state like a deadlift

    # check if this is the time if a new rack from crane 1 is coming
    def check_shift_operations_incoming_rack(self,current_rack, new_rack, myTanks, myFirstCrane):
        current_tank = myTanks.get(tank_number = current_rack.tank_number)
        mins_available_current_rack = current_rack.remaining_tank_time

        new_tank = myTanks.get(tank_number = new_rack.tank_number)


        time_taken_to_get_crane_to_new_tank =rack_pick_time_mins + calculate_tank_shift_time(myFirstCrane.tank_number, new_tank.tank_number) + rack_drop_time_mins

        
        time_taken_for_shifting_new_rack = time_taken_to_get_crane_to_new_tank + rack_pick_time_mins + tank_cross_time + rack_drop_time_mins
        time_left_for_current_rack_after_shifting_new_rack = mins_available_current_rack - time_taken_for_shifting_new_rack - rack_pick_time_mins - calculate_tank_shift_time(new_tank.tank_number, current_tank.tank_number) - rack_drop_time_mins
        if time_left_for_current_rack_after_shifting_new_rack < 0:
            return {'result_id': 0,}

        return {'result_id': 1, 'time_taken_for_shifting_new_rack': time_taken_for_shifting_new_rack,}
    # current rack is basically the min time rack
    def perform_shift_operations_incoming_rack(self,current_rack, myTanks):
        myFirstCrane = self.mycranes[0]
        new_rack_index = len(self.myracks) - 1
        new_rack = self.myracks[new_rack_index]
        ops_resultCheck_map = self.check_shift_operations_incoming_rack(current_rack, new_rack, myTanks, myFirstCrane)
        
        if ops_resultCheck_map['result_id'] == 1:
            time_taken_for_shifting_new_rack = ops_resultCheck_map['time_taken_for_shifting_new_rack']

            for rack in self.myracks:
                rack.remaining_tank_time = rack.remaining_tank_time - time_taken_for_shifting_new_rack

            new_rack.remaining_tank_time = float(myTanks.get(tank_number = new_rack.tank_number).immersion_time_mins)
            new_rack.entry_moment_next_rack_remainingTankTime = new_rack.entry_moment_next_rack_remainingTankTime - time_taken_for_shifting_new_rack
            old_tank_number = self.mycranes[0].tank_number
            myFirstCrane.tank_number = 1
            self.mycranes[0] = myFirstCrane

            crane_op = CraneOperation(0, old_tank_number, -1, 1, new_rack_index)
            self.crane_ops.append(time_taken_for_shifting_new_rack)
            self.crane_ops.append(crane_op)
            result_n = self.calculate_racks_and_cranes()
            '''
            if result_n['result_id'] ==2:
                crane_op = CraneOperation(0, old_tank_number, -1, 1, new_rack_index)
                self.crane_ops.append(time_taken_for_shifting_new_rack)
                self.crane_ops.append(crane_op)
                self.check_data.append(self.serialize_racks(self.myracks))
                self.check_data.append(new_rack_index)
            '''
            return result_n
        else:
            return ops_resultCheck_map
# if that is the case, then i might not need to deupdate
    def check_shift_operations(self, sortedRacks, myTanks):
        if len(sortedRacks) == 1:
            return {'result_id': 0, 'wha': 'wha'}
        current_rack = sortedRacks[0]
        current_rack_index = current_rack.rack_index
        current_tank = myTanks.get(tank_number = current_rack.tank_number)
        mins_available_current_rack = current_rack.remaining_tank_time
        myCraneIndex = get_closest_crane(self.mycranes, current_rack)

        if self.mycranes[myCraneIndex].tank_number == current_tank.tank_number:
            time_taken_to_get_crane_to_current_tank = 0
        else:
            time_taken_to_get_crane_to_current_tank = rack_pick_time_mins + calculate_tank_shift_time(self.mycranes[myCraneIndex].tank_number, current_tank.tank_number) + rack_drop_time_mins

        time_available_for_current_rack_after_getting_crane_to_current_tank = mins_available_current_rack - time_taken_to_get_crane_to_current_tank
        
        other_rack = sortedRacks[1]
        other_tank = myTanks.get(tank_number = other_rack.tank_number)
        mins_available_other_rack = other_rack.remaining_tank_time

        # if next tank already has a rack in it, then it fails yet again, and this needs to be checked before any other check, and in this case,
        # we can use the entry shift time variable


        if time_available_for_current_rack_after_getting_crane_to_current_tank < 0:
            return {'result_id': 0,'time_available_for_current_rack_after_getting_crane_to_current_tank': time_available_for_current_rack_after_getting_crane_to_current_tank}
        
        current_next_tank = find_next_tank(current_tank, self.myracks)
        

        time_left_for_other_rack_after_shifting_current_rack = mins_available_other_rack - ((mins_available_current_rack) + calc_rack_shift_time(current_tank, self.myracks) + rack_pick_time_mins + calculate_tank_shift_time(current_next_tank.tank_number, other_tank.tank_number) + rack_drop_time_mins)
        if time_left_for_other_rack_after_shifting_current_rack < 0:
            return {'result_id': 0, 'time_left_for_other_rack_after_shifting_current_rack': time_left_for_other_rack_after_shifting_current_rack}

        return {'result_id': 1, 'time_taken_to_get_crane_to_current_tank': time_taken_to_get_crane_to_current_tank, 'current_tank': current_tank, 'current_rack_index': current_rack_index, 'current_next_tank': current_next_tank, 'myCraneIndex': myCraneIndex, 'time_left_for_other_rack_after_shifting_current_rack': time_left_for_other_rack_after_shifting_current_rack}

    def perform_shift_operations(self,sortedRacks, myTanks):
        ops_resultCheck_map = self.check_shift_operations(sortedRacks, myTanks)
        print(ops_resultCheck_map)
        if self.myracks[0].tank_number == 15:
        #if self.myracks[0].tank_number == len(myTanks):
            self.final_racks_list = self.myracks
            return {'result_id': 2}
        if ops_resultCheck_map['result_id'] ==1:
            time_taken_to_get_crane_to_current_tank = ops_resultCheck_map['time_taken_to_get_crane_to_current_tank']
            current_tank = ops_resultCheck_map['current_tank']
            current_rack_index = ops_resultCheck_map['current_rack_index']
            current_next_tank = ops_resultCheck_map['current_next_tank']
            myCraneIndex = ops_resultCheck_map['myCraneIndex']
            self.check_data.append(current_rack_index)
            self.check_data.append(self.serialize_racks(self.myracks))
            the_remaining_tank_time = self.myracks[current_rack_index].remaining_tank_time
            for rack in self.myracks:
                rack.remaining_tank_time = rack.remaining_tank_time - ((the_remaining_tank_time) + calc_rack_shift_time(current_tank, self.myracks))

            self.time_t = self.time_t + (the_remaining_tank_time) + calc_rack_shift_time(current_tank, self.myracks)

            self.myracks[current_rack_index].tank_number = current_next_tank.tank_number
            self.myracks[current_rack_index].remaining_tank_time = float(current_next_tank.immersion_time_mins)
            self.mycranes[myCraneIndex].tank_number = current_next_tank.tank_number
            self.check_data.append(self.serialize_racks(self.myracks))
            result_n = self.calculate_racks_and_cranes()
            '''
            if result_n['result_id'] ==2:
                crane_op = CraneOperation(0, old_tank_number, current_tank.tank_number, current_next_tank.tank_number, current_rack_index)
                self.crane_ops.append(time_taken_to_get_crane_to_current_tank)
                self.crane_ops.append(crane_op)
                self.check_data.append(self.serialize_racks(self.myracks))
                self.check_data.append(current_rack_index)
            '''
            return result_n
        else:
            return ops_resultCheck_map

    # for the line shift, you just need to add another clause that if shift bw
    # tank 30 and 31, then add to the crane move time
    # if more than one crane, the times shouldnt be added cumulatively
    # jus be careful of that
    # the check needs to be performed after every crane_shift movement.
    # if the value is less than zero, stop it right there, and perform a sub operation.
    # add a new rack, but do not move the crane to this point just yet, first check shift operation
    # first lets consider the case of it being greater than 0
    # which endes first
    # so once you have the min time racks list, you first need to check this before anything else

    def check_cycle_completion(self, current_rack):
        if self.cycle_number % 2 !=0:
            remaining_cycle_time = self.cycle_x_time_period - self.time_t
            time_available_current_tank = current_rack.remaining_tank_time
            # basically, the incoming rack should be added for whatever case, and then any sorted racks or calculations should be made
            # and if remaining cycle time is less than currentrack.remaining time + rack shift + then add it first
            current_tank = current_rack.tank_number
            time_left_to_cycle_finnish_after_shifting_current_tank = remaining_cycle_time - (time_available_current_tank + calc_rack_shift_time(current_tank, self.myracks))
            if time_left_to_cycle_finnish_after_shifting_current_tank < 0:
                # add new rack first and update the times with a clause within the check and perform shift operations
                # if the checks fail, then there is no point in going forward anyway. If the checks pass, then add a further check, if
                # the new rack is also to be added somewhere in the middle.
                # add the new rack, remove the remaining cycle time from all the other racks. if the remaining cycle time becomes
                # negative for the current rack, then for sure, sure, it was added during the shift, compensate for this time and 
                # make the necessary adjusments
                pass
            if remaining_cycle_time > 0:
                return False
            else:
                time_passed_since_cycle_completion = self.time_t - self.cycle_x_time_period
                self.cycle_number = self.cycle_number + 1
                self.time_t = self.time_t - self.cycle_x_time_period
                return True
        else:
            remaining_cycle_time = self.cycle_y_time_period - self.time_t
            if remaining_cycle_time < 0:
                self.cycle_number = self.cycle_number + 1
                self.time_t = self.time_t - self.cycle_y_time_period
                return True
            else:
                return False

    def calculate_racks_and_cranes(self):

        myTanks = crane_2_tanks
        tanks_list = list(myTanks)
        no_of_tanks = len(tanks_list)

        no_of_racks = len(self.myracks)

        if no_of_racks == 0:
            new_rack_index = no_of_racks
            first_tank = myTanks.get(tank_number = 15)
            new_rack = RackTrack(new_rack_index, 15, (float(first_tank.immersion_time_mins)), -1, -1, -1, -1)
            self.myracks.append(new_rack)
            self.time_t = self.time_t + rack_pick_time_mins + tank_cross_time + rack_drop_time_mins
            new_next_tank = find_next_tank(first_tank, self.myracks)
            new_rack.tank_number = new_next_tank.tank_number
            new_rack.remaining_tank_time = float(new_next_tank.immersion_time_mins)
            self.myracks[new_rack_index] = new_rack
            myCraneIndex = get_closest_crane(self.mycranes, new_rack)
            self.mycranes[myCraneIndex].tank_number = new_next_tank.tank_number
            self.time_t = self.time_t + calc_operation_time(first_tank, new_next_tank, myTanks)
            temp_racks_0 = copy.deepcopy(self.myracks)
            temp_cranes_0 = copy.deepcopy(self.mycranes)
            result_Map = self.calculate_racks_and_cranes(temp_racks_0, temp_cranes_0)

            # if it is getting false at the last tank, then i have achieved my purpose
            # what about the initial time
            while result_Map['result_id'] !=2:
                # first check cycle completion, then actually perform the shift
                # check whether cycle completion is ending first or rack_remaining time is ending first
                firstRack = self.myracks[0]
                first_rack_tankNumber = firstRack.tank_number
                the_tank = myTanks.get(tank_number = first_rack_tankNumber)
                the_next_tank = find_next_tank(the_tank, self.myracks)
                self.check_cycle_completion(firstRack)
                firstRack.tank_number = the_next_tank.tank_number
                firstRack.remaining_tank_time = float(the_next_tank.immersion_time_mins)
                self.myracks[0] = firstRack
                myCraneIndex = get_closest_crane(self.mycranes, firstRack)
                self.mycranes[myCraneIndex].tank_number = the_next_tank.tank_number
                self.time_t = self.time_t + calc_operation_time(first_tank, new_next_tank, myTanks)
                temp_racks_1 = copy.deepcopy(self.myracks)
                temp_cranes_1 = copy.deepcopy(self.mycranes)
                result_Map = self.calculate_racks_and_cranes(temp_racks_1, temp_cranes_1)
                if firstRack.tank_number == no_of_tanks:
                    break
            return result_Map
            # last case scenario, I will just shift the first tank forward

        # first lets try this process by adding a new rack

        else:

            myMinRacks = get_min_time_left_racks(self.myracks)

            current_rack = myMinRacks[0]

            is_new_rack_added = False

            if self.myracks[no_of_racks - 1].tank_number !=1 :

                new_rack_index = no_of_racks
                first_tank = myTanks.get(tank_number = 1)

                entry_moment_shift_time_available = current_rack.remaining_tank_time - (rack_pick_time_mins + calculate_tank_shift_time(self.mycranes[0].tank_number, 1) + tank_cross_time + rack_drop_time_mins + rack_pick_time_mins + tank_cross_time + rack_drop_time_mins + calculate_tank_shift_time(1, current_rack.tank_number))
                if entry_moment_shift_time_available >= 0:
                    entry_moment_shift_time_available_store = entry_moment_shift_time_available
                    entry_moment_next_rack_number = no_of_racks - 1
                    entry_moment_next_rack_tank_number = self.myracks[no_of_racks - 1].tank_number

                    sub_new_rack = RackTrack(new_rack_index, 1, (float(first_tank.immersion_time_mins)), entry_moment_shift_time_available, current_rack.rack_index, current_rack.tank_number, current_rack.remaining_tank_time)
                    self.myracks.append(sub_new_rack)
                    is_new_rack_added = True
                    temp_current_rack_2 = copy.deepcopy(current_rack)
                    temp_racks_2 = copy.deepcopy(self.myracks)
                    temp_Tanks_2 = myTanks
                    temp_cranes_2 = copy.deepcopy(self.mycranes)
                    new_result = self.perform_shift_operations_incoming_rack(temp_current_rack_2, temp_Tanks_2)

            if not is_new_rack_added:
                sortedRacks = get_min_time_left_racks(self.myracks)
                sortedRacks_3 = copy.deepcopy(sortedRacks)
                temp_Tanks_3 = myTanks
                new_result = self.perform_shift_operations(sortedRacks_3, temp_Tanks_3)
                is_new_rack_added = False

            
            if new_result['result_id'] != 2:
                if is_new_rack_added and self.myracks[new_rack_index].tank_number == 1:
                    if 'current_rack_time_shift_needed' in new_result and new_result['current_rack_index'] == new_rack_index and new_result['current_rack_time_shift_needed'] > 0 and new_result['current_rack_time_shift_needed'] < self.myracks[new_rack_index].entry_moment_shift_time_available:
                        while new_result['current_rack_time_shift_needed'] < self.myracks[new_rack_index].entry_moment_shift_time_available:
                            for rack in self.myracks:
                                rack.remaining_tank_time = rack.remaining_tank_time - new_result['current_rack_time_shift_needed'] 
                            self.myracks[new_rack_index].entry_moment_shift_time_available = self.myracks[new_rack_index].entry_moment_shift_time_available - new_result['current_rack_time_shift_needed']
                            self.myracks[new_rack_index].entry_moment_next_rack_remainingTankTime = self.myracks[new_rack_index].entry_moment_next_rack_remainingTankTime - new_result['current_rack_time_shift_needed']
                            self.myracks[new_rack_index].remaining_tank_time = float(myTanks.get(tank_number = self.myracks[new_rack_index].tank_number).immersion_time_mins)
                            sortedRacks = get_min_time_left_racks(self.myracks)
                            shifted_rack_index = new_result['current_rack_index']
                            sortedRacks_4 = copy.deepcopy(sortedRacks)
                            temp_racks_4 = copy.deepcopy(self.myracks)
                            temp_Tanks_4 = myTanks
                            temp_cranes_4 = copy.deepcopy(self.mycranes)
                            new_result = self.perform_shift_operations(sortedRacks_4, temp_Tanks_4)
                            if new_result['result_id'] == 2:
                                return new_result
                            if 'current_rack_time_shift_needed' not in new_result:
                                break
                    # it will compare the difference between the store and the current, then add that time to the store
                    # along with the current
                    #self.check_data.append(new_rack_index)
                    #self.check_data.append(self.serialize_racks(self.myracks))
                    if 'current_rack_time_shift_needed' not in new_result:
                        del self.myracks[new_rack_index]
                        #self.check_data.append(new_rack_index)
                        #self.check_data.append(self.serialize_racks(self.myracks))
                        sortedRacks = get_min_time_left_racks(self.myracks)
                        # if it is not a success, then try without the new_rack
                        sortedRacks_5 = copy.deepcopy(sortedRacks)
                        temp_racks_5 = copy.deepcopy(self.myracks)
                        temp_Tanks_5 = myTanks
                        temp_cranes_5 = copy.deepcopy(self.mycranes)
                        new_result = self.perform_shift_operations(sortedRacks_5, temp_Tanks_5)
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
        self.mycranes.append(CraneTrack(0, 15))
        e_result = self.calculate_racks_and_cranes()
        print(e_result)
        rackJSONData = json.dumps(self.final_racks_list, indent=4, cls=ElectroEncoder)
        rackJSON = json.loads(rackJSONData)
        craneJSONData = json.dumps(self.crane_ops, indent=4, cls=ElectroEncoder)
        craneJSON = json.loads(craneJSONData)
        #print(calc_operation_time(1,14, crane_2_tanks) + 0.17*2 + 0.07*2 + 0.07*15)
        #print(0.98 + calc_operation_time(6,14, crane_2_tanks) + 0.17 + 0.07)
        #print(calc_operation_time(14,19, crane_2_tanks) + 0.17 + 0.07)
        return Response({'message': 'success', 'rackJSON': rackJSON, 'check_data': self.check_data, 'crane_data': craneJSON})

    def serialize_racks(self, myracks):
        rackJSONData = json.dumps(myracks, indent=4, cls=ElectroEncoder)
        rackJSON = json.loads(rackJSONData)
        return rackJSON
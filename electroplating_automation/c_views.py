import json
from rest_framework.response import Response
from rest_framework.views import APIView

from electroplating_automation.tank_functions import CraneOperation, CraneTrack, RackTrack, calc_operation_time, calc_rack_shift_time, calculate_tank_shift_time, find_next_tank, get_closest_crane, get_min_time_left_racks, rackless_pick_time_mins, rackless_drop_time_mins, crane_2_start_tank_number, crane_2_tanks, crane_3_start_tank_number, crane_3_tanks, crane_4_start_tank_number, crane_4_tanks, crane_5_start_tank_number, crane_5_tanks, tank_cross_time, rack_pick_time_mins, rack_drop_time_mins, rackless_pick_time_mins, rackless_drop_time_mins
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

class CraneXCalculator():
    def __init__(self, crane_x_start_tank_number, crane_x_tanks, cycle_types, last_tank_numbers):
        self.crane_x_start_tank_number = crane_x_start_tank_number
        self.crane_x_tanks = crane_x_tanks
        self.crane_x_start_tank = crane_x_tanks.get(tank_number = crane_x_start_tank_number)
        self.first_rack = RackTrack(0, crane_x_start_tank_number, (float(self.crane_x_start_tank.immersion_time_mins)), -1, -1, -1, -1)
        self.first_crane = CraneTrack(0, crane_x_start_tank_number)
        self.cycle_types = cycle_types
        self.last_tank_numbers = last_tank_numbers

    current_cycle_type = 0

    time_t = 0
    total_time = 0
    # after each shift, update this time
    myracks = []
    mycranes = []

    crane_ops = []
    check_data = []

    def perform_shift_operations_incoming_rack(self,current_rack, remaining_cycle_time, time_left_to_cycle_finnish_after_finnishing_current_tank_time, time_left_to_cycle_finnish_after_shifting_current_rack):
        new_rack_index = len(self.myracks)
        if time_left_to_cycle_finnish_after_finnishing_current_tank_time < 0:
            time_required_to_shift_to_incoming_rack = rackless_pick_time_mins + calculate_tank_shift_time(self.mycranes[0].tank_number, self.cycle_types[self.current_cycle_type]['cycle_start_tank']) + rackless_drop_time_mins
            time_to_new_rack_end = float(self.crane_x_tanks.get(tank_number = self.cycle_types[self.current_cycle_type]['cycle_start_tank']).immersion_time_mins) + remaining_cycle_time
            
            if time_required_to_shift_to_incoming_rack >= time_to_new_rack_end:
                return False
            else:
                for rack in self.myracks:
                    rack.remaining_tank_time = rack.remaining_tank_time - remaining_cycle_time
                new_rack = RackTrack(new_rack_index, self.cycle_types[self.current_cycle_type]['cycle_start_tank'], float(self.crane_x_tanks.get(tank_number = self.cycle_types[self.current_cycle_type]['cycle_start_tank']).immersion_time_mins), -1, len(self.myracks) - 1, self.myracks[len(self.myracks) - 1].tank_number, current_rack.remaining_tank_time)
                x_tank = self.crane_x_tanks.get(tank_number = self.cycle_types[self.current_cycle_type]['cycle_start_tank'])
                
                self.myracks.append(new_rack)
                self.time_t = 0
                self.total_time = self.total_time + remaining_cycle_time
                old_cycle_type = self.current_cycle_type
                self.current_cycle_type = self.current_cycle_type + 1
                if self.current_cycle_type == len(self.cycle_types):
                    self.current_cycle_type = 0
                crane_old_tank_number = self.mycranes[0].tank_number
                if current_rack.remaining_tank_time > new_rack.remaining_tank_time:
                    self.mycranes[0].tank_number = self.cycle_types[self.current_cycle_type]['cycle_start_tank']
                current_tank = self.crane_x_tanks.get(tank_number = current_rack.tank_number)
                self.check_data.append({'total_time_passed': self.total_time, 'cycle time passed': self.time_t, 'current cycle number': self.current_cycle_type, 'shifted_rack_index': len(self.myracks) - 1, 'crane_current_tank_number': self.mycranes[0].tank_number, 'new_tank': self.crane_x_tanks.get(tank_number = self.cycle_types[old_cycle_type]['cycle_start_tank']).process_name})
                self.check_data.append(self.serialize_electro(self.myracks))
                self.check_data.append({'------': '-------------------------------------------------------------------------------------------'})
                return True
        elif time_left_to_cycle_finnish_after_shifting_current_rack < 0:
            current_tank = self.crane_x_tanks.get(tank_number = current_rack.tank_number)
            time_left_to_cycle_finnish_beyond_tank_time = remaining_cycle_time - current_rack.remaining_tank_time
            time_used_up_for_new_rack_while_shifting_current_rack = calc_rack_shift_time(current_tank, self.myracks) - time_left_to_cycle_finnish_beyond_tank_time
            the_remaining_tank_time = current_rack.remaining_tank_time
            for rack in self.myracks:
                rack.remaining_tank_time = rack.remaining_tank_time - ((the_remaining_tank_time) + calc_rack_shift_time(current_tank, self.myracks))

            self.total_time = self.total_time + (the_remaining_tank_time) + calc_rack_shift_time(current_tank, self.myracks)
            current_next_tank = find_next_tank(current_tank, self.myracks)
            current_rack.tank_number = current_next_tank.tank_number
            current_rack.remaining_tank_time = float(current_next_tank.immersion_time_mins)
            crane_old_tank_number = self.mycranes[0].tank_number
            self.mycranes[0].tank_number = current_next_tank.tank_number
            new_rack_remaining_tank_time = (float(self.crane_x_start_tank.immersion_time_mins)) - time_used_up_for_new_rack_while_shifting_current_rack
            new_rack = RackTrack(new_rack_index, self.cycle_types[self.current_cycle_type]['cycle_start_tank'], new_rack_remaining_tank_time, -1, len(self.myracks) - 1, self.myracks[len(self.myracks) - 1].tank_number, the_remaining_tank_time)
            self.myracks.append(new_rack)
            self.time_t = time_used_up_for_new_rack_while_shifting_current_rack
            self.current_cycle_type = self.current_cycle_type + 1
            if self.current_cycle_type == len(self.cycle_types):
                    self.current_cycle_type = 0
            next_tank = self.crane_x_tanks.get(tank_number = current_rack.tank_number)
            self.check_data.append({'total_time_passed': self.total_time, 'cycle time passed': self.time_t, 'current cycle number': self.current_cycle_type, 'shifted_rack_index': current_rack.rack_index, 'new_rack_index': new_rack.rack_index, 'crane_old_tank_number': crane_old_tank_number, 'next_tank_number': self.mycranes[0].tank_number, 'next_tank': next_tank.process_name})
            self.check_data.append(self.serialize_electro(self.myracks))
            self.check_data.append({'------': '-------------------------------------------------------------------------------------------'})
            return True
        else:
            self.perform_simple_shift_operations()
       
    def check_shift_operations(self):
        sortedRacksz = get_min_time_left_racks(self.myracks)
        sortedRacks = copy.deepcopy(sortedRacksz)
        #'''
        for x_rack in sortedRacks:
            for special_number in self.last_tank_numbers:
                if x_rack.tank_number == special_number and len(self.myracks)>1:
                    special_index = x_rack.rack_index
                    sortedRacks.remove(x_rack)
                    if self.myracks[special_index].remaining_tank_time < 0:
                        del self.myracks[special_index]
                        for rrack in self.myracks:
                            if rrack.rack_index > special_index:
                                rrack.rack_index = rrack.rack_index - 1
        
        #'''
        sortedRacks = get_min_time_left_racks(sortedRacks)
        #'''
        current_rack = sortedRacks[0]
        #print(self.serialize_electro(sortedRacks))
        current_rack_index = current_rack.rack_index
        current_tank = self.crane_x_tanks.get(tank_number = current_rack.tank_number)
        mins_available_current_rack = current_rack.remaining_tank_time
        myCraneIndex = get_closest_crane(self.mycranes, current_rack)
        if self.mycranes[myCraneIndex].tank_number == current_tank.tank_number:
            time_taken_to_get_crane_to_current_tank = 0
        else:
            time_taken_to_get_crane_to_current_tank = rackless_pick_time_mins + calculate_tank_shift_time(self.mycranes[myCraneIndex].tank_number, current_tank.tank_number) + rackless_drop_time_mins

        time_available_for_current_rack_after_getting_crane_to_current_tank = mins_available_current_rack - time_taken_to_get_crane_to_current_tank

        # if next tank already has a rack in it, then it fails yet again, and this needs to be checked before any other check, and in this case,
        # we can use the entry shift time variable
        
        if time_available_for_current_rack_after_getting_crane_to_current_tank < 0:
            return {'result_id': 0,'time_available_for_current_rack_after_getting_crane_to_current_tank': time_available_for_current_rack_after_getting_crane_to_current_tank}
        
        current_next_tank = find_next_tank(current_tank, self.myracks)
        
        if len(sortedRacks) > 1:
            other_rack = sortedRacks[1]
            other_tank = self.crane_x_tanks.get(tank_number = other_rack.tank_number)
            mins_available_other_rack = other_rack.remaining_tank_time

            time_left_for_other_rack_after_shifting_current_rack = mins_available_other_rack - (mins_available_current_rack + calc_rack_shift_time(current_tank, self.myracks) + rackless_pick_time_mins + calculate_tank_shift_time(current_next_tank.tank_number, other_tank.tank_number) + rackless_drop_time_mins)
            if time_left_for_other_rack_after_shifting_current_rack < 0:
                print(calc_rack_shift_time(current_tank, self.myracks))
                print(mins_available_other_rack)
                print('sdssa')
                return {'result_id': 0, 'time_left_for_other_rack_after_shifting_current_rack': time_left_for_other_rack_after_shifting_current_rack}

        return {'result_id': 1, 'time_taken_to_get_crane_to_current_tank': time_taken_to_get_crane_to_current_tank, 'current_tank': current_tank, 'current_rack_index': current_rack_index, 'current_next_tank': current_next_tank, 'myCraneIndex': myCraneIndex}

    def perform_simple_shift_operations(self):
        ops_resultCheck_map = self.check_shift_operations()
        #if self.myracks[0].tank_number == 15:
        if ops_resultCheck_map['result_id'] ==1:
            current_tank = ops_resultCheck_map['current_tank']
            current_rack_index = ops_resultCheck_map['current_rack_index']
            current_next_tank = ops_resultCheck_map['current_next_tank']
            myCraneIndex = ops_resultCheck_map['myCraneIndex']
            the_remaining_tank_time = self.myracks[current_rack_index].remaining_tank_time
            for rack in self.myracks:
                rack.remaining_tank_time = rack.remaining_tank_time - ((the_remaining_tank_time) + calc_rack_shift_time(current_tank, self.myracks))

            self.time_t = self.time_t + (the_remaining_tank_time) + calc_rack_shift_time(current_tank, self.myracks)
            self.total_time = self.total_time + (the_remaining_tank_time) + calc_rack_shift_time(current_tank, self.myracks)
            self.myracks[current_rack_index].tank_number = current_next_tank.tank_number
            self.myracks[current_rack_index].remaining_tank_time = float(current_next_tank.immersion_time_mins)
            crane_old_tank_number = self.mycranes[myCraneIndex].tank_number
            self.mycranes[myCraneIndex].tank_number = current_next_tank.tank_number
            next_tank = self.crane_x_tanks.get(tank_number = current_next_tank.tank_number)
            self.check_data.append({'total_time_passed': self.total_time, 'cycle time passed': self.time_t, 'current cycle number': self.current_cycle_type, 'shifted_rack_index': current_rack_index, 'crane_old_tank_number': crane_old_tank_number, 'next_tank_number': current_next_tank.tank_number, 'next_tank': next_tank.process_name})
            self.check_data.append(self.serialize_electro(self.myracks))
            self.check_data.append({'------': '-------------------------------------------------------------------------------------------'})
            return {'result_id': 1}
        else:
            return ops_resultCheck_map

    def serialize_electro(self, myracks):
        rackJSONData = json.dumps(myracks, indent=4, cls=ElectroEncoder)
        rackJSON = json.loads(rackJSONData)
        return rackJSON

    def check_cycle_completion(self):
        rack_check_1 = self.check_shift_operations()
        sortedRacks = get_min_time_left_racks(self.myracks)
        current_rack = sortedRacks[0]
        if rack_check_1['result_id'] != 1:
            return rack_check_1
        #print(self.current_cycle_type)
        remaining_cycle_time = self.cycle_types[self.current_cycle_type]['cycle_period'] - self.time_t
        time_available_current_tank = current_rack.remaining_tank_time
        current_tank = self.crane_x_tanks.get(tank_number = current_rack.tank_number)
        time_left_to_cycle_finnish_after_finnishing_current_tank_time = remaining_cycle_time - time_available_current_tank
        # just remove the remaining cycle time i mean
        time_left_to_cycle_finnish_after_shifting_current_rack = time_left_to_cycle_finnish_after_finnishing_current_tank_time - calc_rack_shift_time(current_tank, self.myracks)
        if time_left_to_cycle_finnish_after_shifting_current_rack < 0:
            iq_res = self.perform_shift_operations_incoming_rack(current_rack, remaining_cycle_time, time_left_to_cycle_finnish_after_finnishing_current_tank_time, time_left_to_cycle_finnish_after_shifting_current_rack)
            if not iq_res:
                rack_check_1['result_id'] = 0
            return rack_check_1
        else:
            the_result = self.perform_simple_shift_operations()
            return the_result  

            
    # i return false only at the checks

def present_crane_result(crane_x_start_tank_number, crane_x_tanks, cycle_types, last_tank_numbers):
    crane_x_calculator = CraneXCalculator(crane_x_start_tank_number, crane_x_tanks, cycle_types, last_tank_numbers)
    crane_x_calculator.mycranes.append(crane_x_calculator.first_crane)
    crane_x_calculator.myracks.append(crane_x_calculator.first_rack)
    start_tank = crane_x_calculator.crane_x_tanks.get(tank_number = crane_x_start_tank_number)
    crane_x_calculator.check_data.append({'cycle time passed': crane_x_calculator.time_t, 'current cycle number': crane_x_calculator.current_cycle_type, 'shifted_rack_index': crane_x_calculator.first_rack.rack_index, 'crane_start_tank_number': crane_x_calculator.first_crane.tank_number, 'start_tank': start_tank.process_name})
    crane_x_calculator.check_data.append(crane_x_calculator.serialize_electro(crane_x_calculator.myracks))
    crane_x_calculator.check_data.append({'------': '-------------------------------------------------------------------------------------------'})
    i = 0
    batch_current_cycle_type = 17
    while i <= batch_current_cycle_type:
        z_result = crane_x_calculator.check_cycle_completion()
        if z_result['result_id'] == 0:
            break
        i = i+1
    #'''
    print(z_result)
    
    return crane_x_calculator

class CraneTwoView(APIView):
    def get(self, request, *args, **kwargs):
        crane_2_calculator = present_crane_result(crane_2_start_tank_number, crane_2_tanks, [{'cycle_start_tank':crane_2_start_tank_number, 'cycle_period': 10.13}, {'cycle_start_tank':15, 'cycle_period': 25.5}], [31, 32, 33, 34])
        return Response({'rack_pick_time_mins': rack_pick_time_mins, 'rack_drop_time_mins': rack_drop_time_mins, 'rackless_pick_time_mins': rackless_pick_time_mins, 'rackless_drop_time_mins': rackless_drop_time_mins, 'tank_cross_time_mins': tank_cross_time, 'cycles':[{'cycle_start_tank':crane_2_start_tank_number, 'cycle_period': 10.13}, {'cycle_start_tank':15, 'cycle_period': 25.5}], 'last tanks': [31, 32, 33, 34], 'Data Flow': crane_2_calculator.check_data,})


class CraneThreeView(APIView):
    def get(self, request, *args, **kwargs):
        #print(crane_3_tanks.get(tank_number=34).immersion_time_mins)
        crane_3_calculator = present_crane_result(crane_3_start_tank_number, crane_3_tanks, [{'cycle_start_tank':32, 'cycle_period': 10.2}, {'cycle_start_tank':33, 'cycle_period': 25.57}, {'cycle_start_tank':34, 'cycle_period': 10.2}, {'cycle_start_tank':31, 'cycle_period': 25.29}], [43])
        return Response({'rack_pick_time_mins': rack_pick_time_mins, 'rack_drop_time_mins': rack_drop_time_mins, 'rackless_pick_time_mins': rackless_pick_time_mins, 'rackless_drop_time_mins': rackless_drop_time_mins, 'tank_cross_time_mins': tank_cross_time, 'cycles':[{'cycle_start_tank':32, 'cycle_period': 10.2}, {'cycle_start_tank':33, 'cycle_period': 25.57}, {'cycle_start_tank':34, 'cycle_period': 10.2}, {'cycle_start_tank':31, 'cycle_period': 25.29}], 'last tanks': [43],'Data Flow': crane_3_calculator.check_data})

class CraneFourView(APIView):
    def get(self, request, *args, **kwargs):
        crane_4_calculator = present_crane_result(crane_4_start_tank_number, crane_4_tanks, [{'cycle_start_tank':crane_4_start_tank_number, 'cycle_period': 11.92}, {'cycle_start_tank':crane_4_start_tank_number, 'cycle_period': 23.71}], [52])
        return Response({'rack_pick_time_mins': rack_pick_time_mins, 'rack_drop_time_mins': rack_drop_time_mins, 'rackless_pick_time_mins': rackless_pick_time_mins, 'rackless_drop_time_mins': rackless_drop_time_mins, 'tank_cross_time_mins': tank_cross_time, 'cycles':[{'cycle_start_tank':crane_4_start_tank_number, 'cycle_period': 11.92}, {'cycle_start_tank':crane_4_start_tank_number, 'cycle_period': 23.71}], 'last tanks': [52], 'Data Flow': crane_4_calculator.check_data,})

class CraneFiveView(APIView):
    def get(self, request, *args, **kwargs):
        crane_5_calculator = present_crane_result(crane_5_start_tank_number, crane_5_tanks, [{'cycle_start_tank':crane_5_start_tank_number, 'cycle_period': 11.84}, {'cycle_start_tank':crane_5_start_tank_number, 'cycle_period': 23.79}], [59])
        return Response({'rack_pick_time_mins': rack_pick_time_mins, 'rack_drop_time_mins': rack_drop_time_mins, 'rackless_pick_time_mins': rackless_pick_time_mins, 'rackless_drop_time_mins': rackless_drop_time_mins, 'tank_cross_time_mins': tank_cross_time, 'cycles': [{'cycle_start_tank':crane_5_start_tank_number, 'cycle_period': 11.84}, {'cycle_start_tank':crane_5_start_tank_number, 'cycle_period': 23.79}], 'last tanks': [59], 'Data Flow': crane_5_calculator.check_data,})
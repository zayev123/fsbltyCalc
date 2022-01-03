import json
from rest_framework.response import Response
from rest_framework.views import APIView

from electroplating_automation.tank_functions import CraneOperation, CraneTrack, RackTrack, calc_operation_time, calc_rack_shift_time, calculate_tank_shift_time, find_next_tank, get_closest_crane, get_min_time_left_racks, rackless_pick_time_mins, rackless_drop_time_mins, crane_2_start_tank_number, crane_2_end_tank_number, crane_2_tanks, crane_3_start_tank_number, crane_3_end_tank_number, crane_3_tanks, crane_4_start_tank_number, crane_4_end_tank_number, crane_4_tanks
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
    def __init__(self, crane_x_start_tank_number, crane_x_end_tank_number, crane_x_tanks, cycle_x_time_period, cycle_y_time_period):
        self.crane_x_start_tank_number = crane_x_start_tank_number
        self.crane_x_end_tank_number = crane_x_end_tank_number
        self.crane_x_tanks = crane_x_tanks
        self.crane_x_start_tank = crane_x_tanks.get(tank_number = crane_x_start_tank_number)
        self.first_rack = RackTrack(0, crane_x_start_tank_number, (float(self.crane_x_start_tank.immersion_time_mins)), -1, -1, -1, -1)
        self.first_crane = CraneTrack(0, crane_x_start_tank_number)
        self.cycle_x_time_period = cycle_x_time_period
        self.cycle_y_time_period = cycle_y_time_period

    cycle_number = 1

    time_t = 0
    # after each shift, update this time
    myracks = []
    mycranes = []

    crane_ops = []
    check_data = []

    def perform_shift_operations_incoming_rack(self,current_rack, remaining_cycle_time, time_left_to_cycle_finnish_after_finnishing_current_tank_time, time_left_to_cycle_finnish_after_shifting_current_rack):
        new_rack_index = len(self.myracks)
        if time_left_to_cycle_finnish_after_finnishing_current_tank_time < 0:
            self.check_data.append(current_rack.rack_index)
            self.check_data.append(self.serialize_electro(self.myracks))
            time_required_to_shift_to_incoming_rack = rackless_pick_time_mins + calculate_tank_shift_time(self.mycranes[0].tank_number, self.crane_x_start_tank_number) + rackless_drop_time_mins
            time_to_new_rack_end = float(self.crane_x_tanks.get(tank_number = self.crane_x_start_tank_number).immersion_time_mins) + remaining_cycle_time
            '''
            print(self.mycranes[0].tank_number)
            print(self.crane_x_start_tank_number)
            print(time_required_to_shift_to_incoming_rack)
            print(time_to_new_rack_end)
            '''
            if time_required_to_shift_to_incoming_rack >= time_to_new_rack_end:
                return False
            else:
                for rack in self.myracks:
                    rack.remaining_tank_time = rack.remaining_tank_time - remaining_cycle_time
                new_rack = RackTrack(new_rack_index, self.crane_x_start_tank_number, (float(self.crane_x_start_tank.immersion_time_mins)), -1, len(self.myracks) - 1, self.myracks[len(self.myracks) - 1].tank_number, current_rack.remaining_tank_time)
                self.myracks.append(new_rack)
                self.time_t = 0
                self.cycle_number = self.cycle_number + 1
                if current_rack.remaining_tank_time > new_rack.remaining_tank_time:
                    self.mycranes[0].tank_number = self.crane_x_start_tank_number
                self.check_data.append(self.serialize_electro(self.myracks))
                self.check_data.append(self.time_t)
                return True
        elif time_left_to_cycle_finnish_after_shifting_current_rack < 0:
            current_tank = self.crane_x_tanks.get(tank_number = current_rack.tank_number)
            
            self.check_data.append(current_rack.rack_index)
            self.check_data.append(self.serialize_electro(self.myracks))
            time_left_to_cycle_finnish_beyond_tank_time = remaining_cycle_time - current_rack.remaining_tank_time
            time_used_up_for_new_rack_while_shifting_current_rack = calc_rack_shift_time(current_tank, self.myracks) - time_left_to_cycle_finnish_beyond_tank_time
            the_remaining_tank_time = current_rack.remaining_tank_time
            for rack in self.myracks:
                rack.remaining_tank_time = rack.remaining_tank_time - ((the_remaining_tank_time) + calc_rack_shift_time(current_tank, self.myracks))

            current_next_tank = find_next_tank(current_tank, self.myracks)
            current_rack.tank_number = current_next_tank.tank_number
            current_rack.remaining_tank_time = float(current_next_tank.immersion_time_mins)
            self.mycranes[0].tank_number = current_next_tank.tank_number
            new_rack_remaining_tank_time = (float(self.crane_x_start_tank.immersion_time_mins)) - time_used_up_for_new_rack_while_shifting_current_rack
            new_rack = RackTrack(new_rack_index, self.crane_x_start_tank_number, new_rack_remaining_tank_time, -1, len(self.myracks) - 1, self.myracks[len(self.myracks) - 1].tank_number, the_remaining_tank_time)
            self.myracks.append(new_rack)
            self.time_t = time_used_up_for_new_rack_while_shifting_current_rack
            self.cycle_number = self.cycle_number + 1
            self.check_data.append(self.serialize_electro(self.myracks))
            self.check_data.append(self.time_t)
            return True
        else:
            self.perform_simple_shift_operations()
       
    def check_shift_operations(self):
        sortedRacks = get_min_time_left_racks(self.myracks)

        current_rack = sortedRacks[0]
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
        '''
        print(self.mycranes[myCraneIndex].tank_number)
        print(current_tank.tank_number)
        print(mins_available_current_rack)
        print(time_taken_to_get_crane_to_current_tank)
        print('')
        '''
        if time_available_for_current_rack_after_getting_crane_to_current_tank < 0:
            return {'result_id': 0,'time_available_for_current_rack_after_getting_crane_to_current_tank': time_available_for_current_rack_after_getting_crane_to_current_tank}
        
        current_next_tank = find_next_tank(current_tank, self.myracks)
        
        if len(sortedRacks) > 1:
            other_rack = sortedRacks[1]
            other_tank = self.crane_x_tanks.get(tank_number = other_rack.tank_number)
            mins_available_other_rack = other_rack.remaining_tank_time

            time_left_for_other_rack_after_shifting_current_rack = mins_available_other_rack - ((mins_available_current_rack) + calc_rack_shift_time(current_tank, self.myracks) + rackless_pick_time_mins + calculate_tank_shift_time(current_next_tank.tank_number, other_tank.tank_number) + rackless_drop_time_mins)
            if time_left_for_other_rack_after_shifting_current_rack < 0:
                return {'result_id': 0, 'time_left_for_other_rack_after_shifting_current_rack': time_left_for_other_rack_after_shifting_current_rack}

        return {'result_id': 1, 'time_taken_to_get_crane_to_current_tank': time_taken_to_get_crane_to_current_tank, 'current_tank': current_tank, 'current_rack_index': current_rack_index, 'current_next_tank': current_next_tank, 'myCraneIndex': myCraneIndex}

    def perform_simple_shift_operations(self):
        ops_resultCheck_map = self.check_shift_operations()
        #if self.myracks[0].tank_number == 15:
        if self.myracks[0].tank_number == list(self.crane_x_tanks)[len(list(self.crane_x_tanks)) - 1].tank_number:
            self.final_racks_list = self.myracks
            return {'result_id': 2}
        if ops_resultCheck_map['result_id'] ==1:
            current_tank = ops_resultCheck_map['current_tank']
            current_rack_index = ops_resultCheck_map['current_rack_index']
            current_next_tank = ops_resultCheck_map['current_next_tank']
            myCraneIndex = ops_resultCheck_map['myCraneIndex']
            self.check_data.append({'rack index': current_rack_index})
            self.check_data.append(self.serialize_electro(self.myracks))
            the_remaining_tank_time = self.myracks[current_rack_index].remaining_tank_time
            for rack in self.myracks:
                rack.remaining_tank_time = rack.remaining_tank_time - ((the_remaining_tank_time) + calc_rack_shift_time(current_tank, self.myracks))

            self.time_t = self.time_t + (the_remaining_tank_time) + calc_rack_shift_time(current_tank, self.myracks)

            self.myracks[current_rack_index].tank_number = current_next_tank.tank_number
            self.myracks[current_rack_index].remaining_tank_time = float(current_next_tank.immersion_time_mins)
            self.mycranes[myCraneIndex].tank_number = current_next_tank.tank_number
            self.check_data.append(self.serialize_electro(self.myracks))
            self.check_data.append({'cycle time': self.time_t})
            self.check_data.append({'cycle number': self.cycle_number})
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
        if self.cycle_number % 2 !=0:
            remaining_cycle_time = self.cycle_x_time_period - self.time_t
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
        else:
            remaining_cycle_time = self.cycle_y_time_period - self.time_t
            time_available_current_tank = current_rack.remaining_tank_time
            current_tank = self.crane_x_tanks.get(tank_number = current_rack.tank_number)
            time_left_to_cycle_finnish_after_finnishing_current_tank_time = remaining_cycle_time - time_available_current_tank
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

def present_crane_result(crane_x_start_tank_number, crane_x_end_tank_number, crane_x_tanks, cycle_x_time_period, cycle_y_time_period):
    crane_x_calculator = CraneXCalculator(crane_x_start_tank_number, crane_x_end_tank_number, crane_x_tanks, cycle_x_time_period, cycle_y_time_period)
    crane_x_calculator.mycranes.append(crane_x_calculator.first_crane)
    crane_x_calculator.myracks.append(crane_x_calculator.first_rack)
    i = 0
    batch_cycle_number = 4
    while i <= batch_cycle_number:
        if crane_x_calculator.myracks[0].tank_number == crane_x_calculator.crane_x_end_tank_number:
            #break
            i = i+1
            if i == batch_cycle_number:
                break
            del crane_x_calculator.myracks[0]
            for x_rack in crane_x_calculator.myracks:
                x_rack.rack_index = x_rack.rack_index - 1
        z_result = crane_x_calculator.check_cycle_completion()
        if z_result['result_id'] == 0:
            break
    #'''
    for f_rack in crane_x_calculator.myracks:
        if f_rack.tank_number != crane_x_calculator.crane_x_end_tank_number:
            f_tank = crane_x_calculator.crane_x_tanks.get(tank_number = f_rack.tank_number)
            f_next_tank = find_next_tank(f_tank, crane_x_calculator.myracks)
            if f_next_tank.tank_number == crane_x_calculator.crane_x_end_tank_number:
                time_to_finnish = f_rack.remaining_tank_time + calc_rack_shift_time(f_tank, crane_x_calculator.myracks)
            else:
                time_to_finnish = f_rack.remaining_tank_time + calc_rack_shift_time(f_tank, crane_x_calculator.myracks) + calc_operation_time(f_next_tank, crane_x_calculator.crane_x_end_tank_number, crane_x_calculator.crane_x_tanks, 0)
            print(time_to_finnish)
    return crane_x_calculator

class CraneTwoView(APIView):
    def get(self, request, *args, **kwargs):
        crane_2_calculator = present_crane_result(crane_2_start_tank_number, crane_2_end_tank_number, crane_2_tanks, 10.13, 25.5)
        return Response({'message': 'success', 'rackJSON': 'rackJSON', 'check_data': crane_2_calculator.check_data,})

class CraneThreeView(APIView):
    def get(self, request, *args, **kwargs):
        crane_2_calculator = present_crane_result(crane_3_start_tank_number, crane_3_end_tank_number, crane_3_tanks, 10.13, 25.5)
        return Response({'message': 'success', 'rackJSON': 'rackJSON', 'check_data': crane_2_calculator.check_data,})

class CraneFourView(APIView):
    def get(self, request, *args, **kwargs):
        crane_2_calculator = present_crane_result(crane_4_start_tank_number, crane_4_end_tank_number, crane_4_tanks, 11.6, 24.03)
        return Response({'message': 'success', 'rackJSON': 'rackJSON', 'check_data': crane_2_calculator.check_data,})
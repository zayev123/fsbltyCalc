from electroplating_automation.models import Tank
from django.db.models import Q




tank_cross_time = 0.07
final_racks_list = []


rack_pick_time_mins = 0.2
rack_drop_time_mins = 0.2
rackless_pick_time_mins = 0.14
rackless_drop_time_mins = 0.14

tanks = Tank.objects.all()
crane_1_tanks = tanks
crane_2_start_tank_number = 15
crane_2_tanks = tanks.filter(tank_number__gte=crane_2_start_tank_number)


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


def calculate_tank_shift_time(tank_a_number, tank_b_number):
    crossing_tank_qty = tank_b_number - tank_a_number
    time_for_crossing_mins = crossing_tank_qty * tank_cross_time
    return abs(time_for_crossing_mins)

def check_occupancy(the_tanks, the_racks):
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
    min_racks_list = get_min_time_left_racks(the_racks_list)
    best_tank = tanks.get(tank_number = min_racks_list[0].tank_number)

def find_next_tank(tank_a, z_racks):
    myTanks = tanks
    tank_a_number = tank_a.tank_number
    i = 1
    while i < 6:
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
            best_tank = check_occupancy(the_tanks, z_racks)
            return best_tank
        i = i+1
    return -1

    # after finding next tank, it will do +1, +1 till it finds an empty tank of the same type number

def find_next_tank_general(tank_a):
    myTanks = tanks
    tank_a_number = tank_a.tank_number
    i = 1
    while i < 5:
        tank_b_number = tank_a_number + i
        tank_b = myTanks.get(tank_number = tank_b_number)
        if tank_b.tank_type_number != tank_a.tank_type_number:
            best_tank = tank_b
            return best_tank
    return -1

def calc_rack_shift_time(tank_a, z_racks):
    tank_b = find_next_tank(tank_a, z_racks)
    total_time = calculate_tank_shift_time(tank_a.tank_number, tank_b.tank_number) + rack_pick_time_mins + rack_drop_time_mins
    return total_time

def calc_operation_time(first_tank_number, last_tank_number, myTanks):
    tanks_list = list(myTanks.filter(Q(tank_number__gte=first_tank_number) & Q(tank_number__lte=last_tank_number)))
    op_time = 0
    for tank in tanks_list:
        if tank.tank_number == last_tank_number:
            break
        next_tank = find_next_tank_general(tank)
        op_time = op_time + float(tank.immersion_time_mins) + calc_rack_shift_time(tank, next_tank)
    return op_time



def get_min_time_left_racks(racks):
    min_time_left_racks = sorted(racks, key=lambda rack: rack.remaining_tank_time)
    return min_time_left_racks

def get_sorted_cranes(cranes):
    min_time_left_racks = sorted(cranes, key=lambda crane: crane.tank_number)
    return min_time_left_racks

def get_closest_crane(cranes, rack):
    sorted_cranes = get_sorted_cranes(cranes)
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
# underscores can be evil in the console
from datetime import timedelta


def manage_presave_CompOnlyCosts(original_compCost, changed_compCost, current_comp):
    if current_comp.id != changed_compCost.company.id:
        old_comp = current_comp
        new_comp = changed_compCost.company
        old_comp.total_cost_per_hour_Rs = old_comp.total_cost_per_hour_Rs - original_compCost.per_hour_cost_Rs
        new_comp.total_cost_per_hour_Rs = new_comp.total_cost_per_hour_Rs + changed_compCost.per_hour_cost_Rs
        old_comp.save()
        new_comp.save()
    else:
        current_comp.total_cost_per_hour_Rs = current_comp.total_cost_per_hour_Rs - original_compCost.per_hour_cost_Rs + changed_compCost.per_hour_cost_Rs
        current_comp.save()


def manage_presave_prod(original_prod, changed_prod, current_comp):
    if changed_prod.total_amount_of_products_fnnished_per_hour != 0:
            changed_prod.total_cost_per_product_Rs = changed_prod.total_production_cost_per_hour_Rs / changed_prod.total_amount_of_products_fnnished_per_hour
    else:
        changed_prod.total_cost_per_product_Rs = 0
    # why not preassign sold, because sold can be more than produced sometimes
    changed_prod.total_amount_of_products_sold_per_hour = changed_prod.total_amount_of_products_fnnished_per_hour - changed_prod.total_amount_of_products_rejected_or_leftover_per_hour
    changed_prod.total_revenue_generated_per_hour_Rs = changed_prod.selling_price_per_product_Rs * changed_prod.total_amount_of_products_sold_per_hour    
    
    if current_comp.id != changed_prod.company.id:
        old_comp = current_comp
        new_comp = changed_prod.company
        # here, cost and size are changed
        old_comp.total_cost_per_hour_Rs = old_comp.total_cost_per_hour_Rs - original_prod.total_production_cost_per_hour_Rs
        old_comp.total_revenue_per_hour_Rs = old_comp.total_revenue_per_hour_Rs  - original_prod.total_revenue_generated_per_hour_Rs

        new_comp.total_cost_per_hour_Rs = new_comp.total_cost_per_hour_Rs + changed_prod.total_production_cost_per_hour_Rs
        new_comp.total_revenue_per_hour_Rs = new_comp.total_revenue_per_hour_Rs  + changed_prod.total_revenue_generated_per_hour_Rs

        old_comp.save()
        new_comp.save()   
    else:
        current_comp.total_cost_per_hour_Rs = current_comp.total_cost_per_hour_Rs - original_prod.total_production_cost_per_hour_Rs + changed_prod.total_production_cost_per_hour_Rs
        current_comp.total_revenue_per_hour_Rs = current_comp.total_revenue_per_hour_Rs  - original_prod.total_revenue_generated_per_hour_Rs + changed_prod.total_revenue_generated_per_hour_Rs
        current_comp.save()

def setEndDate(currEvent):
    duration = currEvent.days_to_complete
    my_days = int(duration)
    day_fraction = duration % 1
    my_hours = int(24 * day_fraction)
    currEvent.event_end_date = currEvent.event_start_date + timedelta(days=my_days, hours = my_hours)

def update_event_links(currEvent):
    prevy_events = list(currEvent.previous_related_events.all())
    if not prevy_events:
        currEvent.event_start_date = currEvent.production.project_start_date
        currEvent.latest_previous_dependent_event = None
    else:
        currEvent.latest_previous_dependent_event = str(prevy_events[0])
        currEvent.event_start_date = prevy_events[0].event_end_date
    setEndDate(currEvent)

def manage_presave_events(original_event, changed_event, current_prod):
    if not original_event.event_end_date == changed_event.event_end_date or not str(original_event) == str(changed_event): # Field has changed
        if hasattr(original_event, 'next_related_events') and list(original_event.next_related_events.all()):
            next_events = list(original_event.next_related_events.all())
            for next_event in next_events:
                nextin_prevys = list(next_event.previous_related_events.all())
                if next_event.latest_previous_dependent_event == str(original_event) and len(nextin_prevys)>1 and nextin_prevys[1].event_end_date > changed_event.event_end_date:
                    next_event.latest_previous_dependent_event = str(nextin_prevys[1])
                    next_event.event_start_date = nextin_prevys[1].event_end_date
                    setEndDate(next_event)
                    next_event.save()
                elif next_event.latest_previous_dependent_event == str(original_event) and (len(nextin_prevys)<=1 or (len(nextin_prevys)>1 and changed_event.event_end_date >= nextin_prevys[1].event_end_date)):
                    if not original_event.event_end_date == changed_event.event_end_date:
                        next_event.event_start_date = changed_event.event_end_date
                        setEndDate(next_event)
                    if not str(original_event) == str(changed_event):
                        next_event.latest_previous_dependent_event = str(changed_event)
                    next_event.save()
                elif next_event.latest_previous_dependent_event != str(original_event) and len(nextin_prevys)>1 and changed_event.event_end_date > nextin_prevys[0].event_end_date:
                    next_event.latest_previous_dependent_event = str(changed_event)
                    next_event.event_start_date = changed_event.event_end_date
                    setEndDate(next_event)
                    next_event.save()
    # no need to handle event links when techno changes, because that will be
    # handled manually when m2ms change
    if original_event.production != changed_event.production or original_event.event_cost_Rs != changed_event.event_cost_Rs:
        if original_event.production != changed_event.production:
            old_prod = current_prod
            new_prod = changed_event.production
            old_prod.total_start_up_cost_Rs = old_prod.total_start_up_cost_Rs - original_event.event_cost_Rs
            new_prod.total_start_up_cost_Rs = new_prod.total_start_up_cost_Rs + changed_event.event_cost_Rs
            old_prod.save()
            new_prod.save()
        elif original_event.event_cost_Rs != changed_event.event_cost_Rs:
            current_prod.total_start_up_cost_Rs = current_prod.total_start_up_cost_Rs - original_event.event_cost_Rs + changed_event.event_cost_Rs
            current_prod.save()

def manage_presave_line(original_line, changed_line, current_prod):
    if changed_line.working_days_per_year !=0 and changed_line.working_hours_per_day !=0 and changed_line.line_product_shipping_frequency_per_year != 0:
        changed_line.line_product_net_shipping_cost_per_hour_Rs = changed_line.line_product_shipping_cost_per_bulk_Rs / ((changed_line.working_days_per_year * changed_line.working_hours_per_day) / changed_line.line_product_shipping_frequency_per_year)
    else:
        changed_line.line_product_net_shipping_cost_per_hour_Rs = 0 
    changed_line.amount_of_section_product_missed_per_hour_for_maintenance = changed_line.max_ideal_amount_of_section_product_produced_per_hour * changed_line.entire_maintenance_fraction_per_hour
    changed_line.net_amount_of_product_produced_per_hour = changed_line.max_ideal_amount_of_section_product_produced_per_hour - changed_line.amount_of_section_product_missed_per_hour_for_maintenance
    if current_prod.id == changed_line.production.id:
        current_prod.total_size_required_m2 = current_prod.total_size_required_m2 - original_line.line_area_required_m2 + changed_line.line_area_required_m2
        current_prod.total_production_cost_per_hour_Rs = current_prod.total_production_cost_per_hour_Rs - (original_line.line_operating_cost_per_hour_Rs + original_line.line_product_net_shipping_cost_per_hour_Rs) + (changed_line.line_operating_cost_per_hour_Rs + changed_line.line_product_net_shipping_cost_per_hour_Rs)
        current_prod.save()
    else:
        old_prod = current_prod
        new_prod = changed_line.production
        old_prod.total_size_required_m2 = old_prod.total_size_required_m2 - original_line.line_area_required_m2
        old_prod.total_production_cost_per_hour_Rs = old_prod.total_production_cost_per_hour_Rs - original_line.line_operating_cost_per_hour_Rs - original_line.line_product_net_shipping_cost_per_hour_Rs
        new_prod.total_size_required_m2 = new_prod.total_size_required_m2 + changed_line.line_area_required_m2
        new_prod.total_production_cost_per_hour_Rs = new_prod.total_production_cost_per_hour_Rs + changed_line.line_operating_cost_per_hour_Rs + changed_line.line_product_net_shipping_cost_per_hour_Rs
        old_prod.save()
        new_prod.save()


def manage_presave_lineEquipment(original_equipment, changed_equipment, current_line):
    changed_equipment.total_area_required_for_all_units_m2 = changed_equipment.number_of_equipment_units_needed * changed_equipment.area_required_per_Equipmentunit_m2
    changed_equipment.total_parts_replacement_cost_per_hour_Rs = changed_equipment.number_of_equipment_units_needed * changed_equipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs
    changed_equipment.total_resources_cost_per_hour_Rs = changed_equipment.number_of_equipment_units_needed * changed_equipment.resources_cost_per_equipmentUnit_per_hour_Rs
    changed_equipment.total_maintenance_down_time_fractions_per_hour = changed_equipment.number_of_equipment_units_needed * changed_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour
    changed_equipment.total_running_cost_per_hour_Rs = changed_equipment.total_parts_replacement_cost_per_hour_Rs + changed_equipment.total_resources_cost_per_hour_Rs
    # do all other changes, after parent foreign kef is handled
    if current_line.id != changed_equipment.line.id:
        old_line = current_line
        new_line = changed_equipment.line
        # here, cost and size are changed
        old_line.line_operating_cost_per_hour_Rs = old_line.line_operating_cost_per_hour_Rs - original_equipment.total_running_cost_per_hour_Rs
        old_line.line_area_required_m2 = old_line.line_area_required_m2  - original_equipment.total_area_required_for_all_units_m2
        old_line.entire_maintenance_fraction_per_hour = old_line.entire_maintenance_fraction_per_hour - original_equipment.total_maintenance_down_time_fractions_per_hour

        new_line.line_operating_cost_per_hour_Rs = new_line.line_operating_cost_per_hour_Rs + changed_equipment.total_running_cost_per_hour_Rs
        new_line.line_area_required_m2 = new_line.line_area_required_m2  + changed_equipment.total_area_required_for_all_units_m2
        new_line.entire_maintenance_fraction_per_hour = new_line.entire_maintenance_fraction_per_hour + changed_equipment.total_maintenance_down_time_fractions_per_hour

        old_line.save()
        new_line.save()
    
    else:
        current_line.line_operating_cost_per_hour_Rs = current_line.line_operating_cost_per_hour_Rs - original_equipment.total_running_cost_per_hour_Rs + changed_equipment.total_running_cost_per_hour_Rs
        current_line.line_area_required_m2 = current_line.line_area_required_m2  - original_equipment.total_area_required_for_all_units_m2 + changed_equipment.total_area_required_for_all_units_m2
        current_line.entire_maintenance_fraction_per_hour = current_line.entire_maintenance_fraction_per_hour - original_equipment.total_maintenance_down_time_fractions_per_hour + changed_equipment.total_maintenance_down_time_fractions_per_hour
        current_line.save()

def manage_presave_Linelabour(original_labour, changed_labour, current_line):
    # add an if none for productions later if equi of that section is none
    changed_labour.total_labourCost_per_hour_Rs = changed_labour.number_of_labourers_required_for_this_role * (changed_labour.salary_per_hour_per_labourer_Rs + changed_labour.safety_risk_cost_per_hour_per_labourer_Rs)
    if current_line.id != changed_labour.line.id:
        old_line = current_line
        new_line = changed_labour.line
        # here, cost and size are changed
        print('start')
        print(original_labour.total_labourCost_per_hour_Rs)
        print(changed_labour.total_labourCost_per_hour_Rs)
        old_line.line_operating_cost_per_hour_Rs = old_line.line_operating_cost_per_hour_Rs - original_labour.total_labourCost_per_hour_Rs
        new_line.line_operating_cost_per_hour_Rs = new_line.line_operating_cost_per_hour_Rs + changed_labour.total_labourCost_per_hour_Rs
        print('middle')
        print(old_line.line_operating_cost_per_hour_Rs)
        print(new_line.line_operating_cost_per_hour_Rs)
        old_line.save()
        new_line.save()
        print('end')
        print(old_line.line_operating_cost_per_hour_Rs)
        print(new_line.line_operating_cost_per_hour_Rs)
    else:
        current_line.line_operating_cost_per_hour_Rs = current_line.line_operating_cost_per_hour_Rs - original_labour.total_labourCost_per_hour_Rs + changed_labour.total_labourCost_per_hour_Rs
        current_line.save()


# it is impossible that it will be linked to others where the equipment is not
# the same, so it can only be one at a time production section where it is different
# and then, it is handle individually

            

def manage_presave_LineEquimaintenance(original_maintenance, changed_maintenance, current_equipment):
    if changed_maintenance.equipment.id == original_maintenance.equipment.id:    
        current_equipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = current_equipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs - original_maintenance.part_replacement_cost_per_equipmentUnit_per_hour_Rs + changed_maintenance.part_replacement_cost_per_equipmentUnit_per_hour_Rs
        current_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour = current_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour - original_maintenance.maintenance_downTime_fraction_per_equipmentUnit_per_hour + changed_maintenance.maintenance_downTime_fraction_per_equipmentUnit_per_hour
        current_equipment.save()
    else:
        old_equip = current_equipment
        new_equip = changed_maintenance.equipment
        old_equip.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = old_equip.parts_replacement_cost_per_equipmentUnit_per_hour_Rs - original_maintenance.part_replacement_cost_per_equipmentUnit_per_hour_Rs
        old_equip.maintenance_down_time_fractions_per_equipmentUnit_per_hour = old_equip.maintenance_down_time_fractions_per_equipmentUnit_per_hour - original_maintenance.maintenance_downTime_fraction_per_equipmentUnit_per_hour
        new_equip.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = new_equip.parts_replacement_cost_per_equipmentUnit_per_hour_Rs + changed_maintenance.part_replacement_cost_per_equipmentUnit_per_hour_Rs
        new_equip.maintenance_down_time_fractions_per_equipmentUnit_per_hour = new_equip.maintenance_down_time_fractions_per_equipmentUnit_per_hour + changed_maintenance.maintenance_downTime_fraction_per_equipmentUnit_per_hour
        old_equip.save()
        new_equip.save()

def manage_presave_lineEquiResource(original_resource, changed_resource, current_equipment):
    changed_resource.cost_per_equipmentUnit_per_hour_for_this_resource_Rs = changed_resource.resource_quantity_needed_per_EquipmentUnit_per_hour * changed_resource.cost_per_single_unit_resource_Rs
    if changed_resource.equipment.id == original_resource.equipment.id:    
        current_equipment.resources_cost_per_equipmentUnit_per_hour_Rs = current_equipment.resources_cost_per_equipmentUnit_per_hour_Rs - original_resource.cost_per_equipmentUnit_per_hour_for_this_resource_Rs + changed_resource.cost_per_equipmentUnit_per_hour_for_this_resource_Rs
        current_equipment.save()
    else:
        old_equip = current_equipment
        new_equip = changed_resource.equipment
        old_equip.resources_cost_per_equipmentUnit_per_hour_Rs = old_equip.resources_cost_per_equipmentUnit_per_hour_Rs - original_resource.cost_per_equipmentUnit_per_hour_for_this_resource_Rs
        new_equip.resources_cost_per_equipmentUnit_per_hour_Rs = new_equip.resources_cost_per_equipmentUnit_per_hour_Rs + changed_resource.cost_per_equipmentUnit_per_hour_for_this_resource_Rs
        old_equip.save()
        new_equip.save()

def manage_presave_rawMatHourlyCost(original_rawMatCost, changed_rawMatCost, current_line):
    if changed_rawMatCost.working_days_per_year_for_this_line != 0 and changed_rawMatCost.working_hours_per_day_for_this_line != 0 and changed_rawMatCost.purchase_frquency_per_year:
        changed_rawMatCost.raw_material_net_cost_per_hour_Rs = (changed_rawMatCost.raw_material_bulk_purchase_cost_Rs + changed_rawMatCost.raw_material_transport_cost_per_bulk_Rs) / ((changed_rawMatCost.working_days_per_year_for_this_line * changed_rawMatCost.working_hours_per_day_for_this_line) / changed_rawMatCost.purchase_frquency_per_year)
    else:
        changed_rawMatCost.raw_material_net_cost_per_hour_Rs = 0
    if current_line.id != changed_rawMatCost.line.id:
        new_line = changed_rawMatCost.line
        old_line = current_line
        old_line.line_operating_cost_per_hour_Rs = old_line.line_operating_cost_per_hour_Rs - original_rawMatCost.raw_material_net_cost_per_hour_Rs
        new_line.line_operating_cost_per_hour_Rs = new_line.line_operating_cost_per_hour_Rs + changed_rawMatCost.raw_material_net_cost_per_hour_Rs
        old_line.save()
        new_line.save()
    else:
        current_line.line_operating_cost_per_hour_Rs = current_line.line_operating_cost_per_hour_Rs - original_rawMatCost.raw_material_net_cost_per_hour_Rs + changed_rawMatCost.raw_material_net_cost_per_hour_Rs
        current_line.save()

def manage_presave_msclnsProdOpsCost(original_msclOps, changed_msclOps, current_prod):
    if current_prod.id != changed_msclOps.production.id:
        old_prod = current_prod
        new_prod = changed_msclOps.production
        old_prod.total_production_cost_per_hour_Rs = old_prod.total_production_cost_per_hour_Rs - original_msclOps.per_hour_cost_Rs
        new_prod.total_production_cost_per_hour_Rs = new_prod.total_production_cost_per_hour_Rs + changed_msclOps.per_hour_cost_Rs
        old_prod.save()
        new_prod.save()
    else:
        current_prod.total_production_cost_per_hour_Rs = current_prod.total_production_cost_per_hour_Rs - original_msclOps.per_hour_cost_Rs + changed_msclOps.per_hour_cost_Rs
        current_prod.save()

def manage_presave_msclnsProdInstlsCost(original_msclInstls, changed_msclInstls, current_prod):
    if current_prod.id != changed_msclInstls.production.id:
        old_prod = current_prod
        new_prod = changed_msclInstls.production
        old_prod.total_start_up_cost_Rs = old_prod.total_start_up_cost_Rs - original_msclInstls.cost_Rs
        new_prod.total_start_up_cost_Rs = new_prod.total_start_up_cost_Rs + changed_msclInstls.cost_Rs
        old_prod.save()
        new_prod.save()
    else:
        current_prod.total_start_up_cost_Rs = current_prod.total_start_up_cost_Rs - original_msclInstls.cost_Rs + changed_msclInstls.cost_Rs
        current_prod.save()

def manage_presave_msclnsProdAreaCost(original_msclArea, changed_msclArea, current_prod):
    if current_prod.id != changed_msclArea.production.id:
        old_prod = current_prod
        new_prod = changed_msclArea.production
        old_prod.total_size_required_m2 = old_prod.total_size_required_m2 - original_msclArea.area_allotment_m2
        new_prod.total_size_required_m2 = new_prod.total_size_required_m2 + changed_msclArea.area_allotment_m2
        old_prod.save()
        new_prod.save()
    else:
        current_prod.total_size_required_m2 = current_prod.total_size_required_m2 - original_msclArea.area_allotment_m2 + changed_msclArea.area_allotment_m2
        current_prod.save()

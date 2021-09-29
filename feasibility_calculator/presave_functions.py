# underscores can be evil in the console

def manage_presave_production(original_section_prdtn, changed_section_prdtn, current_tech):
    changed_section_prdtn.amount_of_section_product_missed_per_hour_for_maintenance = changed_section_prdtn.max_amount_of_section_product_produced_per_hour * changed_section_prdtn.entire_maintenance_fraction_per_hour
    changed_section_prdtn.net_amount_of_product_produced_per_hour = changed_section_prdtn.max_amount_of_section_product_produced_per_hour - changed_section_prdtn.amount_of_section_product_missed_per_hour_for_maintenance
    changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs = changed_section_prdtn.selling_price_per_unit_of_product_Rs * changed_section_prdtn.net_amount_of_product_produced_per_hour
    if current_tech.id == changed_section_prdtn.technology.id:
        current_tech.total_revenue_per_hour_Rs = current_tech.total_revenue_per_hour_Rs - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
        current_tech.save()

    else:
        old_tech = current_tech
        new_tech = changed_section_prdtn.technology
        old_tech.total_revenue_per_hour_Rs = old_tech.total_revenue_per_hour_Rs  - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
        new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs  + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
        old_tech.save()
        new_tech.save()


def manage_presave_equipment(original_equipment, changed_equipment, current_tech, current_secProd):
    changed_equipment.total_area_required_for_all_units_m2 = changed_equipment.number_of_equipment_units_needed * changed_equipment.area_required_per_Equipmentunit_m2
    changed_equipment.total_parts_replacement_cost_per_hour_Rs = changed_equipment.number_of_equipment_units_needed * changed_equipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs
    changed_equipment.total_resources_cost_per_hour_Rs = changed_equipment.number_of_equipment_units_needed * changed_equipment.resources_cost_per_equipmentUnit_per_hour_Rs
    changed_equipment.total_maintenance_down_time_fractions_per_hour = changed_equipment.number_of_equipment_units_needed * changed_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour
    changed_equipment.total_running_cost_per_hour_Rs = changed_equipment.total_parts_replacement_cost_per_hour_Rs + changed_equipment.total_resources_cost_per_hour_Rs
    old_net_revenue = 0
    new_net_revenue = 0
    # do all other changes, after parent foreign kef is handled
    if current_secProd != None and changed_equipment.equiProductionSection != None and current_secProd.id != changed_equipment.equiProductionSection.id:
        old_sec_prod = current_secProd
        old1_net_revenue = old_sec_prod.total_hourly_revenue_generated_for_this_section_Rs
        new_sec_prod = changed_equipment.equiProductionSection
        new1_net_revenue = new_sec_prod.total_hourly_revenue_generated_for_this_section_Rs
        # here, cost and size are changed
        old_sec_prod.total_section_operating_cost_per_hour_Rs = old_sec_prod.total_section_operating_cost_per_hour_Rs - original_equipment.total_running_cost_per_hour_Rs
        old_sec_prod.total_section_area_required_m2 = old_sec_prod.total_section_area_required_m2  - original_equipment.total_area_required_for_all_units_m2
        old_sec_prod.entire_maintenance_fraction_per_hour = old_sec_prod.entire_maintenance_fraction_per_hour - original_equipment.total_maintenance_down_time_fractions_per_hour

        new_sec_prod.total_section_operating_cost_per_hour_Rs = new_sec_prod.total_section_operating_cost_per_hour_Rs + changed_equipment.total_running_cost_per_hour_Rs
        new_sec_prod.total_section_area_required_m2 = new_sec_prod.total_section_area_required_m2  + changed_equipment.total_area_required_for_all_units_m2
        new_sec_prod.entire_maintenance_fraction_per_hour = new_sec_prod.entire_maintenance_fraction_per_hour + changed_equipment.total_maintenance_down_time_fractions_per_hour

        old_sec_prod.save()
        old2_net_revenue = old_sec_prod.total_hourly_revenue_generated_for_this_section_Rs
        new_sec_prod.save()
        new2_net_revenue = new_sec_prod.total_hourly_revenue_generated_for_this_section_Rs
        old_net_revenue = old1_net_revenue - old2_net_revenue
        new_net_revenue = new2_net_revenue - new1_net_revenue

    elif current_secProd != None and changed_equipment.equiProductionSection != None and current_secProd.id == changed_equipment.equiProductionSection.id:
        old_net_revenue = current_secProd.total_hourly_revenue_generated_for_this_section_Rs
        current_secProd.total_section_operating_cost_per_hour_Rs = current_secProd.total_section_operating_cost_per_hour_Rs - original_equipment.total_running_cost_per_hour_Rs + changed_equipment.total_running_cost_per_hour_Rs
        current_secProd.total_section_area_required_m2 = current_secProd.total_section_area_required_m2  - original_equipment.total_area_required_for_all_units_m2 + changed_equipment.total_area_required_for_all_units_m2
        current_secProd.entire_maintenance_fraction_per_hour = current_secProd.entire_maintenance_fraction_per_hour - original_equipment.total_maintenance_down_time_fractions_per_hour + changed_equipment.total_maintenance_down_time_fractions_per_hour
        current_secProd.save()
        new_net_revenue = current_secProd.total_hourly_revenue_generated_for_this_section_Rs
    elif current_secProd == None and changed_equipment.equiProductionSection != None:
        new_sec_prod = changed_equipment.equiProductionSection
        old_net_revenue = new_sec_prod.total_hourly_revenue_generated_for_this_section_Rs
        new_sec_prod.total_section_operating_cost_per_hour_Rs = new_sec_prod.total_section_operating_cost_per_hour_Rs + changed_equipment.total_running_cost_per_hour_Rs
        new_sec_prod.total_section_area_required_m2 = new_sec_prod.total_section_area_required_m2  + changed_equipment.total_area_required_for_all_units_m2
        new_sec_prod.entire_maintenance_fraction_per_hour = new_sec_prod.entire_maintenance_fraction_per_hour + changed_equipment.total_maintenance_down_time_fractions_per_hour
        new_sec_prod.save()
        new_net_revenue = new_sec_prod.total_hourly_revenue_generated_for_this_section_Rs
    elif current_secProd != None and changed_equipment.equiProductionSection == None:
        old_sec_prod = current_secProd
        old_net_revenue = old_sec_prod.total_hourly_revenue_generated_for_this_section_Rs
        old_sec_prod.total_section_operating_cost_per_hour_Rs = old_sec_prod.total_section_operating_cost_per_hour_Rs - original_equipment.total_running_cost_per_hour_Rs
        old_sec_prod.total_section_area_required_m2 = old_sec_prod.total_section_area_required_m2  - original_equipment.total_area_required_for_all_units_m2
        old_sec_prod.entire_maintenance_fraction_per_hour = old_sec_prod.entire_maintenance_fraction_per_hour - original_equipment.total_maintenance_down_time_fractions_per_hour
        old_sec_prod.save()
        new_net_revenue = old_sec_prod.total_hourly_revenue_generated_for_this_section_Rs
    current_tech.total_revenue_per_hour_Rs = current_tech.total_revenue_per_hour_Rs - old_net_revenue + new_net_revenue
    current_tech.total_size_required_m2 = current_tech.total_size_required_m2  - original_equipment.total_area_required_for_all_units_m2 + changed_equipment.total_area_required_for_all_units_m2
    current_tech.total_operating_cost_per_hour_Rs = current_tech.total_operating_cost_per_hour_Rs - original_equipment.total_running_cost_per_hour_Rs + changed_equipment.total_running_cost_per_hour_Rs
    current_tech.save()

    

def manage_presave_labour(original_labour, changed_labour, current_tech, current_secProd):
    # add an if none for productions later if equi of that section is none
    changed_labour.total_labourCost_per_hour_Rs = changed_labour.number_of_labourers_required_for_this_role * (changed_labour.salary_per_hour_per_labourer_Rs + changed_labour.safety_risk_cost_per_hour_per_labourer_Rs)
    if current_secProd != None and changed_labour.equiProductionSection != None and not current_secProd.id == changed_labour.equiProductionSection.id:
        old_sec_prod = current_secProd
        new_sec_prod = changed_labour.equiProductionSection
        # here, cost and size are changed
        old_sec_prod.total_section_operating_cost_per_hour_Rs = old_sec_prod.total_section_operating_cost_per_hour_Rs - original_labour.total_labourCost_per_hour_Rs

        new_sec_prod.total_section_operating_cost_per_hour_Rs = new_sec_prod.total_section_operating_cost_per_hour_Rs + changed_labour.total_labourCost_per_hour_Rs

        old_sec_prod.save()
        new_sec_prod.save()

    elif current_secProd != None and changed_labour.equiProductionSection != None and current_secProd.id == changed_labour.equiProductionSection.id:
        current_secProd.total_section_operating_cost_per_hour_Rs = current_secProd.total_section_operating_cost_per_hour_Rs - original_labour.total_labourCost_per_hour_Rs + changed_labour.total_labourCost_per_hour_Rs
        current_secProd.save()
    elif current_secProd == None and changed_labour.equiProductionSection != None:
        new_sec_prod = changed_labour.equiProductionSection
        new_sec_prod.total_section_operating_cost_per_hour_Rs = new_sec_prod.total_section_operating_cost_per_hour_Rs + changed_labour.total_labourCost_per_hour_Rs
        new_sec_prod.save()
    elif current_secProd != None and changed_labour.equiProductionSection == None:
        old_sec_prod = current_secProd
        old_sec_prod.total_section_operating_cost_per_hour_Rs = old_sec_prod.total_section_operating_cost_per_hour_Rs - original_labour.total_labourCost_per_hour_Rs
        old_sec_prod.save()

    current_tech.total_operating_cost_per_hour_Rs = current_tech.total_operating_cost_per_hour_Rs - original_labour.total_labourCost_per_hour_Rs + changed_labour.total_labourCost_per_hour_Rs
    current_tech.save()

# it is impossible that it will be linked to others where the equipment is not
# the same, so it can only be one at a time production section where it is different
# and then, it is handle individually

            

def manage_presave_maintenance(original_maintenance, changed_maintenance, current_equipment):
    if changed_maintenance.equipment.id != original_maintenance.equipment.id or changed_maintenance.part_replacement_cost_per_unit_per_hour_Rs != original_maintenance.part_replacement_cost_per_unit_per_hour_Rs or changed_maintenance.maintenance_downTime_fraction_per_unit_per_hour != original_maintenance.maintenance_downTime_fraction_per_unit_per_hour:
        if changed_maintenance.equipment.id == original_maintenance.equipment.id:    
            current_equipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = current_equipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs - original_maintenance.part_replacement_cost_per_unit_per_hour_Rs + changed_maintenance.part_replacement_cost_per_unit_per_hour_Rs
            current_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour = current_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour - original_maintenance.maintenance_downTime_fraction_per_unit_per_hour + changed_maintenance.maintenance_downTime_fraction_per_unit_per_hour
            current_equipment.save()
        else:
            old_equip = current_equipment
            new_equip = changed_maintenance.equipment
            old_equip.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = old_equip.parts_replacement_cost_per_equipmentUnit_per_hour_Rs - original_maintenance.part_replacement_cost_per_unit_per_hour_Rs
            old_equip.maintenance_down_time_fractions_per_equipmentUnit_per_hour = old_equip.maintenance_down_time_fractions_per_equipmentUnit_per_hour - original_maintenance.maintenance_downTime_fraction_per_unit_per_hour
            new_equip.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = new_equip.parts_replacement_cost_per_equipmentUnit_per_hour_Rs + changed_maintenance.part_replacement_cost_per_unit_per_hour_Rs
            new_equip.maintenance_down_time_fractions_per_equipmentUnit_per_hour = new_equip.maintenance_down_time_fractions_per_equipmentUnit_per_hour + changed_maintenance.maintenance_downTime_fraction_per_unit_per_hour
            old_equip.save()
            new_equip.save()

def manage_presave_equiResource(original_resource, changed_resource, current_equipment):
    if changed_resource.equipment.id != original_resource.equipment.id or changed_resource.cost_per_equipmentUnit_per_hour_for_this_resource_Rs != original_resource.cost_per_equipmentUnit_per_hour_for_this_resource_Rs:
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
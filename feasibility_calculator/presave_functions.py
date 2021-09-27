# underscores can be evil in the console
def manage_presave_equipment(original_equipment, changed_equipment, current_tech):
    changed_equipment.total_area_required_for_all_units_m2 = changed_equipment.number_of_equipment_units_needed * changed_equipment.area_required_per_Equipmentunit_m2
    changed_equipment.total_parts_replacement_cost_per_hour_Rs = changed_equipment.number_of_equipment_units_needed * changed_equipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs
    changed_equipment.total_resources_cost_per_hour_Rs = changed_equipment.number_of_equipment_units_needed * changed_equipment.resources_cost_per_equipmentUnit_per_hour_Rs
    changed_equipment.total_maintenance_down_time_fractions_per_hour = changed_equipment.number_of_equipment_units_needed * changed_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour
    changed_equipment.total_running_cost_per_hour_Rs = changed_equipment.total_parts_replacement_cost_per_hour_Rs + changed_equipment.total_resources_cost_per_hour_Rs
    # do all other changes, after parent foreign kef is handled
    if not original_equipment.technology.id == changed_equipment.technology.id:
        old_tech = current_tech
        new_tech = changed_equipment.technology
        # here, cost and size are changed
        old_tech.total_operating_cost_per_hour_Rs = old_tech.total_operating_cost_per_hour_Rs - original_equipment.total_running_cost_per_hour_Rs
        old_tech.total_size_required_m2 = old_tech.total_size_required_m2  - original_equipment.total_area_required_for_all_units_m2
        
        if hasattr(original_equipment, 'production_sections') and list(original_equipment.production_sections.all()):
            productionSections = list(original_equipment.production_sections.all())
            if original_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour != changed_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour:
                for productionSection in productionSections:
                    # shift revenues to the new technology
                    old_tech.total_revenue_per_hour_Rs = old_tech.total_revenue_per_hour_Rs - productionSection.total_hourly_revenue_generated_for_this_section_Rs
                    productionSection.amount_of_section_product_missed_per_hour_for_maintenance = changed_equipment.total_maintenance_down_time_fractions_per_hour * productionSection.max_amount_of_section_product_produced_per_hour
                    productionSection.net_amount_of_product_produced_per_hour = productionSection.max_amount_of_section_product_produced_per_hour - productionSection.amount_of_section_product_missed_per_hour_for_maintenance
                    productionSection.total_hourly_revenue_generated_for_this_section_Rs = productionSection.selling_price_per_unit_of_product_Rs * productionSection.net_amount_of_product_produced_per_hour
                    productionSection.save()
                    new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs + productionSection.total_hourly_revenue_generated_for_this_section_Rs
            else:
                for productionSection in productionSections:
                    old_tech.total_revenue_per_hour_Rs = old_tech.total_revenue_per_hour_Rs  - productionSection.total_hourly_revenue_generated_for_this_section_Rs
                    new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs  + productionSection.total_hourly_revenue_generated_for_this_section_Rs
        old_tech.save()
        new_tech.total_size_required_m2 = new_tech.total_size_required_m2  + changed_equipment.total_area_required_for_all_units_m2
        new_tech.total_operating_cost_per_hour_Rs = new_tech.total_operating_cost_per_hour_Rs + changed_equipment.total_running_cost_per_hour_Rs
        new_tech.save()
    else:
        current_tech.total_size_required_m2 = current_tech.total_size_required_m2 - original_equipment.total_area_required_for_all_units_m2 + changed_equipment.total_area_required_for_all_units_m2
        current_tech.total_operating_cost_per_hour_Rs = current_tech.total_operating_cost_per_hour_Rs - original_equipment.total_running_cost_per_hour_Rs + changed_equipment.total_running_cost_per_hour_Rs
        if original_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour != changed_equipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour:
            if hasattr(original_equipment, 'production_sections') and list(original_equipment.production_sections.all()):
                productionSections = list(original_equipment.production_sections.all())
                for productionSection in productionSections:
                    old_revenue = productionSection.total_hourly_revenue_generated_for_this_section_Rs
                    productionSection.amount_of_section_product_missed_per_hour_for_maintenance = changed_equipment.total_maintenance_down_time_fractions_per_hour * productionSection.max_amount_of_section_product_produced_per_hour
                    productionSection.net_amount_of_product_produced_per_hour = productionSection.max_amount_of_section_product_produced_per_hour - productionSection.amount_of_section_product_missed_per_hour_for_maintenance
                    productionSection.total_hourly_revenue_generated_for_this_section_Rs = productionSection.selling_price_per_unit_of_product_Rs * productionSection.net_amount_of_product_produced_per_hour
                    productionSection.maintenance_changed = True
                    productionSection.save()
                    current_tech.total_revenue_per_hour_Rs = current_tech.total_revenue_per_hour_Rs - old_revenue + productionSection.total_hourly_revenue_generated_for_this_section_Rs
                # this should be a post save event, but then how will i know its changed
        current_tech.save()

def manage_presave_labour(original_labour, changed_labour, current_tech):
    # add an if none for productions later if equi of that section is none
    changed_labour.total_labourCost_per_hour_Rs = changed_labour.number_of_labourers_required_for_this_role * (changed_labour.salary_per_hour_per_labourer_Rs + changed_labour.safety_risk_cost_per_hour_per_labourer_Rs)
    if not original_labour.technology.id == changed_labour.technology.id:
        old_tech = current_tech
        new_tech = changed_labour.technology

        old_tech.total_operating_cost_per_hour_Rs = old_tech.total_operating_cost_per_hour_Rs - original_labour.total_labourCost_per_hour_Rs
        new_tech.total_operating_cost_per_hour_Rs = new_tech.total_operating_cost_per_hour_Rs + changed_labour.total_labourCost_per_hour_Rs
        if hasattr(original_labour, 'production_sections') and list(original_labour.production_sections.all()):
            productionSections = list(original_labour.production_sections.all())
            for productionSection in productionSections:
                if productionSection.equipment_model_used == None:
                    old_tech.total_revenue_per_hour_Rs = old_tech.total_revenue_per_hour_Rs  - productionSection.total_hourly_revenue_generated_for_this_section_Rs
                    new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs  + productionSection.total_hourly_revenue_generated_for_this_section_Rs
        old_tech.save()
        new_tech.save()
    else:
        current_tech.total_operating_cost_per_hour_Rs = current_tech.total_operating_cost_per_hour_Rs - original_labour.total_labourCost_per_hour_Rs + changed_labour.total_labourCost_per_hour_Rs
        current_tech.save()

# it is impossible that it will be linked to others where the equipment is not
# the same, so it can only be one at a time production section where it is different
# and then, it is handle individually

def manage_presave_production(original_section_prdtn, changed_section_prdtn, current_equip, current_labour):
    if changed_section_prdtn.equipment_model_used != None:
        changed_section_prdtn.amount_of_section_product_missed_per_hour_for_maintenance = changed_section_prdtn.equipment_model_used.total_maintenance_down_time_fractions_per_hour * changed_section_prdtn.max_amount_of_section_product_produced_per_hour
    else:
        changed_section_prdtn.amount_of_section_product_missed_per_hour_for_maintenance = 0
    changed_section_prdtn.net_amount_of_product_produced_per_hour = changed_section_prdtn.max_amount_of_section_product_produced_per_hour - changed_section_prdtn.amount_of_section_product_missed_per_hour_for_maintenance
    changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs = changed_section_prdtn.selling_price_per_unit_of_product_Rs * changed_section_prdtn.net_amount_of_product_produced_per_hour

    if current_equip != None and changed_section_prdtn.equipment_model_used != None:
        if current_equip.id == changed_section_prdtn.equipment_model_used.id:
            current_tech = current_equip.technology
            current_tech.total_revenue_per_hour_Rs = current_tech.total_revenue_per_hour_Rs - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
            current_tech.save()
        else:
            if current_equip.technology.id != changed_section_prdtn.equipment_model_used.technology.id:
                old_tech = current_equip.technology
                new_tech = changed_section_prdtn.equipment_model_used.technology
                old_tech.total_revenue_per_hour_Rs = old_tech.total_revenue_per_hour_Rs  - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
                new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs  + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
                old_tech.save()
                new_tech.save()
            else:
                current_tech = current_equip.technology
                current_tech.total_revenue_per_hour_Rs = current_tech.total_revenue_per_hour_Rs - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
                current_tech.save()
    
    elif current_equip == None and changed_section_prdtn.equipment_model_used != None:
        new_tech = changed_section_prdtn.equipment_model_used.technology
        if current_labour != None and current_labour.technology.id != new_tech.id:
            old_tech = current_labour.technology
            old_tech.total_revenue_per_hour_Rs = old_tech.total_revenue_per_hour_Rs  - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
            new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs  + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
            old_tech.save()
        elif current_labour != None and current_labour.technology.id == new_tech.id:
            # this is correct, no worries
            new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
        elif current_labour == None:
            new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
        new_tech.save()
    
    elif current_equip != None and changed_section_prdtn.equipment_model_used == None:
        old_tech = current_equip.technology
        old_tech.total_revenue_per_hour_Rs = old_tech.total_revenue_per_hour_Rs  - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
        if changed_section_prdtn.labour_role_needed != None:
            new_tech = changed_section_prdtn.labour_role_needed.technology
            if old_tech.id != new_tech.id:
                new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs  + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
                new_tech.save()
            else:
                old_tech.total_revenue_per_hour_Rs = old_tech.total_revenue_per_hour_Rs  + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
        old_tech.save()

    else:
        if changed_section_prdtn.labour_role_needed != None:
            new_labour = changed_section_prdtn.labour_role_needed
            if current_labour != None and current_labour.technology.id != new_labour.technology.id:
                old_tech = current_labour.technology
                new_tech = new_labour.technology
                old_tech.total_revenue_per_hour_Rs = old_tech.total_revenue_per_hour_Rs  - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
                new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs  + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
                old_tech.save()
                new_tech.save()
            elif current_labour != None and current_labour.technology.id == new_labour.technology.id:
                current_tech = current_labour.technology
                current_tech.total_revenue_per_hour_Rs = current_tech.total_revenue_per_hour_Rs  - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
                current_tech.save()            
            else:
                new_tech = new_labour.technology
                new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs + changed_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
                new_tech.save()
        else:
            if current_labour != None:
                old_tech = current_labour.technology
                old_tech.total_revenue_per_hour_Rs = old_tech.total_revenue_per_hour_Rs  - original_section_prdtn.total_hourly_revenue_generated_for_this_section_Rs
                old_tech.save()

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
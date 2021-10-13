from django.contrib import admin

from feasibility_calculator.models import Company, CompanyOnlyOperatingCost, EventSchedule, LineEquipment, LineEquipmentMaintenanceCost, LineEquipmentResourceCost, LineLabourCost, LineRawMaterialCost, MiscellaneousProductionAreaRequirement, MiscellaneousProductionInstallationCost, MiscellaneousProductionOperatingCost, Production, Line, ProjectManager, ResearchPaper, setEndDate
from django import forms
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField, UserCreationForm
from django.core.exceptions import ValidationError

class EventScheduleForm(forms.ModelForm):

    class Meta:
        model = EventSchedule
        fields = ['previous_related_events']

    def __init__(self, *args, **kwargs):
        super(EventScheduleForm, self).__init__(*args, **kwargs)
        if self.instance.id == None:
            self.fields['previous_related_events'].queryset = EventSchedule.objects.all()
        else:
            self.fields['previous_related_events'].queryset = EventSchedule.objects.exclude(id = self.instance.id)
        #filter(event_end_date__lt = self.instance.event_start_date)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'total_cost_per_hour_Rs', 'total_revenue_per_hour_Rs', 'total_profits_per_hour']
    search_fields = ['company_name']
    readonly_fields=['total_cost_per_hour_Rs', 'total_revenue_per_hour_Rs', 'total_profits_per_hour', ]
    
@admin.register(CompanyOnlyOperatingCost)
class CompanyOnlyOperatingCostAdmin(admin.ModelAdmin):
    list_display = ['operation_name', 'company', 'per_hour_cost_Rs']
    search_fields = ['operation_name']

    actions = ['delete_selected']

    def delete_queryset(self, request, queryset):
        for myCompCost in queryset:
            myComp = Company.objects.get(id = myCompCost.company.id)
            myComp.total_cost_per_hour_Rs = myComp.total_cost_per_hour_Rs  - myCompCost.per_hour_cost_Rs
            myComp.save()
            myCompCost.delete(True)

@admin.register(Production)
class ProductionAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'company', 'total_start_up_cost_Rs', 'total_production_cost_per_hour_Rs', 'total_size_required_m2', 'total_revenue_generated_per_hour_Rs', 'total_profit_generated_per_hour_Rs', 'project_start_date', 'break_even_date']
    search_fields = ['product_name']
    readonly_fields=['total_start_up_cost_Rs', 'total_production_cost_per_hour_Rs', 'total_size_required_m2', 'total_amount_of_products_sold_per_hour', 'total_cost_per_product_Rs', 'total_revenue_generated_per_hour_Rs', 'total_profit_generated_per_hour_Rs','break_even_date']

    def delete_queryset(self, request, queryset):
        for myProd in queryset:
            myCompany = Company.objects.get(id = myProd.company.id)
            myCompany.total_cost_per_hour_Rs = myCompany.total_cost_per_hour_Rs - myProd.total_production_cost_per_hour_Rs
            myCompany.total_revenue_per_hour_Rs = myCompany.total_revenue_per_hour_Rs - myProd.total_revenue_generated_per_hour_Rs
            myCompany.save()
            myProd.delete(True)

# it doesnt get its parent field in query delete
@admin.register(EventSchedule)
class EventScheduleAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'id', 'production', 'event_start_date', 'event_end_date', 'event_cost_Rs', 'latest_previous_dependent_event']
    fields = ['production', 'event_name', 'previous_related_events', 'days_to_complete', 'event_cost_Rs', 'reference', 'remarks', 'event_start_date', 'event_end_date', 'latest_previous_dependent_event']
    search_fields = ['event_name']
    readonly_fields=['event_start_date', 'event_end_date', 'latest_previous_dependent_event']
    form = EventScheduleForm
    filter_horizontal = ('previous_related_events',)

    actions = ['delete_selected']

# this needs to be checked especially

    def delete_queryset(self, request, queryset):
        for myEvent in queryset:
            myProduction = Production.objects.get(id = myEvent.production.id)
            if hasattr(myEvent, 'next_related_events') and list(myEvent.next_related_events.all()):
                next_events = list(myEvent.next_related_events.all())
                for next_event in next_events:
                    nextin_prevy_events = list(next_event.previous_related_events.all())
                    if nextin_prevy_events[0].id == myEvent.id:
                        if len(nextin_prevy_events) > 1:
                            next_event.event_start_date = nextin_prevy_events[1].event_end_date
                            next_event.latest_previous_dependent_event = str(nextin_prevy_events[1])
                            setEndDate(next_event)
                            next_event.save()
                        else:
                            next_event.event_start_date = myProduction.project_start_date
                            next_event.latest_previous_dependent_event = None
                            setEndDate(next_event)
                            next_event.save()
                        # yeah obviously, its not calling it myEvent as in the delete function
                        # so no recusrsion as such
            myProduction.total_start_up_cost_Rs = myProduction.total_start_up_cost_Rs - myEvent.event_cost_Rs
            myProduction.save()
            myEvent.delete(True)


@admin.register(Line)
class LineAdmin(admin.ModelAdmin):
    list_display = ['line_name', 'id', 'production', 'net_amount_of_product_produced_per_hour', 'line_operating_cost_per_hour_Rs', 'line_product_net_shipping_cost_per_hour_Rs', 'line_area_required_m2']
    search_fields = ['line_name']
    readonly_fields=['line_area_required_m2', 'line_operating_cost_per_hour_Rs', 'line_product_net_shipping_cost_per_hour_Rs', 'entire_maintenance_fraction_per_hour', 'amount_of_section_product_missed_per_hour_for_maintenance', 'net_amount_of_product_produced_per_hour',]

    actions = ['delete_selected']

    def delete_queryset(self, request, queryset):
        for myLine in queryset:
            myproduction = Production.objects.get(id = myLine.production.id)
            myproduction.total_size_required_m2 = myproduction.total_size_required_m2 - myLine.line_area_required_m2
            myproduction.total_production_cost_per_hour_Rs = myproduction.total_production_cost_per_hour_Rs - myLine.line_operating_cost_per_hour_Rs - myLine.line_product_net_shipping_cost_per_hour_Rs
            myproduction.save()
            myLine.delete(True)

@admin.register(LineEquipment)
class LineEquipmentAdmin(admin.ModelAdmin):
    list_display = ['equipment_name', 'line', 'number_of_equipment_units_needed', 'total_area_required_for_all_units_m2', 'total_running_cost_per_hour_Rs', 'total_maintenance_down_time_fractions_per_hour']
    search_fields = ['equipment_name']
    readonly_fields=['maintenance_down_time_fractions_per_equipmentUnit_per_hour', 'parts_replacement_cost_per_equipmentUnit_per_hour_Rs', 'resources_cost_per_equipmentUnit_per_hour_Rs', 'total_area_required_for_all_units_m2', 'total_running_cost_per_hour_Rs', 'total_parts_replacement_cost_per_hour_Rs', 'total_maintenance_down_time_fractions_per_hour', 'total_resources_cost_per_hour_Rs']

    actions = ['delete_selected']
    # do the same with labour, but with none condition

    def delete_queryset(self, request, queryset):
        for myEquipment in queryset:
            myLine = Line.objects.get(id = myEquipment.line.id)
            myLine.line_operating_cost_per_hour_Rs = myLine.line_operating_cost_per_hour_Rs - myEquipment.total_running_cost_per_hour_Rs
            myLine.line_area_required_m2 = myLine.line_area_required_m2 - myEquipment.total_area_required_for_all_units_m2
            myLine.entire_maintenance_fraction_per_hour = myLine.entire_maintenance_fraction_per_hour - myEquipment.total_maintenance_down_time_fractions_per_hour
            myLine.save()
            myEquipment.delete(True)

@admin.register(LineEquipmentMaintenanceCost)
class LineEquipmentMaintenanceCostAdmin(admin.ModelAdmin):
    list_display = ['maintenance_name', 'equipment', 'maintenance_downTime_fraction_per_equipmentUnit_per_hour', 'part_replacement_cost_per_equipmentUnit_per_hour_Rs']
    search_fields = ['maintenance_name']
    actions = ['delete_selected']

    def delete_queryset(self, request, queryset):
        for myMntnce in queryset:
            myEquipment = LineEquipment.objects.get(id = myMntnce.equipment.id)
            myEquipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = myEquipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs  - myMntnce.part_replacement_cost_per_equipmentUnit_per_hour_Rs
            myEquipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour = myEquipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour - myMntnce.maintenance_downTime_fraction_per_equipmentUnit_per_hour
            myEquipment.save()
            myMntnce.delete(True)

@admin.register(LineEquipmentResourceCost)
class LineEquipmentResourceCostAdmin(admin.ModelAdmin):
    list_display = ['resource_name', 'equipment', 'cost_per_equipmentUnit_per_hour_for_this_resource_Rs']
    search_fields = ['resource_name']
    readonly_fields=['cost_per_equipmentUnit_per_hour_for_this_resource_Rs']

    actions = ['delete_selected']

    def delete_queryset(self, request, queryset):
        for myRsrc in queryset:
            myEquipment = LineEquipment.objects.get(id = myRsrc.equipment.id)
            myEquipment.resources_cost_per_equipmentUnit_per_hour_Rs = myEquipment.resources_cost_per_equipmentUnit_per_hour_Rs  - myRsrc.cost_per_equipmentUnit_per_hour_for_this_resource_Rs
            myEquipment.save()
            myRsrc.delete(True)

@admin.register(LineLabourCost)
class LineLabourCostAdmin(admin.ModelAdmin):
    list_display = ['role', 'line', 'number_of_labourers_required_for_this_role', 'total_labourCost_per_hour_Rs']
    search_fields = ['role']
    readonly_fields=['total_labourCost_per_hour_Rs']

    actions = ['delete_selected']

    def delete_queryset(self, request, queryset):
        for myLbOps in queryset:
            line = Line.objects.get(id = myLbOps.line.id)
            line.line_operating_cost_per_hour_Rs = line.line_operating_cost_per_hour_Rs - myLbOps.total_labourCost_per_hour_Rs
            line.save()
            myLbOps.delete(True)

@admin.register(LineRawMaterialCost)
class LineRawMaterialCostAdmin(admin.ModelAdmin):
    list_display = ['raw_material_name', 'line', 'raw_material_net_cost_per_hour_Rs']
    search_fields = ['raw_material_name']
    readonly_fields=['raw_material_net_cost_per_hour_Rs']

    actions = ['delete_selected']

    def delete_queryset(self, request, queryset):
        for myRawMCost in queryset:
            line = Line.objects.get(id = myRawMCost.line.id)
            line.line_operating_cost_per_hour_Rs = line.line_operating_cost_per_hour_Rs - myRawMCost.raw_material_net_cost_per_hour_Rs
            line.save()
            myRawMCost.delete(True)

@admin.register(MiscellaneousProductionOperatingCost)
class MiscellaneousProductionOperatingCostAdmin(admin.ModelAdmin):
    list_display = ['miscellaneous_operation_name', 'production', 'per_hour_cost_Rs']
    search_fields = ['miscellaneous_operation_name']
    actions = ['delete_selected']

    def delete_queryset(self, request, queryset):
        for myMscOps in queryset:
            myProduction = Production.objects.get(id = myMscOps.production.id)
            myProduction.total_production_cost_per_hour_Rs = myProduction.total_production_cost_per_hour_Rs  - myMscOps.per_hour_cost_Rs
            myProduction.save()
            myMscOps.delete(True)

@admin.register(MiscellaneousProductionInstallationCost)
class MiscellaneousProductionInstallationCostAdmin(admin.ModelAdmin):
    list_display = ['miscellaneous_installation_name', 'production', 'cost_Rs']
    search_fields = ['miscellaneous_installation_name']
    actions = ['delete_selected']

    def delete_queryset(self, request, queryset):
        for myMscInstls in queryset:
            myProduction = Production.objects.get(id = myMscInstls.production.id)
            myProduction.total_start_up_cost_Rs = myProduction.total_start_up_cost_Rs  - myMscInstls.cost_Rs
            myProduction.save()
            myMscInstls.delete(True)

@admin.register(MiscellaneousProductionAreaRequirement)
class MiscellaneousProductionAreaRequirementAdmin(admin.ModelAdmin):
    list_display = ['miscellaneous_area_role', 'production', 'area_allotment_m2']
    search_fields = ['miscellaneous_area_role']
    actions = ['delete_selected']

    def delete_queryset(self, request, queryset):
        for myMscArea in queryset:
            myProduction = Production.objects.get(id = myMscArea.production.id)
            myProduction.total_size_required_m2 = myProduction.total_size_required_m2  - myMscArea.area_allotment_m2
            myProduction.save()
            myMscArea.delete(True)



@admin.register(ResearchPaper)
class ResearchPaperAdmin(admin.ModelAdmin):
    list_display = ['research_paper_name', 'id', 'research_pdf', 'link']
    search_fields = ['research_paper_name']
    
class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    disabled password hash display field.
    """
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = ProjectManager
        fields = ('email', 'password', 'first_name',
                  'last_name', 'is_admin', 'image')


class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('email', 'is_admin')
    list_filter = ('is_admin',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'image')}),
        ('Permissions', {'fields': ('is_admin',)}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'first_name')
    ordering = ('email',)
    filter_horizontal = ()
    list_display = ['id', 'email', 'first_name']

    def delete_queryset(self, request, queryset):
        for user in queryset:
            if hasattr(user, 'productions') and list(user.productions.all()):
                productions = list(user.productions.all())
                for production in productions:
                    production.supervisor = None
                    production.save()
            user.delete(True)


# Now register the new UserAdmin...
admin.site.register(ProjectManager, UserAdmin)

# ... and, since we're not using Django's built-in permissions,
# unregister the Group model from admin.
admin.site.unregister(Group)

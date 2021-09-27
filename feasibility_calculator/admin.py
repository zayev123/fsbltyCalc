from django.contrib import admin

from feasibility_calculator.models import AvailableTechnology, Equipment, Equipment_Maintenance_Cost, Equipment_Resource_Cost, EventSchedule, Labour_PlantOperatingCost, Miscellaneous_Area_Requirement, Miscellaneous_PlantInstallationCost, Miscellaneous_PlantOperatingCost, Project, ProjectManager, Section_Production_Rate
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


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['project_name', 'project_manager', 'production_hours_per_day']

@admin.register(AvailableTechnology)
class AvailableTechnologyAdmin(admin.ModelAdmin):
    list_display = ['technology_name', 'project', 'total_start_up_cost_Rs', 'total_operating_cost_per_hour_Rs', 'total_revenue_per_hour_Rs', 'profit_margins_per_hour_Rs', 'total_size_required_m2', 'start_date', 'end_date', 'break_even_date']
    readonly_fields=['total_start_up_cost_Rs', 'total_operating_cost_per_hour_Rs', 'total_revenue_per_hour_Rs', 'profit_margins_per_hour_Rs', 'total_size_required_m2', 'break_even_date']

@admin.register(EventSchedule)
class EventScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'event_name', 'technology', 'event_start_date', 'event_end_date', 'event_cost_Rs', 'latest_previous_dependent_event']
    fields = ['technology', 'event_name', 'previous_related_events', 'days_to_complete', 'event_cost_Rs', 'reference', 'remarks', 'event_start_date', 'event_end_date', 'latest_previous_dependent_event']
    readonly_fields=['event_start_date', 'event_end_date', 'latest_previous_dependent_event']
    form = EventScheduleForm
    filter_horizontal = ('previous_related_events',)

    actions = ['delete_selected']

    def delete_queryset(self, request, queryset):
        for myEvent in queryset:
            #myPolicy = Policy.objects.get(id = myEndorsement.policy.id)
            #myPolicy.outstanding = myPolicy.outstanding + myEndorsement.premium_paid
            #myPolicy.save()
            myEvent.delete()

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['equipment_name', 'technology', 'number_of_equipment_units_needed', 'total_area_required_for_all_units_m2', 'total_running_cost_per_hour_Rs']
    readonly_fields=['maintenance_down_time_fractions_per_equipmentUnit_per_hour', 'parts_replacement_cost_per_equipmentUnit_per_hour_Rs', 'resources_cost_per_equipmentUnit_per_hour_Rs', 'total_area_required_for_all_units_m2', 'total_running_cost_per_hour_Rs', 'total_parts_replacement_cost_per_hour_Rs', 'total_maintenance_down_time_fractions_per_hour', 'total_resources_cost_per_hour_Rs']

@admin.register(Equipment_Maintenance_Cost)
class Equipment_Maintenance_CostAdmin(admin.ModelAdmin):
    list_display = ['maintenance_name', 'equipment', 'maintenance_downTime_fraction_per_unit_per_hour', 'part_replacement_cost_per_unit_per_hour_Rs']

@admin.register(Equipment_Resource_Cost)
class Equipment_Resource_CostAdmin(admin.ModelAdmin):
    list_display = ['resource_name', 'equipment', 'cost_per_equipmentUnit_per_hour_for_this_resource_Rs']
    readonly_fields=['cost_per_equipmentUnit_per_hour_for_this_resource_Rs']

@admin.register(Labour_PlantOperatingCost)
class Labour_PlantOperatingCostAdmin(admin.ModelAdmin):
    list_display = ['role', 'technology', 'number_of_labourers_required_for_this_role', 'total_labourCost_per_hour_Rs']
    readonly_fields=['total_labourCost_per_hour_Rs']

@admin.register(Miscellaneous_PlantOperatingCost)
class Miscellaneous_PlantOperatingCostAdmin(admin.ModelAdmin):
    list_display = ['miscellaneous_operation_name', 'technology', 'per_hour_cost_Rs']

@admin.register(Miscellaneous_PlantInstallationCost)
class Miscellaneous_PlantInstallationCostAdmin(admin.ModelAdmin):
    list_display = ['miscellaneous_installation_name', 'technology', 'cost_Rs']


@admin.register(Miscellaneous_Area_Requirement)
class Miscellaneous_Area_RequirementAdmin(admin.ModelAdmin):
    list_display = ['miscellaneous_area_role', 'technology', 'area_allotment_m2']


@admin.register(Section_Production_Rate)
class Section_Production_RateAdmin(admin.ModelAdmin):
    list_display = ['id', 'total_hourly_revenue_generated_for_this_section_Rs', 'labour_role_needed', 'equipment_model_used']
    readonly_fields=['amount_of_section_product_missed_per_hour_for_maintenance', 'net_amount_of_product_produced_per_hour', 'total_hourly_revenue_generated_for_this_section_Rs']

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


# Now register the new UserAdmin...
admin.site.register(ProjectManager, UserAdmin)

# ... and, since we're not using Django's built-in permissions,
# unregister the Group model from admin.
admin.site.unregister(Group)

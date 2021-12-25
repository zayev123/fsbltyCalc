from django.contrib import admin

from electroplating_automation.models import Tank

# Register your models here.
@admin.register(Tank)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['tank_number', 'process_name', 'immersion_time_mins', 'tank_type_number', 'is_wait_type_tank', 'max_wait_time_mins',]
    search_fields = ['process_name']

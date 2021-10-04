from feasibility_calculator.presave_functions import manage_presave_CompOnlyCosts, manage_presave_LineEquimaintenance, manage_presave_Linelabour, manage_presave_events, manage_presave_line, manage_presave_lineEquiResource, manage_presave_lineEquipment, manage_presave_msclnsProdAreaCost, manage_presave_msclnsProdInstlsCost, manage_presave_msclnsProdOpsCost, manage_presave_prod, manage_presave_rawMatHourlyCost, setEndDate, update_event_links
from django.db import models

from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser
)
from django.contrib.auth.hashers import make_password
from frzFeasibilityHandler.myStorage import OverwriteStorage


from django.db.models import Q
from datetime import timedelta
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db.models.signals import m2m_changed

from django.core.exceptions import ValidationError
from django.utils.html import format_html
###### equipment rplacement cost is basically maintenance cost:
###### create a different class for it i think
class ProjectManager_Manager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user


class ProjectManager(AbstractBaseUser):
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    first_name = models.CharField(max_length=200, blank=True, null=True)
    last_name = models.CharField(max_length=200, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to='profile_images', blank=True, null=True, storage=OverwriteStorage())
    bas64Image = models.TextField(blank=True, null=True)
    imageType = models.CharField(max_length=10, blank=True, null=True)
    phoneNumber = models.CharField(max_length=30, blank=True, null=True)

    objects = ProjectManager_Manager()

    USERNAME_FIELD = 'email'

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin

    class Meta:
        verbose_name_plural = "            3. Supervisors"

class Company(models.Model):
    company_name = models.CharField(max_length=100)
    total_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=18,decimal_places=6)
    total_revenue_per_hour_Rs = models.DecimalField(default=0, max_digits=20,decimal_places=6)
    total_profits_per_hour = models.DecimalField(default=0, max_digits=20,decimal_places=6)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    remarks = models.TextField(blank=True, null=True,)

    def save(self, *args, **kwargs):
        self.total_profits_per_hour = self.total_revenue_per_hour_Rs - self.total_cost_per_hour_Rs
        # else, the id is retreived, and it is managed during presave
        super(Company, self).save()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', COMPANY NAME: ' + self.company_name

    class Meta:
        verbose_name_plural = "              1. Company" 

# how i found per hour cost: I found per hour cost by finding total per day salary of
# each employee operating the machine
# the total time spent in a day operating the equipment
# that time / total working hours per day
# multiply th fraction with per day salary

class CompanyOnlyOperatingCost(models.Model):
    operation_name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, related_name='company_only_operating_cost', on_delete=models.CASCADE)
    per_hour_cost_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.id == None:
            myCompany = self.company
            myCompany.total_cost_per_hour_Rs = myCompany.total_cost_per_hour_Rs  + self.per_hour_cost_Rs
            myCompany.save()
        # else, the id is retreived, and it is managed during presave
        super(CompanyOnlyOperatingCost, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myCompany = self.production
            myCompany.total_cost_per_hour_Rs = myCompany.total_cost_per_hour_Rs - self.per_hour_cost_Rs
            myCompany.save()
        super(CompanyOnlyOperatingCost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', OPERATION NAME: ' + self.operation_name
    
    class Meta:
        verbose_name_plural = "             2. Company Only Operating Costs"

@receiver(pre_save, sender=CompanyOnlyOperatingCost)
def preSaveCompOnlyCosts(sender, instance, **kwargs):
    try:
        original_compCost = sender.objects.get(pk=instance.pk)
        changed_compCost = instance
        current_comp = original_compCost.company
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        manage_presave_CompOnlyCosts(original_compCost, changed_compCost, current_comp)

class Production(models.Model):
    company = models.ForeignKey(Company, related_name='productions', on_delete=models.CASCADE)
    product_name = models.CharField(max_length=100)
    total_start_up_cost_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    total_production_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    total_size_required_m2 = models.DecimalField(default=0, max_digits=12,decimal_places=6)
    total_amount_of_products_fnnished_per_hour = models.DecimalField(default=0, max_digits=18,decimal_places=6)
    total_amount_of_products_rejected_or_leftover_per_hour = models.DecimalField(default=0, max_digits=18,decimal_places=6)
    total_amount_of_products_sold_per_hour = models.DecimalField(default=0, max_digits=18,decimal_places=6)
    product_measurement_unit = models.CharField(max_length=100, default='Units')
    total_cost_per_product_Rs = models.DecimalField(default=0, max_digits=18,decimal_places=6)
    selling_price_per_product_Rs = models.DecimalField(default=0, max_digits=18,decimal_places=6)
    total_revenue_generated_per_hour_Rs = models.DecimalField(default=0, max_digits=18,decimal_places=6)
    total_profit_generated_per_hour_Rs = models.DecimalField(default=0, max_digits=18,decimal_places=6)
    end_line_production_hours_per_day_weekly_projection = models.DecimalField(default=0, max_digits=8,decimal_places=6)
    supervisor = models.ForeignKey(ProjectManager, related_name='Production', on_delete=models.CASCADE)
    project_start_date = models.DateTimeField()
    project_end_date = models.DateTimeField(blank=True, null=True)
    break_even_date = models.DateTimeField(blank=True, null=True)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    remarks = models.TextField(blank=True, null=True,)
    
    def save(self, *args, **kwargs):
        if self.total_amount_of_products_fnnished_per_hour != 0:
            self.total_cost_per_product_Rs = self.total_production_cost_per_hour_Rs / self.total_amount_of_products_fnnished_per_hour
        else:
            self.total_cost_per_product_Rs = 0
        # why not preassign sold, because sold can be more than produced sometimes
        self.total_amount_of_products_sold_per_hour = self.total_amount_of_products_fnnished_per_hour - self.total_amount_of_products_rejected_or_leftover_per_hour
        self.total_revenue_generated_per_hour_Rs = self.selling_price_per_product_Rs * self.total_amount_of_products_sold_per_hour
        self.total_profit_generated_per_hour_Rs = self.total_revenue_generated_per_hour_Rs - self.total_production_cost_per_hour_Rs
        if self.total_profit_generated_per_hour_Rs != 0 and self.project_end_date != None:
            hours_to_break_even = self.total_start_up_cost_Rs / self.total_profit_generated_per_hour_Rs
            days_to_breakeven = int(hours_to_break_even / self.end_line_production_hours_per_day_weekly_projection)
            self.break_even_date = self.project_end_date + timedelta(days=days_to_breakeven)
        if self.id == None:
            new_comp = self.company
            new_comp.total_cost_per_hour_Rs = new_comp.total_cost_per_hour_Rs + self.total_production_cost_per_hour_Rs
            new_comp.total_revenue_per_hour_Rs = new_comp.total_revenue_per_hour_Rs + self.total_revenue_generated_per_hour_Rs
            new_comp.save()
        super(Production, self).save(False)

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myCompany = self.company
            myCompany.total_cost_per_hour_Rs = myCompany.total_cost_per_hour_Rs - self.total_production_cost_per_hour_Rs
            myCompany.total_revenue_per_hour_Rs = myCompany.total_revenue_per_hour_Rs - self.total_revenue_generated_per_hour_Rs
            myCompany.save()
        super(Production, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', PRODUCT NAME: ' + self.product_name

    class Meta:
        verbose_name_plural = "           4. Production Facilities"

@receiver(pre_save, sender=Production)
def preSaveProdLine(sender, instance, **kwargs):
    try:
        original_prod = sender.objects.get(pk=instance.pk)
        changed_prod = instance
        current_comp = original_prod.company
    except sender.DoesNotExist:
        pass
    else:
        manage_presave_prod(original_prod, changed_prod, current_comp)

# i cant access args in presave thats for sure
class ResearchPaper(models.Model):
    research_paper_name = models.CharField(max_length=100, blank=True, null=True)
    link = models.CharField(max_length=200, blank=True, null=True)
    research_pdf = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    remarks = models.TextField(blank=True, null=True,)

    def __str__(self):
        return 'ID: ' + str(self.id) + ', RESEARCH PAPER NAME: ' + self.research_paper_name

    class Meta:
        verbose_name_plural = "15. Research Papers"


# this will include all financial and non financial events, such as labour installation costs, and
# eqipment installation costs
class EventSchedule(models.Model):
    # the end results of each of these models should end in the available product
    # it just checks with its previous event, so it is going to be simpler
    # you can make a recursive function for this one with a base case
    production = models.ForeignKey(Production, related_name='project_time_line', on_delete=models.CASCADE)
    event_name = models.CharField(max_length=100)
    # use mod calculation for finding hours
    days_to_complete = models.DecimalField(default=0, max_digits=11,decimal_places=6)
    event_start_date = models.DateTimeField(blank=True, null=True)
    event_end_date = models.DateTimeField(blank=True, null=True)
    event_cost_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    # you'll have to use a for loop in this case
    previous_related_events = models.ManyToManyField('EventSchedule', related_name='next_related_events', blank=True)
    latest_previous_dependent_event = models.CharField(max_length=100, blank=True, null=True)
    is_completed = models.BooleanField(default= False)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    remarks = models.TextField(blank=True, null=True,)

    def save(self, *args, **kwargs):
        if self.id == None:
            myproduction = self.production
            self.event_start_date = myproduction.project_start_date
            self.latest_previous_dependent_event = None
            myproduction.total_start_up_cost_Rs = myproduction.total_start_up_cost_Rs + self.event_cost_Rs
            myproduction.save()
            setEndDate(self)
        super(EventSchedule, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myproduction = self.production
        # if related field, then also get all its related fields using filter or related name and delete those aswell
            if hasattr(self, 'next_related_events') and list(self.next_related_events.all()):
                next_events = self.next_related_events.all()
                for next_event in next_events:
                    nextin_prevy_events = next_event.previous_related_events.all()
                    if nextin_prevy_events[0].id == self.id:
                        if len(nextin_prevy_events) > 1:
                            next_event.event_start_date = nextin_prevy_events[1].event_end_date
                            next_event.latest_previous_dependent_event = str(nextin_prevy_events[1])
                            setEndDate(next_event)
                            next_event.save()
                        else:
                            next_event.event_start_date = myproduction.project_start_date
                            next_event.latest_previous_dependent_event = None
                            setEndDate(next_event)
                            next_event.save()
                        # yeah obviously, its not calling it self as in the delete function
                        # so no recusrsion as such
            myproduction.total_start_up_cost_Rs = myproduction.total_start_up_cost_Rs - self.event_cost_Rs
            myproduction.save()
        super(EventSchedule, self).delete()

    class Meta:
        ordering = ['-event_end_date']
        verbose_name_plural = "          5. Project Timelines & Schedules"

    def __str__(self):
        return 'ID: ' + str(self.id) + ', EVENT NAME: ' + self.event_name

@receiver(pre_save, sender=EventSchedule)
def preSaveEvent(sender, instance, **kwargs):
    try:
        original_event = sender.objects.get(pk=instance.pk)
        changed_event = instance
        current_prod = original_event.production
        duration = changed_event.days_to_complete
        my_days = int(duration)
        day_fraction = duration % 1
        my_hours = int(24 * day_fraction)
        changed_event.event_end_date = changed_event.event_start_date + timedelta(days=my_days, hours = my_hours)
    except sender.DoesNotExist:
        pass
    else:
        # first check if date changed, then check if name changed
        # this just matches the events and is independent of any product
        # other stuff happens when m2m change
        manage_presave_events(original_event, changed_event, current_prod)

def events_changed(sender, instance, action, **kwargs):
    if action == "post_add" or action == "post_remove":
        
        selfEvent = instance
        update_event_links(selfEvent)
        selfEvent.save()

m2m_changed.connect(events_changed, sender=EventSchedule.previous_related_events.through)
            
class Line(models.Model):
    production = models.ForeignKey(Production, related_name='production_lines', on_delete=models.CASCADE, blank=True, null=True)
    line_name = models.CharField(max_length=100)
    automation_percentage = models.DecimalField(default=0, max_digits=8,decimal_places=6)
    working_days_per_year = models.DecimalField(default=365, max_digits=9,decimal_places=6)
    working_hours_per_day = models.DecimalField(default=24, max_digits=8,decimal_places=6)
    product_measurement_unit = models.CharField(max_length=100, default='Units')
    # only handle save, if this below value is saved
    line_operating_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    line_product_shipping_cost_per_bulk_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    line_product_shipping_frequency_per_year = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    line_product_net_shipping_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    line_area_required_m2 = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    max_ideal_amount_of_section_product_produced_per_hour = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    entire_maintenance_fraction_per_hour = models.DecimalField(default=0, max_digits=8,decimal_places=6)
    amount_of_section_product_missed_per_hour_for_maintenance = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    net_amount_of_product_produced_per_hour = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    is_last_stage = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.working_days_per_year !=0 and self.working_hours_per_day !=0 and self.line_product_shipping_frequency_per_year != 0:
            self.line_product_net_shipping_cost_per_hour_Rs = self.line_product_shipping_cost_per_bulk_Rs / ((self.working_days_per_year * self.working_hours_per_day) / self.line_product_shipping_frequency_per_year)
        else:
           self.line_product_net_shipping_cost_per_hour_Rs = 0 
        self.amount_of_section_product_missed_per_hour_for_maintenance = self.max_ideal_amount_of_section_product_produced_per_hour * self.entire_maintenance_fraction_per_hour
        self.net_amount_of_product_produced_per_hour = self.max_ideal_amount_of_section_product_produced_per_hour - self.amount_of_section_product_missed_per_hour_for_maintenance
        if self.id == None:
            new_prod = self.production
            new_prod.total_size_required_m2 = new_prod.total_size_required_m2 + self.line_area_required_m2
            new_prod.total_production_cost_per_hour_Rs = new_prod.total_production_cost_per_hour_Rs + self.line_operating_cost_per_hour_Rs + self.line_product_net_shipping_cost_per_hour_Rs
            new_prod.save()
        # else, the id is retreived, and it is managed during presave
        super(Line, self).save()
        return self.net_amount_of_product_produced_per_hour
    
    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myproduction = self.production
            myproduction.total_size_required_m2 = myproduction.total_size_required_m2 - self.line_area_required_m2
            myproduction.total_production_cost_per_hour_Rs = myproduction.total_production_cost_per_hour_Rs - self.line_operating_cost_per_hour_Rs - self.line_product_net_shipping_cost_per_hour_Rs
            myproduction.save()
        super(Line, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', SECTION: ' + self.line_name

    class Meta:
        verbose_name_plural = "         6. Production Lines"

# maintenance will only be done if equipment is used, and that is:
# the only data that comes from outside, so i donot need to add a foreign key
# to labour
@receiver(pre_save, sender=Line)
def preSaveLine(sender, instance, **kwargs):
    try:
        original_line = sender.objects.get(pk=instance.pk)
        changed_line = instance
        current_prod = original_line.production
    except sender.DoesNotExist:
        pass
    else:
        manage_presave_line(original_line, changed_line, current_prod)


# miscellaneous "project" equipments

class LineEquipment(models.Model):
    line = models.ForeignKey(Line, related_name='line_equipments', on_delete=models.CASCADE, blank=True, null=True)
    equipment_name = models.CharField(max_length=100)
    number_of_equipment_units_needed = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    total_area_required_for_all_units_m2 = models.DecimalField(default=0, max_digits=12,decimal_places=6)
    total_running_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    total_parts_replacement_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    total_resources_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    total_maintenance_down_time_fractions_per_hour = models.DecimalField(default=0, max_digits=10,decimal_places=6)
    area_required_per_Equipmentunit_m2 = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    # to be updated whenever a resource is added or subtracted
    parts_replacement_cost_per_equipmentUnit_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    resources_cost_per_equipmentUnit_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    maintenance_down_time_fractions_per_equipmentUnit_per_hour = models.DecimalField(default=0, max_digits=10,decimal_places=6)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    remarks = models.TextField(blank=True, null=True,)

    def save(self, *args, **kwargs):
        self.total_area_required_for_all_units_m2 = self.number_of_equipment_units_needed * self.area_required_per_Equipmentunit_m2
        self.total_parts_replacement_cost_per_hour_Rs = self.number_of_equipment_units_needed * self.parts_replacement_cost_per_equipmentUnit_per_hour_Rs
        self.total_resources_cost_per_hour_Rs = self.number_of_equipment_units_needed * self.resources_cost_per_equipmentUnit_per_hour_Rs
        self.total_maintenance_down_time_fractions_per_hour = self.number_of_equipment_units_needed * self.maintenance_down_time_fractions_per_equipmentUnit_per_hour
        self.total_running_cost_per_hour_Rs = self.total_parts_replacement_cost_per_hour_Rs + self.total_resources_cost_per_hour_Rs
        if self.id == None:
            myLine = self.line
            myLine.line_operating_cost_per_hour_Rs = myLine.line_operating_cost_per_hour_Rs + self.total_running_cost_per_hour_Rs
            myLine.line_area_required_m2 = myLine.line_area_required_m2 + self.total_area_required_for_all_units_m2
            myLine.entire_maintenance_fraction_per_hour = myLine.entire_maintenance_fraction_per_hour + self.total_maintenance_down_time_fractions_per_hour
            myLine.save() 
        super(LineEquipment, self).save()

    
    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myLine = self.line
            myLine.line_operating_cost_per_hour_Rs = myLine.line_operating_cost_per_hour_Rs - self.total_running_cost_per_hour_Rs
            myLine.line_area_required_m2 = myLine.line_area_required_m2 - self.total_area_required_for_all_units_m2
            myLine.entire_maintenance_fraction_per_hour = myLine.entire_maintenance_fraction_per_hour - self.total_maintenance_down_time_fractions_per_hour
            myLine.save()
        super(LineEquipment, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', EQUIPMENT NAME: ' + self.equipment_name

    class Meta:
        verbose_name_plural = "        7. Line Equipments"

@receiver(pre_save, sender=LineEquipment)
def preSaveLineEquipment(sender, instance, **kwargs):
    try:
        original_equipment = sender.objects.get(pk=instance.pk)
        changed_equipment = instance
        current_line = original_equipment.line
    except sender.DoesNotExist:
        pass
    else:
        manage_presave_lineEquipment(original_equipment, changed_equipment, current_line)
            
# the reason why im not adding a calculation for it, is because
# the way i calculate it may change every time
# i am manking assumtions
class LineEquipmentMaintenanceCost(models.Model):
    maintenance_name = models.CharField(max_length=100)
    equipment = models.ForeignKey(LineEquipment, related_name='maintenance_costs', on_delete=models.CASCADE)
    maintenance_downTime_fraction_per_equipmentUnit_per_hour = models.DecimalField(default=0, max_digits=6,decimal_places=6)
    part_replacement_cost_per_equipmentUnit_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.id == None:
            eqpmnt = self.equipment
            eqpmnt.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = eqpmnt.parts_replacement_cost_per_equipmentUnit_per_hour_Rs + self.part_replacement_cost_per_equipmentUnit_per_hour_Rs
            eqpmnt.maintenance_down_time_fractions_per_equipmentUnit_per_hour = eqpmnt.maintenance_down_time_fractions_per_equipmentUnit_per_hour + self.maintenance_downTime_fraction_per_equipmentUnit_per_hour
            eqpmnt.save()
        # else, the id is retreived, and it is managed during presave
        super(LineEquipmentMaintenanceCost, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myEquipment = self.equipment
            myEquipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = myEquipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs  - self.part_replacement_cost_per_equipmentUnit_per_hour_Rs
            myEquipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour = myEquipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour - self.maintenance_downTime_fraction_per_equipmentUnit_per_hour
            myEquipment.save()
        super(LineEquipmentMaintenanceCost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', MAINTENANCE NAME: ' + self.maintenance_name

    class Meta:
        verbose_name_plural = "       8. Line Equipment Maintenance Costs"
    # add a save method that will do the math to subtract the total parts produced per hour for this
    # equipment

@receiver(pre_save, sender=LineEquipmentMaintenanceCost)
def preSaveLineEquiMaintenance(sender, instance, **kwargs):
    try:
        original_maintenance = sender.objects.get(pk=instance.pk)
        changed_maintenance = instance
        current_equipment = original_maintenance.equipment
    except sender.DoesNotExist:
        pass
    else:
        manage_presave_LineEquimaintenance(original_maintenance, changed_maintenance, current_equipment)


class LineEquipmentResourceCost(models.Model):
    equipment = models.ForeignKey(LineEquipment, related_name='resource_costs', on_delete=models.CASCADE)
    resource_name = models.CharField(max_length=100)
    resource_unit_of_measure = models.CharField(max_length=100)
    cost_per_single_unit_resource_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    resource_quantity_needed_per_EquipmentUnit_per_hour = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    cost_per_equipmentUnit_per_hour_for_this_resource_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    
    def save(self, *args, **kwargs):
        self.cost_per_equipmentUnit_per_hour_for_this_resource_Rs = self.resource_quantity_needed_per_EquipmentUnit_per_hour * self.cost_per_single_unit_resource_Rs
        if self.id == None:
            eqpmnt = self.equipment
            eqpmnt.resources_cost_per_equipmentUnit_per_hour_Rs = eqpmnt.resources_cost_per_equipmentUnit_per_hour_Rs + self.cost_per_equipmentUnit_per_hour_for_this_resource_Rs
            eqpmnt.save()
        # else, the id is retreived, and it is managed during presave
        super(LineEquipmentResourceCost, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myEquipment = self.equipment
            myEquipment.resources_cost_per_equipmentUnit_per_hour_Rs = myEquipment.resources_cost_per_equipmentUnit_per_hour_Rs  - self.cost_per_equipmentUnit_per_hour_for_this_resource_Rs
            myEquipment.save()
        super(LineEquipmentResourceCost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', RESOURCE: ' + self.resource_name

    class Meta:
        verbose_name_plural = "      9. Line Equipment Resource Costs"

@receiver(pre_save, sender=LineEquipmentResourceCost)
def preSaveEquiResource(sender, instance, **kwargs):
    try:
        original_resource = sender.objects.get(pk=instance.pk)
        changed_resource = instance
        current_equipment = original_resource.equipment
    except sender.DoesNotExist:
        pass
    else:
        manage_presave_lineEquiResource(original_resource, changed_resource, current_equipment)
# for changing tech of labour, if it is already comitted to a production, 
# and that production has an equipment, and the equipment tech and 
# labour tech are different, then pass, because you can get the old tech, from 
# its affiliated line_equipments tech in production
# do the same checks in save method, and add an error, unless if args provided


class LineLabourCost(models.Model):
    line = models.ForeignKey(Line, related_name='line_labours', on_delete=models.CASCADE, blank=True, null=True)
    role = models.CharField(max_length=300)
    number_of_labourers_required_for_this_role = models.DecimalField(default=0, max_digits=12,decimal_places=6)
    salary_per_hour_per_labourer_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    safety_risk_cost_per_hour_per_labourer_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    total_labourCost_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        self.total_labourCost_per_hour_Rs = self.number_of_labourers_required_for_this_role * (self.salary_per_hour_per_labourer_Rs + self.safety_risk_cost_per_hour_per_labourer_Rs)
        if self.id == None:
            line = self.line
            line.line_operating_cost_per_hour_Rs = line.line_operating_cost_per_hour_Rs + self.total_labourCost_per_hour_Rs
            line.save() 
        # else, the id is retreived, and it is managed during presave
        super(LineLabourCost, self).save()

    
    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            line = self.line
            line.line_operating_cost_per_hour_Rs = line.line_operating_cost_per_hour_Rs - self.total_labourCost_per_hour_Rs
            line.save()
        super(LineLabourCost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', ROLE: ' + self.role

    class Meta:
        verbose_name_plural = "     10. Line Labour Costs"

@receiver(pre_save, sender=LineLabourCost)
def preSaveLabour(sender, instance, **kwargs):
    try:
        original_labour = sender.objects.get(pk=instance.pk)
        changed_labour = instance
        current_line = original_labour.line
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        manage_presave_Linelabour(original_labour, changed_labour, current_line)

class LineRawMaterialCost(models.Model):
    line = models.ForeignKey(Line, related_name='raw_material_costs', on_delete=models.CASCADE)
    raw_material_name = models.CharField(max_length=100)
    raw_material_bulk_purchase_cost_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    raw_material_transport_cost_per_bulk_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    purchase_frquency_per_year = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    raw_material_net_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    working_days_per_year_for_this_line = models.DecimalField(default=0, max_digits=9,decimal_places=6)
    working_hours_per_day_for_this_line = models.DecimalField(default=0, max_digits=8,decimal_places=6)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.working_days_per_year_for_this_line != 0 and self.working_hours_per_day_for_this_line != 0 and self.purchase_frquency_per_year:
            self.raw_material_net_cost_per_hour_Rs = (self.raw_material_bulk_purchase_cost_Rs + self.raw_material_transport_cost_per_bulk_Rs) / ((self.working_days_per_year_for_this_line * self.working_hours_per_day_for_this_line) / self.purchase_frquency_per_year)
        else:
            self.raw_material_net_cost_per_hour_Rs = 0
        if self.id == None:
            myline = self.line
            myline.line_operating_cost_per_hour_Rs = myline.line_operating_cost_per_hour_Rs  + self.raw_material_net_cost_per_hour_Rs
            myline.save()
        # else, the id is retreived, and it is managed during presave
        super(LineRawMaterialCost, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myline = self.line
            myline.line_operating_cost_per_hour_Rs = myline.line_operating_cost_per_hour_Rs  - self.raw_material_net_cost_per_hour_Rs
            myline.save()
        super(LineRawMaterialCost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', RAW MATERIAL NAME: ' + self.raw_material_name

    class Meta:
        verbose_name_plural = "    11. Line Raw Material Costs"

@receiver(pre_save, sender=LineRawMaterialCost)
def preSaveMsclOps(sender, instance, **kwargs):
    try:
        original_rawMatCost = sender.objects.get(pk=instance.pk)
        changed_rawMatCost = instance
        current_line = original_rawMatCost.line
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        manage_presave_rawMatHourlyCost(original_rawMatCost, changed_rawMatCost, current_line)

class MiscellaneousProductionOperatingCost(models.Model):
    miscellaneous_operation_name = models.CharField(max_length=100)
    production = models.ForeignKey(Production, related_name='miscellaneous_production_costs', on_delete=models.CASCADE)
    per_hour_cost_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.id == None:
            myproduction = self.production
            myproduction.total_production_cost_per_hour_Rs = myproduction.total_production_cost_per_hour_Rs  + self.per_hour_cost_Rs
            myproduction.save()
        # else, the id is retreived, and it is managed during presave
        super(MiscellaneousProductionOperatingCost, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myproduction = self.production
            myproduction.total_production_cost_per_hour_Rs = myproduction.total_production_cost_per_hour_Rs - self.per_hour_cost_Rs
            myproduction.save()
        super(MiscellaneousProductionOperatingCost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', PRODUCTION OPERATION NAME: ' + self.miscellaneous_operation_name

    class Meta:
        verbose_name_plural = "   12. Miscellaneous - Production Facility Operating Costs"

@receiver(pre_save, sender=MiscellaneousProductionOperatingCost)
def preSaveMsclOps(sender, instance, **kwargs):
    try:
        original_msclOps = sender.objects.get(pk=instance.pk)
        changed_msclOps = instance
        current_prod = original_msclOps.production
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        manage_presave_msclnsProdOpsCost(original_msclOps, changed_msclOps, current_prod)


class MiscellaneousProductionInstallationCost(models.Model):
    miscellaneous_installation_name = models.CharField(max_length=100)
    production = models.ForeignKey(Production, related_name='miscellaneous_installation_costs', on_delete=models.CASCADE)
    cost_Rs = models.DecimalField(default=0, max_digits=16,decimal_places=6)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.id == None:
            myproduction = self.production
            myproduction.total_start_up_cost_Rs = myproduction.total_start_up_cost_Rs + self.cost_Rs
            myproduction.save()
        # else, the id is retreived, and it is managed during presave
        super(MiscellaneousProductionInstallationCost, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myproduction = self.production
            myproduction.total_start_up_cost_Rs = myproduction.total_start_up_cost_Rs - self.cost_Rs
            myproduction.save()
        super(MiscellaneousProductionInstallationCost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', PRODUCTION INSTALLATION NAME: ' + self.miscellaneous_installation_name

    class Meta:
        verbose_name_plural = "  13. Miscellaneous - Production Facility Installation Costs"

@receiver(pre_save, sender=MiscellaneousProductionInstallationCost)
def preSaveMsclInstls(sender, instance, **kwargs):
    try:
        original_msclInstls = sender.objects.get(pk=instance.pk)
        changed_msclInstls = instance
        current_prod = original_msclInstls.production
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        manage_presave_msclnsProdInstlsCost(original_msclInstls, changed_msclInstls, current_prod)

class MiscellaneousProductionAreaRequirement(models.Model):
    miscellaneous_area_role = models.CharField(max_length=100)
    production = models.ForeignKey(Production, related_name='MiscellaneousProductionAreaRequirements', on_delete=models.CASCADE)
    area_allotment_m2 = models.DecimalField(default=0, max_digits=12,decimal_places=6)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.id == None:
            myproduction = self.production
            myproduction.total_size_required_m2 = myproduction.total_size_required_m2  + self.area_allotment_m2
            myproduction.save()
        # else, the id is retreived, and it is managed during presave
        super(MiscellaneousProductionAreaRequirement, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myproduction = self.production
            myproduction.total_size_required_m2 = myproduction.total_size_required_m2 - self.area_allotment_m2
            myproduction.save()
        super(MiscellaneousProductionAreaRequirement, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', PRODUCTION AREA ROLE: ' + self.miscellaneous_area_role

    class Meta:
        verbose_name_plural = " 14. Miscellaneous - Production Facility Area Requirements"

@receiver(pre_save, sender=MiscellaneousProductionAreaRequirement)
def preSaveMsclArea(sender, instance, **kwargs):
    try:
        original_msclArea = sender.objects.get(pk=instance.pk)
        changed_msclArea = instance
        current_prod = original_msclArea.production
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        manage_presave_msclnsProdAreaCost(original_msclArea, changed_msclArea, current_prod)
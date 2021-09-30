from feasibility_calculator.presave_functions import manage_presave_equiResource, manage_presave_equipment, manage_presave_labour, manage_presave_maintenance, manage_presave_production
from django.db import models

from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser
)
from django.contrib.auth.hashers import make_password
from frzFeasibilityHandler.myStorage import OverwriteStorage


from django.db.models import Q
from datetime import date, timedelta
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

class Project(models.Model):
    project_manager = models.ForeignKey(ProjectManager, related_name='projects', on_delete=models.CASCADE)
    project_name = models.CharField(max_length=100)
    production_hours_per_day = models.IntegerField(default=0)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    remarks = models.TextField(blank=True, null=True,)

    def __str__(self):
        return 'ID: ' + str(self.id) + ', PROJECT NAME: ' + self.project_name

# how i found per hour cost: I found per hour cost by finding total per day salary of
# each employee operating the machine
# the total time spent in a day operating the equipment
# that time / total working hours per day
# multiply th fraction with per day salary

class AvailableTechnology(models.Model):
    project = models.ForeignKey(Project, related_name='available_technologies', on_delete=models.CASCADE)
    technology_name = models.CharField(max_length=100)
    total_start_up_cost_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_operating_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_misc_ops_costs_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_equipment_ops_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_labour_ops_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_revenue_per_hour_Rs = models.DecimalField(default=0, max_digits=13,decimal_places=2)
    profit_margins_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_size_required_m2 = models.DecimalField(default=0, max_digits=8,decimal_places=2)
    total_equip_size_reqs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_misc_size_reqs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)
    break_even_date = models.DateTimeField(blank=True, null=True)
    is_best_option = models.BooleanField(default=False)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    remarks = models.TextField(blank=True, null=True,)
    
    def save(self, *args, **kwargs):
        equip_cost = 0
        area = 0
        if hasattr(self, 'equipments') and list(self.equipments.all()):
            equipments = list(self.equipments.all())
            for equipment in equipments:
                equip_cost = equip_cost + equipment.total_running_cost_per_hour_Rs
                area = area + equipment.total_area_required_for_all_units_m2
        labo_cost = 0
        if hasattr(self, 'labour_operating_costs') and list(self.labour_operating_costs.all()):
            labours = list(self.labour_operating_costs.all())
            for labour in labours:
                labo_cost = labo_cost + labour.total_labourCost_per_hour_Rs
        self.total_equip_size_reqs = area
        self.total_labour_ops_cost_per_hour_Rs = labo_cost
        self.total_equipment_ops_cost_per_hour_Rs = equip_cost
        self.total_size_required_m2 = self.total_equip_size_reqs + self.total_misc_size_reqs        
        self.total_operating_cost_per_hour_Rs = self.total_equipment_ops_cost_per_hour_Rs + self.total_labour_ops_cost_per_hour_Rs + self.total_misc_ops_costs_per_hour_Rs
        self.profit_margins_per_hour_Rs = self.total_revenue_per_hour_Rs - self.total_operating_cost_per_hour_Rs
        if self.end_date != None and self.profit_margins_per_hour_Rs != 0 and self.project.production_hours_per_day !=0:
            hours_to_break_even = self.total_start_up_cost_Rs/self.profit_margins_per_hour_Rs
            days_to_break_even = hours_to_break_even/self.project.production_hours_per_day
            self.break_even_date = self.end_date + timedelta(days=days_to_break_even)
        super(AvailableTechnology, self).save(False)

    class Meta:
        verbose_name_plural = "Available Technologies"

    def __str__(self):
        return 'ID: ' + str(self.id) + ', TECHNOLOGY NAME: ' + self.technology_name

# i cant access args in presave thats for sure
class ResearchPaper(models.Model):
    technology = models.ForeignKey(AvailableTechnology, related_name='research_papers', on_delete=models.CASCADE)
    research_paper_name = models.CharField(max_length=100, blank=True, null=True)
    link = models.CharField(max_length=200, blank=True, null=True)
    research_pdf = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    remarks = models.TextField(blank=True, null=True,)

    def __str__(self):
        return 'ID: ' + str(self.id) + ', RESEARCH PAPER NAME: ' + self.research_paper_name

def setEndDate(currEvent):
    duration = currEvent.days_to_complete
    my_days = int(duration)
    day_fraction = duration % 1
    my_hours = int(24 * day_fraction)
    currEvent.event_end_date = currEvent.event_start_date + timedelta(days=my_days, hours = my_hours)

def update_event_links(currEvent):
    prevy_events = list(currEvent.previous_related_events.all())
    if not prevy_events:
        currEvent.event_start_date = currEvent.technology.start_date
        currEvent.latest_previous_dependent_event = None
    else:
        currEvent.latest_previous_dependent_event = str(prevy_events[0])
        currEvent.event_start_date = prevy_events[0].event_end_date
    setEndDate(currEvent)

# this will include all financial and non financial events, such as labour installation costs, and
# eqipment installation costs
class EventSchedule(models.Model):
    # the end results of each of these models should end in the available technology
    # it just checks with its previous event, so it is going to be simpler
    # you can make a recursive function for this one with a base case
    technology = models.ForeignKey(AvailableTechnology, related_name='time_line', on_delete=models.CASCADE)
    event_name = models.CharField(max_length=100)
    # use mod calculation for finding hours
    days_to_complete = models.DecimalField(default=0, max_digits=7,decimal_places=2)
    event_start_date = models.DateTimeField(blank=True, null=True)
    event_end_date = models.DateTimeField(blank=True, null=True)
    event_cost_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    # you'll have to use a for loop in this case
    previous_related_events = models.ManyToManyField('EventSchedule', related_name='next_related_events', blank=True)
    latest_previous_dependent_event = models.CharField(max_length=100, blank=True, null=True)
    is_completed = models.BooleanField(default= False)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    remarks = models.TextField(blank=True, null=True,)

    def save(self, *args, **kwargs):
        if self.id == None:
            myTechnology = self.technology
            self.event_start_date = myTechnology.start_date
            self.latest_previous_dependent_event = None
            myTechnology.total_start_up_cost_Rs = myTechnology.total_start_up_cost_Rs + self.event_cost_Rs
            myTechnology.save()
            setEndDate(self)
        super(EventSchedule, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
        # if related field, then also get all its related fields using filter or related name and delete those aswell
            if hasattr(self, 'next_related_events') and list(self.next_related_events.all()):
                next_events = self.next_related_events.all()
                for next_event in next_events:
                    nextin_prevy_events = next_event.previous_related_events.all()
                    if nextin_prevy_events[0].id == self.id:
                        next_event.event_start_date = nextin_prevy_events[1].event_end_date
                        next_event.latest_previous_dependent_event = str(nextin_prevy_events[1])
                        setEndDate(next_event)
                        next_event.save()
                        # yeah obviously, its not calling it self as in the delete function
                        # so no recusrsion as such
            myTechnology = self.technology
            myTechnology.total_start_up_cost_Rs = myTechnology.total_start_up_cost_Rs - self.event_cost_Rs
            myTechnology.save()
        super(EventSchedule, self).delete()

    class Meta:
        ordering = ['-event_end_date']

    def __str__(self):
        return 'ID: ' + str(self.id) + ', EVENT NAME: ' + self.event_name

@receiver(pre_save, sender=EventSchedule)
def preSaveEvent(sender, instance, **kwargs):
    try:
        original_event = sender.objects.get(pk=instance.pk)
        changed_event = instance
        current_tech = original_event.technology
        duration = changed_event.days_to_complete
        my_days = int(duration)
        day_fraction = duration % 1
        my_hours = int(24 * day_fraction)
        changed_event.event_end_date = changed_event.event_start_date + timedelta(days=my_days, hours = my_hours)
    except sender.DoesNotExist:
        pass
    else:
        # first check if date changed, then check if name changed
        # this just matches the events and is independent of any technology
        # other stuff happens when m2m change
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
        if original_event.technology != changed_event.technology or original_event.event_cost_Rs != changed_event.event_cost_Rs:
            if original_event.technology != changed_event.technology:
                old_tech = current_tech
                new_tech = changed_event.technology
                old_tech.total_start_up_cost_Rs = old_tech.total_start_up_cost_Rs - original_event.event_cost_Rs
                new_tech.total_start_up_cost_Rs = new_tech.total_start_up_cost_Rs + changed_event.event_cost_Rs
                old_tech.save()
                new_tech.save()
            elif original_event.event_cost_Rs != changed_event.event_cost_Rs:
                current_tech.total_start_up_cost_Rs = current_tech.total_start_up_cost_Rs - original_event.event_cost_Rs + changed_event.event_cost_Rs
                current_tech.save()

def events_changed(sender, instance, action, **kwargs):
    if action == "post_add" or action == "post_remove":
        
        selfEvent = instance
        update_event_links(selfEvent)
        selfEvent.save()

m2m_changed.connect(events_changed, sender=EventSchedule.previous_related_events.through)
            
class Section_Production_Rate(models.Model):
    technology = models.ForeignKey(AvailableTechnology, related_name='production_sections', on_delete=models.CASCADE, blank=True, null=True)
    product_name = models.CharField(max_length=100)
    product_measurement_unit = models.CharField(max_length=100, default='Units')
    # only handle save, if this below value is saved
    total_section_operating_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=14,decimal_places=4)
    total_section_area_required_m2 = models.DecimalField(default=0, max_digits=14,decimal_places=4)
    max_ideal_amount_of_section_product_produced_per_hour = models.DecimalField(default=0, max_digits=14,decimal_places=4)
    entire_maintenance_fraction_per_hour = models.DecimalField(default=0, max_digits=6,decimal_places=4)
    amount_of_section_product_missed_per_hour_for_maintenance = models.DecimalField(default=0, max_digits=12,decimal_places=4)
    net_amount_of_product_produced_per_hour = models.DecimalField(default=0, max_digits=14,decimal_places=4)
    selling_price_per_unit_of_product_Rs = models.DecimalField(default=0, max_digits=8,decimal_places=2)
    total_hourly_revenue_generated_for_this_section_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        self.amount_of_section_product_missed_per_hour_for_maintenance = self.max_ideal_amount_of_section_product_produced_per_hour * self.entire_maintenance_fraction_per_hour
        self.net_amount_of_product_produced_per_hour = self.max_ideal_amount_of_section_product_produced_per_hour - self.amount_of_section_product_missed_per_hour_for_maintenance
        self.total_hourly_revenue_generated_for_this_section_Rs = self.selling_price_per_unit_of_product_Rs * self.net_amount_of_product_produced_per_hour
        revy = self.total_hourly_revenue_generated_for_this_section_Rs
        if self.id == None:
            new_tech = self.technology
            new_tech.total_revenue_per_hour_Rs = new_tech.total_revenue_per_hour_Rs  + self.total_hourly_revenue_generated_for_this_section_Rs
            new_tech.save()
        # else, the id is retreived, and it is managed during presave
        super(Section_Production_Rate, self).save()
        return revy
    
    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            held_rev = 0
            if hasattr(self, 'equipments') and list(self.equipments.all()):
                held_rev = self.amount_of_section_product_missed_per_hour_for_maintenance * self.selling_price_per_unit_of_product_Rs
                equipments = list(self.equipments.all())
                for equipment in equipments:
                    equipment.equiProductionSection = None
                    equipment.save()
            if hasattr(self, 'labours') and list(self.labours.all()):
                labours = list(self.labours.all())
                for labour in labours:
                    labour.laboProductionSection = None
                    labour.save()
            myTechnology = self.technology
            myTechnology.total_revenue_per_hour_Rs = myTechnology.total_revenue_per_hour_Rs  - self.total_hourly_revenue_generated_for_this_section_Rs - held_rev
            myTechnology.save()
        super(Section_Production_Rate, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', PRODUCT: ' + self.product_name + ', PRODUCTION / HOUR: ' + str(self.net_amount_of_product_produced_per_hour) + ' ' + self.product_measurement_unit

# maintenance will only be done if equipment is used, and that is:
# the only data that comes from outside, so i donot need to add a foreign key
# to labour
@receiver(pre_save, sender=Section_Production_Rate)
def preSaveProduction(sender, instance, **kwargs):
    try:
        original_section_prdtn = sender.objects.get(pk=instance.pk)
        changed_section_prdtn = instance
        current_tech = original_section_prdtn.technology
    except sender.DoesNotExist:
        pass
    else:
        if hasattr(changed_section_prdtn, 'maintenance_changed') and changed_section_prdtn.maintenance_changed:
            pass
        else:
            manage_presave_production(original_section_prdtn, changed_section_prdtn, current_tech)




class Equipment(models.Model):
    technology = models.ForeignKey(AvailableTechnology, related_name='equipments', on_delete=models.CASCADE)
    equiProductionSection = models.ForeignKey(Section_Production_Rate, related_name='equipments', on_delete=models.DO_NOTHING, blank=True, null=True)
    equipment_name = models.CharField(max_length=100)
    number_of_equipment_units_needed = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_area_required_for_all_units_m2 = models.DecimalField(default=0, max_digits=8,decimal_places=2)
    total_running_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_parts_replacement_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_resources_cost_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_maintenance_down_time_fractions_per_hour = models.DecimalField(default=0, max_digits=8,decimal_places=4)
    area_required_per_Equipmentunit_m2 = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    # to be updated whenever a resource is added or subtracted
    parts_replacement_cost_per_equipmentUnit_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    resources_cost_per_equipmentUnit_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    maintenance_down_time_fractions_per_equipmentUnit_per_hour = models.DecimalField(default=0, max_digits=8,decimal_places=4)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    remarks = models.TextField(blank=True, null=True,)

    def save(self, *args, **kwargs):
        conflicting_techs = False
        mystring = ''
        if self.equiProductionSection != None and self.technology.id != self.equiProductionSection.technology.id:
            conflicting_techs = True
            mystring = str(self.equiProductionSection.technology)
        self.total_area_required_for_all_units_m2 = self.number_of_equipment_units_needed * self.area_required_per_Equipmentunit_m2
        self.total_parts_replacement_cost_per_hour_Rs = self.number_of_equipment_units_needed * self.parts_replacement_cost_per_equipmentUnit_per_hour_Rs
        self.total_resources_cost_per_hour_Rs = self.number_of_equipment_units_needed * self.resources_cost_per_equipmentUnit_per_hour_Rs
        self.total_maintenance_down_time_fractions_per_hour = self.number_of_equipment_units_needed * self.maintenance_down_time_fractions_per_equipmentUnit_per_hour
        self.total_running_cost_per_hour_Rs = self.total_parts_replacement_cost_per_hour_Rs + self.total_resources_cost_per_hour_Rs
        if self.id == None and not conflicting_techs:
            myequiProductionSection = self.equiProductionSection
            if myequiProductionSection != None:
                myequiProductionSection.total_section_operating_cost_per_hour_Rs = myequiProductionSection.total_section_operating_cost_per_hour_Rs + self.total_running_cost_per_hour_Rs
                myequiProductionSection.total_section_area_required_m2 = myequiProductionSection.total_section_area_required_m2 + self.total_area_required_for_all_units_m2
                myequiProductionSection.entire_maintenance_fraction_per_hour = myequiProductionSection.entire_maintenance_fraction_per_hour + self.total_maintenance_down_time_fractions_per_hour
                myequiProductionSection.save() 
        # else, the id is retreived, and it is managed during presave
        if not conflicting_techs:
            super(Equipment, self).save()
        return mystring

    def clean(self):
        if self.save() != '':
            myString = "The assigned technology and the production_section's assigned technology do not match."
            raise ValidationError(format_html('<span style="color: #cc0033; font-weight: bold; font-size: large;">{0}</span>', myString))

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myequiProductionSection = self.equiProductionSection
            if myequiProductionSection != None:
                myequiProductionSection.total_section_operating_cost_per_hour_Rs = myequiProductionSection.total_section_operating_cost_per_hour_Rs - self.total_running_cost_per_hour_Rs
                myequiProductionSection.total_section_area_required_m2 = myequiProductionSection.total_section_area_required_m2 - self.total_area_required_for_all_units_m2
                myequiProductionSection.entire_maintenance_fraction_per_hour = myequiProductionSection.entire_maintenance_fraction_per_hour - self.total_maintenance_down_time_fractions_per_hour
                myequiProductionSection.save()
        super(Equipment, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', EQUIPMENT NAME: ' + self.equipment_name

@receiver(pre_save, sender=Equipment)
def preSaveEquipment(sender, instance, **kwargs):
    try:
        original_equipment = sender.objects.get(pk=instance.pk)
        changed_equipment = instance
        current_tech = original_equipment.technology
        current_secProd = original_equipment.equiProductionSection
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        if changed_equipment.equiProductionSection != None and changed_equipment.technology.id != changed_equipment.equiProductionSection.technology.id:
            pass
        else:
            manage_presave_equipment(original_equipment, changed_equipment, current_secProd)
            
# the reason why im not adding a calculation for it, is because
# the way i calculate it may change every time
# i am manking assumtions
class Equipment_Maintenance_Cost(models.Model):
    maintenance_name = models.CharField(max_length=100)
    equipment = models.ForeignKey(Equipment, related_name='maintenance_costs', on_delete=models.CASCADE)
    maintenance_downTime_fraction_per_unit_per_hour = models.DecimalField(default=0, max_digits=4,decimal_places=4)
    part_replacement_cost_per_unit_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.id == None:
            eqpmnt = self.equipment
            eqpmnt.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = eqpmnt.parts_replacement_cost_per_equipmentUnit_per_hour_Rs + self.part_replacement_cost_per_unit_per_hour_Rs
            eqpmnt.maintenance_down_time_fractions_per_equipmentUnit_per_hour = eqpmnt.maintenance_down_time_fractions_per_equipmentUnit_per_hour + self.maintenance_downTime_fraction_per_unit_per_hour
            eqpmnt.save()
        # else, the id is retreived, and it is managed during presave
        super(Equipment_Maintenance_Cost, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myEquipment = self.equipment
            myEquipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs = myEquipment.parts_replacement_cost_per_equipmentUnit_per_hour_Rs  - self.part_replacement_cost_per_unit_per_hour_Rs
            myEquipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour = myEquipment.maintenance_down_time_fractions_per_equipmentUnit_per_hour - self.maintenance_downTime_fraction_per_unit_per_hour
            myEquipment.save()
        super(Equipment_Maintenance_Cost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', MAINTENANCE NAME: ' + self.maintenance_name
    # add a save method that will do the math to subtract the total parts produced per hour for this
    # equipment

@receiver(pre_save, sender=Equipment_Maintenance_Cost)
def preSaveEquiMaintenance(sender, instance, **kwargs):
    try:
        original_maintenance = sender.objects.get(pk=instance.pk)
        changed_maintenance = instance
        current_equipment = original_maintenance.equipment
    except sender.DoesNotExist:
        pass
    else:
        manage_presave_maintenance(original_maintenance, changed_maintenance, current_equipment)


class Equipment_Resource_Cost(models.Model):
    equipment = models.ForeignKey(Equipment, related_name='resource_costs', on_delete=models.CASCADE)
    resource_name = models.CharField(max_length=100)
    resource_unit_of_measure = models.CharField(max_length=100)
    cost_per_single_unit_resource_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    resource_quantity_needed_per_EquipmentUnit_per_hour = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    cost_per_equipmentUnit_per_hour_for_this_resource_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())
    
    def save(self, *args, **kwargs):
        self.cost_per_equipmentUnit_per_hour_for_this_resource_Rs = self.resource_quantity_needed_per_EquipmentUnit_per_hour * self.cost_per_single_unit_resource_Rs
        if self.id == None:
            eqpmnt = self.equipment
            eqpmnt.resources_cost_per_equipmentUnit_per_hour_Rs = eqpmnt.resources_cost_per_equipmentUnit_per_hour_Rs + self.cost_per_equipmentUnit_per_hour_for_this_resource_Rs
            eqpmnt.save()
        # else, the id is retreived, and it is managed during presave
        super(Equipment_Resource_Cost, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myEquipment = self.equipment
            myEquipment.resources_cost_per_equipmentUnit_per_hour_Rs = myEquipment.resources_cost_per_equipmentUnit_per_hour_Rs  - self.cost_per_equipmentUnit_per_hour_for_this_resource_Rs
            myEquipment.save()
        super(Equipment_Resource_Cost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', resource: ' + self.resource_name

@receiver(pre_save, sender=Equipment_Resource_Cost)
def preSaveEquiResource(sender, instance, **kwargs):
    try:
        original_resource = sender.objects.get(pk=instance.pk)
        changed_resource = instance
        current_equipment = original_resource.equipment
        changed_resource.cost_per_equipmentUnit_per_hour_for_this_resource_Rs = changed_resource.resource_quantity_needed_per_EquipmentUnit_per_hour * changed_resource.cost_per_single_unit_resource_Rs
    except sender.DoesNotExist:
        pass
    else:
        manage_presave_equiResource(original_resource, changed_resource, current_equipment)
# for changing tech of labour, if it is already comitted to a production, 
# and that production has an equipment, and the equipment tech and 
# labour tech are different, then pass, because you can get the old tech, from 
# its affiliated equipments tech in production
# do the same checks in save method, and add an error, unless if args provided


class Labour_PlantOperatingCost(models.Model):
    technology = models.ForeignKey(AvailableTechnology, related_name='labour_operating_costs', on_delete=models.CASCADE)
    laboProductionSection = models.ForeignKey(Section_Production_Rate, related_name='labours', on_delete=models.DO_NOTHING, blank=True, null=True)
    role = models.CharField(max_length=300)
    number_of_labourers_required_for_this_role = models.DecimalField(default=0, max_digits=8,decimal_places=2)
    salary_per_hour_per_labourer_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    safety_risk_cost_per_hour_per_labourer_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    total_labourCost_per_hour_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        conflicting_techs = False
        mystring = ''
        if self.laboProductionSection != None and self.technology.id != self.laboProductionSection.technology.id:
            conflicting_techs = True
            mystring = str(self.laboProductionSection.technology)
        self.total_labourCost_per_hour_Rs = self.number_of_labourers_required_for_this_role * (self.salary_per_hour_per_labourer_Rs + self.safety_risk_cost_per_hour_per_labourer_Rs)
        if self.id == None and not conflicting_techs:
            laboProductionSection = self.laboProductionSection
            if laboProductionSection != None:
                laboProductionSection.total_section_operating_cost_per_hour_Rs = laboProductionSection.total_section_operating_cost_per_hour_Rs + self.total_labourCost_per_hour_Rs
                laboProductionSection.save() 
        # else, the id is retreived, and it is managed during presave
        if not conflicting_techs:
            super(Labour_PlantOperatingCost, self).save()
        return mystring

    def clean(self):
        if self.save() != '':
            myString = "The assigned technology and the production_section's assigned technology do not match."
            raise ValidationError(format_html('<span style="color: #cc0033; font-weight: bold; font-size: large;">{0}</span>', myString))

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            laboProductionSection = self.laboProductionSection
            if laboProductionSection != None:
                laboProductionSection.total_section_operating_cost_per_hour_Rs = laboProductionSection.total_section_operating_cost_per_hour_Rs - self.total_labourCost_per_hour_Rs
                laboProductionSection.save()
        super(Labour_PlantOperatingCost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', ROLE: ' + self.role

@receiver(pre_save, sender=Labour_PlantOperatingCost)
def preSaveLabour(sender, instance, **kwargs):
    try:
        original_labour = sender.objects.get(pk=instance.pk)
        changed_labour = instance
        current_tech = original_labour.technology
        current_secProd = original_labour.laboProductionSection
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        if changed_labour.laboProductionSection != None and changed_labour.technology.id != changed_labour.laboProductionSection.technology.id:
            pass
        manage_presave_labour(original_labour, changed_labour, current_tech, current_secProd)

class Miscellaneous_PlantOperatingCost(models.Model):
    miscellaneous_operation_name = models.CharField(max_length=100)
    technology = models.ForeignKey(AvailableTechnology, related_name='miscellaneous_operating_costs', on_delete=models.CASCADE)
    per_hour_cost_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.id == None:
            myTechnology = self.technology
            myTechnology.total_misc_ops_costs_per_hour_Rs = myTechnology.total_misc_ops_costs_per_hour_Rs  + self.per_hour_cost_Rs
            myTechnology.save()
        # else, the id is retreived, and it is managed during presave
        super(Miscellaneous_PlantOperatingCost, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myTechnology = self.technology
            myTechnology.total_misc_ops_costs_per_hour_Rs = myTechnology.total_misc_ops_costs_per_hour_Rs  - self.per_hour_cost_Rs
            myTechnology.save()
        super(Miscellaneous_PlantOperatingCost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', MISCELLANEOUS OPERATION NAME: ' + self.miscellaneous_operation_name

@receiver(pre_save, sender=Miscellaneous_PlantOperatingCost)
def preSaveMsclOps(sender, instance, **kwargs):
    try:
        original_msclOps = sender.objects.get(pk=instance.pk)
        changed_msclOps = instance
        current_tech = original_msclOps.technology
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        if current_tech.id != changed_msclOps.technology.id or original_msclOps.per_hour_cost_Rs != changed_msclOps.per_hour_cost_Rs:
            if current_tech.id != changed_msclOps.technology.id:
                old_tech = current_tech
                new_tech = changed_msclOps.technology
                old_tech.total_misc_ops_costs_per_hour_Rs = old_tech.total_misc_ops_costs_per_hour_Rs - original_msclOps.per_hour_cost_Rs
                new_tech.total_misc_ops_costs_per_hour_Rs = new_tech.total_misc_ops_costs_per_hour_Rs + changed_msclOps.per_hour_cost_Rs
                old_tech.save()
                new_tech.save()
            else:
                current_tech.total_misc_ops_costs_per_hour_Rs = current_tech.total_misc_ops_costs_per_hour_Rs - original_msclOps.per_hour_cost_Rs + changed_msclOps.per_hour_cost_Rs
                current_tech.save()


class Miscellaneous_PlantInstallationCost(models.Model):
    miscellaneous_installation_name = models.CharField(max_length=100)
    technology = models.ForeignKey(AvailableTechnology, related_name='miscellaneous_installation_costs', on_delete=models.CASCADE)
    cost_Rs = models.DecimalField(default=0, max_digits=12,decimal_places=2)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.id == None:
            myTechnology = self.technology
            myTechnology.total_start_up_cost_Rs = myTechnology.total_start_up_cost_Rs  + self.cost_Rs
            myTechnology.save()
        # else, the id is retreived, and it is managed during presave
        super(Miscellaneous_PlantInstallationCost, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myTechnology = self.technology
            myTechnology.total_start_up_cost_Rs = myTechnology.total_start_up_cost_Rs  - self.cost_Rs
            myTechnology.save()
        super(Miscellaneous_PlantInstallationCost, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', MISCELLANEOUS INSTALLATION NAME: ' + self.miscellaneous_installation_name

@receiver(pre_save, sender=Miscellaneous_PlantInstallationCost)
def preSaveMsclInstls(sender, instance, **kwargs):
    try:
        original_msclInstls = sender.objects.get(pk=instance.pk)
        changed_msclInstls = instance
        current_tech = original_msclInstls.technology
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        if current_tech.id != changed_msclInstls.technology.id or original_msclInstls.cost_Rs != changed_msclInstls.cost_Rs:
            if current_tech.id != changed_msclInstls.technology.id:
                old_tech = current_tech
                new_tech = changed_msclInstls.technology
                old_tech.total_start_up_cost_Rs = old_tech.total_start_up_cost_Rs - original_msclInstls.cost_Rs
                new_tech.total_start_up_cost_Rs = new_tech.total_start_up_cost_Rs + changed_msclInstls.cost_Rs
                old_tech.save()
                new_tech.save()
            else:
                current_tech.total_start_up_cost_Rs = current_tech.total_start_up_cost_Rs - original_msclInstls.cost_Rs + changed_msclInstls.cost_Rs
                current_tech.save()

class Miscellaneous_Area_Requirement(models.Model):
    miscellaneous_area_role = models.CharField(max_length=100)
    technology = models.ForeignKey(AvailableTechnology, related_name='miscellaneous_area_requirements', on_delete=models.CASCADE)
    area_allotment_m2 = models.DecimalField(default=0, max_digits=8,decimal_places=2)
    remarks = models.TextField(blank=True, null=True,)
    reference = models.FileField(upload_to='research_papers', blank=True, null=True, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        if self.id == None:
            myTechnology = self.technology
            myTechnology.total_misc_size_reqs = myTechnology.total_misc_size_reqs  + self.area_allotment_m2
            myTechnology.save()
        # else, the id is retreived, and it is managed during presave
        super(Miscellaneous_Area_Requirement, self).save()

    def delete(self, *args, **kwargs):
        qdel_check = False
        if args and args[0]==True:
            qdel_check = True
        if not qdel_check:
            myTechnology = self.technology
            myTechnology.total_misc_size_reqs = myTechnology.total_misc_size_reqs  - self.area_allotment_m2
            myTechnology.save()
        super(Miscellaneous_Area_Requirement, self).delete()

    def __str__(self):
        return 'ID: ' + str(self.id) + ', MISCELLANEOUS AREA ROLE: ' + self.miscellaneous_area_role

@receiver(pre_save, sender=Miscellaneous_Area_Requirement)
def preSaveMsclArea(sender, instance, **kwargs):
    try:
        original_msclArea = sender.objects.get(pk=instance.pk)
        changed_msclArea = instance
        current_tech = original_msclArea.technology
    except sender.DoesNotExist:
        pass
    else:
        # first_check if any of the costs changed
        if current_tech.id != changed_msclArea.technology.id or original_msclArea.area_allotment_m2 != changed_msclArea.area_allotment_m2:
            if current_tech.id != changed_msclArea.technology.id:
                old_tech = current_tech
                new_tech = changed_msclArea.technology
                old_tech.total_misc_size_reqs = old_tech.total_misc_size_reqs - original_msclArea.area_allotment_m2
                new_tech.total_misc_size_reqs = new_tech.total_misc_size_reqs + changed_msclArea.area_allotment_m2
                old_tech.save()
                new_tech.save()
            else:
                current_tech.total_misc_size_reqs = current_tech.total_misc_size_reqs - original_msclArea.area_allotment_m2 + changed_msclArea.area_allotment_m2
                current_tech.save()
# either kgs or units
# in presave:
# if labour and not techno, follow labour
# elif techno and not labour, follow techno
# else fif techno not none, follow techno
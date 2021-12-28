from django.db import models
import json
from json import JSONEncoder

class Tank(models.Model):
    tank_number = models.IntegerField(default=0)
    process_name = models.CharField(max_length=100)
    immersion_time_mins = models.DecimalField(default=0, max_digits=4,decimal_places=2)
    tank_type_number = models.IntegerField(default=0)
    is_wait_type_tank = models.BooleanField(default=False)
    max_wait_time_mins = models.DecimalField(default=0, max_digits=4,decimal_places=2)

    def __str__(self):
        return 'TANK NUBMBER: ' + str(self.tank_number) + ', TANK NAME: ' + self.process_name
    
    class Meta:
        ordering = ['tank_number']
        verbose_name_plural = "             1. tanks"

class ElectroEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__




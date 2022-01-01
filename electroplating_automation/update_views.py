import json
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Tank

class UpdateView(APIView):

    # i return false only at the checks
    def get(self, request, *args, **kwargs):
        update_tanks = Tank.objects.all().filter(tank_number__gt=21)
        for u_tank in list(update_tanks):
            u_tank.tank_number = u_tank.tank_number - 1
            u_tank.tank_type_number = u_tank.tank_type_number
            u_tank.save()
        return Response({'message': 'success', 'rackJSON': 'rackJSON', 'check_data': 'self.check_data', 'crane_data': 'craneJSON'})
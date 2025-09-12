from django.contrib import admin
from .models import Driver, Truck, Trip, LogSheet

admin.site.register([Driver, Truck, Trip, LogSheet])

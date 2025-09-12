import uuid
from django.db import models


class Driver(models.Model):
    """
    Represents a truck driver.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    license_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Driver’s license or CDL number"
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.license_number})"


class Truck(models.Model):
    """
    Represents a physical truck.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plate_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Truck license plate number"
    )
    vin = models.CharField(
        max_length=100,
        unique=True,
        help_text="Vehicle Identification Number"
    )
    make_model = models.CharField(max_length=255, help_text="e.g. Volvo VNL 760")
    year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.plate_number} - {self.make_model}"


class Trip(models.Model):
    """
    Stores a trip request and the calculated route information.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trips"
    )
    truck = models.ForeignKey(
        Truck,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trips"
    )
    current_location = models.JSONField(
        null=True,
        blank=True,
        help_text="Current location (could be coordinates or city/state)."
    )
    pickup_location = models.JSONField(
        help_text="Pickup location coordinates or address."
    )
    dropoff_location = models.JSONField(
        help_text="Dropoff location coordinates or address."
    )
    current_cycle_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Hours already used in the 70hr/8day cycle."
    )
    route_distance_miles = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    route_duration_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    route_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Full response from the map API (waypoints, geometry, etc.)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trip {self.id} from {self.pickup_location} to {self.dropoff_location}"


class LogSheet(models.Model):
    """
    Represents a daily Hours-of-Service log sheet for a trip.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="logs"
    )
    date = models.DateField()
    grid_data = models.JSONField(
        help_text="Array of duty status segments for the 24-hour log."
    )
    total_miles = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    total_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"LogSheet {self.date} for Trip {self.trip_id}"

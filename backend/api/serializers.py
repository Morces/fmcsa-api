from rest_framework import serializers
from .models import Driver, Truck, Trip, LogSheet

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = "__all__"

class TruckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Truck
        fields = "__all__"

class LogSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogSheet
        fields = "__all__"

class TripSerializer(serializers.ModelSerializer):
    # Nested read-only logs, driver & truck details
    logs = LogSheetSerializer(many=True, read_only=True)
    driver = DriverSerializer(read_only=True)
    truck = TruckSerializer(read_only=True)

    # allow setting driver/truck by ID when creating
    driver_id = serializers.UUIDField(write_only=True, required=False)
    truck_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Trip
        fields = "__all__"

    def create(self, validated_data):
        driver_id = validated_data.pop("driver_id", None)
        truck_id = validated_data.pop("truck_id", None)

        trip = Trip.objects.create(**validated_data)
        if driver_id:
            trip.driver_id = driver_id
        if truck_id:
            trip.truck_id = truck_id
        trip.save()
        return trip

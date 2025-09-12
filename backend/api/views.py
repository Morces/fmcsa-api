from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Driver, Truck, Trip, LogSheet
from .serializers import DriverSerializer, TruckSerializer, TripSerializer, LogSheetSerializer
import os
import math
from datetime import date, timedelta
import requests
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from rest_framework.decorators import action
from django.db.models import Sum


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all().order_by("-created_at")
    serializer_class = DriverSerializer
    # permission_classes = [IsAuthenticated]


    @action(detail=True, methods=["get"])
    def analytics(self, request, pk=None):
        driver = self.get_object()
        summary = driver.trips.aggregate(
            total_miles=Sum("route_distance_miles"),
            total_hours=Sum("route_duration_hours")
        )
        return Response({
            "driver": driver.name,
            "total_trips": driver.trips.count(),
            "total_miles": round(summary["total_miles"] or 0, 2),
            "total_hours": round(summary["total_hours"] or 0, 2),
        })

class TruckViewSet(viewsets.ModelViewSet):
    queryset = Truck.objects.all().order_by("-created_at")
    serializer_class = TruckSerializer
    # permission_classes = [IsAuthenticated] 

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all().order_by("-created_at")
    serializer_class = TripSerializer
    # permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        data = request.data
        pickup = data.get("pickup_location")
        dropoff = data.get("dropoff_location")
        start_date_str = data.get("start_date")

        if not pickup or not dropoff:
            return Response(
                {"error": "Pickup and dropoff locations are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine trip start date (defaults to today)
        trip_start_date = (
            date.fromisoformat(start_date_str)
            if start_date_str else
            date.today()
        )

        # === 1️⃣ Mapbox Directions API ===
        coords = f"{pickup['lng']},{pickup['lat']};{dropoff['lng']},{dropoff['lat']}"
        url = (
            f"https://api.mapbox.com/directions/v5/mapbox/driving/{coords}"
            f"?geometries=geojson&overview=full&access_token={settings.MAPBOX_API_KEY}"
        )
        r = requests.get(url)
        if r.status_code != 200:
            return Response(
                {"error": "Map API request failed."},
                status=status.HTTP_502_BAD_GATEWAY
            )

        route = r.json()["routes"][0]
        distance_miles = route["distance"] / 1609.34
        base_drive_hours = route["duration"] / 3600

        # === 2️⃣ Mandatory extra times ===
        pickup_time = 1    # hrs
        dropoff_time = 1   # hrs
        fuel_stops = math.floor(distance_miles / 1000)
        fueling_time_each = 1  # hrs per fuel stop
        total_fueling_time = fuel_stops * fueling_time_each

        total_drive_time = base_drive_hours
        total_on_duty_extra = pickup_time + dropoff_time + total_fueling_time
        total_hours = total_drive_time + total_on_duty_extra

        # === 3️⃣ Cycle Compliance Check (70 hrs / 8 days) ===
        current_cycle = float(data.get("current_cycle_hours", 0))
        if current_cycle + total_hours > 70:
            return Response(
                {
                    "error": "Trip exceeds the 70-hour/8-day cycle limit.",
                    "current_cycle_hours": current_cycle,
                    "planned_trip_hours": round(total_hours, 2),
                    "allowed_hours_left": round(70 - current_cycle, 2)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # === 4️⃣ Prepare daily log sheets ===
        remaining_drive = total_drive_time
        remaining_extra = total_on_duty_extra
        fuels_remaining = fuel_stops
        logs = []
        day_index = 0

        while remaining_drive > 0 or remaining_extra > 0:
            log_date = trip_start_date + timedelta(days=day_index)
            drive_today = min(11, remaining_drive)
            on_duty_today = 0
            segments = []

            # Pickup on first day
            if day_index == 0 and pickup_time > 0:
                segments.append({
                    "status": "ON_DUTY_NOT_DRIVING",
                    "hours": pickup_time
                })
                on_duty_today += pickup_time
                remaining_extra -= pickup_time

            # Fuel stop (distribute roughly 1/day if needed)
            if fuels_remaining > 0 and remaining_drive > 0:
                segments.append({
                    "status": "ON_DUTY_NOT_DRIVING",
                    "hours": fueling_time_each
                })
                on_duty_today += fueling_time_each
                fuels_remaining -= 1
                remaining_extra -= fueling_time_each

            # Driving segment
            if drive_today > 0:
                segments.append({"status": "DRIVING", "hours": drive_today})
                remaining_drive -= drive_today

            # Drop-off on last day
            if remaining_drive <= 0 and dropoff_time > 0:
                segments.append({
                    "status": "ON_DUTY_NOT_DRIVING",
                    "hours": dropoff_time
                })
                on_duty_today += dropoff_time
                remaining_extra -= dropoff_time

            total_duty = on_duty_today + drive_today
            off_duty = max(0, 24 - total_duty)
            segments.append({"status": "OFF_DUTY", "hours": off_duty})

            logs.append({
                "date": log_date.isoformat(),
                "duty_segments": segments,
                "total_hours": total_duty
            })
            day_index += 1

        # === 5️⃣ Save Trip ===
        trip = Trip.objects.create(
            driver_id=data.get("driver_id"),
            truck_id=data.get("truck_id"),
            pickup_location=pickup,
            dropoff_location=dropoff,
            current_cycle_hours=current_cycle,
            route_distance_miles=round(distance_miles, 2),
            route_duration_hours=round(total_hours, 2),
            route_data={
                **route,
                "fuel_stops": fuel_stops,
                "fueling_time_each": fueling_time_each,
                "pickup_time": pickup_time,
                "dropoff_time": dropoff_time
            },
        )

        # === 6️⃣ Create LogSheets ===
        for log in logs:
            LogSheet.objects.create(
                trip=trip,
                date=log["date"],
                grid_data=log,
                total_hours=log["total_hours"]
            )

        serializer = TripSerializer(trip)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class LogSheetViewSet(viewsets.ReadOnlyModelViewSet):
    # usually logs are read-only; generated by system logic
    queryset = LogSheet.objects.all().order_by("date")
    serializer_class = LogSheetSerializer
    permission_classes = [IsAuthenticated] 

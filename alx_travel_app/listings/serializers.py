# listings/serializers.py

from django.utils import timezone
from rest_framework import serializers

from .models import Booking, Listing, Review


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for the Review model.
    """

    class Meta:
        model = Review
        fields = ["id", "user", "listing", "rating", "comment", "created_at"]
        read_only_fields = (
            "id",
            "user",
            "created_at",
        )
        extra_kwargs = {"user": {"read_only": True}, "listing": {"read_only": True}}

    def validate_rating(self, value):
        """Check that the rating is between 1 and 5."""
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def create(self, validated_data):
        """Create a new review with the authenticated user."""
        # Set the user from the request context
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["user"] = request.user
        return super().create(validated_data)


class ListingSerializer(serializers.ModelSerializer):
    """
    Serializer for the Listing model.
    """

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "description",
            "price_per_night",
            "max_guests",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_price_per_night(self, value):
        """Ensure price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_max_guests(self, value):
        """Ensure max_guests is positive."""
        if value <= 0:
            raise serializers.ValidationError(
                "Maximum guests must be greater than zero."
            )
        return value


class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for the Booking model.
    """

    class Meta:
        model = Booking
        fields = [
            "id",
            "listing",
            "user",
            "start_date",
            "end_date",
            "status",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")
        extra_kwargs = {"user": {"read_only": True}, "status": {"required": False}}

    def validate(self, data):
        """
        Validate booking dates and availability.
        """
        # Check if start_date is before end_date
        if data["start_date"] >= data["end_date"]:
            raise serializers.ValidationError("End date must be after start date.")

        # Check if booking is for at least 1 night
        if (data["end_date"] - data["start_date"]).days < 1:
            raise serializers.ValidationError("Booking must be for at least one night.")

        # Check if booking is not in the past
        if data["start_date"] < timezone.now().date():
            raise serializers.ValidationError("Cannot book for past dates.")

        # Check if listing exists and is available
        listing = data.get("listing")
        if listing:
            # Check for overlapping bookings
            overlapping_bookings = Booking.objects.filter(
                listing=listing,
                start_date__lt=data["end_date"],
                end_date__gt=data["start_date"],
                status__in=["pending", "confirmed"],
            )

            # Exclude current instance when updating
            if self.instance:
                overlapping_bookings = overlapping_bookings.exclude(pk=self.instance.pk)

            if overlapping_bookings.exists():
                raise serializers.ValidationError(
                    "This listing is already booked for the selected dates."
                )

        return data

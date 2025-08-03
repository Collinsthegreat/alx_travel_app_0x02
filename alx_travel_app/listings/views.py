# listings/views.py

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Booking, Listing, Review
from .serializers import BookingSerializer, ListingSerializer, ReviewSerializer


class ListingViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows listings to be viewed or edited.
    """

    queryset = Listing.objects.all().order_by("-created_at")
    serializer_class = ListingSerializer
    lookup_field = "id"

    def get_queryset(self):
        """
        Optionally filter listings by various parameters.
        """
        queryset = super().get_queryset()
        # Example of filtering by query parameters
        max_price = self.request.query_params.get("max_price")
        if max_price is not None:
            queryset = queryset.filter(price_per_night__lte=max_price)
        return queryset

    @action(detail=True, methods=["get"])
    def reviews(self, request, id=None):
        """
        Retrieve all reviews for a specific listing.
        """
        listing = self.get_object()
        reviews = Review.objects.filter(listing=listing)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows bookings to be viewed or edited.
    """

    serializer_class = BookingSerializer
    lookup_field = "id"

    def get_queryset(self):
        """
        Optionally filter bookings by listing_id or user.
        """
        queryset = Booking.objects.all().order_by("-created_at")
        listing_id = self.request.GET.get("listing_id")
        user_id = self.request.GET.get("user_id")

        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def perform_create(self, serializer):
        """
        Automatically set the user to the current user when creating a booking.
        """
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to prevent deletion of confirmed bookings.
        """
        instance = self.get_object()
        if instance.status == "confirmed":
            return Response(
                {"detail": "Cannot delete a confirmed booking."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Handle PATCH requests for updating a booking.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Save the updated instance
        self.perform_update(serializer)

        # Refresh the instance from the database to get the updated status
        instance.refresh_from_db()

        return Response(serializer.data)

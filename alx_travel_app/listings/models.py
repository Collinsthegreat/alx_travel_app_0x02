# listings/models.py

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Listing(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    max_guests = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="bookings"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.listing.title}"


class Review(models.Model):
    RATING_CHOICES = [
        (1, "1 Star"),
        (2, "2 Stars"),
        (3, "3 Stars"),
        (4, "4 Stars"),
        (5, "5 Stars"),
    ]

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} stars for {self.listing.title}"

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending"
        COMPLETED = "Completed"
        FAILED = "Failed"

    booking_reference = models.CharField(max_length=64, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="ETB")  # Why: keep flexible
    tx_ref = models.CharField(max_length=64, unique=True)
    chapa_txn_id = models.CharField(max_length=64, blank=True)
    checkout_url = models.URLField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    raw_init_response = models.JSONField(default=dict, blank=True)
    raw_verify_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.booking_reference} | {self.tx_ref} | {self.status}"
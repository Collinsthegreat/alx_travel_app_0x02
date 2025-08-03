# listings/admin.py

from django.contrib import admin

from .models import Booking, Listing, Review


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "price_per_night", "max_guests", "created_at")
    search_fields = ("title", "description")
    list_filter = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("listing", "user", "start_date", "end_date", "status", "created_at")
    list_filter = ("status", "start_date", "end_date")
    search_fields = ("listing__title", "user__email")
    date_hierarchy = "start_date"
    ordering = ("-created_at",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("listing", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("listing__title", "comment")
    ordering = ("-created_at",)

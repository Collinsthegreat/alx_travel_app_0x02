# listings/urls.py

from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from . import views

# Create a router for API endpoints
router = DefaultRouter()
router.register(r"listings", views.ListingViewSet, basename="listing")
router.register(r"bookings", views.BookingViewSet, basename="booking")

# Schema view for app-specific documentation
app_schema_view = get_schema_view(
    openapi.Info(
        title="Listings API",
        default_version="v1",
        description="""
        API endpoints for managing travel listings and bookings.
        
        ## Available Endpoints
        - `/listings/` - Manage travel listings (GET, POST)
        - `/listings/{id}/` - Manage a specific listing (GET, PUT, PATCH, DELETE)
        - `/listings/{id}/reviews/` - Get reviews for a listing (GET)
        - `/bookings/` - Manage bookings (GET, POST)
        - `/bookings/{id}/` - Manage a specific booking (GET, PUT, PATCH, DELETE)
        
        ## Filtering
        - Listings can be filtered by `max_price`
        - Bookings can be filtered by `listing_id` and `user_id`
        """,
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[
        path("", include(router.urls)),
    ],
)

app_name = "listings"

urlpatterns = [
    # API endpoints
    path("", include(router.urls)),
    # Documentation
    path(
        "docs/",
        app_schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        app_schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]

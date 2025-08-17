# listings/views.py



from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Booking, Listing, Review
from .serializers import BookingSerializer, ListingSerializer, ReviewSerializer


class ListingViewSet(viewsets.ModelViewSet):

    #API endpoint that allows listings to be viewed or edited.


    queryset = Listing.objects.all().order_by("-created_at")
    serializer_class = ListingSerializer
    lookup_field = "id"

    def get_queryset(self):

        #Optionally filter listings by various parameters.

        queryset = super().get_queryset()
        # Example of filtering by query parameters
        max_price = self.request.query_params.get("max_price")
        if max_price is not None:
            queryset = queryset.filter(price_per_night__lte=max_price)
        return queryset

    @action(detail=True, methods=["get"])
    def reviews(self, request, id=None):

       # Retrieve all reviews for a specific listing.

        listing = self.get_object()
        reviews = Review.objects.filter(listing=listing)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):

   # API endpoint that allows bookings to be viewed or edited.

    serializer_class = BookingSerializer
    lookup_field = "id"

    def get_queryset(self):

       # Optionally filter bookings by listing_id or user.

        queryset = Booking.objects.all().order_by("-created_at")
        listing_id = self.request.GET.get("listing_id")
        user_id = self.request.GET.get("user_id")

        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def perform_create(self, serializer):

       # Automatically set the user to the current user when creating a booking.

        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):

      #  Override destroy to prevent deletion of confirmed bookings.

        instance = self.get_object()
        if instance.status == "confirmed":
            return Response(
                {"detail": "Cannot delete a confirmed booking."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):

      #  Handle PATCH requests for updating a booking.

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Save the updated instance
        self.perform_update(serializer)

        # Refresh the instance from the database to get the updated status
        instance.refresh_from_db()

        return Response(serializer.data)

import uuid
import json
import logging
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from .models import Payment
from .tasks import send_payment_confirmation_email

log = logging.getLogger(__name__)
def _headers():
    return {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json",
    }

def _return_url(tx_ref: str) -> str:
    # Why: keep consistent redirect target even if base changes
    base = settings.CHAPA_RETURN_URL.rstrip("/")
    return f"{base}?tx_ref={tx_ref}"

@require_POST
@csrf_exempt  # For public APIs use proper CSRF/Origin protections in prod
def initiate_payment(request):
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body.decode("utf-8"))
        else:
            data = request.POST.dict()
    except Exception:
        return HttpResponseBadRequest("Invalid payload")

    required = ("booking_reference", "amount", "email", "first_name", "last_name")
    missing = [k for k in required if k not in data or str(data[k]).strip() == ""]
    if missing:
        return HttpResponseBadRequest(f"Missing fields: {missing}")

    booking_reference = str(data["booking_reference"]).strip()
    amount = str(data["amount"]).strip()
    currency = str(data.get("currency", "ETB")).strip()
    email = str(data["email"]).strip()
    first_name = str(data["first_name"]).strip()
    last_name = str(data["last_name"]).strip()

    tx_ref = f"TRX_{uuid.uuid4().hex[:24]}"

    payload = {
        "amount": amount,
        "currency": currency,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "tx_ref": tx_ref,
        "callback_url": _return_url(tx_ref),
        "return_url": _return_url(tx_ref),
        "customization": {"title": "ALX Travel Booking", "description": f"Booking {booking_reference}"},
    }

    try:
        resp = requests.post(
            f"{settings.CHAPA_BASE_URL}/v1/transaction/initialize",
            json=payload,
            headers=_headers(),
            timeout=20,
        )
        resp.raise_for_status()
        j = resp.json()
    except requests.RequestException as exc:
        log.exception("Chapa init error")
        return JsonResponse({"detail": "Failed to contact payment gateway", "error": str(exc)}, status=502)

    status = (j or {}).get("status")
    data_out = (j or {}).get("data") or {}
    checkout_url = data_out.get("checkout_url", "")
    chapa_txn_id = data_out.get("reference") or data_out.get("id") or ""

    if status != "success" or not checkout_url:
        return JsonResponse({"detail": "Payment initialization failed", "response": j}, status=400)

    payment = Payment.objects.create(
        booking_reference=booking_reference,
        amount=amount,
        currency=currency,
        tx_ref=tx_ref,
        chapa_txn_id=chapa_txn_id,
        checkout_url=checkout_url,
        status=Payment.Status.PENDING,
        raw_init_response=j,
    )

    log.info("Payment initiated tx_ref=%s booking=%s amount=%s %s", tx_ref, booking_reference, amount, currency)
    return JsonResponse({"tx_ref": tx_ref, "checkout_url": checkout_url, "status": payment.status}, status=201)

@require_GET
def verify_payment(request, tx_ref: str):
    payment = get_object_or_404(Payment, tx_ref=tx_ref)
    try:
        resp = requests.get(
            f"{settings.CHAPA_BASE_URL}/v1/transaction/verify/{tx_ref}",
            headers=_headers(),
            timeout=20,
        )
        resp.raise_for_status()
        j = resp.json()
    except requests.RequestException as exc:
        log.exception("Chapa verify error tx_ref=%s", tx_ref)
        return JsonResponse({"detail": "Verification failed", "error": str(exc)}, status=502)

    status = (j or {}).get("status")
    data_out = (j or {}).get("data") or {}
    paid_ok = (status == "success") and (str(data_out.get("status", "")).lower() == "success")

    payment.raw_verify_response = j
    payment.status = Payment.Status.COMPLETED if paid_ok else Payment.Status.FAILED
    payment.chapa_txn_id = payment.chapa_txn_id or data_out.get("reference") or data_out.get("id") or ""
    payment.save(update_fields=["raw_verify_response", "status", "chapa_txn_id", "updated_at"])

    if paid_ok:
        # Try reading email from init payload; fallback to query param for safety in dev
        to_email = (payment.raw_init_response.get("data") or {}).get("email") or request.GET.get("email") or ""
        if to_email:
            send_payment_confirmation_email.delay(
                to_email=to_email,
                booking_reference=payment.booking_reference,
                amount=str(payment.amount),
                currency=payment.currency,
                tx_ref=payment.tx_ref,
            )
        log.info("Payment verified COMPLETED tx_ref=%s", tx_ref)
    else:
        log.warning("Payment verify FAILED tx_ref=%s", tx_ref)

    return JsonResponse({"tx_ref": tx_ref, "status": payment.status, "gateway": j}, status=200)

@require_GET
def chapa_callback(request):
    tx_ref = request.GET.get("tx_ref")
    if not tx_ref:
        return HttpResponseBadRequest("Missing tx_ref")
    verify_url = request.build_absolute_uri(f"/api/payments/verify/{tx_ref}/")
    return HttpResponseRedirect(verify_url)

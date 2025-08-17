from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_payment_confirmation_email(self, *, to_email: str, booking_reference: str, amount: str, currency: str, tx_ref: str) -> None:
    # Why: async + retry on transient email errors
    subject = f"Payment Confirmed: {booking_reference}"
    body = (
        f"Hi,\n\n"
        f"Your payment for booking '{booking_reference}' has been confirmed.\n"
        f"Amount: {amount} {currency}\n"
        f"Transaction Ref: {tx_ref}\n\n"
        f"Thank you."
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)
from .utils import safe_script
from apps.users.models import CustomUser
from apps.invoices.models import Payment, Invoice
from django.utils import timezone
from datetime import timedelta

@safe_script
def run():
    now = timezone.now()
    for i in range(14):
        d = now - timedelta(days=i)
        print(
        Payment.factory(invoice=Invoice.factory(user=CustomUser.objects.get(username='audrey')),
                        created_at=d, transaction_date_time=d)
        )



from django.contrib import admin
from apps.invoices.models import Invoice, Payment, InvoiceItem

admin.site.register(Invoice)
admin.site.register(Payment)
admin.site.register(InvoiceItem)
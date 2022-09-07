from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db.models import Sum
from uuid import uuid4
from apps.users.models import CustomUser
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail, mail_admins
from apps import model_base
from django.core.validators import MaxValueValidator
from djchoices import ChoiceItem, DjangoChoices
from django.core.mail import send_mail, mail_admins

def makeKey():
    return str(uuid4()).replace('-', '')[:16].upper()

class Invoice(model_base.TitledBase):

    class InvoiceStatus(DjangoChoices):
        new = ChoiceItem('new', 'New')
        published = ChoiceItem('published', 'Published')
        agreed = ChoiceItem('agreed', 'Agreed')
        partial_payment = ChoiceItem('partial_payment', 'Partial Payment')
        paid_in_full = ChoiceItem('paid_in_full', 'Paid in Full')
    
    class DeliveryChoices(DjangoChoices):
        email = ChoiceItem('email', 'Email')
        link = ChoiceItem('link', 'Link')
        

    objects = models.Manager()
    user = models.ForeignKey(
        CustomUser, on_delete=models.DO_NOTHING, related_name='invoices')
    status = models.CharField(
        max_length=32, default='new', choices=InvoiceStatus.choices)
    delivery = models.CharField(
        max_length=32, default='email', choices=DeliveryChoices.choices)
    recipient_email = models.CharField(max_length=64, null=True, blank=True)
    pay_to = models.ForeignKey(
        'users.WhitelistAddress', on_delete=models.DO_NOTHING, related_name='pay_to')
    key = models.CharField(max_length=32, default=makeKey)
    archived_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=512, null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    sent_date = models.DateTimeField(null=True, blank=True)
    agreed_at = models.DateTimeField(null=True, blank=True)
    invoice_amount = models.DecimalField(max_digits=50, decimal_places=0)
    currency = models.ForeignKey('invoices.PaymentCurrency', on_delete=models.DO_NOTHING)
    paid_amount = models.DecimalField(max_digits=50, decimal_places=0, default=0)
    min_payment_threshold = models.PositiveIntegerField(
        blank=True, default=100, validators=[MaxValueValidator(100), ])
    
    @classmethod
    def factory(cls, *args, **kwargs):
        from apps.invoices.factory import InvoiceFactory
        return InvoiceFactory(*args, **kwargs)

    def save(self, *args, **kwargs):
        
        mail_admins(
            'New Invoice Created',
            'A new invoice was created on PayWei'
        )
        if(self.delivery == 'email' and self.status == 'published' and self.sent_date == None):
            send_mail(
                'Someone has sent you a bill on PayWei',
                'paywei.co/pay/' + self.id,
                'noreply@paywei.co',
                [self.recipient_email]
            )
            self.sent_date = timezone.now()
        self._update_paid_amount(save=False)
        super(Invoice, self).save(*args, **kwargs)

    def _update_paid_amount(self, save=True):
        self.paid_amount = sum([p.converted_amount for p in self.payments.filter(status='confirmed')])
        if self.paid_amount > 0 and self.status == 'agreed':
            self.status = 'partial_payment'
        if self.paid_amount == self.invoice_amount and self.status in ['agreed', 'partial_payment']:
            self.status = 'paid_in_full'
        if save:
            self.save()

    def get_amount_due(self):
        return self.invoice_amount - self.paid_amount

    class Meta:
        ordering = ('-created_at',)

class InvoiceItem(model_base.TitledBase):
    objects = models.Manager()
    order = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=50, decimal_places=0)
    invoice = models.ForeignKey(Invoice, related_name='line_items', on_delete=models.CASCADE)

    class Meta:
        ordering = ['order']

class InvoiceFactory:
    pass


class Payment(model_base.RandomPKBase):

    class PaymentStatus(DjangoChoices):
        new = ChoiceItem('new', 'New')
        confirmed = ChoiceItem('confirmed', 'Confirmed')

    objects = models.Manager()
    status = models.CharField(
        max_length=32, default='new', choices=PaymentStatus.choices)
    invoice = models.ForeignKey(Invoice, related_name='payments', on_delete=models.DO_NOTHING)
    amount = models.DecimalField(max_digits=50, decimal_places=0)
    currency = models.ForeignKey('invoices.PaymentCurrency', on_delete=models.DO_NOTHING)
    conversion_rate = models.DecimalField(max_digits=20, decimal_places=10)
    converted_amount = models.DecimalField(max_digits=50, decimal_places=0)
    block_hash = models.TextField()
    block_number = models.PositiveIntegerField()
    created_at = models.DateTimeField()
    gas = models.PositiveIntegerField()
    gas_price = models.DecimalField(max_digits=50, decimal_places=0)
    tx_hash = models.CharField(max_length=128, db_index=True)
    tx_input = models.TextField()
    parameters_json = models.TextField(null=True, blank=True)
    nonce = models.PositiveIntegerField()
    from_address = models.CharField(max_length=64)
    to_address = models.CharField(max_length=64)
    transaction_date_time = models.DateTimeField()

    @classmethod
    def factory(cls, *args, **kwargs):
        from apps.invoices.factory import PaymentFactory
        return PaymentFactory(*args, **kwargs)

    @property
    def parameters(self):
        try:
            return json.loads(self.parameters_json)
        except:
            return {}

    class Meta:
        ordering = ('-created_at',)

class PaymentCurrency(model_base.TitledBase):
    objects = models.Manager()
    contract_address = models.CharField(max_length=50)
    symbol = models.CharField(max_length=64)
    decimal_places = models.PositiveIntegerField()

    @classmethod
    def ETH(cls):
        return DEFAULT_CURRENCIES['ETH']()

    # SOMEDAY - eth_usd_price is only needed because we cheat on DAI/USD conversion
    # We'll make a simpler convert_rate(self, currency) that omits this parameter in the future
    def convert_rate(self, other_currency, eth_usd_price):
        if self == other_currency: return 1

        elif self.symbol == 'ETH' and other_currency.symbol == 'DAI':
            return eth_usd_price
        elif self.symbol == 'DAI' and other_currency.symbol == 'ETH':
            return 1.0/eth_usd_price
        else:
            from django.core.mail import mail_admins
            mail_admins('Invalid Conversion Rate', '%s/%s'%(self, other_currency))
            raise Exception('Invalid Conversion Rate')

    def convert_amount(self, other_currency, amount, eth_usd_price):
        return amount * self.convert_rate(other_currency, eth_usd_price)

def _update_paid_amount(sender, instance, **kwargs):
    instance.invoice._update_paid_amount()

from django.db.models.signals import post_save
post_save.connect(_update_paid_amount, sender=Payment)



DEFAULT_CURRENCIES = dict(
    DAI=lambda: PaymentCurrency.objects.get_or_create(
        title='USD Stable',
        symbol='DAI',
        decimal_places=18,
        contract_address='0x89d24a6b4ccb1b6faa2625fe562bdd9a23260359'
    )[0],
    ETH=lambda: PaymentCurrency.objects.get_or_create(
        title='Ether',
        symbol='ETH',
        decimal_places=18,
        contract_address='0x0000000000000000000000000000000000000000'
    )[0],
)

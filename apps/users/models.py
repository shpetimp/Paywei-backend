from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db.models import Sum
from uuid import uuid4
from .. import model_base
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail, mail_admins
from djchoices import ChoiceItem, DjangoChoices


class CustomUser(AbstractUser):
    STATUS_CHOICES = [('active', 'active'), ('paused', 'paused')]
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='active')
    default_notify_url = models.CharField(max_length=2048, blank=True, null=True)
    default_address = models.ForeignKey(
        'users.WhitelistAddress',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True
    )
    default_pricing_currency = models.ForeignKey(
        'invoices.PaymentCurrency',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True
    )

    @classmethod
    def factory(cls, *args, **kwargs):
        from apps.users.factory import UserFactory
        return UserFactory(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(CustomUser, self).save(*args, **kwargs)
        mail_admins(
            'New User Registration',
            'A new user has registered with txgun'
        )
    

def makeKey():
    return str(uuid4()).replace('-', '')


class APIKey(model_base.RandomPKBase):
    objects = models.Manager()
    user = models.ForeignKey(
        CustomUser, on_delete=models.DO_NOTHING, related_name='api_keys')
    key = models.CharField(max_length=32, default=makeKey)
    archived_at = models.DateTimeField(null=True, blank=True)
    nickname = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

class WhitelistAddress(model_base.RandomPKBase):

    class AddressStatus(DjangoChoices):
        pending = ChoiceItem('pending', 'Pending')
        verified = ChoiceItem('verified', 'Verified')
        denied = ChoiceItem('denied', 'Denied')
        archived = ChoiceItem('archived', 'Archived')

    objects = models.Manager()
    nickname = models.CharField(max_length=64)
    address = models.CharField(max_length=64)
    secret = models.CharField(max_length=32, default=makeKey)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='addresses')
    status = models.CharField(
        max_length=32, default='pending', choices=AddressStatus.choices)
    
    @classmethod
    def factory(cls, *args, **kwargs):
        from apps.users.factory import WhitelistAddressFactory
        return WhitelistAddressFactory(*args, **kwargs)

    def save(self, *args, **kwargs):
        _new = bool(getattr(self, 'pk', None))
        super(WhitelistAddress, self).save(*args, **kwargs)
        if (self.status == 'pending' and _new):
            send_mail(
                    'An address is pending verification on PayWei',
                    "Click here to verify: https://paywei.co/verify_address/%s/%s"%(self.id, self.secret),
                    'noreply@paywei.co',
                    [self.user.email]
                )

    


    

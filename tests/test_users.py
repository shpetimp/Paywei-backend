from django.test import TestCase
from django.core import mail
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.test import force_authenticate
from apps.users.models import CustomUser as User, APIKey, WhitelistAddress
from apps.invoices.models import Invoice, PaymentCurrency
from datetime import datetime, timedelta
import json
import pytest
import io
from pprint import pprint


@pytest.mark.django_db
class UserTestCase(TestCase):
    @classmethod
    def setup_class(cls):
        cls.client = APIClient()
        cls.factory = APIRequestFactory()
        

    def test_make_api_key(self):
        test_user = User.objects.create_user(username="audrey", email="test@audrey.com", password="audrey")
        key = test_user.api_keys.create(nickname='testkey')
        self.assertEqual(len(key.key), 32)
        self.assertEqual(key.nickname, 'testkey')
        self.assertEqual(key.user, test_user)

    def api_key_api(self):
        from apps.users import views

        factory = APIRequestFactory()
        test_user = User.objects.create_user(username='audrey', email='test@audrey.com', password='audrey')

        request = factory.get('/keys/')
        force_authenticate(request, user=test_user)
        list_response = views.APIKeyViewSet.as_view()(request)
        self.assertEqual([], list_response.data['results'])

        request = factory.post('/keys/', {
            'user': test_user.id,
            'key': '12345678987654321',
            'nickname': 'test api'
        })
        force_authenticate(request, user=test_user)
        response = views.APIKeyViewSet.as_view()(request)

        request = factory.get('/keys/')
        force_authenticate(request, user=test_user)
        list_response= views.APIKeyViewSet.as_view()(request)
        self.assertEqual(APIKey.objects.count(), 1)

    def test_whitelist_address(self):
        from apps.invoices import views
        factory = APIRequestFactory()

        test_user = User.objects.create_user(username="audrey", email="test@audrey.com", password="audrey")
        address1 = WhitelistAddress.objects.create(
            address='0xC2C255932A77F4831566822c1f01d9F735CC152E',
            nickname='Mark',
            user=test_user
        )
        address2 = WhitelistAddress.objects.create(
            address='0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8',
            nickname='Barbara',
            user=test_user,
            status=WhitelistAddress.AddressStatus.verified
        )
        
        request = factory.post('/invoices/', {
            'user': test_user.id,
            'pay_to': address1.id,
            'invoice_amount': 1000000000,
            'currency': PaymentCurrency.ETH().id,
        })

        force_authenticate(request, user=test_user)
        response= views.InvoiceViewSet.as_view({'post': 'create'})(request)
        self.assertEqual(Invoice.objects.count(), 0)

        request = factory.post('/invoices/', {
            'user': test_user.id,
            'pay_to': address2.id,
            'invoice_amount': 2000000000,
            'currency': PaymentCurrency.ETH().id,
        })
        
        force_authenticate(request, user=test_user)
        response= views.InvoiceViewSet.as_view({'post': 'create'})(request)
        self.assertEqual(Invoice.objects.count(), 1)
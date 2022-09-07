from django.test import TestCase
from django.core import mail
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.test import force_authenticate
from apps.users.models import CustomUser as User, WhitelistAddress
from apps.invoices.models import Invoice, Payment, InvoiceItem, PaymentCurrency
from apps.invoices.serializers import InvoiceSerializer
from datetime import datetime, timedelta
import json
import pytest
import io
from pprint import pprint

def get_payment_data(invoice, amount=None, symbol='ETH'):
    data = json.load(open('tests/fixtures/testFullPayment.json'))
    data['transaction']['value'] = amount or invoice.invoice_amount
    if symbol != 'ETH': # TODO Needs to support generating mocked txgun DAI token transactions
        currency = PaymentCurrency.objects.get(symbol=symbol)
        data['to_address'] = PaymentCurrency.contract_address
        data['token_to'] = invoice.pay_to
        data['token_amount'] = amount

    params = json.loads(data['transaction']['parameters_json'])
    params['values']['invoiceId'] = invoice.id

    data['transaction']['parameters_json'] = json.dumps(params)
    return data


@pytest.mark.django_db
class InvoiceTestCase(TestCase):
    @classmethod
    def setup_class(cls):
        cls.client = APIClient()
        cls.factory = APIRequestFactory()

    def _get(self, user, url):
        factory = APIRequestFactory()
        request = factory.get(url)
        force_authenticate(request, user)
        return request

    def _post(self, user, url, data):
        factory = APIRequestFactory()
        request = factory.post(url, data, format='json')
        force_authenticate(request, user)
        return request

    def _put(self, user, url, data):
        factory = APIRequestFactory()
        request = factory.put(url, data, format='json')
        force_authenticate(request, user)
        return request

    def _make_payment(self, invoice, amount=None):
        from apps.invoices import views
        return views.PaymentNotification.as_view()(self._post(None, '/api/payment_received', get_payment_data(invoice, amount)))

    def test_send_invoice(self):
        from apps.invoices import views

        test_user = User.objects.create_user(
            username="audrey", email="test@audrey.com", password="audrey")
        email = 'test@paywei.co'
        address = WhitelistAddress.objects.create(
            address='0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8',
            nickname='Barbara',
            user=test_user,
            status=WhitelistAddress.AddressStatus.verified
        )

        response = views.InvoiceViewSet.as_view(
            {'post': 'create'})(self._post(
                test_user,
                '/invoices/',
                {
                    'user': test_user.id,
                    'pay_to': address.id,
                    'recipient_email': email,
                    'invoice_amount': 1000000000,
                    'currency': PaymentCurrency.ETH().id,
                    'status': 'published'
                }
            ))
        self.assertEqual(Invoice.objects.count(), 1)

        # Email subjects: New User Registration, New Invoice Created, Someone has sent you a bill on PayWei
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(mail.outbox[-1].subject,
                         'Someone has sent you a bill on PayWei')

        response = views.InvoiceViewSet.as_view(
            {'post': 'create'})(self._post(
                test_user,
                '/invoices/',
                {
                    'user': test_user.id,
                    'pay_to': address.id,
                    'recipient_email': email,
                    'invoice_amount': 1000000000,
                    'currency': PaymentCurrency.ETH().id,
                    'delivery': Invoice.DeliveryChoices.link
                }
            ))
        self.assertEqual(Invoice.objects.count(), 2)
        self.assertEqual(len(mail.outbox), 4)
        self.assertNotEqual(mail.outbox[-1].subject, 'New Invoice Created')

    # test paying an invoice in full
    #   if I create an invoice, and a payment is made

    def test_pay_invoice_in_full(self):
        from apps.invoices import views

        factory = APIRequestFactory()
        test_user = User.objects.create_user(
            username="audrey", email="test@audrey.com", password="audrey")
        email = 'test@paywei.co'

        address = WhitelistAddress.objects.create(
            address='0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8',
            nickname='Barbara',
            user=test_user,
            status=WhitelistAddress.AddressStatus.verified
        )

        invoice_response = views.InvoiceViewSet.as_view(
            {'post': 'create'})(self._post(
                test_user,
                '/invoices/',
                {
                    'user': test_user.id,
                    'pay_to': address.id,
                    'recipient_email': email,
                    'invoice_amount': 1000000000,
                    'currency': PaymentCurrency.ETH().id,
                    'status': 'agreed',
                }
            ))
        self.assertEqual(Invoice.objects.count(), 1)

        invoice = Invoice.objects.first()
        self.assertEqual(invoice.status, 'agreed')

        payment = factory.post('/api/payment_received/',
                               get_payment_data(invoice), format='json')
        payment_response = views.PaymentNotification.as_view()(payment)

    #   should mark the invoice status paid
        invoice = Invoice.objects.first()
        self.assertEqual(invoice.status, 'paid_in_full')
    #   should have no balance due
        self.assertEqual(invoice.invoice_amount -
                         invoice.paid_amount, 0)
    #   should have an associated payment
        self.assertEqual(Payment.objects.count(), 1)

    # test paying an invoice partially
    #   if I make a partial payment on an invoice
    def test_pay_invoice_partially(self):
        from apps.invoices import views

        factory = APIRequestFactory()
        test_user = User.objects.create_user(
            username="audrey", email="test@audrey.com", password="audrey")
        email = 'test@paywei.co'

        address = WhitelistAddress.objects.create(
            address='0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8',
            nickname='Barbara',
            user=test_user,
            status=WhitelistAddress.AddressStatus.verified
        )

        invoice_response = views.InvoiceViewSet.as_view(
            {'post': 'create'})(self._post(
                test_user,
                '/invoices/',
                {
                    'user': test_user.id,
                    'pay_to': address.id,
                    'recipient_email': email,
                    'invoice_amount': 1000000000,
                    'currency': PaymentCurrency.ETH().id,
                    'status': 'agreed',
                    'min_payment_threshold': 25
                }
            ))
        self.assertEqual(Invoice.objects.count(), 1)
        invoice = Invoice.objects.first()

        payment = factory.post(
            '/api/payment_received/', get_payment_data(invoice, amount='500000000'), format='json')
        payment_response = views.PaymentNotification.as_view()(payment)
        invoice = Invoice.objects.first()

    #   should have the correct balance due
        self.assertEqual(invoice.invoice_amount -
                         invoice.paid_amount, 500000000)
    #   should have an associated payment
        self.assertEqual(Payment.objects.count(), 1)
    #   should make the invoice status partial payment
        self.assertEqual(invoice.status, "partial_payment")
    #   if I make another partial payment on an invoice
        payment = factory.post(
            '/api/payment_received/', get_payment_data(invoice, amount='250000000'), format='json')
        payment_response = views.PaymentNotification.as_view()(payment)
        invoice = Invoice.objects.first()
    #   should have the correct balance due
        self.assertEqual(invoice.invoice_amount -
                         invoice.paid_amount, 250000000)
    #   should have 2 associated payment
        self.assertEqual(Payment.objects.count(), 2)
    #   should make the invoice status partial payment
        self.assertEqual(invoice.status, "partial_payment")
    #   if I make a final partial payment on an invoice
        payment = factory.post(
            '/api/payment_received/', get_payment_data(invoice, amount='250000000'), format='json')
        payment_response = views.PaymentNotification.as_view()(payment)
        invoice = Invoice.objects.first()
    #   should have no balance due
        self.assertEqual(invoice.invoice_amount -
                         invoice.paid_amount, 0)
    #   should have 3 associated payment
        self.assertEqual(Payment.objects.count(), 3)
    #   should make the invoice status paid
        self.assertEqual(invoice.status, "paid_in_full")

    # test can't change agreed terms
    #   if an invoice has been agreed to

    def test_cannot_change_agreed_terms(self):
        from apps.invoices import views

        test_user = User.objects.create_user(
            username="audrey", email="test@audrey.com", password="audrey")
        email = 'test@paywei.co'

        address = WhitelistAddress.objects.create(
            address='0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8',
            nickname='Barbara',
            user=test_user,
            status=WhitelistAddress.AddressStatus.verified
        )

        invoice_response = views.InvoiceViewSet.as_view(
            {'post': 'create'})(self._post(
                test_user,
                '/invoices/',
                {
                    'user': test_user.id,
                    'pay_to': address.id,
                    'recipient_email': email,
                    'invoice_amount': 1000000000,
                    'currency': PaymentCurrency.ETH().id,
                    'status': 'new'
                }))
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(
            Invoice.objects.first().invoice_amount, 1000000000)
        invoice = Invoice.objects.first()

    #   should be able to edit invoice details
        invoice_response = views.InvoiceViewSet.as_view(
            {'put': 'update'})(self._put(
                test_user,
                '/invoices/' + invoice.id,
                {
                    'user': test_user.id,
                    'pay_to': address.id,
                    'recipient_email': email,
                    'invoice_amount': 2000000000,
                    'currency': PaymentCurrency.ETH().id,
                    'status': 'agreed'
                }), pk=invoice.id)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(
            Invoice.objects.first().invoice_amount, 2000000000)
        invoice = Invoice.objects.first()

    #   should not be able to edit invoice details
        invoice_response = views.InvoiceViewSet.as_view(
            {'put': 'update'})(self._put(
                test_user,
                '/invoices/' + invoice.id,
                {
                    'user': test_user.id,
                    'pay_to': address.id,
                    'recipient_email': email,
                    'invoice_amount': 3000000000,
                    'currency': PaymentCurrency.ETH().id,
                    'status': 'agreed'
                }), pk=invoice.id)

        invoice = Invoice.objects.first()
        self.assertEqual(
            invoice_response.data['_'][0], 'This invoice has already been agreed upon')
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(
            Invoice.objects.first().invoice_amount, 2000000000)

    # test save invoice without sending
    #   if I save an invoice

    def test_save_an_invoice(self):
        from apps.invoices import views

        test_user = User.objects.create_user(
            username="audrey", email="test@audrey.com", password="audrey")
        email = 'test@paywei.co'

        address = WhitelistAddress.objects.create(
            address='0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8',
            nickname='Barbara',
            user=test_user,
            status=WhitelistAddress.AddressStatus.verified
        )

        invoice_response = views.InvoiceViewSet.as_view(
            {'post': 'create'})(self._post(
                test_user,
                '/invoices/',
                {
                    'user': test_user.id,
                    'pay_to': address.id,
                    'recipient_email': email,
                    'invoice_amount': 1000000000,
                    'currency': PaymentCurrency.ETH().id,
                }))

    #   should have an outbox of 0
        self.assertEqual(len(mail.outbox), 2)
    #   should have added an invoice to the invoice list
        self.assertEqual(Invoice.objects.count(), 1)
    #   should have an invoice status- new
        self.assertEqual(Invoice.objects.first().status, 'new')

    # test user api permissions
    #   if I make 2 users, and they make invoices
    def test_user_permissions(self):
        from apps.invoices import views

        test_user1 = User.objects.create_user(
            username="audrey", email="test@audrey.com", password="audrey")
        test_user2 = User.objects.create_user(
            username="bob", email="test@bob.com", password="bob")
        email = 'test@paywei.co'

        address1 = WhitelistAddress.objects.create(
            address='0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8',
            nickname='Audrey',
            user=test_user1,
            status=WhitelistAddress.AddressStatus.verified
        )

        address2 = WhitelistAddress.objects.create(
            address='0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8',
            nickname='Bob',
            user=test_user2,
            status=WhitelistAddress.AddressStatus.verified
        )

        invoice_a = Invoice.objects.create(
            user=test_user1,
            pay_to=address1,
            recipient_email=email,
            invoice_amount=1000000000,
            currency=PaymentCurrency.ETH()
        )

        invoice_b = Invoice.objects.create(
            user=test_user1,
            pay_to=address1,
            recipient_email=email,
            invoice_amount=2000000000,
            currency=PaymentCurrency.ETH()
        )

        invoice_c = Invoice.objects.create(
            user=test_user2,
            pay_to=address2,
            recipient_email=email,
            invoice_amount=3000000000,
            currency=PaymentCurrency.ETH()
        )

        list_response = views.InvoiceViewSet.as_view(
            {'get': 'list'})(self._get(test_user2, '/invoices'))

        self.assertEqual(len(list_response.data['results']), 1)
    #   they should not be able to list eachothers invoices
        self.assertEqual(list_response.data['results'][0]['id'], invoice_c.id)

        self._make_payment(invoice_a)
        self._make_payment(invoice_b)
        self._make_payment(invoice_c)

        self.assertEqual(Payment.objects.count(), 3)

    #   they should not be able to list eachothers payments
        payment_list_response = views.PaymentViewSet.as_view(
            {'get': 'list'})(self._get(test_user1, '/payments'))

        self.assertEqual(len(payment_list_response.data['results']), 2)

        payment_list_response = views.PaymentViewSet.as_view(
            {'get': 'list'})(self._get(test_user2, '/payments/'))

        self.assertEqual(len(payment_list_response.data['results']), 1)

    #   they should not be able to see eachothers invoice or payment details
        list_response = views.InvoiceViewSet.as_view(
            {'get': 'retrieve'})(self._get(test_user2, '/invoices/' + invoice_a.id), pk=invoice_a.id)
        self.assertEqual(list_response.data['detail'], 'Not found.')

        payment_id = str(invoice_a.payments.first().id)
        list_response = views.PaymentViewSet.as_view(
            {'get': 'retrieve'})(self._get(test_user2, '/payments/' + payment_id), pk=payment_id)
        self.assertEqual(list_response.data['detail'], 'Not found.')

    #   they should not be able to create an invoice with the other user's id
        cross_account_invoice = views.InvoiceViewSet.as_view(
            {'post': 'create'})(self._post(
                test_user1,
                '/invoices/',
                {
                    'user': test_user2.id,
                    'pay_to': address2.id,
                    'recipient_email': email,
                    'invoice_amount': 1000000000,
                    'currency': PaymentCurrency.ETH().id,
                }))

        self.assertEqual(cross_account_invoice.data['user'], test_user1.id)

    def test_invoice_lineitem_serializers(self):

        test_user = User.objects.create_user(
            username="audrey", email="test@audrey.com", password="audrey")
        email = 'test@paywei.co'

        address = WhitelistAddress.objects.create(
            address='0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8',
            nickname='Audrey',
            user=test_user,
            status=WhitelistAddress.AddressStatus.verified
        )
        # inv = Invoice.objects.create()
        invoice = Invoice.objects.create(
            user=test_user,
            pay_to=address,
            recipient_email=email,
            invoice_amount=3000000000,
            currency=PaymentCurrency.ETH()
        )
        # item_a = inv.items.create()
        InvoiceItem.objects.create(
            order=1,
            title='First',
            quantity=1,
            price=1000000000,
            invoice=invoice
        )
        # item_b = inv.items.create()
        InvoiceItem.objects.create(
            order=2,
            title='Second',
            quantity=1,
            price=2000000000,
            invoice=invoice
        )
        # ser = InvoiceSerializer(inv)
        serializer = InvoiceSerializer(invoice)
        # assert(2, len(ser.data['items']))
        self.assertEqual(2, len(serializer.data['line_items']))

        # make = InvoiceSerializer( { ...invoice_details, items: [...] })
        make = InvoiceSerializer( data={
            'user': test_user.id,
            'pay_to': address.id,
            'recipient_email': email,
            'invoice_amount': 10000000000,
            'currency': PaymentCurrency.ETH().id,
            'line_items': [
                {'order': 1, 'title': 'Item1', 'quantity': 1, 'price': 500000000},
                {'order': 2, 'title': 'Item2', 'quantity': 1, 'price': 250000000},
                {'order': 3, 'title': 'Item3', 'quantity': 1, 'price': 250000000},
            ],
        })
        
        self.assertEqual(True, make.is_valid(), "Serializer should be valid: %s"%make.errors)
        obj = make.save()
        # assert(Invoice.objects.count(), 2)
        self.assertEqual(2, Invoice.objects.count())
        # assert(obj.items.count(), 2)
        self.assertEqual(3, obj.line_items.count())

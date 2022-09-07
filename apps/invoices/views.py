from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime, timedelta
from django.db.models import Sum
from apps.invoices.serializers import InvoiceSerializer, PaymentSerializer, PaymentCurrencySerializer
from apps.invoices.models import Invoice, Payment, PaymentCurrency
from rest_framework import viewsets
from apps.users.permissions import IsOwner
from django.utils import timezone
from rest_framework.decorators import action
import json
from django.db.models.functions import TruncDate
from decimal import Decimal

# Create your views here.

class InvoiceViewSet(viewsets.ModelViewSet):
    model = Invoice
    permission_classes = (IsOwner,)
    serializer_class = InvoiceSerializer

    @action(detail=True, methods=['post'])
    def agree(self, request, pk=None):
        obj = self.get_object()
        if obj.status in ['new', 'published']:
            obj.status = 'agreed'
            obj.save()
            return Response(self.serializer_class(obj).data)
        else:
            return Response({'error': 'unable to agree to invoice'})

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Invoice.objects.none()
        qs = Invoice.objects.filter(user=self.request.user)

        if self.action == 'list' and \
            self.request.query_params.get('show_archived', '').lower() != 'true':
            qs = qs.exclude(archived_at__lte=timezone.now())

        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if not instance.archived_at:
            instance.archived_at = timezone.now()
        instance.save()
        return instance
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(self.serializer_class(instance).data)
    
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        instance = self.get_object()
        instance.archived_at = None
        instance.save()
        return Response(self.serializer_class(instance).data)
        

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    model = Payment
    serializer_class = PaymentSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Payment.objects.none()
        return Payment.objects.filter(invoice__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PaymentCurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    model = PaymentCurrency
    serializer_class = PaymentCurrencySerializer
    queryset = PaymentCurrency.objects.all()


# TODO: SECURITY ALERT!
# We need to add an AdminEmail when a Payment is received in an invoice that is not Agreed
# because this should basically never happen! It is indicative of an attack on the service!


# TODO: Need to add support for Confirmations; right now, all payments are Confirmed

class PaymentNotification(APIView):
    def post(self, request, format=None):
        from .models import PaymentCurrency
        tx = request.data['transaction']
        if not tx['parameters_json']:
            return Response({
                'status': 'failed',
                'errors': {'parameters_json': 'No function parameters'}
            })

        parameters = json.loads(tx['parameters_json'])
        try:
            invoice = Invoice.objects.get(pk=parameters['values']['invoiceId'])
        except:
            return Response({
                'status': 'failed',
                'errors': {'invoice_id': 'No such invoice'}
            })
        if tx['is_token']:
            try:
                currency = PaymentCurrency.objects.get(contract_address=tx['to_address'])
            except PaymentCurrency.DoesNotExist:
                from django.core.mail import mail_admins
                mail_admins(
                    'Unexpected Currency Recieved For Invoice',
                    'https://etherscan.io/tx/'+tx['tx_hash']
                )
                raise
        else:
            currency = PaymentCurrency.ETH()

        amount = int(tx['is_token'] and tx['token_amount'] or tx['value'])

        obj = PaymentSerializer(data={
            'invoice': invoice.id,
            'block_hash': tx['block_hash'],
            'block_number': tx['block_number'],
            'from_address': tx['from_address'],
            'gas': tx['gas'],
            'gas_price': tx['gas_price'],
            'tx_hash': tx['tx_hash'],
            'tx_input': tx['tx_input'],
            'nonce': tx['nonce'],
            'to_address': tx['is_token'] and tx['token_to'] or tx['to_address'],
            'transaction_date_time': tx['created_at'],
            'amount': amount,
            'conversion_rate': currency.convert_rate(invoice.currency, eth_usd_price=tx['pricing_info']['price']),
            'converted_amount': currency.convert_amount(invoice.currency, amount, eth_usd_price=tx['pricing_info']['price']),
            'parameters_json': tx['parameters_json'],
            'currency': currency.id,
            'status': 'confirmed',
            'created_at': timezone.now()
        })
        if not obj.is_valid():
            return Response({
                'status': 'failed',
                'errors': obj.errors
            })
        obj.save()
        invoice.save()
        return Response({
            'status': 'ok',
            'details': obj.data
        })

class Dashboard(APIView):
    def get(self, request):
        today = timezone.now().date()
        start = today - timedelta(days=7)
        my_payments = Payment.objects.filter(
                invoice__user_id=request.user.id,
                transaction_date_time__gte=start
            )

        grouped_by_date = my_payments.all(
            ).annotate(
                day=TruncDate('transaction_date_time')
            ).values('day'
            ).order_by('day'
            ).annotate(total=Sum('amount')
            ).values('day', 'total'
            )

        print(grouped_by_date)

        # Start with a dictionary so we can fill the empty days easily
        data = {
            obj['day']: obj['total'] / Decimal(10E18)
            for obj in grouped_by_date
        }

        zero_filled_list = [
            {
                'date': start + timedelta(days=i),
                'ETH': data.get(start + timedelta(days=i), 0)
            }
            for i in range( (today - start).days + 1)
        ]

        return Response({
            'payments_by_day': zero_filled_list
        })
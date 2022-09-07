from apps.invoices.models import Invoice, Payment, InvoiceItem, PaymentCurrency
from rest_framework import serializers
import re

class InvoiceItemSerializer(serializers.ModelSerializer):
    invoice = serializers.PrimaryKeyRelatedField(read_only=True, required=False)

    class Meta:
        model = InvoiceItem
        fields = ('__all__')

class InvoiceSerializer(serializers.ModelSerializer):
    line_items = InvoiceItemSerializer(many=True, required=False)
    currency_data = serializers.SerializerMethodField()
    amount_due = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ('__all__')

    def get_currency_data(self, obj):
        return PaymentCurrencySerializer(obj.currency).data

    def get_amount_due(self, obj):
        return obj.get_amount_due()

    def create(self, validated_data):
        item_data = validated_data.pop('line_items', [])
        invoice = Invoice.objects.create(**validated_data)
        for item in item_data:
            InvoiceItem.objects.create(invoice=invoice, **item)
        return invoice

    def validate_pay_to(self, value):
        if not value.status == 'verified':
            raise serializers.ValidationError({'pay_to': 'Must be a whitelist-verified address'})
        return value

    def validate(self, data):
        if data['pay_to'].user != data['user']:
            raise serializers.ValidationError({'pay_to': 'This address does not belong to you'})
        if self.instance and self.instance.status == 'agreed':
            raise serializers.ValidationError({ '_': 'This invoice has already been agreed upon'})
        return data

class PaymentSerializer(serializers.ModelSerializer):
    currency_data = serializers.SerializerMethodField()

    def get_currency_data(self, obj):
        return PaymentCurrencySerializer(obj.currency).data

    class Meta:
        model = Payment
        fields = ('__all__')

class PaymentCurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentCurrency
        fields = ('__all__')


    
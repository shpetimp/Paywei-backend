# Generated by Django 2.0 on 2019-09-18 08:13

import apps.invoices.models
import apps.model_base
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0003_auto_20190904_0919'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.CharField(default=apps.model_base.cutePk, editable=False, max_length=8, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('status', models.CharField(choices=[('new', 'New'), ('published', 'Published'), ('agreed', 'Agreed'), ('partial_payment', 'Partial Payment'), ('paid_in_full', 'Paid in Full')], default='new', max_length=32)),
                ('delivery', models.CharField(choices=[('email', 'Email'), ('link', 'Link')], default='email', max_length=32)),
                ('recipient_email', models.CharField(blank=True, max_length=64, null=True)),
                ('key', models.CharField(default=apps.invoices.models.makeKey, max_length=32)),
                ('archived_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.CharField(blank=True, max_length=512, null=True)),
                ('due_date', models.DateTimeField(blank=True, null=True)),
                ('sent_date', models.DateTimeField(blank=True, null=True)),
                ('agreed_at', models.DateTimeField(blank=True, null=True)),
                ('invoice_amount', models.DecimalField(decimal_places=0, max_digits=50)),
                ('paid_amount', models.DecimalField(decimal_places=0, default=0, max_digits=50)),
                ('min_payment_threshold', models.PositiveIntegerField(blank=True, default=100, validators=[django.core.validators.MaxValueValidator(100)])),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.CharField(default=apps.model_base.cutePk, editable=False, max_length=8, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('order', models.PositiveIntegerField()),
                ('quantity', models.PositiveIntegerField()),
                ('price', models.DecimalField(decimal_places=0, max_digits=50)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='line_items', to='invoices.Invoice')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('new', 'New'), ('confirmed', 'Confirmed')], default='new', max_length=32)),
                ('amount', models.DecimalField(decimal_places=0, max_digits=50)),
                ('usd_eth_price', models.DecimalField(decimal_places=10, max_digits=20)),
                ('block_hash', models.TextField()),
                ('block_number', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField()),
                ('gas', models.PositiveIntegerField()),
                ('gas_price', models.DecimalField(decimal_places=0, max_digits=50)),
                ('tx_hash', models.CharField(db_index=True, max_length=128)),
                ('tx_input', models.TextField()),
                ('parameters_json', models.TextField(blank=True, null=True)),
                ('nonce', models.PositiveIntegerField()),
                ('from_address', models.CharField(max_length=64)),
                ('to_address', models.CharField(max_length=64)),
                ('transaction_date_time', models.DateTimeField()),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='PaymentCurrency',
            fields=[
                ('id', models.CharField(default=apps.model_base.cutePk, editable=False, max_length=8, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('contract_address', models.CharField(max_length=50)),
                ('symbol', models.CharField(max_length=64)),
                ('decimal_places', models.PositiveIntegerField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='payment',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='invoices.PaymentCurrency'),
        ),
        migrations.AddField(
            model_name='payment',
            name='invoice',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='payments', to='invoices.Invoice'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='invoices.PaymentCurrency'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='pay_to',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='pay_to', to='users.WhitelistAddress'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='invoices', to=settings.AUTH_USER_MODEL),
        ),
    ]

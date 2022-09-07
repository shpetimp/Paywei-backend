import factory
from django.utils import timezone
from apps.invoices.models import Invoice, Payment
from apps.users.factory import UserFactory, WhitelistAddressFactory
import random

ADDRESS_VALID = '0123456789abcdef'
def make_address():
  return '0x'+''.join(random.choice(ADDRESS_VALID) for i in range(20))
  
def random_currency():
  from apps.invoices.models import DEFAULT_CURRENCIES
  return random.choice(list(create() for create in DEFAULT_CURRENCIES.values()))

def random_title():
  # madlib time
  verb = ['cleaning', 'moving', 'bringing', 'helping', 'building', 'wiping']
  noun = ['lawn', 'car', 'yard', 'dog', 'mom', 'face', 'feet', 'walls', 'roof', 'porch']
  when = ['yesterday', 'soon', 'today', 'tomorrow', 'last week', 'last year']
  return 'For %s my %s %s'%(random.choice(verb), random.choice(noun), random.choice(when))

class InvoiceFactory(factory.DjangoModelFactory):
  class Meta:
    model = Invoice

  user = factory.SubFactory(UserFactory)
  title = factory.LazyFunction(random_title)
  recipient_email = factory.LazyAttribute(lambda a: '{0}.test@example.com'.format(a.user).lower())
  invoice_amount = factory.LazyFunction(lambda: 100000000000000000*random.randrange(100))
  currency = factory.LazyFunction(random_currency)
  min_payment_threshold = 10
  status = 'agreed'

  @factory.lazy_attribute
  def pay_to(self):
    addresses = self.user.addresses
    if addresses.count(): return addresses.all()[addresses.count()-1]
    else: return WhitelistAddressFactory(user=self.user)


class PaymentFactory(factory.DjangoModelFactory):
  class Meta:
    model = Payment

  status = "confirmed"
  invoice = factory.SubFactory(InvoiceFactory)
  amount = factory.LazyAttribute(lambda p: random.choice([
    p.invoice.invoice_amount,
    p.invoice.invoice_amount/2,
  ]))
  currency = factory.LazyFunction(random_currency)
  usd_eth_price = 220
  block_hash = 0
  created_at = factory.LazyFunction(timezone.now)
  gas = 0
  gas_price = 0
  tx_hash = 0
  tx_input = 0
  nonce = factory.Sequence(lambda n: n)
  block_number = factory.Sequence(lambda n: n)
  from_address = factory.LazyFunction(make_address)
  to_address = factory.LazyFunction(make_address)
  transaction_date_time = factory.LazyFunction(timezone.now)



  
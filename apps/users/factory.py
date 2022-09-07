import factory
from django.utils import timezone
from apps.users.models import CustomUser as User, WhitelistAddress, makeKey
from random import choice

ADDRESS_VALID = '0123456789abcdef'
def make_address():
  return '0x'+''.join(choice(ADDRESS_VALID) for i in range(20))

class UserFactory(factory.DjangoModelFactory):
  class Meta:
    model = User

  username = factory.LazyAttribute(lambda a: '{0}.{1}'.format(a.first_name, a.last_name).lower())
  password = "test"
  first_name = factory.Faker('first_name')
  last_name = factory.Faker('last_name')
  email = factory.LazyAttribute(lambda a: '{0}.{1}@example.com'.format(a.first_name, a.last_name).lower())
  is_active = True
  is_staff = False
  is_superuser = False
  date_joined = factory.LazyFunction(timezone.now)

class WhitelistAddressFactory(factory.DjangoModelFactory):
  class Meta:
    model = WhitelistAddress

  nickname = factory.Faker('first_name')
  address = factory.LazyFunction(make_address)
  user = factory.SubFactory(UserFactory)
  status = "verified"


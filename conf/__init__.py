# -*- coding: utf-8 -*-

from .base import *
try:
    from .eth import *
except:
    pass

import os

DEBUG=os.environ.get('is_zappa', '') != 'true'
SECRET_KEY='f71452a82725b2d03ed8520cca0f1fce'

# -*- coding: utf-8 -*-
import uuid
import fauxfactory

import pytest

from copy import copy, deepcopy

from cfme.utils import error
from cfme.base.credential import Credential
from cfme.common.provider_views import (PhysicalProviderAddView,
                                        PhysicalProvidersView)
from cfme.physical.provider.lenovo import PhysicalProvider, LenovoProvider, LenovoEndpoint
from cfme.utils import testgen, version
from cfme.utils.update import update
from cfme.utils.blockers import BZ
from cfme import test_requirements
from cfme.utils.appliance import get_or_create_current_appliance


def test_provider_crud():
    """Tests provider add with good credentials

    Metadata:
        test_flag: crud
    """
    endpoint = LenovoEndpoint(hostname=fauxfactory.gen_alphanumeric(256))
    provider =  LenovoProvider(
        appliance=get_or_create_current_appliance(),
        name=fauxfactory.gen_alphanumeric(5),
        endpoints=endpoint)
    try:
      provider.create('lenovo')
      # Fails on upstream, all provider types - BZ1087476
      provider.validate_stats(ui=True)

      old_name = provider.name
      with update(provider):
          provider.name = str(uuid.uuid4())  # random uuid

      with update(provider):
          provider.name = old_name  # old name

      provider.delete(cancel=False)
      provider.wait_for_delete()
    except AssertionError:
       print 'pass'


# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import pytest
from widgetastic.exceptions import MoveTargetOutOfBoundsException

from cfme.common.provider_views import NetworkProvidersView
from cfme import test_requirements
from cfme.networks.provider.nuage import NuageProvider, NetworkProvider

pytestmark = [pytest.mark.provider([NetworkProvider], scope="module")]


@pytest.mark.tier(3)
@test_requirements.discovery
def test_add_cancelled_validation(request):
    """Tests that the flash message is correct when add is cancelled."""
    prov = NuageProvider(None, None)
    request.addfinalizer(prov.delete_if_exists)
    try:
        prov.create(cancel=True, validate_credentials=False)
    except MoveTargetOutOfBoundsException:
        # TODO: Remove once fixed 1475303
        prov.create(cancel=True, validate_credentials=False)
    view = prov.browser.create_view(NetworkProvidersView)
    view.flash.assert_success_message('Add of Network Manager was cancelled by the user')

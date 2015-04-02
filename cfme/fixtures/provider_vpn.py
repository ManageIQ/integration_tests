# -*- coding: utf-8 -*-
"""This module handles connections to providers that are hidden in some private networks, accessible
by a VPN connection.

This requires some additional fields in cfme_data:

.. code-block:: yaml

   basic_info:
     epel: url-to-epel-repo-rpm
   management_systems:
     my_mgmt_system:
       vpn:
         url6: url
         test_machine: url

So far we have url6 for the RHEL6 based appliances. Will be needed to be extended if RHEL7 comes.

The ``url6`` url is a root-based archive (starts in ``i`` in the filesystem).
This one gets downloaded
into the ``/`` of the appliance and unpacked so it produces ``/etc/openvpn/*`` configuration files
for RHEL6 based systems.

The ``test_machine`` url is a flat archive with configuration and keys, the keys should not have
any prefix path in the configuration file. This one is used to start openvpn client in the testing
environment. The testing environemnt should have ``sudo`` command without password to successfully
start the VPN environment.

The :py:func:`provider_vpn` fixture should detect that non-password ``sudo`` is supported or not
and should act accordingly (without it skip the test)
"""
import pytest
from Runner import Run

from fixtures.pytest_store import store
from utils import local_vpn


@pytest.yield_fixture(scope="module")
def provider_vpn(provider_data, provider_key, provider_crud):
    """This fixture sets up a VPN connection between the provider and the appliance and also between
    the provider and the test host to be able to access it using mgmt_system"""
    if "vpn" not in provider_data:
        yield
    else:
        if not Run.command("sudo -n true"):
            pytest.skip("The environment does not allow non-password sudo.")
        with store.current_appliance.vpn_for(provider_key):
            with local_vpn.vpn_for(provider_key):
                yield
                # And delete to prevent having inaccessible providers
                provider_crud.delete(cancel=False)

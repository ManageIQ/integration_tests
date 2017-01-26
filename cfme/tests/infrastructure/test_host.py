# -*- coding: utf-8 -*-
import pytest
import random

import cfme.fixtures.pytest_selenium as sel
from cfme.infrastructure.host import credential_form
from cfme.infrastructure.provider import details_page, InfraProvider
from cfme.web_ui import Quadicon, fill, toolbar as tb, flash
from utils import testgen
from utils import version
import utils.conf as conf
from utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.meta(blockers=[1296258]),
    pytest.mark.tier(3),
]


def config_option():
    return version.pick({version.LOWEST: 'Edit Selected Hosts', '5.4': 'Edit Selected items'})


def pytest_generate_tests(metafunc):
    # Filter out providers without multiple hosts defined
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [InfraProvider], required_fields=["hosts"])

    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        hosts = args['provider'].data.get('hosts', {})

        if len(hosts) < 2:
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


# Tests to automate BZ 1201092
def test_multiple_host_good_creds(setup_provider, provider):
    """  Tests multiple host credentialing  with good credentials """

    navigate_to(provider, 'Details')
    sel.click(details_page.infoblock.element("Relationships", "Hosts"))

    quads = Quadicon.all("host", this_page=True)
    for quad in quads:
            sel.check(quad.checkbox())
    tb.select("Configuration", config_option())

    cfme_host = random.choice(provider.data["hosts"])
    cred = cfme_host['credentials']
    creds = conf.credentials[cred]
    fill(credential_form, {'default_principal': creds['username'],
                           'default_secret': creds['password'],
                           'default_verify_secret': creds['password'],
                           'validate_host': cfme_host["name"]})

    sel.click(credential_form.validate_multi_host)
    flash.assert_message_match('Credential validation was successful')

    sel.click(credential_form.save_btn)
    flash.assert_message_match('Credentials/Settings saved successfully')


def test_multiple_host_bad_creds(setup_provider, provider):
    """    Tests multiple host credentialing with bad credentials """

    navigate_to(provider, 'Details')
    sel.click(details_page.infoblock.element("Relationships", "Hosts"))

    quads = Quadicon.all("host", this_page=True)
    for quad in quads:
            sel.check(quad.checkbox())
    tb.select("Configuration", config_option())

    cfme_host = random.choice(provider.data["hosts"])
    creds = conf.credentials['bad_credentials']
    fill(credential_form, {'default_principal': creds['username'],
                           'default_secret': creds['password'],
                           'default_verify_secret': creds['password'],
                           'validate_host': cfme_host["name"]})

    sel.click(credential_form.validate_multi_host)
    flash.assert_message_match('Cannot complete login due to an incorrect user name or password.')

    sel.click(credential_form.cancel_changes)

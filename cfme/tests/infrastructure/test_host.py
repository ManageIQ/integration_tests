# -*- coding: utf-8 -*-

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.toolbar as tb
import cfme.web_ui.flash as flash
import random
import utils.conf as conf

from cfme.infrastructure.host import credential_form
from cfme.infrastructure.provider import details_page
from cfme.web_ui import Quadicon, fill
from utils import testgen
from utils import version


def config_option():
    return version.pick({version.LOWEST: 'Edit Selected Hosts', '5.4': 'Edit Selected items'})


def pytest_generate_tests(metafunc):
    # Filter out providers without multiple hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'hosts')
    argnames = argnames + ['host_list']

    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['hosts']:
            # No host data available
            continue

        if len(args['hosts']) < 2:
            continue

        host_list = [host['name'] for host in args['hosts']]

        new_idlist.append(idlist[i])
        argvalues[i].append(host_list)
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


# Tests to automate BZ 1201092
def test_multiple_host_good_creds(setup_provider, provider, hosts, host_list):
    """  Tests multiple host credentialing  with good credentials """

    sel.force_navigate('infrastructure_provider', context={'provider': provider})
    sel.click(details_page.infoblock.element("Relationships", "Hosts"))

    quads = Quadicon.all("host", this_page=True)
    for quad in quads:
            sel.check(quad.checkbox())
    tb.select("Configuration", config_option())

    cfme_host = random.choice(provider.get_yaml_data()["hosts"])
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


def test_multiple_host_bad_creds(setup_provider, provider, hosts, host_list):
    """    Tests multiple host credentialing with bad credentials """

    sel.force_navigate('infrastructure_provider', context={'provider': provider})
    sel.click(details_page.infoblock.element("Relationships", "Hosts"))

    quads = Quadicon.all("host", this_page=True)
    for quad in quads:
            sel.check(quad.checkbox())
    tb.select("Configuration", config_option())

    cfme_host = random.choice(provider.get_yaml_data()["hosts"])
    creds = conf.credentials['bad_credentials']
    fill(credential_form, {'default_principal': creds['username'],
                           'default_secret': creds['password'],
                           'default_verify_secret': creds['password'],
                           'validate_host': cfme_host["name"]})

    sel.click(credential_form.validate_multi_host)
    flash.assert_message_match('Cannot complete login due to an incorrect user name or password.')

    sel.click(credential_form.cancel_changes)

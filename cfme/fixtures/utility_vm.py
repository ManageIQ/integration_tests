# -*- coding: utf-8 -*-
import os.path

import fauxfactory
import pytest

from cfme.utils.conf import cfme_data
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.net import find_pingable
from cfme.utils.virtual_machines import deploy_template
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


@pytest.fixture(scope='module')
def utility_vm():
    """ Deploy an utility vm for tests to use.

    This fixture creates a vm on provider and then receives its ip.
    After the test run vm is deleted from provider.
    """
    try:
        root_password = fauxfactory.gen_alphanumeric(length=10)
        try:
            with open(os.path.expanduser('~/.ssh/id_rsa.pub')) as f:
                authorized_ssh_keys = f.read()
        except FileNotFoundError:
            authorized_ssh_keys = None
        data = cfme_data.utility_vm
        vm = deploy_template(
            data.provider,
            random_vm_name('proxy'),
            template_name=data.template_name,
            root_password=root_password,
            authorized_ssh_keys=authorized_ssh_keys
        )
    except AttributeError:
        msg = 'Missing data in cfme_data.yaml, cannot deploy proxy'
        logger.exception(msg)
        pytest.skip(msg)

    try:
        found_ip, _ = wait_for(
            find_pingable,
            func_args=[vm],
            fail_condition=None,
            delay=5,
            num_sec=300
        )
    except TimedOutError:
        msg = 'Timed out waiting for reachable proxy VM IP'
        logger.exception(msg)
        pytest.skip(msg)

    yield found_ip, root_password
    vm.delete()

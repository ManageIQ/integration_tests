import pytest

from cfme.configure.configuration.region_settings import RedHatUpdates
from utils import conf, version
from utils.testgen import parametrize
from utils.wait import wait_for
from utils.log import logger
from utils.conf import cfme_data
from scripts.repo_gen import process_url

REG_METHODS = ('rhsm', 'sat6')

"""
Tests RHSM and Sat6 validation and registration, checks result over ssh
(update is not performed - it is non-destructive).

For setup, see test_update_appliances.py (red_hat_updates section in cfme_data yaml).

These tests do not check registration results in the web UI, only through SSH.
"""


def pytest_generate_tests(metafunc):
    if metafunc.function in {test_rh_updates}:
        return
    """ Generates tests specific to RHSM or SAT6 with proxy-on or off """
    argnames = ['reg_method', 'reg_data', 'proxy_url', 'proxy_creds']
    argvalues = []
    idlist = []

    stream = version.current_stream()
    try:
        all_reg_data = conf.cfme_data.get('redhat_updates', {})['streams'][stream]
    except KeyError:
        logger.warning('Could not find rhsm data for stream in yaml')
        pytest.mark.uncollect(
            metafunc.function, message='Could not find rhsm data for stream in yaml')
        return

    if 'reg_method' in metafunc.fixturenames:
        for reg_method in REG_METHODS:

            reg_data = all_reg_data.get(reg_method)
            if not reg_data or not reg_data.get('test_registration', False):
                continue

            proxy_data = conf.cfme_data.get('redhat_updates', {}).get('http_proxy', False)
            if proxy_data and reg_data.get('use_http_proxy', False):
                proxy_url = proxy_data['url']
                proxy_creds_key = proxy_data['credentials']
                proxy_creds = conf.credentials[proxy_creds_key]
                argval = [reg_method, reg_data, proxy_url, proxy_creds]
                argid = '{}-{}'.format(reg_method, 'proxy_on')
                idlist.append(argid)
                argvalues.append(argval)

            argval = [reg_method, reg_data, None, None]
            argid = '{}-{}'.format(reg_method, 'proxy_off')
            idlist.append(argid)
            argvalues.append(argval)
        parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


def is_appliance_updated(self, appliance):
    version = appliance.version
    split_ver = str(version).split(".")
    next_build = '99'
    upgrade_version = ("{}.{}.{}".format(split_ver[0], split_ver[1], next_build))
    ver = self.version
    del ver.__dict__['version']
    assert self.version == upgrade_version


@pytest.yield_fixture(scope="function")
def appliance_preupdate(temp_appliance_preconfig_funcscope, appliance):
    """Requests appliance from sprout and configures rpms for fake update"""
    series = appliance.version.series()
    run = temp_appliance_preconfig_funcscope.ssh_client.run_command
    url = process_url(cfme_data['basic_info']['rpmbuild'])
    url_local = process_url(cfme_data['basic_info']['local_url'])
    temp_appliance_preconfig_funcscope.db.extend_partition()
    run('curl -o /etc/yum.repos.d/rpmrebuild.repo {}'.format(url))
    run('yum install rpmrebuild -y')
    run('mkdir /myrepo')
    run('rpmrebuild --release=99 cfme-appliance')
    run('cp /root/rpmbuild/RPMS/x86_64/cfme-appliance-* '
        '/myrepo/cfme-{}-update-99.x86_64.rpm'.format(series))
    run('createrepo /myrepo/')
    run('curl -o /etc/yum.repos.d/update.repo {}'.format(url_local))
    yield temp_appliance_preconfig_funcscope


@pytest.mark.ignore_stream("upstream")
def test_rh_creds_validation(request, reg_method, reg_data, proxy_url, proxy_creds):
    """ Tests whether credentials are validated correctly for RHSM and SAT6 """
    repo = reg_data.get('enable_repo')
    if not repo:
        set_default_repo = True
    else:
        set_default_repo = False

    if proxy_url:
        use_proxy = True
        proxy_username = proxy_creds['username']
        proxy_password = proxy_creds['password']
    else:
        use_proxy = False
        proxy_url = None
        proxy_username = None
        proxy_password = None
    red_hat_updates = RedHatUpdates(
        service=reg_method,
        url=reg_data['url'],
        username=conf.credentials[reg_method]['username'],
        password=conf.credentials[reg_method]['password'],
        repo_name=repo,
        organization=reg_data.get('organization'),
        use_proxy=use_proxy,
        proxy_url=proxy_url,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
        set_default_repository=set_default_repo
    )
    red_hat_updates.update_registration(cancel=True)


@pytest.mark.ignore_stream("upstream")
def test_rh_registration(appliance, request, reg_method, reg_data, proxy_url, proxy_creds):
    """ Tests whether an appliance can be registered againt RHSM and SAT6 """
    repo = reg_data.get('enable_repo')
    if not repo:
        set_default_repo = True
    else:
        set_default_repo = False

    if proxy_url:
        use_proxy = True
        proxy_username = proxy_creds['username']
        proxy_password = proxy_creds['password']
    else:
        use_proxy = False
        proxy_url = None
        proxy_username = None
        proxy_password = None
    red_hat_updates = RedHatUpdates(
        service=reg_method,
        url=reg_data['url'],
        username=conf.credentials[reg_method]['username'],
        password=conf.credentials[reg_method]['password'],
        repo_name=repo,
        organization=reg_data.get('organization'),
        use_proxy=use_proxy,
        proxy_url=proxy_url,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
        set_default_repository=set_default_repo
    )
    red_hat_updates.update_registration(validate=False if reg_method != 'sat6' else True)

    used_repo_or_channel = red_hat_updates.get_repository_names()

    red_hat_updates.register_appliances()  # Register all

    request.addfinalizer(appliance.unregister)

    wait_for(
        func=red_hat_updates.is_registering,
        func_args=[appliance.server.name],
        delay=10,
        num_sec=100,
        fail_func=red_hat_updates.refresh
    )

    '''if/else added to overcome bz #1463588 these can be removed once fixed'''

    if reg_method == 'rhsm':
        wait_for(
            func=red_hat_updates.is_registered,
            handle_exception=True,
            func_args=[appliance.server.name],
            delay=40,
            num_sec=400,
            fail_func=red_hat_updates.refresh
        )
    else:
        # First registration with sat6 fails; we need to click it after this failure
        wait_for(
            func=red_hat_updates.is_registered,
            func_args=[appliance.server.name],
            delay=50,
            num_sec=1200,
            fail_func=red_hat_updates.register_appliances
        )

    wait_for(
        func=appliance.is_registration_complete,
        func_args=[used_repo_or_channel],
        delay=20,
        num_sec=400
    )


def test_rh_updates(appliance_preupdate, appliance):
    """ Tests whether the update button in the webui functions correctly """

    set_default_repo = True

    red_hat_updates = RedHatUpdates(
        service='rhsm',
        url=conf.cfme_data['redhat_updates']['registration']['rhsm']['url'],
        username=conf.credentials['rhsm']['username'],
        password=conf.credentials['rhsm']['password'],
        set_default_repository=set_default_repo
    )
    red_hat_updates.update_registration(validate=False)

    red_hat_updates.check_updates()

    wait_for(
        func=red_hat_updates.checked_updates,
        func_args=[appliance.server.name],
        delay=10,
        num_sec=100,
        fail_func=red_hat_updates.refresh
    )

    if red_hat_updates.platform_updates_available():
        red_hat_updates.update_appliances()

    wait_for(lambda: is_appliance_updated, num_sec=900)
    assert appliance_preupdate.ssh_client.run_command(
        'rpm -qa cfme-appliance-{}-99x86_64.rpm'.format(appliance.version))

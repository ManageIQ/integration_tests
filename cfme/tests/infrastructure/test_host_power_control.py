# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from utils.wait import wait_for
from utils import error


@pytest.fixture(scope="module")
def hosts_data():
    name = fauxfactory.gen_alphanumeric()
    hosts_data = [{
        "name": "name_{}_{}".format(index, name),
        "hostname": "hostname_{}_{}".format(index, name),
        "userid": "userid_{}".format(index),
        "password": "".format(fauxfactory.gen_alphanumeric()),
        "ipaddress": "192.168.1.{}".format(index)
    } for index in range(1, 5)]

    return hosts_data


@pytest.fixture(scope="class")
def added_hosts(request, hosts_data, rest_api):
    for host in hosts_data:
        rest_api.collections.hosts.action.add(host)
        wait_for(
            lambda: rest_api.collections.policies.find_by(name=host.get("name")),
            num_sec=180,
            delay=10,
        )

    def fin():
        hosts = [host.id for host in rest_api.collections.hosts]
        rest_api.collections.hosts.delete(hosts)

    request.addfinalizer(fin)

    return [host.id for host in rest_api.collections.hosts]


@pytest.fixture(scope="class")
def host_name(hosts_data):
    for host in hosts_data:
        if host.get('name'):
            return host.get('name')
    return None


@pytest.mark.usefixtures("added_hosts")
class TestHostPowerControlRESTAPI(object):
    @pytest.fixture(scope="function")
    def host(self, rest_api, host_name):
        result = rest_api.collections.hosts.get(name=host_name)
        assert result.name == host_name
        return result

    def test_power_off(self, host):
        assert "poweroff" in host.action
        host.action.stop()
        wait_for(lambda: host.power_state == "off", num_sec=300, delay=5, fail_func=host.reload)

    def test_power_on(self, host):
        assert "poweron" in host.action
        host.action.start()
        wait_for(lambda: host.power_state == "on", num_sec=300, delay=5, fail_func=host.reload)

    def test_reset(self, host):
        assert "reset" in host.action
        old_updated_time = host.updated_on
        host.action.reset()
        wait_for(lambda: host.updated_on != old_updated_time, num_sec=300, delay=5,
            fail_func=host.reload)

    def test_restart(self, host):
        assert "restart" in host.action
        old_updated_time = host.updated_on
        host.action.restart()
        wait_for(lambda: host.updated_on != old_updated_time, num_sec=300, delay=5,
            fail_func=host.reload)

    def test_shutdown(self, host):
        assert "shutdown" in host.action
        host.action.shutdown()
        wait_for(lambda: host.power_state == "off", num_sec=300, delay=5, fail_func=host.reload)

    def test_standby(self, host):
        assert "standby" in host.action
        old_updated_time = host.updated_on
        host.action.standby()
        wait_for(lambda: host.updated_on != old_updated_time, num_sec=300, delay=5,
            fail_func=host.reload)


@pytest.mark.usefixtures("added_hosts")
class TestHostCrudViaREST(object):

    @pytest.fixture(scope="function")
    def host(self, rest_api, host_name):
        result = rest_api.collections.vms.get(name=host_name)
        assert result.name == host_name
        return result

    def test_delete(self, host, rest_api):
        assert "delete" in host.action
        host.action.delete()
        wait_for(
            lambda: not rest_api.collections.vms.find_by(name=host_name),
            num_sec=240, delay=5)

    def test_edit(self, host, rest_api):
        assert "edit" in host.action
        new_name = fauxfactory.gen_alphanumeric()
        host.action.edit(name=new_name)
        wait_for(
            lambda: rest_api.collections.vms.find_by(name=new_name),
            num_sec=240, delay=5)

    def test_add_delete_all(self, hosts_data, rest_api):
        names = []
        for host_name in hosts_data:
            names.append(host_name.get('name'))
        delete_hosts = [host.id for host in rest_api.collections.hosts if host.name in names]
        rest_api.collections.hosts.action.delete(delete_hosts)
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.hosts.action.delete(delete_hosts)

    def test_refresh(self, host, rest_api):
        assert "refresh" in host.action
        old_updated_on = host.updated_on
        assert host.action.refresh()["success"], "Refresh was unsuccessful"
        wait_for(
            lambda: host.updated_on != old_updated_on,
            fail_func=host.reload,
            num_sec=720,
            delay=5,
        )

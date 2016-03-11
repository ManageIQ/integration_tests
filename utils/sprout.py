# -*- coding: utf-8 -*-
import json
import os
import requests

from utils import lazycache
from utils.appliance import Appliance, ApplianceSet
from utils.conf import credentials, env
from utils.log import logger
from utils.version import get_stream
from utils.wait import wait_for


class SproutException(Exception):
    pass


class AuthException(SproutException):
    pass


class APIMethodCall(object):
    def __init__(self, client, method_name):
        self._client = client
        self._method_name = method_name

    def __call__(self, *args, **kwargs):
        return self._client.call_method(self._method_name, *args, **kwargs)


class SproutClient(object):
    def __init__(
            self, protocol="http", host="localhost", port=8000, entry="appliances/api", auth=None):
        self._proto = protocol
        self._host = host
        self._port = port
        self._entry = entry
        self._auth = auth

    @property
    def api_entry(self):
        return "{}://{}:{}/{}".format(self._proto, self._host, self._port, self._entry)

    def _post(self, **data):
        return requests.post(self.api_entry, data=json.dumps(data))

    def _call_post(self, **data):
        """Protect from the Sprout being updated (error 502,503)"""
        result = wait_for(
            lambda: self._post(**data),
            num_sec=60,
            fail_condition=lambda r: r.status_code in {502, 503},
            delay=2,
        )
        return result.out.json()

    def call_method(self, name, *args, **kwargs):
        req_data = {
            "method": name,
            "args": args,
            "kwargs": kwargs,
        }
        if self._auth is not None:
            req_data["auth"] = self._auth
        result = self._call_post(**req_data)
        try:
            if result["status"] == "exception":
                raise SproutException(
                    "Exception {} raised! {}".format(
                        result["result"]["class"], result["result"]["message"]))
            elif result["status"] == "autherror":
                raise AuthException(
                    "Authentication failed! {}".format(result["result"]["message"]))
            else:
                return result["result"]
        except KeyError:
            raise Exception("Malformed response from Sprout!")

    def __getattr__(self, attr):
        return APIMethodCall(self, attr)

    @classmethod
    def from_config(cls, **kwargs):
        host = env.get("sprout", {}).get("hostname", "localhost")
        port = env.get("sprout", {}).get("port", 8000)
        user = os.environ.get("SPROUT_USER", credentials.get("sprout", {}).get("username", None))
        password = os.environ.get(
            "SPROUT_PASSWORD", credentials.get("sprout", {}).get("password", None))
        if user and password:
            auth = user, password
        else:
            auth = None
        return cls(host=host, port=port, auth=auth, **kwargs)


class SproutAppliance(Appliance):
    """Appliance provisioned through sprout

    Overrides the `destroy` method to get rid of the appliance properly.
    """

    def __init__(self, sprout_id, **kwargs):
        self.sprout_id = sprout_id
        # Check that it exists in sprout
        app_data = self.sprout_client.appliance_data(sprout_id)
        # Get data to pass into Appliance obj
        kwargs['provider_name'] = app_data['provider']
        kwargs['vm_name'] = app_data['name']
        super(SproutAppliance, self).__init__(**kwargs)

    def destroy(self):
        """Kill through sprout"""
        self.sprout_client.destroy_appliance(self.sprout_id)

    @lazycache
    def sprout_client(self):
        return SproutClient.from_config()


def provision_appliance(version, vm_name=None, browser_steal=False, **kwargs):
    """Provision a single configured or unconfigured appliance using sprout

    Args:
        version: Version to provision; see 'sprout.provision_appliances'
        vm_name: Name of the VM
        browser_steal: Set to True if browser session should be replaced when used
        kwargs: Kwargs to be passed to 'sprout_provision_appliances'; see for more info
                (except 'count' and 'vm_names')
    """
    kwargs['count'] = 1
    kwargs['vm_names'] = [vm_name] if vm_name is not None else None
    app = provision_appliances(version, **kwargs)[0]
    app.ipapp.browser_steal = browser_steal
    return app


def provision_appliance_set(version, evm_names, configure_kwargs=None, primary_browser_steal=True,
                            **kwargs):
    """Provision a configured appliance set using sprout

    Primary appliance will have internal database enabled and secondary appliances
    will be connected to the database on primary.

    Args:
        evm_names: EVM server names to be used (not VM names)
                   Number of appliances in the set depends on the number of passed evm_names
        version: Version of appliances to provision; see 'sprout.provision_appliances'
        configure_kwargs: Configuration kwargs (passed into .configure() of each appliance)
        primary_browser_steal: If True, browser session will be replaced when primary appliance
                               is used
        kwargs: Kwargs to be passed to 'sprout.provision_appliances'; see it for more info
                (except 'preconfigured' and 'count')
    """
    kwargs['preconfigured'] = False
    kwargs['count'] = len(evm_names)
    appliances = provision_appliances(version, **kwargs)
    appliances[0].ipapp.primary_browser_steal = primary_browser_steal
    appliance_set = ApplianceSet(appliances[0], appliances[1:])
    logger.info('Configuring appliances')
    configure_kwargs = configure_kwargs or dict()
    appliance_set.primary.configure(name_to_set=evm_names[0], **configure_kwargs)
    for i, appliance in enumerate(appliance_set.secondary):
        appliance.configure(db_address=appliance_set.primary.address,
                            name_to_set=evm_names[i + 1],
                            **configure_kwargs)
    logger.info('Done - configuring appliances')
    return appliance_set


def provision_appliances(version, count=1, lease_time=60, date=None, provider=None,
                         preconfigured=True, vm_names=None, vm_name_prefix=None):
    """Provision configured or unconfigured appliances using sprout

    Args:
        version: Version to provision
                 To get latest version from a specific stream, pass 'major.minor'
                 E.g.: To get latest 5.2.z, pass '5.2' as version
                       To get a 5.3.0.15, you would pass '5.3.0.15'
                       For upstream, use version.LATEST
        count: Size of the provisioned appliance pool (number of provisioned appliances)
        lease_time: Time, in minutes, until the appliance(s) expire
        date: Appliance template creation date - some versions have multiple of these
              (will use latest by default; format: YYYY-MM-DD)
        provider: Provider key of the provider to use (best left unset for auto-pick)
        preconfigured: If True, will preconfigure the appliance(s) with default preset (internal DB)
        vm_names: List of names used to rename each of the VMs after provisioning
        vm_prefix: A prefix used to rename each of the VMs after provisioning

    Note:
        VM names take priority over vm prefix.

    Warning:
        Sprout has to be pre-configured in env yaml for this to work.

    Returns:
        List of provisioned appliances (Appliance objs).
    """
    logger.info('Provisioning {} appliance(s) using sprout'.format(count))
    sprout_cli = SproutClient.from_config()
    group = get_stream(version)
    # If the passed version is not a specific version
    if version not in sprout_cli.available_cfme_versions(preconfigured):
        # Assume we want latest of that stream (sprout does that when we pass None)
        if version is not None:
            # Unless we specifically asked for latest, we log it (hopefully it's 'major.minor')
            logger.info("Version {} not found, assuming latest from stream {}"
                        .format(version, group))
            version = None

    pool_id = sprout_cli.request_appliances(
        group=group, count=count, lease_time=lease_time, version=version,
        date=date, provider=provider, preconfigured=preconfigured)
    # Wait until appliances are provisioned and have IPs
    wait_for(
        func=lambda: sprout_cli.request_check(pool_id)['fulfilled'],
        num_sec=1200,
        message="provision {} appliance(s) (pool #{})".format(count, pool_id))
    apps_serialized = sprout_cli.request_check(pool_id)['appliances']

    # After provisioning, rename VMs (if needed)
    if vm_names is not None:
        if count != len(vm_names):
            raise SproutException('Incorrect number of VM names passed; {} names for {} VMs'
                                  .format(len(vm_names), count))
    # Rename VMs using prefix + desc + date + pool_id + num in pool if we got a prefix
    elif vm_name_prefix is not None:
        # Stream name for upstream, else we remove dots from version and use that
        desc = group if group == get_stream(version.LATEST) else version.replace('.', '')
        # Remove dashes from iso-formatted date
        date = apps_serialized[0]['template_build_date'].replace('-', '')
        vm_names = []
        for i in range(count):
            new_vm_name = "{}_{}_{}_{}_{}".format(vm_name_prefix, desc, date, pool_id, i + 1)
            vm_names.append(new_vm_name)

    if vm_names is not None:
        logger.info('Renaming {} appliances to {} respectively'.format(len(vm_names), vm_names))
        task_ids = []
        for i, app in enumerate(apps_serialized):
            task_ids.append(sprout_cli.rename_appliance(app['id'], vm_names[i]))
        for task_id in task_ids:
            wait_for(
                func=lambda: sprout_cli.task_finished(task_id),
                num_sec=300,
                message="rename appliance with id ".format(app['id']))

    apps = []
    for app in apps_serialized:
        s_app = SproutAppliance(app['id'])
        apps.append(s_app)

    return apps

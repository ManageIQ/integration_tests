from os import path
from urllib.error import URLError

import attr
from cached_property import cached_property
from varmeth import variable
from wrapanapi.systems.container import Openshift

from cfme.common import Taggable
from cfme.common.provider import DefaultEndpoint
from cfme.common.vm_console import ConsoleMixin
from cfme.containers.provider import ContainersProvider
from cfme.containers.provider import ContainersProviderDefaultEndpoint
from cfme.containers.provider import ContainersProviderEndpointsForm
from cfme.control.explorer.alert_profiles import NodeAlertProfile
from cfme.control.explorer.alert_profiles import ProviderAlertProfile
from cfme.utils import ssh
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.ocp_cli import OcpCli
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


class CustomAttribute:
    def __init__(self, name, value, field_type=None, href=None):
        self.name = name
        self.value = value
        self.field_type = field_type
        self.href = href


class OpenshiftDefaultEndpoint(ContainersProviderDefaultEndpoint):
    """Represents Openshift default endpoint"""

    @staticmethod
    def get_ca_cert(connection_info):
        """Getting OpenShift's certificate from the master machine.
        Args:
            connection_info (dict): username, password and hostname for OCP
        returns:
            certificate's content.
        """

        with ssh.SSHClient(**connection_info) as provider_ssh:
            _, stdout, _ = provider_ssh.exec_command("cat /etc/origin/master/ca.crt")
            return str("".join(stdout.readlines()))


class ServiceBasedEndpoint(DefaultEndpoint):

    @property
    def view_value_mapping(self):
        out = {'hostname': self.hostname,
               'api_port': self.api_port,
               'sec_protocol': self.sec_protocol}

        if out['sec_protocol'] and self.sec_protocol.lower() == 'ssl trusting custom ca':
            out['trusted_ca_certificates'] = OpenshiftDefaultEndpoint.get_ca_cert(
                {"username": self.ssh_creds.principal,
                 "password": self.ssh_creds.secret,
                 "hostname": self.master_hostname})

        return out


class VirtualizationEndpoint(ServiceBasedEndpoint):
    """Represents virtualization Endpoint"""
    name = 'virtualization'

    @property
    def view_value_mapping(self):
        # values like host, port are taken from Default endpoint
        # and not editable in Virtualization endpoint, only token can be added
        return {'kubevirt_token': self.token}


class MetricsEndpoint(ServiceBasedEndpoint):
    """Represents metrics Endpoint"""
    name = 'metrics'


class AlertsEndpoint(ServiceBasedEndpoint):
    """Represents Alerts Endpoint"""
    name = 'alerts'


@attr.s(eq=False)
class OpenshiftProvider(ContainersProvider, ConsoleMixin, Taggable):

    num_route = ['num_route']
    STATS_TO_MATCH = ContainersProvider.STATS_TO_MATCH + num_route
    type_name = "openshift"
    mgmt_class = Openshift
    db_types = ["Openshift::ContainerManager"]
    endpoints_form = ContainersProviderEndpointsForm
    settings_key = 'ems_openshift'
    ems_pretty_name = 'OpenShift Container Platform'

    http_proxy = attr.ib(default=None)
    adv_http = attr.ib(default=None)
    adv_https = attr.ib(default=None)
    no_proxy = attr.ib(default=None)
    image_repo = attr.ib(default=None)
    image_reg = attr.ib(default=None)
    image_tag = attr.ib(default=None)
    cve_loc = attr.ib(default=None)
    virt_type = attr.ib(default=None)
    provider = attr.ib(default=None)

    def create(self, **kwargs):

        # Enable alerts collection before adding the provider to avoid missing active
        # alert after adding the provider
        # For more info: https://bugzilla.redhat.com/show_bug.cgi?id=1514950
        if getattr(self, "alerts_type") == "Prometheus":
            alert_profiles = self.appliance.collections.alert_profiles
            provider_profile = alert_profiles.instantiate(ProviderAlertProfile,
                                                          "Prometheus Provider Profile")
            node_profile = alert_profiles.instantiate(NodeAlertProfile,
                                                      "Prometheus node Profile")
            for profile in [provider_profile, node_profile]:
                profile.assign_to("The Enterprise")

        super().create(**kwargs)

    @cached_property
    def cli(self):
        return OcpCli(self)

    def href(self):
        return self.appliance.rest_api.collections.providers\
            .find_by(name=self.name).resources[0].href

    @property
    def view_value_mapping(self):

        mapping = {'name': self.name,
                   'zone': self.zone,
                   'prov_type': ('OpenShift Container Platform' if self.appliance.is_downstream
                                 else 'OpenShift')}

        mapping['metrics_type'] = self.metrics_type
        mapping['alerts_type'] = self.alerts_type
        mapping['proxy'] = {
            'http_proxy': self.http_proxy
        }
        mapping['advanced'] = {
            'adv_http': self.adv_http,
            'adv_https': self.adv_https,
            'no_proxy': self.no_proxy,
            'image_repo': self.image_repo,
            'image_reg': self.image_reg,
            'image_tag': self.image_tag,
            'cve_loc': self.cve_loc
        }
        mapping['virt_type'] = self.virt_type

        return mapping

    @property
    def is_provider_enabled(self):
        return self.appliance.rest_api.collections.providers.get(name=self.name).enabled

    @variable(alias='db')
    def num_route(self):
        return self._num_db_generic('container_routes')

    @num_route.variant('ui')
    def num_route_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of('Container Routes'))

    @variable(alias='db')
    def num_template(self):
        return self._num_db_generic('container_templates')

    @num_template.variant('ui')
    def num_template_ui(self):
        view = navigate_to(self, "Details")
        return int(view.entities.summary("Relationships").get_text_of("Container Templates"))

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):
        appliance = appliance or cls.appliance
        endpoints = {}
        token_creds = cls.process_credential_yaml_key(prov_config['credentials'], cred_type='token')

        master_hostname = prov_config['endpoints']['default'].hostname
        ssh_creds = cls.process_credential_yaml_key(prov_config['ssh_creds'])

        for endp in prov_config['endpoints']:
            # Add ssh_password for each endpoint, so get_ca_cert
            # will be able to get SSL cert form OCP for each endpoint
            setattr(prov_config['endpoints'][endp], "master_hostname", master_hostname)
            setattr(prov_config['endpoints'][endp], "ssh_creds", ssh_creds)

            if OpenshiftDefaultEndpoint.name == endp:
                prov_config['endpoints'][endp]['token'] = token_creds.token
                endpoints[endp] = OpenshiftDefaultEndpoint(**prov_config['endpoints'][endp])
            elif MetricsEndpoint.name == endp:
                endpoints[endp] = MetricsEndpoint(**prov_config['endpoints'][endp])
            elif AlertsEndpoint.name == endp:
                endpoints[endp] = AlertsEndpoint(**prov_config['endpoints'][endp])
            else:
                raise Exception(f'Unsupported endpoint type "{endp}".')

        settings = prov_config.get('settings', {})
        advanced = settings.get('advanced', {})
        http_proxy = settings.get('proxy', {}).get('http_proxy')
        adv_http, adv_https, no_proxy, image_repo, image_reg, image_tag, cve_loc = [
            advanced.get(field) for field in
            ('adv_http', 'adv_https', 'no_proxy',
             'image_repo', 'image_reg', 'image_tag', 'cve_loc')
        ]

        return appliance.collections.containers_providers.instantiate(
            prov_class=cls,
            name=prov_config.get('name'),
            key=prov_key,
            zone=prov_config.get('server_zone'),
            metrics_type=prov_config.get('metrics_type'),
            alerts_type=prov_config.get('alerts_type'),
            endpoints=endpoints,
            provider_data=prov_config,
            http_proxy=http_proxy,
            adv_http=adv_http,
            adv_https=adv_https,
            no_proxy=no_proxy,
            image_repo=image_repo,
            image_reg=image_reg,
            image_tag=image_tag,
            cve_loc=cve_loc,
            virt_type=prov_config.get('virt_type'))

    def custom_attributes(self):
        """returns custom attributes"""
        response = self.appliance.rest_api.get(
            path.join(self.href(), 'custom_attributes'))
        out = []
        for attr_dict in response['resources']:
            attr = self.appliance.rest_api.get(attr_dict['href'])
            out.append(
                CustomAttribute(
                    attr['name'], attr['value'],
                    (attr['field_type'] if 'field_type' in attr else None),
                    attr_dict['href']
                )
            )
        return out

    def add_custom_attributes(self, *custom_attributes):
        """Adding static custom attributes to provider.
        Args:
            custom_attributes: The custom attributes to add.
        returns: response.
        """
        if not custom_attributes:
            raise TypeError('{} takes at least 1 argument.'
                            .format(self.add_custom_attributes.__name__))
        for c_attr in custom_attributes:
            if not isinstance(c_attr, CustomAttribute):
                raise TypeError('All arguments should be of type {}. ({} != {})'
                                .format(CustomAttribute, type(c_attr), CustomAttribute))
        payload = {
            "action": "add",
            "resources": [{
                "name": ca.name,
                "value": str(ca.value)
            } for ca in custom_attributes]}
        for i, fld_tp in enumerate([c_attr.field_type for c_attr in custom_attributes]):
            if fld_tp:
                payload['resources'][i]['field_type'] = fld_tp
        return self.appliance.rest_api.post(
            path.join(self.href(), 'custom_attributes'), **payload)

    def edit_custom_attributes(self, *custom_attributes):
        """Editing static custom attributes in provider.
        Args:
            custom_attributes: The custom attributes to edit.
        returns: response.
        """
        if not custom_attributes:
            raise TypeError('{} takes at least 1 argument.'
                            .format(self.edit_custom_attributes.__name__))
        for c_attr in custom_attributes:
            if not isinstance(c_attr, CustomAttribute):
                raise TypeError('All arguments should be of type {}. ({} != {})'
                                .format(CustomAttribute, type(c_attr), CustomAttribute))
        attribs = self.custom_attributes()
        payload = {
            "action": "edit",
            "resources": [{
                "href": [c_attr for c_attr in attribs if c_attr.name == ca.name][-1].href,
                "value": ca.value
            } for ca in custom_attributes]}
        return self.appliance.rest_api.post(
            path.join(self.href(), 'custom_attributes'), **payload)

    def delete_custom_attributes(self, *custom_attributes):
        """Deleting static custom attributes from provider.

        Args:
            custom_attributes: The custom attributes to delete.
                               (Could be also names (str))
        Returns: response.
        """
        names = []
        for c_attr in custom_attributes:
            attr_type = type(c_attr)
            if attr_type in (str, CustomAttribute):
                names.append(c_attr if attr_type is str else c_attr.name)
            else:
                raise TypeError('Type of arguments should be either'
                                'str or CustomAttribute. ({} not in [str, CustomAttribute])'
                                .format(type(c_attr)))
        attribs = self.custom_attributes()
        if not names:
            names = [attrib.name for attrib in attribs]
        payload = {
            "action": "delete",
            "resources": [{
                "href": attrib.href,
            } for attrib in attribs if attrib.name in names]}
        return self.appliance.rest_api.post(
            path.join(self.href(), 'custom_attributes'), **payload)

    def sync_ssl_certificate(self):
        """ fixture which sync SSL certificate between CFME and OCP
        Args:
            provider (OpenShiftProvider):  OCP system to sync cert from
            appliance (IPAppliance): CFME appliance to sync cert with
        Returns:
             None
        """

        def _copy_certificate():
            is_succeed = True
            try:
                # Copy certificate to the appliance
                provider_ssh.get_file("/etc/origin/master/ca.crt", "/tmp/ca.crt")
                appliance_ssh.put_file("/tmp/ca.crt",
                                       "/etc/pki/ca-trust/source/anchors/{crt}".format(
                                           crt=cert_name))
            except URLError:
                logger.debug("Fail to deploy certificate from Openshift to CFME")
                is_succeed = False
            finally:
                return is_succeed

        provider_ssh = self.cli.ssh_client
        appliance_ssh = self.appliance.ssh_client()

        # Connection to the applince in case of dead connection
        if not appliance_ssh.connected:
            appliance_ssh.connect()

        # Checking if SSL is already configured between appliance and provider,
        # by send a HTTPS request (using SSL) from the appliance to the provider,
        # hiding the output and sending back the return code of the action
        _, stdout, stderr = \
            appliance_ssh.exec_command(
                "curl https://{provider}:8443 -sS > /dev/null;echo $?".format(
                    provider=self.provider_data.hostname))

        # Do in case of failure (return code is not 0)
        if stdout.readline().replace('\n', "") != "0":
            cert_name = "{provider_name}.ca.crt".format(
                provider_name=self.provider_data.hostname.split(".")[0])
            wait_for(_copy_certificate, num_sec=600, delay=30,
                     message="Copy certificate from OCP to CFME")
            appliance_ssh.exec_command("update-ca-trust")

            # restarting evemserverd to apply the new SSL certificate
            self.appliance.evmserverd.restart()
            self.appliance.evmserverd.wait_for_running()
            self.appliance.wait_for_web_ui()

    def get_system_id(self):
        mgmt_systems_tbl = self.appliance.db.client['ext_management_systems']
        return self.appliance.db.client.session.query(mgmt_systems_tbl).filter(
            mgmt_systems_tbl.name == self.name).first().id

    def get_metrics(self, **kwargs):
        """"Returns all the collected metrics for this provider

        Args:
            filters: list of dicts with column name and values
                        e.g [{"resource_type": "Container"}, {"parent_ems_id": "1L"}]
            metrics_table: Metrics table name, there are few metrics table
                        e.g metrics, metric_rollups, etc
        Returns:
            Query object with the relevant records
        """

        filters = kwargs.get("filters", {})
        metrics_table = kwargs.get("metrics_table", "metric_rollups")

        metrics_tbl = self.appliance.db.client[metrics_table]

        mgmt_system_id = self.get_system_id()

        logger.info("Getting metrics for {name} (parent_ems_id == {id})".format(
            name=self.name, id=mgmt_system_id))

        if filters:
            logger.info(f"Filtering by: {filters}")

        filters["parent_ems_id"] = mgmt_system_id
        return self.appliance.db.client.session.query(metrics_tbl).filter_by(**filters)

    def wait_for_collected_metrics(self, timeout="50m", table_name="metrics"):
        """Check the db if gathering collection data

        Args:
            timeout: timeout in minutes
        Return:
            Bool: is collected metrics count is greater than 0
        """

        def is_collected():
            metrics_count = self.get_metrics(table=table_name).count()
            logger.info(f"Current metrics found count is {metrics_count}")
            return metrics_count > 0

        logger.info("Monitoring DB for metrics collection")

        result = True
        try:
            wait_for(is_collected, timeout=timeout, delay=30)
        except TimedOutError:
            logger.error(
                "Timeout exceeded, No metrics found in MIQ DB for the provider \"{name}\"".format(
                    name=self.name))
            result = False
        finally:
            return result

    def pause(self):
        """ Pause the OCP provider.

            Returns:
                API response.
        """
        return self.appliance.rest_api.collections.providers.get(name=self.name).action.pause()

    def resume(self):
        """ Resume the OCP provider.

            Returns:
                API response.
        """
        return self.appliance.rest_api.collections.providers.get(name=self.name).action.resume()

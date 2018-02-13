from cached_property import cached_property
from os import path

from wrapanapi.containers.providers.rhopenshift import Openshift

from . import ContainersProvider

from cfme.containers.provider import (
    ContainersProviderDefaultEndpoint, ContainersProviderEndpointsForm
)

from cfme.common.provider import DefaultEndpoint
from cfme.utils.ocp_cli import OcpCli
from cfme.utils.varmeth import variable
from cfme.utils import version, ssh


class CustomAttribute(object):
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


class HawkularEndpoint(DefaultEndpoint):
    """Represents Hawkular Endpoint"""
    name = 'hawkular'

    @property
    def view_value_mapping(self):
        out = {
            'hostname': self.hostname,
            'api_port': self.api_port,
            'sec_protocol': self.sec_protocol
        }

        if out['sec_protocol'] and self.sec_protocol.lower() == 'ssl trusting custom ca':
            out['trusted_ca_certificates'] = OpenshiftDefaultEndpoint.get_ca_cert(
                {"username": self.ssh_creds.principal,
                 "password": self.ssh_creds.secret,
                 "hostname": self.master_hostname})

        return out


class AlertsEndpoint(DefaultEndpoint):
    """Represents Alerts Endpoint"""
    name = 'alerts'

    @property
    def view_value_mapping(self):

        out = {}

        out['hostname'] = version.pick({
            version.LOWEST: None,
            '5.9': self.hostname})
        out['api_port'] = version.pick({
            version.LOWEST: None,
            '5.9': self.api_port})
        out['sec_protocol'] = version.pick({
            version.LOWEST: None,
            '5.9': self.sec_protocol})

        if out['sec_protocol'] and self.sec_protocol.lower() == 'ssl trusting custom ca':
            out['trusted_ca_certificates'] = OpenshiftDefaultEndpoint.get_ca_cert(
                {"username": self.ssh_creds.principal,
                 "password": self.ssh_creds.secret,
                 "hostname": self.master_hostname})

        return out


class OpenshiftProvider(ContainersProvider):
    num_route = ['num_route']
    STATS_TO_MATCH = ContainersProvider.STATS_TO_MATCH + num_route
    type_name = "openshift"
    mgmt_class = Openshift
    db_types = ["Openshift::ContainerManager"]
    endpoints_form = ContainersProviderEndpointsForm

    def __init__(
            self,
            name=None,
            key=None,
            zone=None,
            metrics_type=None,
            alerts_type=None,
            provider_data=None,
            endpoints=None,
            appliance=None,
            http_proxy=None,
            adv_http=None,
            adv_https=None,
            no_proxy=None,
            image_repo=None,
            image_reg=None,
            image_tag=None,
            cve_loc=None):

        self.http_proxy = http_proxy
        self.adv_http = adv_http
        self.adv_https = adv_https
        self.no_proxy = no_proxy
        self.image_repo = image_repo
        self.image_reg = image_reg
        self.image_tag = image_tag
        self.cve_loc = cve_loc

        super(OpenshiftProvider, self).__init__(
            name=name,
            key=key,
            zone=zone,
            metrics_type=metrics_type,
            provider_data=provider_data,
            alerts_type=alerts_type,
            endpoints=endpoints,
            appliance=appliance)

    @cached_property
    def cli(self):
        return OcpCli(self)

    def href(self):
        return self.appliance.rest_api.collections.providers\
            .find_by(name=self.name).resources[0].href

    @property
    def view_value_mapping(self):

        mapping = {
            'name': self.name,
            'zone': self.zone
        }

        mapping['prov_type'] = (
            'OpenShift Container Platform'
            if self.appliance.is_downstream
            else 'OpenShift')

        if self.appliance.version >= '5.9':
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
        else:
            mapping['metrics_type'] = None
            mapping['alerts_type'] = None
            mapping['proxy'] = None
            mapping['advanced'] = None

        return mapping

    @variable(alias='db')
    def num_route(self):
        return self._num_db_generic('container_routes')

    @num_route.variant('ui')
    def num_route_ui(self):
        return int(self.get_detail("Relationships", "Routes"))

    @variable(alias='db')
    def num_template(self):
        return self._num_db_generic('container_templates')

    @num_template.variant('ui')
    def num_template_ui(self):
        return int(self.get_detail("Relationships", "Container Templates"))

    @classmethod
    def from_config(cls, prov_config, prov_key, appliance=None):

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
            elif HawkularEndpoint.name == endp:
                endpoints[endp] = HawkularEndpoint(**prov_config['endpoints'][endp])
            elif AlertsEndpoint.name == endp:
                endpoints[endp] = AlertsEndpoint(**prov_config['endpoints'][endp])
            # TODO Add Prometheus and logic for having to select or the other based on metrcis_type
            else:
                raise Exception('Unsupported endpoint type "{}".'.format(endp))

        settings = prov_config.get('settings', {})
        advanced = settings.get('advanced', {})
        http_proxy = settings.get('proxy', {}).get('http_proxy')
        adv_http, adv_https, no_proxy, image_repo, image_reg, image_tag, cve_loc = [
            advanced.get(field) for field in
            ('adv_http', 'adv_https', 'no_proxy',
             'image_repo', 'image_reg', 'image_tag', 'cve_loc')
        ]

        return cls(
            name=prov_config.get('name'),
            key=prov_key,
            zone=prov_config.get('server_zone'),
            metrics_type=prov_config.get('metrics_type'),
            alerts_type=prov_config.get('alerts_type'),
            endpoints=endpoints,
            provider_data=prov_config,
            appliance=appliance,
            http_proxy=http_proxy,
            adv_http=adv_http,
            adv_https=adv_https,
            no_proxy=no_proxy,
            image_repo=image_repo,
            image_reg=image_reg,
            image_tag=image_tag,
            cve_loc=cve_loc
        )

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
        for attr in custom_attributes:
            if not isinstance(attr, CustomAttribute):
                raise TypeError('All arguments should be of type {}. ({} != {})'
                                .format(CustomAttribute, type(attr), CustomAttribute))
        payload = {
            "action": "add",
            "resources": [{
                "name": ca.name,
                "value": str(ca.value)
            } for ca in custom_attributes]}
        for i, fld_tp in enumerate([attr.field_type for attr in custom_attributes]):
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
        for attr in custom_attributes:
            if not isinstance(attr, CustomAttribute):
                raise TypeError('All arguments should be of type {}. ({} != {})'
                                .format(CustomAttribute, type(attr), CustomAttribute))
        attribs = self.custom_attributes()
        payload = {
            "action": "edit",
            "resources": [{
                "href": filter(lambda attr: attr.name == ca.name, attribs)[-1].href,
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
        for attr in custom_attributes:
            attr_type = type(attr)
            if attr_type in (str, CustomAttribute):
                names.append(attr if attr_type is str else attr.name)
            else:
                raise TypeError('Type of arguments should be either'
                                'str or CustomAttribute. ({} not in [str, CustomAttribute])'
                                .format(type(attr)))
        attribs = self.custom_attributes()
        if not names:
            names = [attr.name for attr in attribs]
        payload = {
            "action": "delete",
            "resources": [{
                "href": attr.href,
            } for attr in attribs if attr.name in names]}
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

            # Copy certificate to the appliance
            provider_ssh.get_file("/etc/origin/master/ca.crt", "/tmp/ca.crt")
            appliance_ssh.put_file("/tmp/ca.crt",
                                   "/etc/pki/ca-trust/source/anchors/{crt}".format(crt=cert_name))

            appliance_ssh.exec_command("update-ca-trust")

            # restarting evemserverd to apply the new SSL certificate
            self.appliance.restart_evm_service()
            self.appliance.wait_for_evm_service()
            self.appliance.wait_for_web_ui()

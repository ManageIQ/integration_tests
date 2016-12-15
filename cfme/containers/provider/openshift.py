from . import ContainersProvider
from utils.varmeth import variable
from os import path
from mgmtsystem.openshift import Openshift


class CustomAttribute(object):
    def __init__(self, name, value, field_type=None, href=None):
        self.name = name
        self.value = value
        self.field_type = field_type
        self.href = href


@ContainersProvider.add_provider_type
class OpenshiftProvider(ContainersProvider):
    num_route = ['num_route']
    STATS_TO_MATCH = ContainersProvider.STATS_TO_MATCH + num_route
    type_name = "openshift"
    mgmt_class = Openshift

    def __init__(self, name=None, credentials=None, key=None,
                 zone=None, hostname=None, port=None, provider_data=None):
        super(OpenshiftProvider, self).__init__(
            name=name, credentials=credentials, key=key, zone=zone, hostname=hostname, port=port,
            provider_data=provider_data)

    def create(self, validate_credentials=True, **kwargs):
        # Workaround - randomly fails on 5.5.0.8 with no validation
        # probably a js wait issue, not reproducible manually
        super(OpenshiftProvider, self).create(validate_credentials=validate_credentials, **kwargs)

    def _href(self):
        return self.appliance.rest_api.collections.providers\
            .find_by(name=self.name).resources[0].href

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'OpenShift',
                'hostname_text': kwargs.get('hostname'),
                'port_text': kwargs.get('port'),
                'zone_select': kwargs.get('zone')}

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

    @staticmethod
    def from_config(prov_config, prov_key):
        token_creds = OpenshiftProvider.process_credential_yaml_key(
            prov_config['credentials'], cred_type='token')
        return OpenshiftProvider(
            name=prov_config['name'],
            credentials={'token': token_creds},
            key=prov_key,
            zone=prov_config['server_zone'],
            hostname=prov_config.get('hostname', None) or prov_config['ip_address'],
            port=prov_config['port'],
            provider_data=prov_config)

    def custom_attributes(self):
        """returns custom attributes"""
        response = self.appliance.rest_api.get(
            path.join(self._href(), 'custom_attributes'))
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
            path.join(self._href(), 'custom_attributes'), **payload)

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
            path.join(self._href(), 'custom_attributes'), **payload)

    def delete_custom_attributes(self, *names):
        """Deleting static custom attributes from provider.
        Args:
            names: The names of the custom attributes to delete.
        returns: response.
        """
        for name in names:
            if type(name) is not str:
                raise TypeError('Type of names should be {}. ({} != {})'
                                .format(str, type(name), str))
        attribs = self.custom_attributes()
        if not names:
            names = [attr.name for attr in attribs]
        payload = {
            "action": "delete",
            "resources": [{
                "href": attr.href,
            } for attr in attribs if attr.name in names]}
        return self.appliance.rest_api.post(
            path.join(self._href(), 'custom_attributes'), **payload)

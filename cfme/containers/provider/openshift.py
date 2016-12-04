from . import ContainersProvider
from utils.varmeth import variable
from mgmtsystem.openshift import Openshift
from os import path
from types import NoneType


@ContainersProvider.add_provider_type
class OpenshiftProvider(ContainersProvider):
    STATS_TO_MATCH = ContainersProvider.STATS_TO_MATCH + ['num_route']
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
        """returns custom attributes in {name: {data}}"""
        response = self.appliance.rest_api.get(
            path.join(self._href(), 'custom_attributes'))
        out = {}
        for attr_dict in response['resources']:
            attr = self.appliance.rest_api.get(attr_dict['href'])
            out[attr['name']] = attr
        return out

    def add_custom_attributes(self, names, values, field_types):
        """Adding static custom attributes to provider.
        Args:
            names: List of names of the attributes
            value: List of values of the attributes
            field_type: List of field types of the attributes
                (field type could be None)
        """
        for arg in (names, values, field_types):
            if type(arg) not in (tuple, list):
                raise TypeError('add_custom_attributes(): '
                    'Argument types should be list or tuple. got: {} = {}'
                    .format(repr(arg), type(arg)))
            elif not len(names) == len(arg):
                raise Exception('add_custom_attributes(): '
                    'All arguments should have the same length.')
        payload = {
            "action": "add",
            "resources": [{
                "name": name,
                "value": str(value)
            } for name, value in zip(names, values)]}
        for i, fld_tp in enumerate(field_types):
            if fld_tp:
                payload['resources'][i]['field_type'] = fld_tp
        self.appliance.rest_api.post(
            path.join(self._href(), 'custom_attributes'), **payload)

    def edit_custom_attributes(self, names, values):
        """Editing static custom attributes in provider.
        Args:
            names: List of names of the attributes to edit
            values: List of the new values to set
        """
        for arg in (names, values):
            if type(arg) not in (tuple, list):
                raise TypeError('add_custom_attributes(): '
                    'Argument types should be list or tuple. got: {} = {}'
                    .format(repr(arg), type(arg)))
            elif not len(names) == len(arg):
                raise Exception('add_custom_attributes(): '
                    'All arguments should have the same length.')
        attribs = self.custom_attributes()
        payload = {
            "action": "edit",
            "resources": [{
                "href": attribs[name]['href'],
                "value": value
            } for name, value in zip(names, values)]}
        self.appliance.rest_api.post(path.join(self._href(), 'custom_attributes'), **payload)

    def delete_custom_attributes(self, names=None):
        """Deleting static custom attributes from provider.
        Args:
            names: List of names of the attributes to delete
                if names is None: delete all
        """
        if type(names) not in (list, tuple, NoneType):
            raise TypeError('delete_custom_attributes(names={}):'
                            ' names type should be list, tuple or NoneType. got {}'
                            .format(names, type(names)))
        attribs = self.custom_attributes()
        if not names:
            names = attribs.keys()
        payload = {
            "action": "delete",
            "resources": [{
                "href": attr['href'],
            } for name, attr in attribs.items() if name in names]}
        self.appliance.rest_api.post(
            path.join(self._href(), 'custom_attributes'), **payload)

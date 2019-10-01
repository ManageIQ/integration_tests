from copy import deepcopy

import attr
from cached_property import cached_property
from keycloak import KeycloakAdmin

from cfme.configure.configuration.server_settings import AmazonAuthenticationView
from cfme.configure.configuration.server_settings import ExternalAuthenticationView
from cfme.configure.configuration.server_settings import LdapAuthenticationView
from cfme.configure.configuration.server_settings import LdapsAuthenticationView
from cfme.configure.configuration.server_settings import USER_TYPES
from cfme.exceptions import UnknownProviderType
from cfme.utils.conf import auth_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger

auth_prov_data = auth_data.get("auth_providers", {})  # setup on module import

LDAP_PORT = 389
LDAPS_PORT = 636


def auth_provider_types():
    """Fetch the registered classes from entry_points manageiq.auth_provider_categories"""
    from pkg_resources import iter_entry_points
    return {
        ep.name: ep.resolve()
        for ep in iter_entry_points('manageiq.auth_provider_types')
    }


def auth_class_from_type(auth_prov_type):
    """Using the registered auth provider classes, fetch a class by its type key

    Args:
        auth_prov_type: string key matching a registered type in entry_points

    Raises:
        UnknownProviderType when the given type isn't registered in entry_points
    """
    try:
        return auth_provider_types()[auth_prov_type]
    except KeyError:
        raise UnknownProviderType('Unknown auth provider type: {}'.format(auth_prov_type))


def get_auth_crud(auth_prov_key):
    """Get a BaseAuthProvider derived class with the auth_data.yaml configuration for the key

    Args:
        auth_prov_key: string key matching one in conf/auth_data.yaml 'auth_providers' dict
    Raises:
        ValueError if the yaml type for given key doesn't match auth_type on fetched class
    """
    auth_prov_config = auth_prov_data[auth_prov_key]
    klass = auth_class_from_type(auth_prov_config.get('type'))
    if auth_prov_config.get('type') != klass.auth_type:
        raise ValueError('{} must have type "{}"'.format(klass.__name__, klass.auth_type))
    return klass.from_config(auth_prov_config, auth_prov_key)


def auth_user_data(provider_key, user_type):
    """Grab user data attrdict from auth provider's user data in yaml

    Expected formatting of yaml containing user data:
        test_users:
        -
          username: ldapuser2
          password: mysecretpassworddontguess
          fullname: Ldap User2
          groups:
            - customgroup1
          providers:
            - freeipa01
          user_types:
            - uid

    Only include user data for users where the user_type matches that under test

    Assert the data isn't empty, and skip the test if so
    """
    try:
        data = [user
                for user in auth_data.test_data.test_users
                if provider_key in user.providers and user_type in user.user_types]
        assert data
    except (KeyError, AttributeError, AssertionError):
        logger.warning('Exception fetching auth_user_data from key %s and type %s',
                       provider_key, user_type)
        return None
    return data


@attr.s
class BaseAuthProvider(object):
    """Base class for authentication provider objects    """
    auth_type = None
    view_class = None
    key = attr.ib()

    @cached_property
    def data(self):
        return auth_data.auth_providers.get(self.key)

    @cached_property
    def user_data(self):
        """Pull users from auth_data if provider key is in items providers list"""
        return [user for user in auth_data.test_data.test_users if self.key in user.providers]

    @classmethod
    def from_config(cls, prov_config, prov_key):
        """Returns an object using the passed yaml config
        Sets defaults for yaml configured objects separate from attr.ib definitions
        """
        config_copy = deepcopy(prov_config)  # copy to avoid modifying passed attrdict
        config_copy.update(credentials[config_copy.get('credentials')])
        class_params = {k: v
                        for k, v in config_copy.items()
                        if k in attr.fields_dict(cls)}
        return cls(key=prov_key, **class_params)

    def as_fill_value(self, user_type=None, auth_mode=None):
        """Basic implementation matches instance attributes to view form attributes"""
        if user_type not in list(USER_TYPES.keys()):
            raise ValueError('invalid user_type "{}", must be key in USER_TYPES'.format(user_type))
        class_attrs = attr.fields_dict(type(self))  # dict of attr objects keyed by name
        # attr filter needs the Attribute object
        include_attrs = [class_attrs.get(name)
                         for name in self.view_class.cls_widget_names()
                         if name in class_attrs]
        fill = attr.asdict(self, filter=attr.filters.include(*include_attrs))
        return fill

    def as_fill_external_value(self):
        """openLDAP and FreeIPA providers can be configured for external auth
        Same view for all auth provider types
        """
        class_attrs = attr.fields_dict(type(self))  # dict of attr objects keyed by name
        # attr filter needs the Attribute object
        include_attrs = [class_attrs.get(name)
                         for name in ExternalAuthenticationView.cls_widget_names()
                         if name in class_attrs]
        fill = attr.asdict(self, filter=attr.filters.include(*include_attrs))
        return fill


@attr.s
class AmazonAuthProvider(BaseAuthProvider):
    """AWS IAM auth provider"""
    auth_type = 'amazon'
    view_class = AmazonAuthenticationView

    username = attr.ib()
    password = attr.ib()
    get_groups = attr.ib(default=False)

    def as_fill_value(self, **kwargs):
        """Amazon auth only has 3 UI values"""
        return {'access_key': self.username,
                'secret_key': self.password,
                'get_groups': self.get_groups}


@attr.s
class MIQAuthProvider(BaseAuthProvider):
    """base class for miq auth providers (ldap/ldaps modes in UI)
    Intended to be used for freeipa, AD, openldap and openldaps type providers
    """
    host1 = attr.ib()
    bind_password = attr.ib()  # Ordered to adhere to mandatory attrs sequence
    host2 = attr.ib(default=None)
    host3 = attr.ib(default=None)
    ports = attr.ib(default=None)  # dict of mode: port pairs, ex ldap: 389
    # user_types is dict with keys matching USER TYPE keys, and user_suffix key/value for that type
    user_types = attr.ib(default=None)
    domain_prefix = attr.ib(default=None)
    base_dn = attr.ib(default=None)
    bind_dn = attr.ib(default=None)
    get_groups = attr.ib(default=False)
    get_roles = attr.ib(default=False)
    follow_referrals = attr.ib(default=False)

    # attrs for SSL
    domain_name = attr.ib(default=None)
    cert_filename = attr.ib(default=None)
    cert_filepath = attr.ib(default=None)
    ipaddress = attr.ib(default=None)
    ldap_conf = attr.ib(default=None)
    sssd_conf = attr.ib(default=None)

    # TODO as_external_value method
    def as_fill_value(self, user_type='upn', auth_mode='ldap'):
        """miqldap config can have multiple settings per-provider based on user_type and
        auth_mode

        Args:
            user_type: key for USER_TYPES, used to lookup user_suffix
            auth_mode: key for AUTH_MODES, used to lookup port
        """
        fill = super(MIQAuthProvider, self).as_fill_value(user_type=user_type, auth_mode=auth_mode)

        # Handle args that have multiple possibilities depending on user_type and auth_mode
        if self.ports:
            fill['port'] = self.ports[auth_mode]
        else:
            # default port numbers if not specified
            fill['port'] = LDAP_PORT if auth_mode == 'ldap' else LDAPS_PORT
        fill['user_suffix'] = self.user_types.get(user_type, {}).get('user_suffix')
        # value lookup for user type
        fill['user_type'] = USER_TYPES[user_type]
        return fill


@attr.s
class OpenLDAPAuthProvider(MIQAuthProvider):
    """openldap auth provider, NO SSL No attributes beyond MIQAuthProvider"""
    auth_type = 'openldap'
    view_class = LdapAuthenticationView


@attr.s
class OpenLDAPSAuthProvider(MIQAuthProvider):
    """openldap auth provider, WITH SSL"""
    auth_type = 'openldaps'
    view_class = LdapsAuthenticationView


@attr.s
class ActiveDirectoryAuthProvider(MIQAuthProvider):
    """openldap auth provider, WITH SSL"""
    auth_type = 'ad'
    view_class = LdapAuthenticationView


@attr.s
class FreeIPAAuthProvider(MIQAuthProvider):
    """freeipa can be used with ldap auth config or external

    For ldap config:

    * 3 hosts can be configured
    * bind_dn is used for admin user validation
    * ipa realm and ipadomain are not part of config
    * user_type will use the cfme.utils.auth.USER_TYPES dict

    For external config:

    * 1 host is configured as --ipaserver
    * realm and domain are optional params
    * all user type, suffix, base/bind_dn, get_groups/roles/referrals args are not used

    """
    auth_type = 'freeipa'
    view_class = LdapAuthenticationView  # TODO could be SSL view, but ATM no difference in widgets

    ipaprincipal = attr.ib(default=None)  # ipaprincipal in external
    iparealm = attr.ib(default=None)  # external only, optional
    ipadomain = attr.ib(default=None)  # external only, optional

    def as_external_value(self):
        """return a dictionary that can be used with appliance_console_cli.configure_ipa"""
        external = dict(
            ipaserver=self.host1,
            ipaprincipal=self.ipaprincipal,
            ipapassword=self.bind_password
        )
        for att in ['iparealm', 'ipadomain']:  # optional args for external config
            if getattr(self, att):  # only include if set, don't pass key if None
                external.update({att: getattr(self, att)})

        return external


@attr.s
class SAMLAuthProvider(MIQAuthProvider):
    """ External auth provider for SAML"""
    auth_type = "saml"
    view_class = LdapAuthenticationView

    # overwrite bind_password as it's not necessary here
    bind_password = attr.ib(default=None)

    # attrs for SAML
    username = attr.ib(default=None)
    password = attr.ib(default=None)
    realms = attr.ib(default=None)
    default_client_scopes = attr.ib(default=None)

    @property
    def saml_endpoint(self):
        port = self.ports.get("http")
        return f"http://{self.host1}:{port}/auth"

    @property
    def keycloak_api(self):
        """ one limitation of this api endpoint is that you must first connect to the
            master realm, then connect to the desired realm. To get the api for a different realm,
            use self.get_keycloak_api
        """
        server_url = f"{self.saml_endpoint}/"
        realm = self.realms.get('master')
        return KeycloakAdmin(
            server_url=server_url,
            realm_name=realm,
            username=self.username,
            password=self.password
        )

    def get_keycloak_api(self, realm_name="CFME"):
        new_realm_api = self.keycloak_api
        new_realm_api.realm_name = realm_name
        return new_realm_api

    def as_fill_external_value(self):
        external = dict(
            get_groups=True,
            provider_type="Enable SAML",
            enable_sso=True
        )
        return external

from six import iteritems
import attr

from cfme.configure.configuration.server_settings import (
    AmazonAuthenticationView, LdapAuthenticationView, LdapsAuthenticationView
)
from cfme.exceptions import UnknownProviderType
from cfme.utils.conf import credentials, auth_data

auth_prov_data = auth_data.get("auth_providers", {})  # setup on module import

USER_TYPES = {
    'principal': 'User Principal Name',
    'email': 'E-mail Address',
    'dn-cn': 'Distinguished Name (CN=<user>)',
    'dn-uid': 'Distinguished Name (UID=<user>)',
    'sam': 'SAM Account Name'
}
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
    auth_prov_config = auth_prov_data[auth_prov_key].copy()
    klass = auth_class_from_type(auth_prov_config.get('type'))
    if auth_prov_config.get('type') != klass.auth_type:
        raise ValueError('{} must have type "{}"'.format(klass.__name__, klass.auth_type))
    return klass.from_config(auth_prov_config, auth_prov_key)


@attr.s
class BaseAuthProvider(object):
    """Base class for authentication provider objects    """
    auth_type = None
    view_class = None
    key = attr.ib()

    @classmethod
    def from_config(cls, prov_config, prov_key):
        """Returns an object using the passed yaml config
        Sets defaults for yaml configured objects separate from attr.ib definitions
        """
        prov_config.update(credentials[prov_config.get('credentials')])
        class_attrs = [att.name for att in cls.__attrs_attrs__]
        class_params = {k: v for k, v in iteritems(prov_config) if k in class_attrs}
        return cls(key=prov_key, **class_params)

    def as_fill_value(self):
        class_attrs = [att.name for att in self.__attrs_attrs__]
        include_attrs = [getattr(self.__class__, name)
                         for name in self.view_class.cls_widget_names()
                         if name in class_attrs]
        return attr.asdict(self, filter=attr.filters.include(*include_attrs))


@attr.s
class AmazonAuthProvider(BaseAuthProvider):
    """AWS IAM auth provider"""
    auth_type = 'amazon'
    view_class = AmazonAuthenticationView

    access_key = attr.ib()
    secret_key = attr.ib()
    get_groups = attr.ib(default=False)


@attr.s
class MIQAuthProvider(BaseAuthProvider):
    """base class for miq auth providers (ldap/ldaps modes in UI)
    Intended to be used for freeipa, AD, openldap and openldaps type providers
    """
    host1 = attr.ib()
    bind_password = attr.ib()  # Ordered to adhere to mandatory attrs sequence
    host2 = attr.ib(default=None)
    host3 = attr.ib(default=None)
    port = attr.ib(default=LDAP_PORT)
    user_type = attr.ib(default='principal',
                        validator=lambda item, attribute, value: value in list(USER_TYPES.keys()))
    domain_prefix = attr.ib(default=None)
    user_suffix = attr.ib(default=None)
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
class FreeIPAAuthProvider(MIQAuthProvider):
    """freeipa can be used with ldap auth config or external
    For ldap config:
        3 hosts can be configured
        bind_dn is used for admin user validation
        ipa realm and ipadomain are not part of config
        user_type will use the cfme.utils.auth.USER_TYPES dict
    For external config:
        1 host is configured as --ipaserver
        realm and domain are optional params
        all user type, suffix, base/bind_dn, get_groups/roles/referrals args are not used
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
            principal=self.ipaprincipal,
            password=self.bind_password
        )
        for att in ['iparealm', 'ipadomain']:  # optional args for external config
            if getattr(self, att):  # only include if set, don't pass key if None
                external.update({att: getattr(self, att)})

        return external

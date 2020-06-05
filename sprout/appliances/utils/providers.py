from collections import Mapping

import six

from cfme.common.provider import all_types
from cfme.exceptions import UnknownProviderType
from cfme.utils import conf
from cfme.utils.log import logger
from sprout.vault.vault import settings

providers_data = conf.cfme_data.get("management_systems", {})

PROVIDER_MGMT_CACHE = {}


def get_class_from_type(prov_type):
    try:
        return all_types()[prov_type]
    except KeyError:
        raise UnknownProviderType("Unknown provider type: {}!".format(prov_type))


def get_mgmt(provider_key, providers=None, credentials=None):
    """ Provides a ``wrapanapi`` object, based on the request.

    Args:
        provider_key: The name of a provider, as supplied in the yaml configuration files.
            You can also use the dictionary if you want to pass the provider data directly.
        providers: A set of data in the same format as the ``management_systems`` section in the
            configuration yamls. If ``None`` then the configuration is loaded from the default
            locations. Expects a dict.
        credentials: A set of credentials in the same format as the ``credentials`` yamls files.
            If ``None`` then credentials are loaded from the vault using dynaconf. Expects a dict.
    Return: A provider instance of the appropriate ``wrapanapi.WrapanapiAPIBase``
        subclass
    """
    if providers is None:
        providers = providers_data
    # provider_key can also be provider_data for some reason
    # TODO rename the parameter; might break things
    if isinstance(provider_key, Mapping):
        provider_data = provider_key
        provider_key = provider_data['name']
    else:
        provider_data = providers[provider_key]

    if credentials is None:
        # create env matching provider_keys in vault to hold credentials
        with settings.using_env(provider_key):
            credentials = {key.lower(): val for key, val in settings.as_dict().items()
            if 'VAULT' not in key}

    # Munge together provider dict and creds,
    # Let the provider do whatever they need with them
    provider_kwargs = provider_data.copy()
    provider_kwargs.update(credentials)

    if not provider_kwargs.get('username') and provider_kwargs.get('principal'):
        provider_kwargs['username'] = provider_kwargs['principal']
        provider_kwargs['password'] = provider_kwargs['secret']

    if isinstance(provider_key, six.string_types):
        provider_kwargs['provider_key'] = provider_key
    provider_kwargs['logger'] = logger

    if provider_key not in PROVIDER_MGMT_CACHE:
        mgmt_instance = get_class_from_type(provider_data['type']).mgmt_class(**provider_kwargs)
        PROVIDER_MGMT_CACHE[provider_key] = mgmt_instance
    else:
        logger.debug("returning cached mgmt class for '%s'", provider_key)
    return PROVIDER_MGMT_CACHE[provider_key]

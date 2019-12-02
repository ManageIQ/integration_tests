from urllib.parse import urlparse

from cfme.utils.appliance import load_appliances_from_config
from .regular import APP_TYPE as DEFAULT_APP_TYPE


def appliances_from_cli(cli_appliances, appliance_version):
    appliance_config = dict(appliances=[])
    for appliance_data in cli_appliances:
        parsed_url = urlparse(appliance_data['hostname'])
        if not parsed_url.hostname:
            raise ValueError(
                "Invalid appliance url: {}".format(appliance_data)
            )

        appliance = appliance_data.copy()
        appliance.update(dict(
            hostname=parsed_url.hostname,
            ui_protocol=parsed_url.scheme if parsed_url.scheme else "https",
            ui_port=parsed_url.port if parsed_url.port else 443,
            version=appliance_version
        ))

        appliance_config['appliances'].append(appliance)

    return load_appliances_from_config(appliance_config)

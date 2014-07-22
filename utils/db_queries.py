# -*- coding: utf-8 -*-

from utils.db import cfmedb, database_on_server


def get_configuration_details(ip_address=None):
    """Return details that are necessary to navigate through Configuration accordions.

    Args:
        ip_address: IP address of the server to match. If None, uses hostname from
            ``conf.env['base_url']``

    Returns:
        If the data weren't found in the DB, :py:class:`NoneType`
        If the data were found, it returns tuple `(region, server name, server id, server zone id)`
    """
    if ip_address is None:
        ip_address = cfmedb.hostname

    with database_on_server(ip_address) as db:
        SEQ_FACT = 1000000000000
        miq_servers = db['miq_servers']
        for region in db.session.query(db['miq_regions']):
            reg_min = region.region * SEQ_FACT
            reg_max = reg_min + SEQ_FACT
            servers = list(
                db.session.query(miq_servers).filter(
                    miq_servers.id >= reg_min,
                    miq_servers.id < reg_max,
                    miq_servers.ipaddress == ip_address
                )
            )
            if servers:
                return region.region, servers[0].name, servers[0].id, servers[0].zone_id
            else:
                return None, None, None, None
        else:
            return None


def get_server_id(ip_address=None):
    try:
        return get_configuration_details(ip_address)[2]
    except TypeError:
        return None


def get_server_region(ip_address=None):
    try:
        return get_configuration_details(ip_address)[0]
    except TypeError:
        return None


def get_server_name(ip_address=None):
    try:
        return get_configuration_details(ip_address)[1]
    except TypeError:
        return None


def get_server_zone_id(ip_address=None):
    try:
        return get_configuration_details(ip_address)[3]
    except TypeError:
        return None


def get_zone_description(zone_id, ip_address=None):
    if ip_address is None:
        ip_address = cfmedb.hostname

    with database_on_server(ip_address) as db:
        zones = list(
            db.session.query(db["zones"]).filter(
                db["zones"].id == zone_id
            )
        )
        if zones:
            return zones[0].description
        else:
            return None

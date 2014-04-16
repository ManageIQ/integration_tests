#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from utils.db import cfmedb
from functools import wraps


def db_query(function):
    """Decorator providing DB access functions that want it.

    Puts db as the first argument, other arguments follow. db will be an instance of
    :py:class:`utils.Db`.

    Returns: Wrapped function.
    """
    @wraps(function)
    def f(*args, **kwargs):
        if "db_session" in kwargs:
            db_session = kwargs["db_session"]
        else:
            db_session = cfmedb
        return function(db_session, *args, **kwargs)
    return f


@db_query
def get_configuration_details(db, ip_address=None):
    """Return details that are necessary to navigate through Configuration accordions.

    Args:
        ip_address: IP address of the server to match. If None, uses hostname from
            ``conf.env['base_url']``

    Returns:
        If the data weren't found in the DB, :py:class:`NoneType`
        If the data were found, it returns tuple `(region, server name, server id)`
    """
    if ip_address is None:
        ip_address = db.hostname
    SEQ_FACT = 1000000000000
    miq_servers = db['miq_servers']
    for region in db.session.query(db['miq_regions']):
        reg_min = region.region * SEQ_FACT
        reg_max = reg_min + SEQ_FACT
        servers = list(db.session.query(miq_servers)
            .filter(
                miq_servers.id >= reg_min,
                miq_servers.id < reg_max,
                miq_servers.ipaddress == ip_address
            )
        )
        if servers:
            return region.region, servers[0].name, servers[0].id
        else:
            return None, None, None
    else:
        return None


def get_server_id(ip_address=None, **kwargs):
    try:
        return get_configuration_details(ip_address, **kwargs)[2]
    except TypeError:
        return None


def get_server_region(ip_address=None, **kwargs):
    try:
        return get_configuration_details(ip_address, **kwargs)[0]
    except TypeError:
        return None


def get_server_name(ip_address=None, **kwargs):
    try:
        return get_configuration_details(ip_address, **kwargs)[1]
    except TypeError:
        return None

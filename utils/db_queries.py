#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import db
from functools import wraps
from utils.cfmedb import db_session_maker


def db_query(function):
    """Decorator providing the DB session for functions that want it.

    Puts it as the first argument, other arguments follow.

    Args:
        function: Function to decorate
    Returns: Wrapped function.
    """
    @wraps(function)
    def f(*args, **kwargs):
        return function(db_session_maker(recreate=True), *args, **kwargs)
    return f


@db_query
def get_configuration_details(session, ip_address):
    """Return details that are necessary to navigate through Configuration accordions.

    Args:
        ip_address: IP address of the appliance
    Returns:
        If the data weren't found in the DB, :py:class:`NoneType`
        If the data were found, it returns tuple `(region, server name, server id)`
    """
    SEQ_FACT = 1000000000000
    for region in session.query(db.MiqRegion):
        reg_min = region.region * SEQ_FACT
        reg_max = reg_min + SEQ_FACT - 1
        servers = list(session.query(db.MiqServer)
            .filter(
                db.MiqServer.id > reg_min,
                db.MiqServer.id <= reg_max,
                db.MiqServer.ipaddress == ip_address
            )
        )
        if len(servers) == 1:
            return region.region, servers[0].name, servers[0].id
    else:
        return None


def get_server_id(ip_address):
    try:
        return get_configuration_details(ip_address)[2]
    except TypeError:
        return None


def get_server_region(ip_address):
    try:
        return get_configuration_details(ip_address)[0]
    except TypeError:
        return None


def get_server_name(ip_address):
    try:
        return get_configuration_details(ip_address)[1]
    except TypeError:
        return None

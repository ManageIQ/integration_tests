# -*- coding: utf-8 -*-
from utils.db import cfmedb, Db


def _db(db=None, ip_address=None):
    if ip_address is None:
        ip_address = cfmedb().hostname

    if db is None:
        db = Db(hostname=ip_address)
    return db


def get_configuration_details(db=None, ip_address=None):
    """Return details that are necessary to navigate through Configuration accordions.

    Args:
        ip_address: IP address of the server to match. If None, uses hostname from
            ``conf.env['base_url']``

    Returns:
        If the data weren't found in the DB, :py:class:`NoneType`
        If the data were found, it returns tuple `(region, server name, server id, server zone id)`
    """
    db = _db(db, ip_address)

    SEQ_FACT = 1e12
    miq_servers = db['miq_servers']
    for region in db.session.query(db['miq_regions']):
        reg_min = region.region * SEQ_FACT
        reg_max = reg_min + SEQ_FACT
        all_servers = db.session.query(miq_servers).all()
        server = None
        if len(all_servers) == 1:
            # If there's only one server, it's the one we want
            server = all_servers[0]
        else:
            # Otherwise, filter based on id and ip address
            def server_filter(server):
                return all([
                    server.id >= reg_min,
                    server.id < reg_max,
                    # XXX: This currently fails due to public/private addresses on openstack
                    server.ipaddress == ip_address
                ])
            servers = filter(server_filter, all_servers)
            if servers:
                server = servers[0]
        if server:
            return region.region, server.name, server.id, server.zone_id
        else:
            return None, None, None, None
    else:
        return None


def get_zone_description(zone_id, ip_address=None, db=None):
    db = _db(db, ip_address)
    zone = db.session.query(db["zones"]).filter_by(id=zone_id).first()
    if zone is not None:
        return zone.description


def get_host_id(hostname, ip_address=None, db=None):
    db = _db(db, ip_address)

    host = db.session.query(db["hosts"]).filter_by(name=hostname).first()

    if host is not None:
        return str(host.id)


def check_domain_enabled(domain, ip_address=None, db=None):
    db = _db(db, ip_address)

    namespaces = db["miq_ae_namespaces"]
    ns = db.session.query(namespaces).filter_by(parent_id=None, name=domain).first()
    if ns is not None:
        return ns.enabled
    else:
        raise KeyError("No such Domain: {}".format(domain))

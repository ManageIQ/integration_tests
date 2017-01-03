# -*- coding: utf-8 -*-
from utils.db import cfmedb, Db
from collections import namedtuple


class ConfigDetailResult(namedtuple('ConfigDetailResult',
                                    'server_region, server_name, server_id, server_zone_id')):
    @classmethod
    def from_region_and_server(cls, region, server):
        if not server:
            return cls(None, None, None, None)
        else:
            return cls(region.region, server.name, server.id, server.zone_id)


def config_detail_method(descriptor, attribute='configuration_details'):
    name = next(
        # __base__ is needed because we layer a subclass on top and need to walk the base class dict
        name for name, value in vars(ConfigDetailResult.__base__).items()
        if value is descriptor)

    def method(self):
        conf = getattr(self, attribute)
        return getattr(conf, name, None)
    method.__name__ = name
    method.__doc__ = "alias for self.{attribute}.{name}".format(
        attribute=attribute, name=name)
    return method


def _db(db=None, ip_address=None):
    return db or Db(hostname=ip_address or cfmedb().hostname)


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
            server = next((
                s for s in all_servers
                if server.id >= reg_min and server.id < reg_max and
                # XXX: This currently fails due to public/private addresses on openstack
                server.ipaddress == ip_address), default=None)
        if server is not None:
            return ConfigDetailResult.from_region_and_server(region, server)
    else:
        return None


def get_zone_description(zone_id, ip_address=None, db=None):
    db = _db(db, ip_address)
    zone = db.get_first_of("zones", id=zone_id)
    if zone is not None:
        return zone.description


def get_host_id(hostname, ip_address=None, db=None):
    db = _db(db, ip_address)

    host = db.db.get_first_of("hosts", name=hostname)

    if host is not None:
        return str(host.id)


def check_domain_enabled(domain, ip_address=None, db=None):
    db = _db(db, ip_address)

    ns = db.get_first_of("miq_ae_namespaces", parent_id=None, name=domain)
    if ns is not None:
        return ns.enabled
    else:
        raise KeyError("No such Domain: {}".format(domain))

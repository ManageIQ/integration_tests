# -*- coding: utf-8 -*-
from copy import copy

from cfme.configure.configuration import set_server_roles, get_server_roles
from cfme.storage.managers import StorageManager
from utils.conf import cfme_data, credentials


def objects_from_config(*keys):
    result = {}
    for key, data in cfme_data.get("storage", {}).get("managers", {}).iteritems():
        if keys and key not in keys:
            continue
        data = copy(data)
        if "credentials" in data:
            data["credentials"] = StorageManager.Credential(
                **credentials.get(data["credentials"], {}))
        result[key] = StorageManager(**data)
    return result


def setup_storage_manager(key):
    set_roles_for_sm()
    sm = objects_from_config(key)[key]
    if not sm.exists:
        sm.create()
    return sm


def setup_storage_managers():
    set_roles_for_sm()
    result = []
    for k, sm in objects_from_config().iteritems():
        if not sm.exists:
            sm.create()
            result.append(sm)
    return result


def set_roles_for_sm():
    roles = get_server_roles()
    roles["storage_metrics_processor"] = True
    roles["storage_metrics_collector"] = True
    roles["storage_metrics_coordinator"] = True
    roles["storage_inventory"] = True
    return set_server_roles(**roles)

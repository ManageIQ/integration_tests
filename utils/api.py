# -*- coding: utf-8 -*-
# TODO: WIP WIP WIP WIP!
# I got another stage of this library aside, but this is perfectly usable with some restrictions :)
import iso8601
import json
import re
import requests
import simplejson
from copy import copy
from fixtures.pytest_store import store
from utils.log import logger
from utils.version import Version
from utils.wait import wait_for


class APIException(Exception):
    pass


class API(object):
    def __init__(self, entry_point, auth):
        self._entry_point = entry_point
        if isinstance(auth, dict):
            self._auth = (auth["user"], auth["password"])
        elif isinstance(auth, (tuple, list)):
            self._auth = tuple(auth[:2])
        else:
            raise ValueError("Unknown values provider for auth")
        self._load_data()

    def _load_data(self):
        data = self.get(self._entry_point)
        self.collections = CollectionsIndex(self, data.pop("collections", []))
        self._version = data.pop("version", None)
        self._versions = {}
        for version in data.pop("versions", []):
            self._versions[version["name"]] = version["href"]
        for key, value in data.iteritems():
            setattr(self, key, value)

    @property
    def version(self):
        return Version(self._version)

    @staticmethod
    def _result_processor(result):
        if not isinstance(result, dict):
            return result
        if "error" in result:
            # raise
            raise APIException(
                "{}: {}".format(result["error"]["klass"], result["error"]["message"]))
        else:
            return result

    def get(self, url, **get_params):
        logger.info("[RESTAPI] GET {} {}".format(url, repr(get_params)))
        data = requests.get(url, auth=self._auth, params=get_params, verify=False)
        try:
            data = data.json()
        except simplejson.scanner.JSONDecodeError:
            raise APIException("JSONDecodeError: {}".format(data.text))
        return self._result_processor(data)

    def post(self, url, **payload):
        logger.info("[RESTAPI] POST {} {}".format(url, repr(payload)))
        data = requests.post(url, auth=self._auth, data=json.dumps(payload), verify=False)
        logger.info("[RESTAPI] RESPONSE {}".format(data))
        try:
            data = data.json()
        except simplejson.scanner.JSONDecodeError:
            if len(data.text.strip()) == 0:
                return None
            else:
                raise APIException("JSONDecodeError: {}".format(data.text))
        return self._result_processor(data)

    def delete(self, url, **payload):
        logger.info("[RESTAPI] DELETE {} {}".format(url, repr(payload)))
        data = requests.delete(url, auth=self._auth, data=json.dumps(payload), verify=False)
        logger.info("[RESTAPI] RESPONSE {}".format(data))
        try:
            data = data.json()
        except simplejson.scanner.JSONDecodeError:
            if len(data.text.strip()) == 0:
                return None
            else:
                raise APIException("JSONDecodeError: {}".format(data.text))
        return self._result_processor(data)

    def get_entity(self, collection_or_name, entity_id, attributes=None):
        if not isinstance(collection_or_name, Collection):
            collection = Collection(
                self, "{}/{}".format(self._entry_point, collection_or_name), collection_or_name)
        else:
            collection = collection_or_name
        entity = Entity(collection, {"href": "{}/{}".format(collection._href, entity_id)})
        if attributes is not None:
            entity.reload(attributes=attributes)
        return entity

    def api_version(self, version):
        return type(self)(self._versions[version], self._auth)

    @property
    def versions(self):
        return sorted(self._versions.keys(), reverse=True, key=Version)

    @property
    def new_id_behaviour(self):
        """2.0.0 introduced a new id/href difference."""
        return self.version >= "2.0.0"

    @property
    def latest_version(self):
        return self.versions[0]

    @property
    def on_latest_version(self):
        return self.version == self.latest_version


class CollectionsIndex(object):
    def __init__(self, api, data):
        self._api = api
        self._data = data
        self._collections = []
        self._load_data()

    def _load_data(self):
        for collection in self._data:
            c = Collection(
                self._api, collection["href"], collection["name"], collection["description"])
            setattr(self, collection["name"], c)
            self._collections.append(c)

    @property
    def all(self):
        return self._collections

    @property
    def all_names(self):
        return map(lambda c: c.name, self.all)

    def __contains__(self, collection):
        if isinstance(collection, basestring):
            return collection in self.all_names
        else:
            return collection in self.all


class SearchResult(object):
    def __init__(self, collection, data):
        self.collection = collection
        self.count = data.pop("count")
        self.subcount = data.pop("subcount")
        self.name = data.pop("name")
        self.resources = []
        for resource in data["resources"]:
            self.resources.append(Entity(collection, resource))

    def __iter__(self):
        for resource in self.resources:
            resource.reload()
            yield resource

    def __getitem__(self, position):
        entity = self.resources[position]
        entity.reload()
        return entity

    def __len__(self):
        return self.subcount

    def __repr__(self):
        return "<SearchResult for {}>".format(repr(self.collection))


class Collection(object):
    def __init__(self, api, href, name, description=None):
        self._api = api
        self._href = href
        self._data = None
        self.action = ActionContainer(self)
        self.name = name
        self.description = description

    @property
    def api(self):
        return self._api

    def reload(self, expand=False):
        if expand is True:
            kwargs = {"expand": "resources"}
        elif expand:
            kwargs = {"expand": expand}
        else:
            kwargs = {}
        self._data = self._api.get(self._href, **kwargs)
        self._resources = self._data["resources"]
        self._count = self._data["count"]
        self._subcount = self._data["subcount"]
        self._actions = self._data.pop("actions", [])
        if self._data["name"] != self.name:
            raise ValueError("Name mishap!")

    def reload_if_needed(self):
        if self._data is None:
            self.reload()

    def find_by(self, **params):
        """Search items in collection. Filters based on keywords passed."""
        if self._api.version == "2.0.0-pre":
            # Special case, there can be both, so try sqlfilter first and if that does not work ...
            try:
                return self._find_by_sqlfilter(**params)
            except APIException:
                return self._find_by_filter(**params)
        elif self._api.version.is_in_series("1.1") or self._api.version >= "2.0.0":
            # New function
            return self._find_by_filter(**params)
        else:
            # Old function
            return self._find_by_sqlfilter(**params)

    def _find_by_sqlfilter(self, **params):
        search_query = []
        for key, value in params.iteritems():
            search_query.append("{} = {}".format(key, repr(str(value))))
        return SearchResult(
            self, self._api.get(self._href, **{"sqlfilter": " AND ".join(search_query)}))

    def _find_by_filter(self, **params):
        search_query = []
        for key, value in params.iteritems():
            if isinstance(value, int):
                search_query.append("{}={}".format(key, value))
            else:
                search_query.append("{}={}".format(key, repr(str(value))))
        return SearchResult(self, self._api.get(self._href, **{"filter[]": search_query}))

    def get(self, **params):
        try:
            return self.find_by(**params)[0]
        except IndexError:
            raise ValueError("No such '{}' matching query {}!".format(self.name, repr(params)))

    @property
    def count(self):
        self.reload_if_needed()
        return self._count

    @property
    def subcount(self):
        self.reload_if_needed()
        return self._subcount

    @property
    def all(self):
        self.reload_if_needed()
        return map(lambda r: Entity(self, r), self._resources)

    def __repr__(self):
        return "<Collection {} ({})>".format(repr(self.name), repr(self.description))

    def __call__(self, entity_id, attributes=None):
        return self._api.get_entity(self, entity_id, attributes=attributes)

    def __iter__(self):
        self.reload(expand=True)
        for resource in self._resources:
            yield Entity(self, resource)

    def __getitem__(self, position):
        self.reload_if_needed()
        entity = Entity(self, self._resources[position])
        entity.reload()
        return entity

    def __len__(self):
        return self.subcount


class Entity(object):
    # TODO: Extend these fields
    TIME_FIELDS = {
        "updated_on", "created_on", "last_scan_attempt_on", "state_changed_on", "lastlogon",
        "updated_at", "created_at", "last_scan_on", "last_sync_on", "last_refresh_date", "retires_on",}
    COLLECTION_MAPPING = dict(
        ems_id="providers",
        storage_id="data_stores",
        zone_id="zones",
        host_id="hosts",
        current_group_id="groups",
        miq_user_role_id="roles",
        evm_owner_id="users",
        task_id="tasks",
    )
    # TODO: Extend
    SUBCOLLECTIONS = dict(
        service_catalogs={"service_templates"},
        roles={"features"},
        providers={"tags"},
        hosts={"tags"},
        data_stores={"tags"},
        resource_pools={"tags"},
        clusters={"tags"},
        services={"tags"},
        service_templates={"tags"},
        tenants={"tags"},
        vms={"tags"},
    )

    EXTENDED_COLLECTIONS = dict(
        roles={"features"},
    )

    def __init__(self, collection, data, incomplete=False):
        self.collection = collection
        self.action = ActionContainer(self)
        self._data = data
        self._incomplete = incomplete
        self._load_data()

    def _load_data(self):
        if "id" in self._data:  # We have complete data
            self.reload(get=False)
        elif "href" in self._data:  # We have only href
            self._href = self._data["href"]
            # self._data = None
        else:  # Malformed
            raise ValueError("Malformed data: {}".format(repr(self._data)))

    def reload(self, expand=None, get=True, attributes=None):
        kwargs = {}
        if expand:
            if isinstance(expand, (list, tuple)):
                expand = ",".join(map(str, expand))
            kwargs.update(expand=expand)
        if attributes is not None:
            if isinstance(attributes, basestring):
                attributes = [attributes]
            kwargs.update(attributes=",".join(attributes))
        if get:
            new = self.collection._api.get(self._href, **kwargs)
            if self._data is None:
                self._data = new
            else:
                self._data.update(new)
        if (
                "id" in self._data and "href" in self._data
                and isinstance(self._data["href"], basestring)):
            self._href = self._data["href"]
        else:
            self._href = self._data["id" if not self.collection._api.new_id_behaviour else "href"]
        self._actions = self._data.pop("actions", [])
        for key, value in self._data.iteritems():
            if key in self.TIME_FIELDS:
                setattr(self, key, iso8601.parse_date(value))
            elif key in self.COLLECTION_MAPPING.keys():
                setattr(
                    self,
                    re.sub(r"_id$", "", key),
                    self.collection._api.get_entity(self.COLLECTION_MAPPING[key], value)
                )
                setattr(self, key, value)
            elif isinstance(value, dict) and "count" in value and "resources" in value:
                href = self._href
                if not href.endswith("/"):
                    href += "/"
                subcol = Collection(self.collection._api, href + key, key)
                setattr(self, key, subcol)
            elif isinstance(value, list) and key in self.EXTENDED_COLLECTIONS.get(
                    self.collection.name, set([])):
                href = self._href
                if not href.endswith("/"):
                    href += "/"
                subcol = Collection(self.collection._api, href + key, key)
                setattr(self, key, subcol)
            else:
                setattr(self, key, value)

    @property
    def exists(self):
        try:
            self.reload()
        except APIException:
            return False
        else:
            return True

    def wait_for_existence(self, existence, **kwargs):
        return wait_for(
            lambda: self.exists, fail_condition=not existence, **kwargs)

    def wait_exists(self, **kwargs):
        return self.wait_for_existence(True, **kwargs)

    def wait_not_exists(self, **kwargs):
        return self.wait_for_existence(False, **kwargs)

    def reload_if_needed(self):
        if self._data is None or self._incomplete or not hasattr(self, "_actions"):
            self.reload()
            self._incomplete = False

    def __getattr__(self, attr):
        self.reload()
        if attr in self.__dict__:
            # It got loaded
            return self.__dict__[attr]
        if attr not in self.SUBCOLLECTIONS.get(self.collection.name, set([])):
            raise AttributeError("No such attribute/subcollection {}".format(attr))
        # Try to get subcollection
        href = self._href
        if not href.endswith("/"):
            href += "/"
        subcol = Collection(self.collection._api, href + attr, attr)
        try:
            subcol.reload()
        except APIException:
            raise AttributeError("No such attribute/subcollection {}".format(attr))
        else:
            return subcol

    def __getitem__(self, item):
        # Backward compatibility
        return getattr(self, item)

    def __repr__(self):
        return "<Entity {}>".format(repr(self._href))

    def _ref_repr(self):
        return {"href": self._href}


class ActionContainer(object):
    def __init__(self, obj):
        self._obj = obj

    def reload(self):
        self._obj.reload_if_needed()
        for action in self._obj._actions:
            setattr(
                self,
                action["name"],
                Action(self, action["name"], action["method"], action["href"]))

    def execute_action(self, action_name, *args, **kwargs):
        # To circumvent bad method names, like `import`, you can use this one directly
        action = getattr(self, action_name)
        return action(*args, **kwargs)

    @property
    def all(self):
        self.reload()
        return map(lambda a: a["name"], self._obj._actions)

    @property
    def collection(self):
        if isinstance(self._obj, Collection):
            return self._obj
        elif isinstance(self._obj, Entity):
            return self._obj.collection
        else:
            raise ValueError("ActionContainer assigned to wrong object!")

    def __getattr__(self, attr):
        self.reload()
        if not hasattr(self, attr):
            raise AttributeError("No such action {}".format(attr))
        return getattr(self, attr)

    def __contains__(self, action):
        return action in self.all


class Action(object):
    def __init__(self, container, name, method, href):
        self._container = container
        self._method = method
        self._href = href
        self._name = name

    @property
    def collection(self):
        return self._container.collection

    @property
    def api(self):
        return self.collection.api

    def __call__(self, *args, **kwargs):
        resources = []
        # We got resources to post
        for res in args:
            if isinstance(res, Entity):
                resources.append(res._ref_repr())
            else:
                resources.append(res)
        query_dict = {"action": self._name}
        if resources:
            query_dict["resources"] = []
            for resource in resources:
                new_res = dict(resource)
                if kwargs:
                    new_res.update(kwargs)
                query_dict["resources"].append(new_res)
        else:
            if kwargs:
                query_dict["resource"] = kwargs
        if self._method == "post":
            result = self.api.post(self._href, **query_dict)
        elif self._method == "delete":
            result = self.api.delete(self._href, **query_dict)
        else:
            raise NotImplementedError
        if result is None:
            return None
        elif "results" in result:
            return map(self._process_result, result["results"])
        else:
            return self._process_result(result)

    def _process_result(self, result):
        if "href" in result:
            return Entity(self.collection, result, incomplete=True)
        elif "id" in result:
            d = copy(result)
            d["href"] = "{}/{}".format(self.collection._href, result["id"])
            return Entity(self.collection, d, incomplete=True)
        # TODO: Remove the branch under this condition since it can cause bad things to happen!
        elif "request_state" in result and "requester_id" in result:
            collection = getattr(self.api.collections, "service_requests")
            d = copy(result)
            if "id" in result:
                d["href"] = "{}/{}".format(collection._href, result["id"])
            return Entity(collection, d)
        elif "message" in result:
            return result
        else:
            raise NotImplementedError

    def __repr__(self):
        return "<Action {} {}#{}>".format(self._method, self._container._obj._href, self._name)


def rest_api():
    return store.current_appliance.rest_api

# -*- coding: utf-8 -*-
import slumber
from requests import Session

from fixtures.pytest_store import store
from utils.conf import credentials


def APIException(Exception):
    pass


def api():
    url = store.base_url
    creds = credentials["default"]["username"], credentials["default"]["password"]
    session = Session()
    session.auth = creds
    session.verify = False
    return slumber.API("{}/api".format(url.rstrip('/')), session=session)


def _result_processor(result):
    if not isinstance(result, dict):
        return result
    if "error" in result:
        # raise
        raise APIException("{}: {}".format(result["error"]["klass"], result["error"]["message"]))
    else:
        return result


def find_template_by_name(template_name):
    return _result_processor(
        api().templates().get(sqlfilter="name = '{}'".format(template_name), expand="resources")
    )["resources"]


def get_template_guid(template):
    return find_template_by_name(template)[0]["guid"]


def create_service_catalog(name, description, service_templates):
    return _result_processor(api().service_catalogs().post(
        data={
            "action": "add",
            "resource": {
                "name": name,
                "description": description,
                "service_templates": [{"href": tpl} for tpl in service_templates]
            }
        }
    ))["results"][0]


def create_service_catalogs(*catalogs):
    return _result_processor(api().service_catalogs().post(
        data={
            "action": "add",
            "resources": [
                {
                    "name": catalog["name"],
                    "description": catalog["description"],
                    "service_templates": [{"href": tpl} for tpl in catalog["service_templates"]]
                }
                for catalog
                in catalogs
            ]
        }
    ))["results"]


def delete_service_catalogs(*catalogs):
    return _result_processor(api().service_catalogs().post(
        data={
            "action": "delete",
            "resources": [
                {
                    "href":
                    catalog
                    if isinstance(catalog, basestring)
                    else api().service_catalogs(catalog).get()["id"],
                }
                for catalog
                in catalogs
            ]
        }
    ))["results"]


def delete_service_catalog(id):
    return _result_processor(api().service_catalogs(id).delete())

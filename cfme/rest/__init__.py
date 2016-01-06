import fauxfactory
from utils.wait import wait_for


def service_catalogs(request, rest_api):
    name = fauxfactory.gen_alphanumeric()
    scls_data = [{
        "name": "name_{}_{}".format(name, index),
        "description": "description_{}_{}".format(name, index),
        "service_templates": []
    } for index in range(1, 5)]

    scls = rest_api.collections.service_catalogs.action.add(*scls_data)
    for scl in scls:
        wait_for(
            lambda: rest_api.collections.service_catalogs.find_by(name=scl.name),
            num_sec=180,
            delay=10,
        )

    @request.addfinalizer
    def _finished():
        ids = [s.id for s in scls]
        delete_scls = [s for s in rest_api.collections.service_catalogs if s.id in ids]
        if len(delete_scls) != 0:
            rest_api.collections.service_catalogs.action.delete(*delete_scls)

    return scls

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


def categories(request, rest_api, num=1):
    ctg_data = [{
        'name': 'test_category_{}_{}'.format(fauxfactory.gen_alphanumeric().lower(), _index),
        'description': 'test_category_{}_{}'.format(fauxfactory.gen_alphanumeric().lower(), _index)
    } for _index in range(0, num)]
    ctgs = rest_api.collections.categories.action.create(*ctg_data)
    for ctg in ctgs:
        wait_for(
            lambda: rest_api.collections.categories.find_by(description=ctg.description),
            num_sec=180,
            delay=10,
        )

    @request.addfinalizer
    def _finished():
        ids = [ctg.id for ctg in ctgs]
        delete_ctgs = [ctg for ctg in rest_api.collections.categories
            if ctg.id in ids]
        if len(delete_ctgs) != 0:
            rest_api.collections.categories.action.delete(*delete_ctgs)

    return ctgs

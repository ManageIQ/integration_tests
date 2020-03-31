# TODO: add more association types
_ASSOCIATION_TYPES_MAPPING = {
    'Service': {'rest_collection': 'services'},
    'Vms': {'rest_collection': 'vms'},
}


def get_rest_resource(appliance, association_type, resource):
    mapping = _ASSOCIATION_TYPES_MAPPING.get(association_type)
    if not mapping:
        raise NotImplementedError(f'Mapping is not implemented for `{association_type}`.')

    rest_collection = getattr(appliance.rest_api.collections, mapping['rest_collection'])
    return rest_collection.find_by(name=resource.name)

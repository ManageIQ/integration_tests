# -*- coding: utf-8 -*-
"""Helper functions for tests using REST API."""


def action_exists(collection, name, method='post'):
    """Check if action is present for given collection/subcollection.

    You can do following:

    .. code-block:: python

        assert action_exists(rest_api.collections.providers[0], 'delete', 'delete')

    """
    try:
        collection_actions = collection._actions
    except AttributeError:
        return False

    for action in collection_actions:
        if action['method'] == method and action['name'] == name:
            return True
    return False

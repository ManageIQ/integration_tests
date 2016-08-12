"""crud: Marker for marking the test as a CRUD test (crud)

Useful for eg. running only crud tests.
Tests will be marked automatically if:

* their name starts with crud\_
* their name ends with \_crud
* their name contains \_crud\_
"""
from __future__ import unicode_literals
import re

matcher = re.compile(r"^crud_|_crud_|_crud$")
marker = "crud"


def pytest_configure(config):
    config.addinivalue_line('markers', __doc__.splitlines()[0])


def pytest_itemcollected(item):
    if matcher.search(item.name) is not None:
        item.add_marker(marker)
        item.extra_keyword_matches.add(marker)

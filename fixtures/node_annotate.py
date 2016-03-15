import py
import pytest
import csv
import yaml
import os

from operator import itemgetter
from utils.path import project_path
from utils.conf import cfme_data
from .pytest_store import store


class MarkFromMap(object):
    def __init__(self, mark_map):
        self.mark_map = mark_map

    def pytest_itemcollected(self, item):
        mark = self.mark_map.get(item.nodeid)
        if mark is not None:
            # todo: warn when the applied marker differs from the data
            if not item.get_marker(mark.name):
                item.add_marker(mark)

    @classmethod
    def from_parsed_list(cls, parsed, key, map_value):
        data = dict(map(itemgetter('id', key), parsed))
        mark_map = dict((k, map_value(v)) for k, v in data.items())
        return cls(mark_map)


def pytest_configure(config):
    path = cfme_data.get('cfme_annotations_path')
    if path:
        to_parse = project_path.join(path)
        parsed = parse(to_parse)
        if not parsed:
            store.terminalreporter.line(
                'no test annotation found in {}'.format(to_parse), yellow=True)
    else:
        store.terminalreporter.line('no test annotation found in {}'.format(path), yellow=True)
        parsed = []
    config.pluginmanager.register(MarkFromMap.from_parsed_list(
        parsed, 'tier', pytest.mark.tier))
    config.pluginmanager.register(MarkFromMap.from_parsed_list(
        parsed, 'requirement', pytest.mark.requirement))
    config.pluginmanager.register(MarkFromMap.from_parsed_list(parsed, 'type',
                                                               pytest.mark.__getattr__))


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--tier', type=int, action='append', help='only run tests of the given tiers')
    group.addoption('--requirement', type=str, action='append',
        help='only run tests of the given requirements')


def tier_matches(item, tiers):
    mark = item.get_marker('tier')
    if getattr(mark, 'args', None) is None:
        return False
    return mark.args[0] in tiers


def requirement_matches(item, requirements):
    mark = item.get_marker('requirement')
    if getattr(mark, 'args', None) is None:
        return False
    return mark.args[0] in requirements


def pytest_collection_modifyitems(config, items):
    tiers = config.getoption('tier')
    requirements = config.getoption('requirement')
    if not tiers and not requirements:
        return
    # TODO(rpfannsc) trim after pytest #1373 is done
    keep, discard = [], []

    for item in items:
        if tiers and not tier_matches(item, tiers):
            discard.append(item)
            continue
        elif requirements and not requirement_matches(item, requirements):
            discard.append(item)
            continue
        else:
            keep.append(item)

    items[:] = keep
    # TODO(rpfannsc) add a reason after pytest #1372 is fixed
    config.hook.pytest_deselected(items=discard)


def generate_nodeid(mapping):
    title = mapping['Title']
    caseid = mapping['Test Case ID']
    if not caseid:
        raise ValueError('incomplete entry')

    needle = title.find('[')
    attribute_part = title[:needle].replace('.', '::')

    parameter_part = title[needle:]
    if os.sep not in caseid:
        file_part = caseid[:-needle - 1].replace('.', os.sep)
    else:
        file_part = caseid

    return "{}.py::{}{}".format(file_part, attribute_part, parameter_part)


def _clean(mapping):
    mapping.pop('', '')
    try:
        return {
            'requirement': int(mapping['Requirement']),
            'tier': int(mapping['TestTier']),
            'id': generate_nodeid(mapping),
            'type': mapping['TestType'].lower(),
        }
    except (TypeError, ValueError):
        return None


def parse(path):
    if not path.check():
        return []
    with path.open() as fp:
        return filter(None, map(_clean, csv.DictReader(fp)))


if __name__ == '__main__':
    mapping_file = project_path.join(py.std.sys.argv[1])
    print(yaml.dump(parse(mapping_file), default_flow_style=False))

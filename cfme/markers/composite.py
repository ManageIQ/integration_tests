def pytest_addoption(parser):
    """Adds options for the composite uncollection system"""
    parser.addoption("--composite-uncollect", action="store_true", default=False,
                     help="Enables composite uncollecting")
    parser.addoption("--composite-job-name", action="store", default=None,
                     help="Overrides the default job name which is derived from the appliance")
    parser.addoption("--composite-template-name", action="store", default=None,
                     help="Overrides the default template name which is obtained from trackerbot")
    parser.addoption("--composite-source", action="store", default=None,
                     help="Narrow down composite uncollection by providing a source")


def pytest_collection_modifyitems(session, config, items):
    if not config.getvalue('composite_uncollect'):
        return

    from fixtures.artifactor_plugin import get_test_idents
    from fixtures.pytest_store import store

    from cfme.utils.log import logger
    from cfme.utils.trackerbot import composite_uncollect

    len_collected = len(items)

    new_items = []

    build = store.current_appliance.build
    if str(store.current_appliance.version) not in build:
        build = "{}-{}".format(str(store.current_appliance.version), build)

    source = config.getoption('composite_source')
    if not source:
        source = 'jenkins'

    store.terminalreporter.write(
        'Attempting Uncollect for build: {} and source: {}'.format(build, source), bold=True)

    pl = composite_uncollect(build, source)

    if pl:
        for test in pl['tests']:
            pl['tests'][test]['old'] = True

        # Here we pump into artifactor
        # art_client.fire_hook('composite_pump', old_artifacts=pl['tests'])
        for item in items:
            try:
                name, location = get_test_idents(item)
                test_ident = "{}/{}".format(location, name)
                status = pl['tests'][test_ident]['statuses']['overall']

                if status == 'passed':
                    logger.info('Uncollecting {} as it passed last time'.format(item.name))
                    continue
                else:
                    new_items.append(item)
            except:
                new_items.append(item)

        items[:] = new_items

    len_filtered = len(items)
    filtered_count = len_collected - len_filtered
    store.uncollection_stats['composite_uncollect'] = filtered_count

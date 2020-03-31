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

    from cfme.fixtures.artifactor_plugin import get_test_idents
    from cfme.fixtures.pytest_store import store

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
        f'Attempting Uncollect for build: {build} and source: {source}\n', bold=True)

    # The following code assumes slaves collect AFTER master is done, this prevents a parallel
    # speed up, but in the future we may move uncollection to a later stage and only do it on
    # master anyway.
    if store.parallelizer_role == 'master':
        # Master always stores the composite uncollection
        store.terminalreporter.write('Storing composite uncollect in cache...\n')
        pl = composite_uncollect(build, source)
        config.cache.set('miq-composite-uncollect', pl)
    else:
        # Slaves always retrieve from cache
        logger.info('Slave retrieving composite uncollect from cache')
        pl = config.cache.get('miq-composite-uncollect', None)

    if pl:
        for test in pl['tests']:
            pl['tests'][test]['old'] = True

        # Here we pump into artifactor
        # art_client.fire_hook('composite_pump', old_artifacts=pl['tests'])
        for item in items:
            try:
                name, location = get_test_idents(item)
                test_ident = f"{location}/{name}"
                status = pl['tests'][test_ident]['statuses']['overall']

                if status == 'passed':
                    logger.info(f'Uncollecting {item.name} as it passed last time')
                    continue
                else:
                    new_items.append(item)
            except Exception:
                new_items.append(item)

        items[:] = new_items

    len_filtered = len(items)
    filtered_count = len_collected - len_filtered
    store.uncollection_stats['composite_uncollect'] = filtered_count

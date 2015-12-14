from fixtures.artifactor_plugin import get_test_idents
from utils.composite import ReportCompile
from fixtures.pytest_store import store
from fixtures.artifactor_plugin import art_client
from utils.log import logger
from utils import version
from utils.trackerbot import api


def pytest_addoption(parser):
    parser.addoption("--composite-uncollect", action="store_true", default=False,
                     help="Enables composite uncollecting")
    parser.addoption("--composite-job-name", action="store", default=None,
                     help="Overrides the default job name which is derived from the appliance")
    parser.addoption("--composite-template-name", action="store", default=None,
                     help="Overrides the default template name which is obtained from trackerbot")


def pytest_collection_modifyitems(session, config, items):
    if not config.getvalue('composite_uncollect'):
        return

    len_collected = len(items)

    new_items = []

    try:
        stream_name = version.get_stream(version.current_version())
        job_name = config.getvalue('composite_job_name') or "{}-tests".format(stream_name)
        template_name = config.getvalue('composite_template_name') or \
            api().group.get(name=stream_name)['objects'][0]['latest_template']
        store.terminalreporter.write(
            "Trying to collect composite results for "
            "stream [{}], template [{}] and job [{}]\n".format(
                stream_name, template_name, job_name))
        if stream_name == "upstream":
            rc = ReportCompile(job_name=job_name, template=template_name, num_builds=5)
        else:
            rc = ReportCompile(job_name=job_name, template=template_name)
        pl = rc.compile()
    except Exception as e:
        store.terminalreporter.write("Stream collection failed: {}\n".format(e))
        pl = None

    if pl:
        for test in pl['tests']:
            pl['tests'][test]['old'] = True

        # Here we pump into artifactor
        art_client.fire_hook('composite_pump', old_artifacts=pl['tests'])
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

    if filtered_count:
        # A warning should go into log/cfme.log when a test has this mark applied.
        # It might be good to write uncollected test names out via terminalreporter,
        # but I suspect it would be extremely spammy. It might be useful in the
        # --collect-only output?
        store.terminalreporter.write(
            '{} tests uncollected because they previously passed'.format(filtered_count), bold=True)

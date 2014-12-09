from contextlib import contextmanager
import os.path
import function_trace

import cfme
import utils.log
import inspect
import multimethods

from fixtures.artifactor_plugin import art_client
# disable traceback of the tracer functions
function_trace.__tracebackhide__ = True

default_to_trace = None
manual_depths = None
default_depths = None
to_trace = None
depths = None

# Constants (eventually move to function_trace)
IGNORE = 0
THIS_ONLY = 1  # Don't go deeper in this function


def import_module(module_str):
    """Use __import__ to import a module and then retrieve the imported submodule"""
    root = __import__(module_str)
    path = module_str.split(".")[1:]
    result = root
    for step in path:
        result = getattr(result, step)
    return result


def load():
    global default_to_trace
    global manual_depths
    global default_depths
    global to_trace
    global depths

    # import everything we want to trace
    default_to_trace = function_trace.mapcat(
        function_trace.all,
        map(
            import_module,
            [
                "cfme.automate.buttons",
                "cfme.automate.explorer",
                "cfme.automate.provisioning_dialogs",
                "cfme.automate.service_dialogs",
                "cfme.automate.simulation",
                "cfme.cloud.availability_zone",
                "cfme.cloud.flavor",
                "cfme.cloud.instance",
                "cfme.cloud.provider",
                "cfme.cloud.security_group",
                "cfme.cloud.tenant",
                "cfme.configure.configuration",
                "cfme.configure.configuration.candu",
                "cfme.configure.about",
                "cfme.configure.settings",
                "cfme.configure.red_hat_updates",
                "cfme.configure.tasks",
                "cfme.configure.access_control",
                "cfme.control.explorer",
                "cfme.control.import_export",
                "cfme.control.snmp_form",
                "cfme.fixtures.pytest_selenium",
                "cfme.infrastructure.cluster",
                "cfme.infrastructure.datastore",
                "cfme.infrastructure.host",
                "cfme.infrastructure.provider",
                "cfme.infrastructure.pxe",
                "cfme.infrastructure.resource_pool",
                "cfme.infrastructure.virtual_machines",
                "cfme.intelligence.chargeback",
                "cfme.intelligence.reports.dashboards",
                "cfme.intelligence.reports.import_export",
                "cfme.intelligence.reports.menus",
                "cfme.intelligence.reports.reports",
                "cfme.intelligence.reports.saved",
                "cfme.intelligence.reports.schedules",
                "cfme.intelligence.reports.ui_elements",
                "cfme.intelligence.reports.widgets",
                "cfme.dashboard",
                "cfme.login",
                "cfme.provisioning",
                "cfme.services.requests",
                "cfme.services.catalogs.catalog_item",
                "cfme.services.catalogs.catalog",
                "cfme.services.catalogs.cloud_catalog_item",
                "cfme.services.catalogs.service_catalogs",
                "cfme.services.catalogs.myservice",
                "cfme.storage.file_shares",
                "cfme.storage.filers",
                "cfme.storage.luns",
                "cfme.storage.managers",
                "cfme.storage.volumes",
                "cfme.web_ui",
                "cfme.web_ui.accordion",
                "cfme.web_ui.cfme_exception",
                "cfme.web_ui.expression_editor",
                "cfme.web_ui.flash",
                "cfme.web_ui.form_buttons",
                "cfme.web_ui.listaccordion",
                "cfme.web_ui.menu",
                "cfme.web_ui.mixins",
                "cfme.web_ui.multibox",
                "cfme.web_ui.paginator",
                "cfme.web_ui.search",
                "cfme.web_ui.tabstrip",
                "cfme.web_ui.toolbar",
                "utils.appliance",
                "utils.events",
                "utils.ext_auth",
                "utils.hosts",
                "utils.mgmt_system",
                "utils.randomness",
                "utils.rest_api",
                "utils.smtp_collector_client",
                "utils.ssh",
                "multimethods",
            ]))
    # 0 = do not trace into

    manual_depths = {cfme.fixtures.pytest_selenium.wait_until: IGNORE,
                     cfme.fixtures.pytest_selenium.wait_for_ajax: IGNORE,
                     cfme.fixtures.pytest_selenium.elements: IGNORE,
                     cfme.fixtures.pytest_selenium.element: IGNORE,
                     cfme.fixtures.pytest_selenium.browser: IGNORE,
                     cfme.fixtures.pytest_selenium.move_to_element: IGNORE,
                     cfme.fixtures.pytest_selenium.wait_for_element: IGNORE,
                     cfme.fixtures.pytest_selenium.click: THIS_ONLY,
                     cfme.fixtures.pytest_selenium.set_text: THIS_ONLY,
                     cfme.fixtures.pytest_selenium.detect_observed_field: IGNORE,
                     cfme.fixtures.pytest_selenium.select: THIS_ONLY,
                     cfme.fixtures.pytest_selenium.check: THIS_ONLY,
                     cfme.web_ui.toolbar.is_greyed: THIS_ONLY,
                     cfme.web_ui.flash.message: THIS_ONLY,
                     cfme.web_ui.fill_tag: IGNORE,
                     utils.log.ArtifactorLoggerAdapter.process: IGNORE,
                     multimethods.MultiMethod.get_method: IGNORE,
                     utils.ssh.command_runner: IGNORE,
                     utils.ssh.rake_runner: IGNORE,
                     utils.ssh.version_getter: IGNORE,
                     utils.ssh.build_datetime_getter: IGNORE,
                     utils.ssh.is_downstream_getter: IGNORE,
                     utils.ssh.appliance_has_netapp: IGNORE,
                     utils.ssh.scp_putter: IGNORE,
                     utils.ssh.scp_getter: IGNORE,
                     cfme.web_ui.menu.any_box_displayed: THIS_ONLY,
                     }

    default_depths = function_trace.add_all_at_depth(manual_depths, inspect, 0)
    to_trace = default_to_trace
    depths = default_depths


def pytest_addoption(parser):
    parser.addoption("--no-tracer", dest="tracer", action="store_false", default=True,
                     help="Disable the function tracer")


def pytest_configure(config):
    if config.getoption("tracer"):
        load()


def pytest_runtest_call(__multicall__, item):
    """hook to run each test with traced function calls"""
    if item.config.getvalue('tracer'):
        out = art_client.fire_hook('filedump', grab_result=True,
                                   test_name=item.name, test_location=item.parent.name,
                                   filename="function_trace.txt", contents="",
                                   fd_ident="func_trace")
        if out:
            filename = os.path.join(out['artifact_path'], 'filedump-function_trace.txt')
        else:
            filename = './tracelogs/' + item.name.replace("/", "_")
        with function_trace.trace_on(
                tracer=function_trace.PerThreadFileTracer(
                    to_trace,
                    depths=depths,
                    filename=filename)):
            __multicall__.execute()


@contextmanager
def trace_on():
    with function_trace.trace_on(
            tracer=function_trace.StdoutTracer(
                to_trace,
                depths=depths)):
        yield

# fix the representation of various classes to not suck

# setattr(webelement.WebElement, '__repr__', pretty.pr_obj(['tag_name', 'id', 'text']))
# setattr(Exception, '__repr__', pretty.pr_obj(['message']))

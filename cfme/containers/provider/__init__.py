import re
import random
from random import sample
from traceback import format_exc

from navmazing import NavigateToSibling, NavigateToAttribute

from widgetastic_patternfly import (
    SelectorDropdown, Dropdown, BootstrapSelect, Input, Button, Tab, FlashMessages
)
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import Text, View, TextInput
from widgetastic_manageiq import (
    SummaryTable, BreadCrumb, Accordion, ManageIQTree
)
from widgetastic.exceptions import RowNotFound

from wrapanapi.utils import eval_strings

from cfme import exceptions
from cfme.base.credential import TokenCredential
from cfme.base.login import BaseLoggedInPage
from cfme.common import TagPageView
from cfme.common.provider import BaseProvider, DefaultEndpoint, DefaultEndpointForm
from cfme.common.provider_views import (
    BeforeFillMixin, ContainerProviderAddView, ContainerProvidersView,
    ContainerProviderEditView, ContainerProviderEditViewUpdated, ProvidersView,
    ContainerProviderAddViewUpdated, ProviderSideBar,
    ProviderDetailsToolBar, ContainerProviderDetailsView
)
from cfme.utils import version
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.browser import browser
from cfme.utils.pretty import Pretty
from cfme.utils.varmeth import variable
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


class ContainersProviderDefaultEndpoint(DefaultEndpoint):
    """Represents Containers Provider default endpoint"""
    credential_class = TokenCredential

    @property
    def view_value_mapping(self):
        out = {
            'hostname': self.hostname,
            'password': self.token,
            'api_port': self.api_port
        }
        if version.current_version() >= '5.8':
            out['sec_protocol'] = self.sec_protocol
            if self.sec_protocol.lower() == 'ssl trusting custom ca' and \
                    hasattr(self, 'get_ca_cert'):
                out['trusted_ca_certificates'] = self.get_ca_cert()
        if version.current_version() < '5.9':
            out['confirm_password'] = self.token

        return out


class ContainersProviderEndpointsForm(View):
    """
     represents default Containers Provider endpoint form in UI (Add/Edit dialogs)
    """
    @View.nested
    class default(Tab, DefaultEndpointForm, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Default'
        sec_protocol = BootstrapSelect('default_security_protocol')
        # trusted_ca_certificates appears only in 5.8
        trusted_ca_certificates = TextInput('default_tls_ca_certs')
        api_port = Input('default_api_port')

    @View.nested
    class hawkular(Tab, BeforeFillMixin):  # NOQA
        TAB_NAME = 'Hawkular'
        sec_protocol = BootstrapSelect(id='hawkular_security_protocol')
        TAB_NAME = VersionPick({
            Version.lowest(): 'Hawkular',
            '5.9': 'Metrics'
        })
        sec_protocol = VersionPick({
            Version.lowest(): BootstrapSelect(id='hawkular_security_protocol'),
            '5.9': BootstrapSelect(id='metrics_security_protocol')
        })
        # trusted_ca_certificates appears only in 5.8
        trusted_ca_certificates = VersionPick({
            Version.lowest(): TextInput('hawkular_tls_ca_certs'),
            '5.9': TextInput('metrics_tls_ca_certs')
        })
        hostname = VersionPick({
            Version.lowest(): Input('hawkular_hostname'),
            '5.9': Input('metrics_hostname')
        })
        api_port = VersionPick({
            Version.lowest(): Input('hawkular_api_port'),
            '5.9': Input('metrics_api_port')
        })
        validate = Button('Validate')


class LoggingableView(View):

    monitor = Dropdown('Monitoring')

    def get_logging_url(self):

        def report_kibana_failure():
            raise RuntimeError("Kibana not found in the window title or content")

        browser_instance = browser()

        all_windows_before = browser_instance.window_handles
        appliance_window = browser_instance.current_window_handle

        self.monitor.item_select('External Logging')

        all_windows_after = browser_instance.window_handles

        new_windows = set(all_windows_after) - set(all_windows_before)

        if not new_windows:
            raise RuntimeError("No logging window was open!")

        logging_window = new_windows.pop()
        browser_instance.switch_to_window(logging_window)

        logging_url = browser_instance.current_url

        wait_for(lambda: "kibana" in
                         browser_instance.title.lower() + " " +
                         browser_instance.page_source.lower(),
                 fail_func=report_kibana_failure, num_sec=60, delay=5)

        browser_instance.close()
        browser_instance.switch_to_window(appliance_window)

        return logging_url


class ContainersProvider(BaseProvider, Pretty):
    PLURAL = 'Providers'
    provider_types = {}
    in_version = ('5.5', version.LATEST)
    category = "container"
    pretty_attrs = ['name', 'key', 'zone', 'metrics_type']
    STATS_TO_MATCH = [
        'num_project',
        'num_service',
        'num_replication_controller',
        'num_pod',
        'num_node',
        'num_image_registry',
        'num_container']
    # TODO add 'num_volume'
    string_name = "Containers"
    page_name = "containers"
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    quad_name = None
    db_types = ["ContainerManager"]
    endpoints_form = ContainersProviderEndpointsForm
    all_view = ContainerProvidersView
    details_view = ContainerProviderDetailsView

    def __init__(
            self,
            name=None,
            key=None,
            zone=None,
            metrics_type=None,
            endpoints=None,
            provider_data=None,
            appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.key = key
        self.zone = zone
        self.endpoints = endpoints
        self.provider_data = provider_data
        self.metrics_type = (metrics_type if self.appliance.version >= '5.9' else None)

    @property
    def view_value_mapping(self):
        return {
            'name': self.name,
            'prov_type': self.type,
            'zone': self.zone,
            'metrics_type': self.metrics_type
        }

    @variable(alias='db')
    def num_project(self):
        return self._num_db_generic('container_projects')

    @num_project.variant('ui')
    def num_project_ui(self):
        return int(self.get_detail("Relationships", "Projects"))

    @variable(alias='db')
    def num_service(self):
        return self._num_db_generic('container_services')

    @num_service.variant('ui')
    def num_service_ui(self):
        if self.appliance.version < "5.7":
            name = "Services"
        else:
            name = "Container Services"
        return int(self.get_detail("Relationships", name))

    @variable(alias='db')
    def num_replication_controller(self):
        return self._num_db_generic('container_replicators')

    @num_replication_controller.variant('ui')
    def num_replication_controller_ui(self):
        return int(self.get_detail("Relationships", "Replicators"))

    @variable(alias='db')
    def num_container_group(self):
        return self._num_db_generic('container_groups')

    @num_container_group.variant('ui')
    def num_container_group_ui(self):
        return int(self.get_detail("Relationships", "Pods"))

    @variable(alias='db')
    def num_pod(self):
        # potato tomato
        return self.num_container_group()

    @num_pod.variant('ui')
    def num_pod_ui(self):
        # potato tomato
        return self.num_container_group(method='ui')

    @variable(alias='db')
    def num_node(self):
        return self._num_db_generic('container_nodes')

    @num_node.variant('ui')
    def num_node_ui(self):
        return int(self.get_detail("Relationships", "Nodes"))

    @variable(alias='db')
    def num_container(self):
        # Containers are linked to providers through container definitions and then through pods
        res = self.appliance.db.client.engine.execute(
            "SELECT count(*) "
            "FROM ext_management_systems, container_groups, container_definitions, containers "
            "WHERE containers.container_definition_id=container_definitions.id "
            "AND container_definitions.container_group_id=container_groups.id "
            "AND container_groups.ems_id=ext_management_systems.id "
            "AND ext_management_systems.name='{}'".format(self.name))
        return int(res.first()[0])

    @num_container.variant('ui')
    def num_container_ui(self):
        return int(self.get_detail("Relationships", "Containers"))

    @variable(alias='db')
    def num_image(self):
        return self._num_db_generic('container_images')

    @num_image.variant('ui')
    def num_image_ui(self):
        if self.appliance.version < "5.7":
            name = "Images"
        else:
            name = "Container Images"
        return int(self.get_detail("Relationships", name))

    @variable(alias='db')
    def num_image_registry(self):
        return self._num_db_generic('container_image_registries')

    @num_image_registry.variant('ui')
    def num_image_registry_ui(self):
        return int(self.get_detail("Relationships", "Image Registries"))

    def pods_per_ready_status(self):
        """Grabing the Container Statuses Summary of the pods from API"""
        #  TODO: Add later this logic to wrapanapi
        entities = self.mgmt.api.get('pod')[1]['items']
        out = {}
        for entity_j in entities:
            out[entity_j['metadata']['name']] = {
                condition['type']: eval_strings([condition['status']]).pop()
                for condition in entity_j['status'].get('conditions', [])
            }
        return out


@navigator.register(ContainersProvider, 'All')
class All(CFMENavigateStep):
    VIEW = ContainerProvidersView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Providers')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("Grid View")
        self.view.paginator.check_all()
        self.view.paginator.uncheck_all()


@navigator.register(ContainersProvider, 'Add')
class Add(CFMENavigateStep):

    def container_provider_view_class(self):
        return VersionPick({
            Version.lowest(): ContainerProviderAddView,
            '5.9': ContainerProviderAddViewUpdated
        })

    @property
    def VIEW(self):  # noqa
        return self.container_provider_view_class().pick(self.obj.appliance.version)
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select(
            VersionPick({
                Version.lowest(): 'Add Existing Containers Provider',
                '5.9': 'Add a new Containers Provider'
            }).pick(self.obj.appliance.version))


@navigator.register(ContainersProvider, 'Details')
class Details(CFMENavigateStep):
    VIEW = ContainerProviderDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(self.obj.name,
                                                   surf_pages=True).click()

    def resetter(self):
        self.view.toolbar.view_selector.select("Summary View")


@navigator.register(ContainersProvider, 'Edit')
class Edit(CFMENavigateStep):

    def container_provider_edit_view_class(self):
        return VersionPick({
            Version.lowest(): ContainerProviderEditView,
            '5.9': ContainerProviderEditViewUpdated
        })

    @property
    def VIEW(self):  # noqa
        return self.container_provider_edit_view_class().pick(self.obj.appliance.version)
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(by_name=self.obj.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.configuration.item_select(
            'Edit Selected Containers Provider')


@navigator.register(ContainersProvider, 'EditFromDetails')
class EditFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Containers Provider')


@navigator.register(ContainersProvider, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(self.obj.name,
                                                   surf_pages=True).click()
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(ContainersProvider, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(ContainersProvider, 'TimelinesFromDetails')
class TimelinesFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(ContainersProvider, 'TopologyFromDetails')
class TopologyFromDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        # TODO: implement topology view
        self.prerequisite_view.toolbar.view_selector.select("Topology View")


class AdHocMetricsView(BaseLoggedInPage):
    filter_dropdown = SelectorDropdown('uib-tooltip', 'Filter by')
    filter_result_header = Text('h5.ng-binding')
    apply_btn = Button("Apply Filters")

    selected_filter = None

    @property
    def is_displayed(self):
        return False

    def wait_for_filter_option_to_load(self):
        wait_for(lambda: bool(self.filter_dropdown.items), delay=5, num_sec=60)

    def wait_for_results_to_load(self):
        wait_for(lambda: bool(int(self.filter_result_header.text.split()[0])),
                 delay=5, num_sec=60)

    def apply_filter(self):
        self.apply_btn.click()

    def set_filter(self, desired_filter):
        self.selected_filter = desired_filter
        self.filter_dropdown.fill_with(desired_filter)

    def get_random_filter(self):
        return str(random.choice(self.filter_dropdown.items))

    def get_total_results_count(self):
        return int(self.filter_result_header.text.split()[0])


@navigator.register(ContainersProvider, 'AdHoc')
class AdHocMain(CFMENavigateStep):
    VIEW = AdHocMetricsView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.monitor.item_select('Ad hoc Metrics')


class ContainerObjectAllBaseView(ProvidersView):
    """Base class for container object All view.
    SUMMARY_TEXT should be defined in child.
    """
    summary = Text('//div[@id="main-content"]//h1')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    @property
    def table(self):
        return self.entities.elements

    @property
    def is_displayed(self):
        return self.summary.text == self.SUMMARY_TEXT


class ContainerObjectDetailsEntities(View):
    properties = SummaryTable(title="Properties")
    status = SummaryTable(title="Status")
    relationships = SummaryTable(title="Relationships")
    overview = SummaryTable(title="Overview")
    smart_management = SummaryTable(title="Smart Management")
    labels = SummaryTable(title="Labels")


class ContainerObjectDetailsBaseView(BaseLoggedInPage, LoggingableView):

    title = Text('//div[@id="main-content"]//h1')
    breadcrumb = BreadCrumb(locator='//ol[@class="breadcrumb"]')
    toolbar = View.nested(ProviderDetailsToolBar)
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')

    entities = View.nested(ContainerObjectDetailsEntities)

    @View.nested
    class sidebar(ProviderSideBar):  # noqa

        @View.nested
        class properties(Accordion):  # noqa
            tree = ManageIQTree()

        @View.nested
        class relationships(Accordion):  # noqa
            tree = ManageIQTree()

    @property
    def is_displayed(self):
        return (
            self.title.is_displayed and
            self.breadcrumb.is_displayed and
            self.breadcrumb.active_location == '{} (Summary)'.format(self.context['object'].name)
        )


# Common methods:

class ContainersTestItem(object):
    """This is a generic test item. Especially used for parametrized functions
    """
    __test__ = False

    def __init__(self, obj, polarion_id, **additional_attrs):
        """Args:
            * obj: The container object in this test (e.g. Image)
            * The polarion test case ID
        """
        self.obj = obj
        self.polarion_id = polarion_id
        for name, value in additional_attrs.items():
            self.__setattr__(name, value)

    def pretty_id(self):
        return '{} ({})'.format(
            getattr(self.obj, '__name__', str(self.obj)),
            self.polarion_id)

    @classmethod
    def get_pretty_id(cls, obj):
        """Since sometimes the test object is wrapped within markers,
        it's difficult to find get it inside the args tree.
        hence we use this to get the object and all pretty_id function.

        Args:
            * obj: Either a ContainersTestItem or a marker that include it
        returns:
            str pretty id
        """
        if isinstance(obj, cls):
            return obj.pretty_id()
        elif hasattr(obj, 'args') and hasattr(obj, '__iter__'):
            for arg in obj.args:
                pretty_id = cls.get_pretty_id(arg)
                if pretty_id:
                    return pretty_id


class LoadDetailsMixin(object):
    """Embed load details functionality for objects -
    required for some classes like PolicyProfileAssignable"""
    def load_details(self, refresh=False):
        view = navigate_to(self, 'Details')
        if refresh:
            view.browser.refresh()

    def get_detail(self, table_name, field_name):
        """ Gets details from the details infoblock
        Args:
            table_name: the name of the table to get the data from.
            table: the name of the field to get from this table.
        Returns: A string representing the contents of the summary's value.
        """
        view = navigate_to(self, 'Details')
        table = getattr(view, table_name.lower(), getattr(view.entities, table_name.lower()))
        return table.read().get(field_name)


class Labelable(object):
    """Provide the functionality to set labels"""
    _LABEL_NAMEVAL_PATTERN = re.compile(r'^[A-Za-z0-9_.]+$')

    def get_labels(self):
        """List labels"""
        return self.mgmt.list_labels()

    def set_label(self, name, value):

        """Sets a label to the object instance

        Args:
            :var name: the name of the label
            :var value: the value of the label

        Returns:
            self.mgmt.set_label return value.
        """
        assert self._LABEL_NAMEVAL_PATTERN.match(name), \
            'name part ({}) must match the regex pattern {}'.format(
                name, self._LABEL_NAMEVAL_PATTERN.pattern)
        assert self._LABEL_NAMEVAL_PATTERN.match(value), \
            'value part ({}) must match the regex pattern {}'.format(
                value, self._LABEL_NAMEVAL_PATTERN.pattern)
        return self.mgmt.set_label(name, value)

    def remove_label(self, name, silent_failure=False):
        """Remove label by name.
        Args:
            name: name of label
            silent_failure: whether to raise an error or not in case of failure.

        Returns: ``bool`` pass or fail

        Raises:
            :py:class:`LabelNotFoundException`.
        """
        try:
            self.mgmt.delete_label(name)
            return True
        except Exception:  # TODO: add appropriate exception in wrapanapi
            failure_signature = format_exc()
            if silent_failure:
                logger.warning(failure_signature)
                return False
            raise exceptions.LabelNotFoundException(failure_signature)


def navigate_and_get_rows(provider, obj, count, silent_failure=False):
    """Get <count> random rows from the obj list table,
    if <count> is greater that the number of rows, return number of rows.

    Args:
        provider: containers provider
        obj: the containers object
        table: the object's Table object
        count: number of random rows to return
        silent_failure: If True and no records found for obj, it'll
                        return None instead of raise exception

    return: list of rows"""

    view = navigate_to(obj, 'All')
    view.toolbar.view_selector.list_button.click()
    if filter(lambda msg: 'No Records Found.' in msg.text, view.flash.messages) and silent_failure:
        return []
    view.paginator.set_items_per_page(1000)
    rows = list(view.table.rows())
    if not rows:
        return []

    return sample(rows, min(count, len(rows)))


def click_row(view, **filters):
    """Since we still unable to get entity by multiple elements (not only by name),
    We have this workaround for the navigation to details page.
    Args:
        view (ContainerObjectAllBaseView): the prerequisite view of the details view.
        filters: the filters, the elements of this object.
    """
    view.toolbar.view_selector.select('List View')
    for _ in view.paginator.pages():
        try:
            row = view.table.row(**filters)
            row.click()
            break
        except RowNotFound:
            pass


def refresh_and_navigate(*args, **kwargs):
    # Refreshing the page and navigate - we need this for cases that we already in
    # the page and want to reload it
    view = navigate_to(*args, **kwargs)
    view.browser.refresh()
    return view

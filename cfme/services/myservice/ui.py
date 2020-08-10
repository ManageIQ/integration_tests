from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import Parameter
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import CandidateNotFound
from widgetastic_patternfly import Dropdown

from cfme.common import BaseLoggedInPage
from cfme.common import TagPageView
from cfme.common.vm_views import VMDetailsEntities
from cfme.exceptions import displayed_not_implemented
from cfme.exceptions import ItemNotFound
from cfme.exceptions import RestLookupError
from cfme.services.myservice import MyService
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.appliance.implementations.ui import ViaUI
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import Calendar
from widgetastic_manageiq import EntitiesConditionalView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import JSBaseEntity
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import ParametrizedSummaryTable
from widgetastic_manageiq import ReactTextInput
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable


class MyServiceToolbar(View):
    """
    Represents provider toolbar and its controls
    """
    reload = Button(title='Refresh this page')
    configuration = Dropdown(text='Configuration')
    policy = Dropdown(text='Policy')
    lifecycle = Dropdown(text='Lifecycle')
    download = Dropdown(text='Download')
    view_selector = View.nested(ItemsToolBarViewSelector)


class MyServicesView(BaseLoggedInPage):
    toolbar = View.nested(MyServiceToolbar)
    search = View.nested(Search)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def in_myservices(self):
        # Slicing in currently_selected is workaround for BZ-1733489
        nav_selected = (
            self.navigation.currently_selected[:2]
            if BZ(1733489).blocks
            else self.navigation.currently_selected
        )
        return (
            self.logged_in_as_current_user and
            nav_selected == ["Services", "My Services"]
        )

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.toolbar.configuration.is_displayed and
            not self.myservice.is_dimmed
        )

    @View.nested
    class myservice(Accordion):  # noqa
        # Note: Services in tree now hidden to improve performance BZ-1692531
        ACCORDION_NAME = 'Services'
        tree = ManageIQTree()


class ServiceRetirementForm(MyServicesView):
    title = Text('#explorer_title_text')

    retirement_date = Calendar('retirement_date_datepicker')
    retirement_warning = BootstrapSelect('retirement_warn')


class ServiceEditForm(MyServicesView):
    title = Text('#explorer_title_text')

    name = ReactTextInput(name='name')
    description = ReactTextInput(name='description')


class SetOwnershipForm(MyServicesView):
    title = Text('#explorer_title_text')

    select_owner = BootstrapSelect('user_name')
    select_group = BootstrapSelect('group_name')


class MyServiceDetailsToolbar(MyServiceToolbar):
    """View of toolbar widgets to nest"""
    @ParametrizedView.nested
    class custom_button(ParametrizedView):  # noqa
        PARAMETERS = ('button_group', )
        _dropdown = Dropdown(text=Parameter('button_group'))

        def item_select(self, button, handle_alert=None):
            self._dropdown.item_select(button, handle_alert=handle_alert)


class MyServiceDetailsEntities(View):
    """Represents Details page."""
    # TODO: use a ParametrizedSummaryTable eventually to do this
    summary = ParametrizedView.nested(ParametrizedSummaryTable)
    properties = SummaryTable(title='Properties')
    lifecycle = SummaryTable(title='Lifecycle')
    relationships = SummaryTable(title='Relationships')
    vm = SummaryTable(title='Totals for Service VMs ')
    smart_management = SummaryTable(title='Smart Management')
    generic_objects = SummaryTable(title='Generic Objects')
    vms = EntitiesConditionalView()

    @property
    def entity_class(self):
        return JSBaseEntity


class MyServiceDetailView(MyServicesView):
    title = Text('#explorer_title_text')
    toolbar = View.nested(MyServiceDetailsToolbar)
    entities = View.nested(MyServiceDetailsEntities)
    provisioning_tab = Text('//*[@id="provisioning_tab"]')
    retirement_tab = Text('//*[@id="retirement_tab"]')

    @View.nested
    class provisioning(View):  # noqa
        results = SummaryTable(title='Results')
        plays = Table('.//table[./thead/tr/th[contains(@align, "left") and '
                      'normalize-space(.)="Plays"]]')
        details = SummaryTable(title='Details')
        credentials = SummaryTable(title='Credentials')
        standart_output = Text('.//div[@id="provisioning"]//pre')

    @View.nested
    class retirement(View):  # noqa
        results = SummaryTable(title='Results')
        plays = Table('.//table[./thead/tr/th[contains(@align, "left") and '
                      'normalize-space(.)="Plays"]]')
        details = SummaryTable(title='Details')
        credentials = SummaryTable(title='Credentials')
        standart_output = Text('.//div[@id="retirement"]//pre')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.myservice.is_opened and
            self.title.text == 'Service "{}"'.format(self.context['object'].name))


class EditMyServiceView(ServiceEditForm):
    title = Text('#explorer_title_text')

    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.myservice.is_opened and
            self.title.text == 'Editing Service "{}"'.format(self.context['object'].name)
        )


class SetOwnershipView(SetOwnershipForm):
    title = Text('#explorer_title_text')

    save_button = Button('Save')

    is_displayed = displayed_not_implemented


@MiqImplementationContext.external_for(MyService.get_ownership, ViaUI)
def get_ownership(self, owner, group):
    view = navigate_to(self, 'Details')
    exists = (view.entities.lifecycle.get_text_of("Owner") == owner and
              view.entities.lifecycle.get_text_of("Group") == group)
    return exists


class ServiceRetirementView(ServiceRetirementForm):
    title = Text('#explorer_title_text')

    save_button = Button('Save')

    @property
    def is_displayed(self):
        return (
            self.in_myservices and
            self.myservice.is_opened and
            self.title.text == 'Set/Remove retirement date for Service'
        )


class ReconfigureServiceView(SetOwnershipForm):
    title = Text('#explorer_title_text')

    submit_button = Button('Submit')

    @property
    def is_displayed(self):
        name = self.context['object'].name
        if BZ(1658906).blocks:
            # there is shorten name in view title due to above BZ
            name = self.context['object'].name.split('-')[0]

        return (
            self.in_myservices and
            self.myservice.is_opened and
            self.title.text == f'Reconfigure Service "{name}"'
        )


class ServiceVMDetailsView(VMDetailsEntities):
    @property
    def is_displayed(self):
        return self.title.text == 'VM and Instance "{}"'.format(self.context['object'].vm_name)


class AllGenericObjectInstanceView(BaseLoggedInPage):
    @View.nested
    class toolbar(View):  # noqa
        reload = Button(title='Refresh this page')
        policy = Dropdown(text='Policy')
        download = Dropdown(text='Download')
        view_selector = View.nested(ItemsToolBarViewSelector)
    title = Text('.//div[@id="main-content"]//h1')
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @property
    def is_displayed(self):
        return self.title.text == '{} (All Generic Objects)'.format(self.context['object'].name)


@MiqImplementationContext.external_for(MyService.retire, ViaUI)
def retire(self, wait=True):
    view = navigate_to(self, 'Details')
    view.toolbar.lifecycle.item_select('Retire this Service', handle_alert=True)
    view.flash.assert_no_error()

    service_request = self.appliance.collections.requests.instantiate(
        description=f"Service Retire for: {self.name}")
    if wait:
        service_request.wait_for_request()
    return service_request


@MiqImplementationContext.external_for(MyService.retire_on_date, ViaUI)
def retire_on_date(self, retirement_date):
    view = navigate_to(self, 'SetRetirement')
    view.retirement_date.fill(retirement_date)
    view.save_button.click()
    view = navigate_to(self, 'Details')
    wait_for(
        lambda: view.entities.lifecycle.get_text_of('Retirement State') == 'Retired',
        fail_func=view.toolbar.reload.click,
        num_sec=10 * 60, delay=3,
        message='Service Retirement wait')


@MiqImplementationContext.external_for(MyService.update, ViaUI)
def update(self, updates):
    view = navigate_to(self, 'Edit')
    changed = view.fill_with(updates, on_change=view.save_button, no_change=view.cancel_button)
    view.flash.assert_no_error()
    if changed:
        view.flash.assert_success_message(
            'Service "{}" was saved'.format(updates.get('name', self.name)))
    else:
        view.flash.assert_success_message(
            'Edit of Service "{}" was cancelled by the user'.format(
                updates.get('description', self.description)))
    self.create_view(MyServiceDetailView, override=updates, wait='5s')


@MiqImplementationContext.external_for(MyService.exists.getter, ViaUI)
def exists(self):
    try:
        navigate_to(self, 'Details')
        return True
    except (CandidateNotFound, ItemNotFound, RestLookupError):
        return False


@MiqImplementationContext.external_for(MyService.is_retired.getter, ViaUI)
def is_retired(self):
    view = navigate_to(self, 'Details')
    return view.entities.lifecycle.get_text_of("Retirement State") == "Retired"


@MiqImplementationContext.external_for(MyService.delete, ViaUI)
def delete(self):
    view = navigate_to(self, 'Details')
    view.toolbar.configuration.item_select("Remove Service from Inventory", handle_alert=True)
    view = self.create_view(MyServicesView, wait='5s')
    view.flash.assert_no_error()
    view.flash.assert_success_message(f'Service "{self.name}": Delete successful')


@MiqImplementationContext.external_for(MyService.status.getter, ViaUI)
def status(self):
    view = navigate_to(self, 'Details')
    return view.provisioning.results.get_text_of("Status")


@MiqImplementationContext.external_for(MyService.set_ownership, ViaUI)
def set_ownership(self, owner, group):
    view = navigate_to(self, 'SetOwnership')
    view.fill({'select_owner': owner,
               'select_group': group})
    view.save_button.click()
    view = self.create_view(MyServiceDetailView, wait='5s')
    view.flash.assert_no_error()
    view.flash.assert_success_message('Ownership saved for selected Service')


@MiqImplementationContext.external_for(MyService.edit_tags, ViaUI)
def edit_tags(self, tag, value):
    view = navigate_to(self, 'EditTagsFromDetails')
    view.fill({'select_tag': tag,
               'select_value': value})
    view.save_button.click()
    view = self.create_view(MyServiceDetailView, wait='5s')
    view.flash.assert_no_error()
    view.flash.assert_success_message('Tag edits were successfully saved')


@MiqImplementationContext.external_for(MyService.check_vm_add, ViaUI)
def check_vm_add(self, vm):
    view = navigate_to(vm, 'Details')
    assert self.name == view.entities.summary('Relationships').get_text_of('Service')


@MiqImplementationContext.external_for(MyService.download_file, ViaUI)
def download_file(self, extension):
    view = navigate_to(self, 'All')
    view.toolbar.download.item_select(f'Download as {extension}')
    view.flash.assert_no_error()


@MiqImplementationContext.external_for(MyService.reconfigure_service, ViaUI)
def reconfigure_service(self):
    # TODO refactor this method - it does nothing at the moment. Bug 1575935
    view = navigate_to(self, 'Reconfigure')
    view.submit_button.wait_displayed('5s')
    view.submit_button.click()
    view.flash.assert_no_error()
    self.create_view(MyServiceDetailView, wait='5s')


@navigator.register(MyService, 'All')
class MyServiceAll(CFMENavigateStep):
    VIEW = MyServicesView

    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'My Services')

    def resetter(self, *args, **kwargs):
        self.view.myservice.tree.click_path('Active Services')


@navigator.register(MyService, 'Details')
class MyServiceDetails(CFMENavigateStep):
    VIEW = MyServiceDetailView

    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        if self.obj.rest_api_entity.retired:
            self.view.myservice.tree.click_path('Retired Services')
        else:
            self.view.myservice.tree.click_path('Active Services')
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(MyService, 'Edit')
class MyServiceEdit(CFMENavigateStep):
    VIEW = EditMyServiceView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Service')


@navigator.register(MyService, 'SetOwnership')
class MyServiceSetOwnership(CFMENavigateStep):
    VIEW = SetOwnershipView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Set Ownership')


@navigator.register(MyService, 'EditTagsFromDetails')
class MyServiceEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(MyService, 'SetRetirement')
class MyServiceSetRetirement(CFMENavigateStep):
    VIEW = ServiceRetirementView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.lifecycle.item_select(
            'Set Retirement Dates for this Service')


@navigator.register(MyService, 'Reconfigure')
class MyServiceReconfigure(CFMENavigateStep):
    VIEW = ReconfigureServiceView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Reconfigure this Service')


@navigator.register(MyService, "VMDetails")
class MyServiceVMDetails(CFMENavigateStep):
    VIEW = ServiceVMDetailsView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.vms.get_entity(name=self.obj.vm_name).click()


@navigator.register(MyService, 'GenericObjectInstance')
class AllGenericObjectInstance(CFMENavigateStep):
    VIEW = AllGenericObjectInstanceView

    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.generic_objects.click_at('Instances')

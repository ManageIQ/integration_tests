import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import MoveTargetOutOfBoundsException
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown

from cfme.base.ui import BaseLoggedInPage
from cfme.common import Taggable
from cfme.common.vm_views import SetOwnershipView
from cfme.exceptions import ItemNotFound
from cfme.exceptions import KeyPairNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import BootstrapSelect
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Text
from widgetastic_manageiq import TextInput


class KeyPairToolbar(View):
    policy = Dropdown('Policy')
    configuration = Dropdown('Configuration')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class KeyPairDetailsToolbar(View):
    policy = Dropdown('Policy')
    configuration = Dropdown('Configuration')
    download = Button(title='Print or export summary')


class KeyPairDetailsAccordion(View):
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class KeyPairDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
    lifecycle = SummaryTable(title='Lifecycle')
    smart_management = SummaryTable(title='Smart Management')


class KeyPairAddEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')


class KeyPairAddForm(View):
    name = TextInput(id='name')
    public_key = TextInput(id='public_key')
    provider = BootstrapSelect(id='ems_id')
    add = Button('Add')
    cancel = Button('Cancel')


class KeyPairView(BaseLoggedInPage):
    """Base view for header and nav checking, navigatable views should inherit this"""
    @property
    def in_keypair(self):
        return(
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Key Pairs']
        )


class KeyPairAllView(KeyPairView):
    @property
    def is_displayed(self):
        return (
            self.in_keypair and
            self.entities.title.text == 'Key Pairs')

    paginator = PaginationPane()
    toolbar = View.nested(KeyPairToolbar)
    search = View.nested(Search)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class KeyPairDetailsView(KeyPairView):
    @property
    def is_displayed(self):
        obj = self.context['object']
        return (
            self.in_keypair and
            self.entities.title.text == obj.expected_details_title and
            self.entities.breadcrumb.active_location == obj.expected_details_breadcrumb
        )

    toolbar = View.nested(KeyPairDetailsToolbar)
    sidebar = View.nested(KeyPairDetailsAccordion)
    entities = View.nested(KeyPairDetailsEntities)


class KeyPairAddView(KeyPairView):
    @property
    def is_displayed(self):
        return (
            self.in_keypair and
            self.entities.breadcrumb.active_location == 'Add New Key Pair' and
            self.entities.title.text == 'Add New Key Pair')

    entities = View.nested(KeyPairAddEntities)
    form = View.nested(KeyPairAddForm)


@attr.s
class KeyPair(BaseEntity, Taggable):
    """ Automate Model page of KeyPairs

    Args:
        name: Name of Keypairs.
    """
    _param_name = "KeyPair"

    name = attr.ib()
    provider = attr.ib(default=None)
    public_key = attr.ib(default="")

    def delete(self, cancel=False, wait=False):
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove this Key Pair from Inventory',
                                               handle_alert=(not cancel))
        # cancel doesn't redirect, confirmation does
        view.flush_widget_cache()
        if cancel:
            view = self.create_view(KeyPairDetailsView)
        else:
            view = self.create_view(KeyPairAllView)
        wait_for(lambda: view.is_displayed, fail_condition=False, num_sec=10, delay=1)

        # flash message only displayed if it was deleted
        if not cancel:
            view.flash.assert_no_error()
            view.flash.assert_success_message('Delete initiated for 1 Key Pair')

        if wait:
            def refresh():
                self.provider.refresh_provider_relationships()
                view.browser.refresh()
                view.flush_widget_cache()

            view = navigate_to(self.parent, 'All')

            wait_for(
                lambda: self.name in view.entities.all_entity_names,
                message="Wait keypairs to disappear",
                fail_condition=True,
                num_sec=300,
                delay=5,
                fail_func=refresh
            )

    def download_private_key(self):
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select('Download private key')
        view.flash.assert_no_error()

    def set_ownership(self, owner=None, group=None, cancel=False, reset=False):
        """Set keypair ownership

        Args:
            user (User): user object for ownership
            group (Group): group object for ownership
            click_cancel (bool): Whether to cancel form submission
            click_reset (bool): Whether to reset form after filling
        """
        view = navigate_to(self, 'SetOwnership', wait_for_view=0)
        fill_result = view.form.fill({
            'user_name': owner.name if owner else None,
            'group_name': group.description if group else None})
        if not fill_result:
            view.form.cancel_button.click()
            view = self.create_view(navigator.get_class(self, 'Details').VIEW)
            view.flash.assert_no_error()
            return

        # Only if the form changed
        if reset:
            view.form.reset_button.click()
            view.flash.assert_message('All changes have been reset', 'warning')
            # Cancel after reset
            assert view.form.is_displayed
            view.form.cancel_button.click()
        elif cancel:
            view.form.cancel_button.click()
            view.flash.assert_no_error()
        else:
            # save the form
            view.form.save_button.click()
            view = self.create_view(navigator.get_class(self, 'Details').VIEW)
            view.flash.assert_no_error()


@attr.s
class KeyPairCollection(BaseCollection):
    """ Collection object for the :py:class: `cfme.cloud.KeyPair`. """
    ENTITY = KeyPair

    def create(self, name, provider, public_key=None, cancel=False):
        """Create new keyPair.

        Args:
            name (str): name of the KeyPair
            public_key (str): RSA Key if present
            provider (str): Cloud Provider
            cancel (boolean): Cancel Keypair creation
        """

        view = navigate_to(self, 'Add')
        changed = view.form.fill({'name': name,
                                  'public_key': public_key,
                                  'provider': provider.name
                                  })
        if cancel and not changed:
            view.form.cancel.click()
            flash_message = 'Add of new Key Pair was cancelled by the user'
        else:
            view.form.add.click()
            flash_message = 'Key Pair "{}" created'.format(name)

        # add/cancel should redirect, new view
        view = self.create_view(KeyPairAllView)
        # TODO BZ 1444520 causing ridiculous redirection times after submitting the form
        wait_for(lambda: view.is_displayed, num_sec=240, delay=2,
                 fail_func=view.flush_widget_cache, handle_exception=True)
        assert view.is_displayed
        view.flash.assert_success_message(flash_message)
        keypair = self.instantiate(name, provider, public_key=public_key)
        if not cancel:
            wait_for(lambda: keypair.exists, delay=2, timeout=240, fail_func=self.browser.refresh)
        return keypair

    def all(self):
        view = navigate_to(self, 'All')
        return [self.instantiate(name) for name in view.entities.all_entity_names]


@navigator.register(KeyPairCollection, 'All')
class CloudKeyPairs(CFMENavigateStep):
    VIEW = KeyPairAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Key Pairs')


@navigator.register(KeyPair, 'Details')
class Details(CFMENavigateStep):
    VIEW = KeyPairDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            item = self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                              surf_pages=True)
        except ItemNotFound:
            raise KeyPairNotFound

        item.click()


@navigator.register(KeyPair, 'SetOwnership')
class SetOwnership(CFMENavigateStep):
    VIEW = SetOwnershipView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select('Set Ownership')


@navigator.register(KeyPairCollection, 'Add')
class Add(CFMENavigateStep):
    VIEW = KeyPairAddView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        """Raises DropdownItemDisabled from widgetastic_patternfly if no RHOS provider present"""
        try:
            self.prerequisite_view.toolbar.configuration.item_select('Add a new Key Pair')
            # TODO: Remove once fixed 1475303
        except MoveTargetOutOfBoundsException:
            self.prerequisite_view.toolbar.configuration.item_select('Add a new Key Pair')

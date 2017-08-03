# -*- coding: utf-8 -*-
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import View
from widgetastic.utils import VersionPick, Version
from widgetastic.exceptions import NoSuchElementException
from widgetastic_patternfly import Dropdown, Button, FlashMessages
from cfme.exceptions import KeyPairNotFound
from cfme.base.ui import BaseLoggedInPage
from cfme.web_ui import match_location, mixins
from utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from utils.appliance import Navigatable
from utils.wait import wait_for
from widgetastic_manageiq import (
    ItemsToolBarViewSelector, Text, TextInput, Table, Search, PaginationPane, Accordion,
    ManageIQTree, BreadCrumb, SummaryTable, BootstrapSelect)


class KeyPairToolbar(View):
    policy = Dropdown('Policy')
    configuration = Dropdown('Configuration')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class KeyPairDetailsToolbar(View):
    policy = Dropdown('Policy')
    configuration = Dropdown('Configuration')
    download = Button(title='Download summary in PDF format')


class KeyPairDetailsAccordion(View):
    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


class KeyPairEntities(View):
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='list_grid']//table")
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class KeyPairDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    table = Table("//div[@id='list_grid']//table")
    properties = SummaryTable(title='Properties')
    relationships = SummaryTable(title='Relationships')
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
            self.navigation.currently_selected == ['Compute', 'Clouds', 'Key Pairs'] and
            match_location(controller='auth_key_pair_cloud', title='Key Pairs'))


class KeyPairAllView(KeyPairView):
    @property
    def is_displayed(self):
        return (
            self.in_keypair and
            self.entities.title.text == 'Key Pairs')

    toolbar = View.nested(KeyPairToolbar)
    entities = View.nested(KeyPairEntities)
    paginator = View.nested(PaginationPane)


class KeyPairDetailsView(KeyPairView):
    @property
    def is_displayed(self):
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_keypair and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(KeyPairDetailsToolbar)
    sidebar = View.nested(KeyPairDetailsAccordion)
    entities = View.nested(KeyPairDetailsEntities)
    paginator = View.nested(PaginationPane)


class KeyPairAddView(KeyPairView):
    @property
    def is_displayed(self):
        return (
            self.in_keypair and
            self.entities.breadcrumb.active_location == 'Add New Key Pair' and
            self.entities.title.text == 'Add New Key Pair')

    entities = View.nested(KeyPairAddEntities)
    form = View.nested(KeyPairAddForm)


class KeyPairCollection(Navigatable):
    """ Collection object for the :py:class: `cfme.cloud.KeyPair`. """

    def instantiate(self, name, provider, public_key=None):
        return KeyPair(name, provider, public_key=public_key or "", collection=self)

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
            flash_message = VersionPick({
                Version.lowest(): 'Creating Key Pair {}'.format(name),
                '5.8': 'Key Pair "{}" created'.format(name)}).pick(self.appliance.version)

        # add/cancel should redirect, new view
        view = self.create_view(KeyPairAllView)
        # TODO BZ 1444520 causing ridiculous redirection times after submitting the form
        wait_for(lambda: view.is_displayed, num_sec=120, delay=3,
                 fail_func=view.flush_widget_cache, handle_exception=True)
        view = self.create_view(KeyPairAllView)
        assert view.is_displayed
        view.entities.flash.assert_success_message(flash_message)
        keypair = self.instantiate(name, provider, public_key=public_key)
        return keypair


class KeyPair(Navigatable):
    """ Automate Model page of KeyPairs

    Args:
        name: Name of Keypairs.
    """
    _param_name = "KeyPair"

    def __init__(self, name, provider, public_key=None, appliance=None, collection=None):
        self.collection = collection or KeyPairCollection(appliance=appliance)
        Navigatable.__init__(self, appliance=self.collection.appliance)
        self.name = name
        self.provider = provider
        self.public_key = public_key or ""

    def delete(self, cancel=False, wait=False):
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove this Key Pair',
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
            view.entities.flash.assert_no_error()
            view.entities.flash.assert_success_message('Delete initiated for 1 Key Pair')

        if wait:
            def refresh():
                self.provider.refresh_provider_relationships()
                view.browser.refresh()
                view.flush_widget_cache()

                # look for the row, call is_displayed on it to get boolean
                # find_row_on_pages is going to raise NoSuchElement when the row disappears
            wait_for(
                lambda: not self.exists,
                message="Wait keypairs to disappear",
                fail_condition=False,
                num_sec=300,
                timeout=1000,
                delay=20,
                fail_func=refresh
            )

    def add_tag(self, tag, **kwargs):
        """Tags the Keypair by given tag"""
        navigate_to(self, 'Details')
        mixins.add_tag(tag, **kwargs)

    def remove_tag(self, tag, **kwargs):
        """Untag the Keypair by given tag"""
        navigate_to(self, 'Details')
        mixins.remove_tag(tag)

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
        except KeyPairNotFound:
            return False
        else:
            return True


@navigator.register(KeyPairCollection, 'All')
class CloudKeyPairs(CFMENavigateStep):
    VIEW = KeyPairAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Clouds', 'Key Pairs')


@navigator.register(KeyPair, 'Details')
class Details(CFMENavigateStep):
    VIEW = KeyPairDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.view_selector.select('List View')
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table,
                name=self.obj.name
            )
        except NoSuchElementException:
            raise KeyPairNotFound

        row.click()


@navigator.register(KeyPairCollection, 'Add')
class Add(CFMENavigateStep):
    VIEW = KeyPairAddView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        """Raises DropdownItemDisabled from widgetastic_patternfly if no RHOS provider present"""
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Key Pair')

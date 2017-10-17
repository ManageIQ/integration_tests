# -*- coding: utf-8 -*-
import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import View
from widgetastic.utils import VersionPick, Version
from widgetastic_patternfly import Dropdown, Button, FlashMessages
from widgetastic_manageiq import (
    ItemsToolBarViewSelector, Text, TextInput, Accordion, ManageIQTree, BreadCrumb,
    SummaryTable, BootstrapSelect, ItemNotFound, BaseEntitiesView, PaginationPane)

from cfme.common import WidgetasticTaggable
from cfme.base.ui import BaseLoggedInPage
from cfme.exceptions import KeyPairNotFound

from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.wait import wait_for


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


class KeyPairDetailsEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')
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
    including_entities = View.include(BaseEntitiesView, use_parent=True)


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
class KeyPair(BaseEntity, WidgetasticTaggable):
    """ Automate Model page of KeyPairs

    Args:
        name: Name of Keypairs.
    """
    _param_name = "KeyPair"

    name = attr.ib()
    provider = attr.ib()
    public_key = attr.ib(default="")

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

            view = navigate_to(self.parent, 'All')

            wait_for(
                lambda: self.name in view.entities.all_entity_names,
                message="Wait keypairs to disappear",
                fail_condition=True,
                num_sec=300,
                delay=5,
                fail_func=refresh
            )

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
        except KeyPairNotFound:
            return False
        else:
            return True


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
            flash_message = VersionPick({
                Version.lowest(): 'Creating Key Pair {}'.format(name),
                '5.8': 'Key Pair "{}" created'.format(name)}).pick(self.appliance.version)

        # add/cancel should redirect, new view
        view = self.create_view(KeyPairAllView)
        # TODO BZ 1444520 causing ridiculous redirection times after submitting the form
        wait_for(lambda: view.is_displayed, num_sec=240, delay=2,
                 fail_func=view.flush_widget_cache, handle_exception=True)
        assert view.is_displayed
        view.entities.flash.assert_success_message(flash_message)
        return self.instantiate(name, provider, public_key=public_key)


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
            item = self.prerequisite_view.entities.get_entity(by_name=self.obj.name,
                                                              surf_pages=True)
        except ItemNotFound:
            raise KeyPairNotFound

        item.click()


@navigator.register(KeyPairCollection, 'Add')
class Add(CFMENavigateStep):
    VIEW = KeyPairAddView
    prerequisite = NavigateToSibling("All")

    def step(self, *args, **kwargs):
        """Raises DropdownItemDisabled from widgetastic_patternfly if no RHOS provider present"""
        self.prerequisite_view.toolbar.configuration.item_select('Add a new Key Pair')

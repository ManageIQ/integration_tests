import re

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import RowNotFound
from widgetastic.exceptions import UnexpectedAlertPresentException
from widgetastic.widget import Checkbox
from widgetastic.widget import FileInput
from widgetastic.widget import Select
from widgetastic.widget import Text
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import BootstrapSwitch
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input
from widgetastic_patternfly import Kebab

from cfme.base.ui import RegionView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils import conf
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance import NavigatableMixin
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from widgetastic_manageiq import DynamicTable
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq import Table
from widgetastic_manageiq import VanillaTable


# =======================================TAGS=============================================

table_button_classes = [Button.DEFAULT, Button.SMALL, Button.BLOCK]


class CompanyTagsAllView(RegionView):
    """Company Tags list view"""
    category_dropdown = BootstrapSelect('classification_name')
    table = DynamicTable(locator='//div[@id="classification_entries_div"]/table',
                         column_widgets={
                             'Name': Input(id='entry_name'),
                             'Description': Input(id='entry_description'),
                             'Actions': Button(title='Add this entry',
                                               classes=table_button_classes)},
                         assoc_column='Name', rows_ignore_top=1, action_row=0)

    @property
    def is_displayed(self):
        return (
            self.company_tags.is_active() and
            self.table.is_displayed
        )


class CompanyTagsImportView(RegionView):
    """Import Company Tags list view"""
    upload_file = FileInput(id="upload_file")
    upload_button = Button(id='upload_tags')
    apply_button = Button("Apply")

    @property
    def is_displayed(self):
        return (self.tags.is_active() and self.import_tags.is_active())


@attr.s(eq=False)
class Tag(Pretty, BaseEntity, Updateable):
    """ Class represents a category in CFME UI

        Args:
            name: Name of the tag
            display_name: Tag display name
            category: Tags Category

    """
    pretty_attrs = ['name', 'display_name']

    display_name = attr.ib()
    name = attr.ib(default=None)

    def __eq__(self, other):
        # compare the display_name attributes of the tag and its parent category
        # display name itself is unique in MIQ
        # use getattr in case other is not actually a tag
        # provide default Category object so we can call display_name regardless
        return (
            self.display_name == getattr(other, 'display_name') and
            self.category.display_name == getattr(other, 'category',
                                                  Category(parent=None, display_name=None)
                                                  ).display_name
        )

    def update(self, updates):
        """ Update category method """
        view = navigate_to(self.parent, 'All')
        view.table.row(name=self.name).click()
        view.table.fill({
            self.name: {
                'Name': updates.get('name'),
                'Description': updates.get('display_name')
            }
        })
        view.flash.assert_no_error()

    def delete(self, cancel=False):
        """ Delete category method """
        view = navigate_to(self.parent, 'All')
        view.table.row(description=self.display_name).actions.click()
        view.browser.handle_alert(cancel=cancel)
        view.flash.assert_no_error()

    @property
    def exists(self):
        """Check if tag exists"""
        view = navigate_to(self.parent, 'All')
        try:
            view.table.row(description=self.display_name)
            return True
        except RowNotFound:
            return False

    @property
    def category(self):
        return self.parent.parent


@attr.s
class TagsCollection(BaseCollection):

    ENTITY = Tag

    def create(self, name, display_name):
        """ Create category method """
        view = navigate_to(self, 'All')
        view.table.fill([{'Name': name, 'Description': display_name}])
        view.table.row_save()
        return self.instantiate(name=name, display_name=display_name)

    def all(self):
        """Get all tags for the category"""
        view = navigate_to(self, 'All')
        all_tags = []
        for name, values_dict in view.table.read().items():
            all_tags = all_tags.append(
                self.instantiate(name=name, display_name=values_dict['Description'])
            )


@navigator.register(TagsCollection, 'All')
class TagsAll(CFMENavigateStep):
    VIEW = CompanyTagsAllView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.tags.company_tags.select()
        self.view.fill({'category_dropdown': self.obj.parent.display_name})


# =====================================CATEGORY===================================


class CompanyCategoriesAllView(RegionView):
    """Company Categories List View"""
    add_button = Button('Add')
    table = VanillaTable('//div[@id="settings_co_categories"]/table')

    @property
    def is_displayed(self):
        return (
            self.tags.is_active() and
            self.company_categories.is_active()
        )


class CompanyCategoriesAddView(CompanyCategoriesAllView):
    """ Add Company Categories View"""
    name = Input(id='name')
    display_name = Input(id='description')
    long_description = Input(id='example_text')
    show_in_console = BootstrapSwitch(id='show')
    single_value = BootstrapSwitch(id='single_value')
    capture_candu = BootstrapSwitch(id='perf_by_tag')

    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.company_categories.is_active() and
            self.name.is_displayed
        )


class CompanyCategoriesEditView(CompanyCategoriesAddView):
    """Edit Company Categories View"""
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.company_categories.is_active() and
            self.name.is_displayed and
            self.save_button.is_displayed
        )


@attr.s
class Category(Pretty, BaseEntity, Updateable):
    """ Class represents a category in CFME UI

        Args:
            name: Name of the category
            display_name: Category display name
            description: Category description
            show_in_console: Option to show category in console (True/False)
            single_value: Option if category is single value (True/False)
            capture_candu: True/False, capture c&u data by tag

    """
    pretty_attrs = ['name', 'display_name', 'description', 'show_in_console',
                    'single_value', 'capture_candu']

    _collections = {'tags': TagsCollection}

    display_name = attr.ib()
    name = attr.ib(default=None)
    description = attr.ib(default=None)
    show_in_console = attr.ib(default=True)
    single_value = attr.ib(default=True)
    capture_candu = attr.ib(default=False)

    def update(self, updates, cancel=False):
        """ Update category method

            Args:
                updates: category data that should be changed
                cancel:
        """
        view = navigate_to(self, 'Edit')
        change = view.fill({
            'name': updates.get('name'),
            'display_name': updates.get('display_name'),
            'long_description': updates.get('description'),
            'show_in_console': updates.get('show_in_console'),
            'single_value': updates.get('single_value'),
            'capture_candu': updates.get('capture_candu'),
        })

        if cancel or not change:
            view.cancel_button.click()
        else:
            view.save_button.click()

        view = self.create_view(navigator.get_class(self.parent, 'All').VIEW)
        assert view.is_displayed
        view.flash.assert_no_error()

    def delete(self, cancel=False):
        """ Delete existing category

            Args:
                cancel: Default value 'False', category will be deleted
                        'True' - deletion of category will be canceled
        """
        view = navigate_to(self.parent, 'All')
        row = view.table.row(description=self.display_name)
        row.actions.click()
        view.browser.handle_alert(cancel=cancel)
        if not cancel:
            view = self.create_view(navigator.get_class(self.parent, 'All').VIEW)
        assert view.is_displayed
        view.flash.assert_no_error()

    def import_tag_from_file(self, file_name):
        """Assign tag to VM via Import from CSV formatted file

            Args:
                file_name: Name of .csv file containing tag data.
        """
        view = navigate_to(self.parent, 'ImportTags')
        view.upload_file.fill(file_name)
        view.upload_button.click()
        view.flash.assert_no_error()
        view.apply_button.click()
        view.flash.assert_no_error()

    @property
    def exists(self):
        """Check if category exists"""
        view = navigate_to(self.parent, 'All')
        try:
            view.table.row(description=self.display_name)
            return True
        except RowNotFound:
            return False


@attr.s
class CategoriesCollection(BaseCollection):

    ENTITY = Category

    def create(self, name, display_name, description, show_in_console=True, single_value=True,
               capture_candu=False, cancel=False):
        """ Create category method

        Args:
            name: Name of the category
            display_name: Category display name
            description: Category description
            show_in_console: Option to show category in console (True/False)
            single_value: Option if category is single value (True/False)
            capture_candu: True/False, capture c&u data by tag
            cancel: To cancel creation pass True, cancellation message will be verified
                    By default user will be created
        """
        view = navigate_to(self, 'Add')
        view.fill({
            'name': name,
            'display_name': display_name,
            'long_description': description,
            'show_in_console': show_in_console,
            'single_value': single_value,
            'capture_candu': capture_candu,
        })

        if cancel:
            view.cancel_button.click()
        else:
            view.add_button.click()

        view = self.create_view(navigator.get_class(self, 'All').VIEW)
        assert view.is_displayed
        view.flash.assert_no_error()
        return self.instantiate(
            display_name=display_name,
            name=name,
            description=description,
            show_in_console=show_in_console,
            single_value=single_value,
            capture_candu=capture_candu
        )


@navigator.register(CategoriesCollection, 'All')
class CategoryAll(CFMENavigateStep):
    VIEW = CompanyCategoriesAllView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.tags.company_categories.select()


@navigator.register(CategoriesCollection, 'Add')
class CategoryAdd(CFMENavigateStep):
    VIEW = CompanyCategoriesAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.add_button.click()


@navigator.register(CategoriesCollection, 'ImportTags')
class CategoryImportTags(CFMENavigateStep):
    VIEW = CompanyTagsImportView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.tags.import_tags.select()


@navigator.register(Category, 'Edit')
class CategoryEdit(CFMENavigateStep):
    VIEW = CompanyCategoriesEditView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.table.row(name=self.obj.name).click()
# =======================================MAP TAGS==============================================


class MapTagsAllView(RegionView):
    """Map Tags list view"""
    table = VanillaTable('//div[@id="settings_label_tag_mapping"]/table')
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.map_tags.is_active() and
            self.table.is_displayed
        )


class MapTagsAddView(RegionView):
    """Add Map Tags view"""
    resource_entity = BootstrapSelect(id='entity')
    resource_label = Input(id='label_name')
    category = Input(id='category')

    add_button = Button('Add')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.map_tags.is_active() and
            self.resource_entity.is_displayed
        )


class MapTagsEditView(MapTagsAddView):
    """Edit Map Tags view"""
    save_button = Button('Save')
    reset_button = Button('Reset')


@attr.s
class MapTag(BaseEntity, Pretty, Updateable):
    """ Class represents a category in CFME UI

        Args:
            entity_type: Name of the tag
            label: Tag display name
            category: Tags Category
    """
    pretty_attrs = ['entity_type', 'label', 'category']

    entity_type = attr.ib()
    label = attr.ib()
    category = attr.ib()

    def update(self, updates, cancel=False):
        """ Update tag map method

            Args:
                updates: tag map data that should be changed
                cancel: True - if you want to cancel map edition,
                        by default map will be updated
        """
        view = navigate_to(self, 'Edit')
        # only category can be updated, as other fields disabled by default
        view.fill({
            'category': updates.get('category')
        })

        if cancel:
            view.cancel_button.click()
        else:
            view.save_button.click()

        view = self.create_view(navigator.get_class(self.parent, 'All').VIEW, override=updates)
        assert view.is_displayed
        view.flash.assert_no_error()

    def delete(self, cancel=False):
        """ Delete existing user

            Args:
                cancel: Default value 'False', map will be deleted
                        'True' - map will not be deleted
        """
        view = navigate_to(self.parent, 'All')
        row = view.table.row(tag_category=self.category, resource_label=self.label)
        row.actions.click()
        view.browser.handle_alert(cancel=cancel)

        if not cancel:
            view = self.create_view(navigator.get_class(self.parent, 'All').VIEW)
        assert view.is_displayed
        view.flash.assert_no_error()


@attr.s
class MapTagsCollection(BaseCollection):

    ENTITY = MapTag

    def all(self):
        all_map_tagging = []
        view = navigate_to(self, 'Add')
        for row in view.table:
            all_map_tagging.append(self.instantiate(
                entity_type=row.resource_entity.text,
                label=row.resource_label.text,
                category=row.tag_category.text,
            ))
        return all_map_tagging

    def create(self, entity_type, label, category, cancel=False):
        """ Map tags creation method

            Args:
                cancel: True - if you want to cancel map creation,
                        by defaul map will be created
        """
        view = navigate_to(self, 'Add')
        view.fill({
            'resource_entity': entity_type,
            'resource_label': label,
            'category': category
        })

        if cancel:
            view.cancel_button.click()
        else:
            view.add_button.click()

        view = self.create_view(navigator.get_class(self, 'All').VIEW)
        assert view.is_displayed
        view.flash.assert_no_error()

        return self.instantiate(
            entity_type=entity_type,
            label=label,
            category=category
        )


@navigator.register(MapTagsCollection, 'All')
class MapTagsAll(CFMENavigateStep):
    VIEW = MapTagsAllView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.tags.map_tags.select()


@navigator.register(MapTagsCollection, 'Add')
class MapTagsAdd(CFMENavigateStep):
    VIEW = MapTagsAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.add_button.click()


@navigator.register(MapTag, 'Edit')
class MapTagsEdit(CFMENavigateStep):
    VIEW = MapTagsEditView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.table.row(tag_category=self.obj.category).click()


# ====================Red Hat Updates===================================


class RedHatUpdatesView(RegionView):
    """Red Hat Updates details view"""
    title = Text('//div[@id="main-content"]//h3[1]')
    available_update_version = Text('//td[contains(text(), "Available Product version:")]')
    edit_registration = Button('Edit Registration')
    refresh = Button('Refresh List')
    check_for_updates = Button('Check for Updates')
    register = Button('Register')
    apply_cfme_update = Button('Apply CFME Update')
    updates_table = Table('.table.table-striped.table-bordered')
    repository_names_info = SummaryFormItem('Red Hat Software Updates', 'Repository Name(s)')

    @property
    def is_displayed(self):
        return (
            self.redhat_updates.is_active() and
            self.edit_registration.is_displayed and
            self.title.text == 'Red Hat Software Updates'
        )


class RedHatUpdatesEditView(RegionView):
    """Red Hat Updates edit view"""
    title = Text('//div[@id="main-content"]//h3[1]')

    register_to = BootstrapSelect(id='register_to')
    url = Input(id='server_url')
    repo_name = Input(id='repo_name')
    use_proxy = Checkbox('use_proxy')
    proxy_url = Input(id='proxy_address')
    proxy_username = Input(id='proxy_userid')
    proxy_password = Input(id='proxy_password')
    username = Input(id='customer_userid')
    password = Input(id='customer_password')

    repo_default_name = Button(id='repo_default_name')
    rhn_default_url = Button(id='rhn_default_button')

    validate_button = Button('Validate')
    reset_button = Button('Reset')
    save_button = Button('Save')
    cancel_button = Button('Cancel')
    organization = Select(id='customer_org')

    @property
    def is_displayed(self):
        return (
            self.redhat_updates.is_active() and
            self.validate_button.is_displayed and
            self.title.text == 'Red Hat Software Updates'
        )


class RedHatUpdates(Navigatable, Pretty):
    """ Class represents a Red Hat updates tab in CFME UI

    Args:
        service: Service type (registration method).
        url: Service server URL address.
        username: Username to use for registration.
        password: Password to use for registration.
        repo_name: Repository/channel to enable.
        organization: Organization (sat6 only).
        use_proxy: `True` if proxy should be used, `False` otherwise (default `False`).
        proxy_url: Address of the proxy server.
        proxy_username: Username for the proxy server.
        proxy_password: Password for the proxy server.
        set_default_rhsm_address: Click the Default button connected to
            the RHSM (only) address if `True`
        set_default_repository: Click the Default button connected to the repo/channel if `True`
        Note:
            With satellite 6, it is necessary to validate credentials to obtain
            available organizations from the server.
            With satellite 5, 'validate' parameter is ignored because there is
            no validation button available.
    """

    pretty_attrs = ['service', 'url', 'username', 'password']
    service_types = {
        'rhsm': 'Red Hat Subscription Management',
        'sat6': 'Red Hat Satellite 6'
    }

    def __init__(self, service, url, username, password, repo_name=None,
                 organization=None, use_proxy=False, proxy_url=None, proxy_username=None,
                 proxy_password=None, set_default_rhsm_address=False,
                 set_default_repository=False, appliance=None):
        self.service = service
        self.url = url
        self.username = username
        self.password = password
        self.repo_name = repo_name
        self.organization = organization
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.set_default_rhsm_address = set_default_rhsm_address
        self.set_default_repository = set_default_repository
        Navigatable.__init__(self, appliance=appliance)

    def update_registration(self, validate=True, cancel=False):
        """ Fill in the registration form, validate and save/cancel

        Args:
            validate: Click the Validate button and check the
                      flash message for errors if `True` (default `True`)
            cancel: Click the Cancel button if `True` or the Save button
                    if `False` (default `False`)
        """
        assert self.service in self.service_types, "Unknown service type '{}'".format(
            self.service)
        service_value = self.service_types[self.service]

        view = navigate_to(self, 'Edit')
        details = {
            'register_to': service_value,
            'url': self.url,
            'username': self.username,
            'password': self.password,
            'repo_name': self.repo_name,
            'use_proxy': self.use_proxy,
            'proxy_url': self.proxy_url,
            'proxy_username': self.proxy_username,
            'proxy_password': self.proxy_password,
        }

        view.fill(details)

        if self.set_default_rhsm_address:
            view.rhn_default_url.click()

        if self.set_default_repository:
            view.repo_default_name.click()

        if validate:
            view.validate_button.click()

        if self.organization:
            view.fill({'organization': self.organization})

        if cancel:
            view.cancel_button.click()
            flash_message = 'Edit of Customer Information was cancelled'
        else:
            view.save_button.click()
            flash_message = 'Customer Information successfully saved'

        view = self.create_view(RedHatUpdatesView)
        assert view.is_displayed
        view.flash.assert_message(flash_message)

    def refresh(self):
        """ Click refresh button to update statuses of appliances """
        view = navigate_to(self, 'Details')
        view.refresh.click()

    def register_appliances(self, *appliance_names):
        """ Register appliances by names

        Args:
            appliance_names: Names of appliances to register; will register all if empty
        """
        view = navigate_to(self, 'Details')
        self.select_appliances(*appliance_names)
        view.register.click()
        view.flash.assert_message("Registration has been initiated for the selected Servers")

    def update_appliances(self, *appliance_names):
        """ Update appliances by names

        Args:
            appliance_names: Names of appliances to update; will update all if empty
        """
        view = navigate_to(self, 'Details')
        self.select_appliances(*appliance_names)
        view.apply_cfme_update.click()
        view.flash.assert_message("Update has been initiated for the selected Servers")

    def check_updates(self, *appliance_names):
        """ Run update check on appliances by names

        Args:
            appliance_names: Names of appliances to check; will check all if empty
        """
        view = navigate_to(self, 'Details')
        self.select_appliances(*appliance_names)
        view.check_for_updates.click()
        view.flash.assert_message(
            "Check for updates has been initiated for the selected Servers")

    def is_registering(self, *appliance_names):
        """ Check if at least one appliance is registering """
        view = navigate_to(self, 'Details')
        for appliance_name in appliance_names:
            row = view.updates_table.row(appliance=appliance_name)
            if row.last_message.text.lower() == 'registering':
                return True
        else:
            return False

    def is_registered(self, *appliance_names):
        """ Check if each appliance is registered

        Args:
            appliance_names: Names of appliances to check; will check all if empty
        """
        view = navigate_to(self, 'Details')
        for appliance_name in appliance_names:
            row = view.updates_table.row(appliance=appliance_name)
            if row.last_message.text.lower() == 'registered':
                return True
        else:
            return False

    def is_subscribed(self, *appliance_names):
        """ Check if appliances are subscribed

        Args:
            appliance_names: Names of appliances to check; will check all if empty
        """
        for row in self.get_appliance_rows(*appliance_names):
            if row.update_status.text.lower() != 'subscribed':
                return False
        return True

    def versions_match(self, version, *appliance_names):
        """ Check if versions of appliances match version

        Args:
            version: Version to match against
            appliance_names: Names of appliances to check; will check all if empty
        """
        for row in self.get_appliance_rows(*appliance_names):
            if row.cfme_version.text != version:
                return False
        return True

    def checked_updates(self, *appliance_names):
        """ Check if appliances checked if there is an update available

        Args:
            appliance_names: Names of appliances to check; will check all if empty
        """
        for row in self.get_appliance_rows(*appliance_names):
            if row.last_checked_for_updates.text == '':
                return False
        return True

    def platform_updates_available(self, *appliance_names):
        """ Check if appliances have a platform update available

        Args:
            appliance_names: Names of appliances to check; will check all if empty
        """
        for row in self.get_appliance_rows(*appliance_names):
            if row.platform_updates_available.text.lower() != 'yes':
                return False
        return True

    def get_available_version(self):
        """ Get available version printed on the page

        Returns:
            `None` if not available; string with version otherwise
             e.g. ``1.2.2.3``
        """
        view = navigate_to(self, 'Details')
        available_version_raw = view.available_update_version.text()
        available_version_search_res = re.search(r"([0-9]+\.)*[0-9]+", available_version_raw)
        if available_version_search_res:
            return available_version_search_res.group(0)
        return None

    def get_repository_names(self):
        """Get available repositories names

        Returns:
            string: summary info for repositories names
        """
        view = navigate_to(self, 'Details')
        return view.repository_names_info.text

    def select_appliances(self, *appliance_names):
        """ Select appliances by names

        Args:
            appliance_names: Names of appliances to select; will select all if empty
        """
        view = navigate_to(self, 'Details')
        if appliance_names:
            view.updates_table.uncheck_all()
            for name in appliance_names:
                view.updates_table.row(appliance=name)[0].click()
        else:
            view.updates_table.check_all()

    def get_appliance_rows(self, *appliance_names):
        """ Get appliances as table rows

        Args:
            appliance_names: Names of appliances to get; will get all if empty
        """
        view = navigate_to(self, 'Details')
        if appliance_names:
            rows = [row for row in view.updates_table.rows()
                    if row.appliance.text in appliance_names]
        else:
            rows = view.updates_table.rows()
        return rows


@navigator.register(RedHatUpdates)
class Details(CFMENavigateStep):
    VIEW = RedHatUpdatesView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.redhat_updates.select()


@navigator.register(RedHatUpdates)
class Edit(CFMENavigateStep):
    VIEW = RedHatUpdatesEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.edit_registration.click()


# ====================C and U===================================


class CANDUCollectionView(RegionView):
    """C and U View"""
    all_clusters_cb = BootstrapSwitch(id='all_clusters')
    all_datastores_cb = BootstrapSwitch(id='all_storages')

    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.candu_collection.is_active() and
            self.all_clusters_cb.is_displayed
        )


@attr.s
class CANDUCollection(BaseCollection):
    """ Class represents a C and U in CFME UI """

    def _set_state(self, enable=True, reset=False):
        """ Enable/Disable C and U

            Args:
                enable: Switches states, 'True'- enable
                reset: Reset changes, default is 'False' - changes will not be reset
        """
        view = navigate_to(self, 'Details')
        changed = view.fill({
            'all_clusters_cb': enable,
            'all_datastores_cb': enable
        })
        # Save and Reset buttons are active only if view was changed
        if changed:
            if reset:
                view.reset_button.click()
                flash_message = 'All changes have been reset'
            else:
                view.save_button.click()
                flash_message = 'Capacity and Utilization Collection settings saved'
            view.flash.assert_success_message(flash_message)

    def enable_all(self, reset=False):
        """ Enable C and U

            Args:
                reset: Reset changes, default is 'False' - changes will not be reset
        """
        self._set_state(reset=reset)

    def disable_all(self, reset=False):
        """ Disable C and U

            Args:
                reset: Reset changes, default is 'False' - changes will not be reset
        """
        self._set_state(False, reset=reset)


@navigator.register(CANDUCollection, 'Details')
class CANDUCollectionDetails(CFMENavigateStep):
    VIEW = CANDUCollectionView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.candu_collection.select()


# ========================= Replication ================================

class ReplicationView(RegionView):
    """ Replication Tab View """
    replication_type = BootstrapSelect(id='replication_type')
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def in_region(self):
        return (
            self.accordions.settings.tree.currently_selected == [
                self.context["object"].appliance.server.zone.region.settings_string]
        )

    @property
    def is_displayed(self):
        return (
            self.in_region and
            self.replication_type.is_displayed
        )


class ReplicationGlobalView(ReplicationView):
    """ Replication Global setup View"""
    add_subscription = Button('Add Subscription')
    subscription_table = VanillaTable(
        '//form[@id="form_div"]//table[contains(@class, "table")]',
        column_widgets={
            8: Button("Update"),
            10: Kebab(locator='//td[10]/div[contains(@class, "dropdown-kebab-pf")]')
        }
    )

    @property
    def is_displayed(self):
        return (
            self.in_region and
            self.add_subscription.is_displayed
        )


class ReplicationKebab(Kebab):
    ITEM = './ul/li/a[normalize-space(.)={} and not(contains(@class, "disabled"))]'
    ITEMS = './ul/li/a[not(contains(@class, "disabled"))]'


class ReplicationGlobalAddView(ReplicationView):
    database = Input(locator='//input[contains(@ng-model, "dbname")]')
    host = Input(locator='//input[contains(@ng-model, "host")]')
    username = Input(locator='//input[contains(@ng-model, "user")]')
    password = Input(name='password')
    port = Input(name='port')
    accept_button = Button('Accept')
    action_dropdown = ReplicationKebab(locator='//div[contains(@class, "dropdown-kebab-pf")]')

    @property
    def is_displayed(self):
        return self.accept_button.is_displayed


class ReplicationRemoteView(ReplicationView):
    """ Replication Remote setup View """
    pass
    # TODO add widget for "Excluded Tables"


class Replication(NavigatableMixin):
    """ Class represents a Replication tab in CFME UI

        Note:
        Remote settings is not covered for now as 'Excluded Tables' element widget should be added
    """

    def __init__(self, appliance):
        self.appliance = appliance

    def set_replication(self, updates=None, replication_type=None, reset=False, validate=False):
        """ Set replication settings

            Args:
                 updates(dict): Replication update values, mandatory is host,
                     db creds get from credentials
                 replication_type(str): Replication type, use 'global' or 'remote'
                 reset: Pass True to reset made changes
        """
        db_creds = conf.credentials.database
        if not replication_type:
            view = navigate_to(self, 'Details')
            view.replication_type.fill('<None>')
        elif replication_type == 'global':
            view = navigate_to(self, 'GlobalAdd')
            view.fill({
                'database': (
                    updates.get('database') if updates.get('database') else 'vmdb_production'),
                'host': updates.get('host'),
                'port': updates.get('port') if updates.get('port') else '5432',
                'username': (
                    updates.get('username') if updates.get('username') else db_creds.username),
                'password': (
                    updates.get('password') if updates.get('password') else db_creds.password)
            })
        elif replication_type == 'remote':
            view = navigate_to(self, 'RemoteAdd')
            # TODO fill remote settings will be done after widget added
        if reset:
            view.reset_button.click()
            view.flash.assert_message('All changes have been reset')
        else:
            try:
                if replication_type == 'global':
                    if validate:
                        view.action_dropdown.item_select("Validate")
                        view.flash.assert_no_error()
                    view.accept_button.click()
                view.save_button.click()
            except Exception:
                logger.warning('Nothing was updated, please check the data')

    def _global_replication_row(self, host=None):
        """ Get replication row from table

            Kwargs:
                host: :py:class`str` to match on the Host column in the table
            Returns:
                :py:class:`TableRow` of matching row.
                If host is not specified, then the first table row is returned.
        """
        view = navigate_to(self, 'Global')
        if host:
            return view.subscription_table.row(host=host)
        else:
            return view.subscription_table[0]

    def get_replication_status(self, replication_type='global', host=None):
        """ Get replication status, if replication is active

            Args:
                replication_type: Replication type string, default is global
                host: host to check
            Returns: True if active, otherwise False
        """
        view = navigate_to(self, replication_type.capitalize())
        if replication_type == 'remote':
            return view.is_displayed
        else:
            is_host_present = self._global_replication_row(host).is_displayed
            host_row = view.subscription_table.row(host=host)
            wait_for(lambda: host_row.status.text == "replicating",
                     fail_func=view.browser.refresh)
            return is_host_present

    def get_global_replication_backlog(self, host=None):
        """ Get global replication backlog value

            Args:
                host: host value
            Returns: backlog number value
        """
        row = self._global_replication_row(host)
        return int(row.backlog.text.split(' ')[0])

    def remove_global_appliance(self, host=None):
        """ Remove the remote appliance subscription from the Global region

            Args:
                host: host value
            Returns: True once the subsciption is removed
        """
        row = self._global_replication_row(host)
        view = self.create_view(ReplicationGlobalView)

        try:
            row[10].widget.item_select("Delete")
        except UnexpectedAlertPresentException:
            view.browser.handle_alert()

        view.save_button.click()

        def _row_exists():
            try:
                view.browser.refresh()
                self._global_replication_row(host)
                return True
            except RowNotFound:
                return False

        # wait until the row no longer exists
        wait_for(_row_exists, fail_condition=True, num_sec=60, delay=2)
        return True


@navigator.register(Replication, 'Details')
class ReplicationDetails(CFMENavigateStep):
    VIEW = ReplicationView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.replication.select()


@navigator.register(Replication, 'Global')
class ReplicationGlobalSetup(CFMENavigateStep):
    VIEW = ReplicationGlobalView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.replication_type.fill('Global')


@navigator.register(Replication, 'GlobalAdd')
class ReplicationGlobalAdd(CFMENavigateStep):
    VIEW = ReplicationGlobalAddView
    prerequisite = NavigateToSibling('Global')

    def step(self, *args, **kwargs):
        if not self.view.accept_button.is_displayed:
            self.prerequisite_view.add_subscription.click()


@navigator.register(Replication, 'RemoteAdd')
class ReplicationRemoteAdd(CFMENavigateStep):
    VIEW = ReplicationRemoteView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.replication_type.fill('Remote')

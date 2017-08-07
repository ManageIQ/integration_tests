import re

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic_patternfly import Input, BootstrapSelect, Button, BootstrapSwitch
# TODO replace with dynamic table
from widgetastic_manageiq import VanillaTable, SummaryFormItem, Table
from widgetastic.widget import Checkbox, Text

from cfme.base.ui import RegionView
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.pretty import Pretty
from utils.update import Updateable


# =====================================CATEGORY===================================


class CompanyCategoriesAllView(RegionView):
    """Company Categories List View"""
    add_button = Button('Add')
    table = VanillaTable('//div[@id="settings_co_categories"]/table')

    @property
    def is_displayed(self):
        return (
            self.companycategories.is_active() and
            self.table.is_displayed
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
            self.companycategories.is_active() and
            self.name.is_displayed
        )


class CompanyCategoriesEditView(CompanyCategoriesAddView):
    """Edit Company Categories View"""
    save_button = Button('Save')
    reset_button = Button('Reset')

    @property
    def is_displayed(self):
        return (
            self.companycategories.is_active() and
            self.name.is_displayed and
            self.save_button.is_displayed
        )


class Category(Pretty, Navigatable, Updateable):
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

    def __init__(self, name=None, display_name=None, description=None, show_in_console=True,
                 single_value=True, capture_candu=False, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.display_name = display_name
        self.description = description
        self.show_in_console = show_in_console
        self.single_value = single_value
        self.capture_candu = capture_candu

    def _form_mapping(self, **kwargs):
        """Returns dist used to fill forms """
        return {
            'name': kwargs.get('name'),
            'display_name': kwargs.get('display_name'),
            'long_description': kwargs.get('description'),
            'show_in_console': kwargs.get('show_in_console'),
            'single_value': kwargs.get('single_value'),
            'capture_candu': kwargs.get('capture_candu'),
        }

    def create(self, cancel=False):
        """ Create category method
            Args:
                cancel: To cancel creation pass True, cancellation message will be verified
                        By defaul user will be created
        """
        view = navigate_to(self, 'Add')
        view.fill(self._form_mapping(**self.__dict__))

        if cancel:
            view.cancel_button.click()
            flash_message = 'Add of new Category was cancelled by the user'
        else:
            view.add_button.click()
            flash_message = 'Category "{}" was added'.format(self.display_name)

        view = self.create_view(CompanyCategoriesAllView)
        view.flash.assert_success_message(flash_message)

    def update(self, updates, cancel=False):
        """ Update category method
            Args:
                updates: category data that should be changed
        """
        view = navigate_to(self, 'Edit')
        view.fill(self._form_mapping(**updates))
        if cancel:
            view.cancel_button.click()
            flash_message = 'Edit of Category "{}" was cancelled by the user'.format(self.name)
        else:
            view.save_button.click()
            flash_message = 'Category "{}" was saved'.format(self.name)

        view = self.create_view(CompanyCategoriesAllView)
        view.flash.assert_success_message(flash_message)

    def delete(self, cancel=True):
        """ Delete existing category
            Args:
                cancel: Default value 'True', category will be deleted
                        'False' - deletion of category will be canceled
        """
        view = navigate_to(self, 'All')
        row = view.table.row(name=self.name)
        row.actions.click()
        view.browser.handle_alert(cancel=cancel)
        if not cancel:
            view.flash.assert_success_message('Category "{}": Delete successful'.format(self.name))


@navigator.register(Category, 'All')
class CategoryAll(CFMENavigateStep):
    VIEW = CompanyCategoriesAllView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self):
        self.prerequisite_view.companycategories.select()


@navigator.register(Category, 'Add')
class CategoryAdd(CFMENavigateStep):
    VIEW = CompanyCategoriesAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.add_button.click()


@navigator.register(Category, 'Edit')
class CategoryEdit(CFMENavigateStep):
    VIEW = CompanyCategoriesEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.table.row(name=self.obj.name).click()

# =======================================TAGS=============================================


class CompanyTagsAllView(RegionView):
    """Company Tags list view"""
    category_dropdown = BootstrapSelect('classification_name')
    table = VanillaTable('//div[@id="classification_entries_div"]/table')
    add_button = Button('Add')

    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.companycategories.is_active() and
            self.table.is_displayed
        )


class CompanyTagsAddView(CompanyTagsAllView):
    """Add Company Tags view"""
    tag_name = Input(id='entry_name')
    tag_description = Input(id='entry_description')

    @property
    def is_displayed(self):
        return (
            self.companycategories.is_active() and
            self.tag_name.is_displayed
        )


class CompanyTagsEditView(CompanyTagsAddView):
    """Edit Company Tags view"""
    save_button = Button('Save')
    reset_button = Button('Reset')


class Tag(Pretty, Navigatable, Updateable):
    """ Class represents a category in CFME UI
        Args:
            name: Name of the tag
            display_name: Tag display name
            category: Tags Category

    """
    pretty_attrs = ['name', 'display_name', 'category']

    def __init__(self, name=None, display_name=None, category=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.display_name = display_name
        self.category = category

    def _form_mapping(self, **kwargs):
        """Returns dist used to fill forms """
        return {
            'tag_name': kwargs.get('name'),
            'tag_description': kwargs.get('display_name')
        }

    def create(self):
        """ Create category method """
        view = navigate_to(self, 'Add')
        view.fill(self._form_mapping(**self.__dict__))
        view.add_button.click()

    def update(self, updates):
        """ Update category method """
        view = navigate_to(self, 'Edit')
        view.fill(self._form_mapping(**updates))
        view.save_button.click()

    def delete(self, cancel=True):
        """ Delete category method """
        view = navigate_to(self, 'All')
        row = view.table.row(name=self.name)
        row.actions.click()
        view.browser.handle_alert(cancel=cancel)


@navigator.register(Tag, 'All')
class TagsAll(CFMENavigateStep):
    VIEW = CompanyTagsAllView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self):
        self.prerequisite_view.companytags.select()
        self.view.fill({'category_dropdown': self.obj.category.display_name})


@navigator.register(Tag, 'Add')
class TagsAdd(CFMENavigateStep):
    VIEW = CompanyTagsAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.add_button.click()


@navigator.register(Tag, 'Edit')
class TagsEdit(CFMENavigateStep):
    VIEW = CompanyTagsEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.table.row(name=self.obj.name).click()

# =======================================MAP TAGS==============================================


class MapTagsAllView(RegionView):
    """Map Tags list view"""
    table = VanillaTable('//div[@id="settings_label_tag_mapping"]/table')
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return (
            self.maptags.is_active() and
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
            self.maptags.is_active() and
            self.resource_entity.is_displayed
        )


class MapTagsEditView(MapTagsAddView):
    """Edit Map Tags view"""
    save_button = Button('Save')
    reset_button = Button('Reset')


class MapTags(Navigatable, Pretty, Updateable):
    """ Class represents a category in CFME UI
        Args:
            entity: Name of the tag
            label: Tag display name
            category: Tags Category

    """
    pretty_attrs = ['entity', 'label', 'category']

    def __init__(self, entity=None, label=None, category=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.entity = entity
        self.label = label
        self.category = category

    def _form_mapping(self, **kwargs):
        """Returns dist used to fill forms """
        return {
            'resource_entity': kwargs.get('entity'),
            'resource_label': kwargs.get('label'),
            'category': kwargs.get('category')
        }

    def create(self, cancel=False):
        """ Map tags creation method
            Args:
                cancel: True - if you want to cancel map creation,
                        by defaul map will be created
        """
        view = navigate_to(self, 'Add')
        view.fill(self._form_mapping(**self.__dict__))

        if cancel:
            view.cancel_button.click()
            flash_message = 'Add of new Container Label Tag Mapping was cancelled by the user'
        else:
            view.add_button.click()
            flash_message = 'Container Label Tag Mapping "{}" was added'.format(self.label)

        view = self.create_view(MapTagsAllView)
        view.flash.assert_success_message(flash_message)

    def update(self, updates, cancel=False):
        """ Update tag map method
            Args:
                updates: tag map data that should be changed
                cancel: True - if you want to cancel map edition,
                        by defaul map will be updated
        """
        view = navigate_to(self, 'Edit')
        # only category can be updated, as other fields disabled by default
        view.fill({
            'category': updates.get('category')
        })

        if cancel:
            view.cancel_button.click()
            flash_message = (
                'Edit of Container Label Tag Mapping "{}" was cancelled by the user'.format(
                    self.label)
            )
        else:
            view.save_button.click()
            flash_message = 'Container Label Tag Mapping "{}" was saved'.format(self.label)

        view = self.create_view(MapTagsAllView, override=updates)
        view.flash.assert_success_message(flash_message)

    def delete(self, cancel=False):
        """ Delete existing user
            Args:
                cancel: Default value 'False', map will be deleted
                        'True' - map will not be deleted
        """
        view = navigate_to(self, 'All')
        row = view.table.row(tag_category=self.category)
        row.actions.click()
        view.browser.handle_alert(cancel=cancel)

        if not cancel:
            view = self.create_view(MapTagsAllView)
            view.flash.assert_success_message(
                'Container Label Tag Mapping "{}": Delete successful'.format(self.label))


@navigator.register(MapTags, 'All')
class MapTagsAll(CFMENavigateStep):
    VIEW = MapTagsAllView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self):
        self.prerequisite_view.maptags.select()


@navigator.register(MapTags, 'Add')
class MapTagsAdd(CFMENavigateStep):
    VIEW = MapTagsAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.add_button.click()


@navigator.register(MapTags, 'Edit')
class MapTagsEdit(CFMENavigateStep):
    VIEW = MapTagsEditView
    prerequisite = NavigateToSibling('All')

    def step(self):
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
            self.redhatupdates.is_active() and
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
    proxy_password_verify = Input(id='proxy_password2')
    username = Input(id='customer_userid')
    password = Input(id='customer_password')
    password_verify = Input(id='customer_password2')

    repo_default_name = Button(id='repo_default_name')
    rhn_default_url = Button(id='rhn_default_button')

    validate_button = Button('Validate')
    reset_button = Button('Reset')
    save_button = Button('Save')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.redhatupdates.is_active() and
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
        password_verify: 2nd entry of password for verification. Same as 'password' if None.
        repo_name: Repository/channel to enable.
        organization: Organization (sat6 only).
        use_proxy: `True` if proxy should be used, `False` otherwise (default `False`).
        proxy_url: Address of the proxy server.
        proxy_username: Username for the proxy server.
        proxy_password: Password for the proxy server.
        proxy_password_verify: 2nd entry of proxy server password for verification.
            Same as 'proxy_password' if None.
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

    def __init__(self, service, url, username, password, password_verify=None, repo_name=None,
                 organization=None, use_proxy=False, proxy_url=None, proxy_username=None,
                 proxy_password=None, proxy_password_verify=None,
                 set_default_rhsm_address=False,
                 set_default_repository=False, appliance=None):
        self.service = service
        self.url = url
        self.username = username
        self.password = password
        self.password_verify = password_verify
        self.repo_name = repo_name
        self.organization = organization
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.proxy_password_verify = proxy_password_verify
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

        password_verify = self.password_verify or self.password
        proxy_password_verify = self.proxy_password_verify or self.proxy_password

        view = navigate_to(self, 'Edit')
        details = {
            'register_to': service_value,
            'url': self.url,
            'username': self.username,
            'password': self.password,
            'password_verify': password_verify,
            'repo_name': self.repo_name,
            'use_proxy': self.use_proxy,
            'proxy_url': self.proxy_url,
            'proxy_username': self.proxy_username,
            'proxy_password': self.proxy_password,
            'proxy_password_verify': proxy_password_verify
        }

        view.fill(details)

        if self.set_default_rhsm_address:
            view.rhn_default_url.click()

        if self.set_default_repository:
            view.repo_default_name.click()

        if validate:
            view.validate_button.click()

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
        view.apply_updates.click()
        view.flash.assert_message("Update has been initiated for the selected Servers")

    def check_updates(self, *appliance_names):
        """ Run update check on appliances by names

        Args:
            appliance_names: Names of appliances to check; will check all if empty
        """
        view = navigate_to(self, 'Details')
        self.select_appliances(*appliance_names)
        view.check_updates.click()
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
            if row.update_status.text.lower() in {'not registered', 'unsubscribed'}:
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

    def step(self):
        self.prerequisite_view.redhatupdates.select()


@navigator.register(RedHatUpdates)
class Edit(CFMENavigateStep):
    VIEW = RedHatUpdatesEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
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
            self.canducollection.is_active() and
            self.all_clusters_cb.is_displayed
        )


class CANDUCollection(Navigatable):
    """ Class represents a C and U in CFME UI """
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance=appliance)

    def _set_state(self, enable=True, reset=False):
        """ Enable/Disable C and U

            Args:
                enable: Switches states, 'True'- enable
                reset: Reset changes, default is 'False' - changes will not be reset
        """
        view = navigate_to(self, 'Details')
        view.fill({
            'all_clusters_cb': enable,
            'all_datastores_cb': enable
        })
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


@navigator.register(CANDUCollection)
class Details(CFMENavigateStep):
    VIEW = CANDUCollectionView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Details')

    def step(self):
        self.prerequisite_view.canducollection.select()

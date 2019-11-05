import re

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSwitch
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import CheckableBootstrapTreeview
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input

from cfme.base import BaseCollection
from cfme.base import BaseEntity
from cfme.common import BaseLoggedInPage
from cfme.utils.appliance import NavigatableMixin
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from widgetastic_manageiq import BootstrapSelect
from widgetastic_manageiq import Table
from widgetastic_manageiq import Text
from widgetastic_manageiq import ViewButtonGroup
from widgetastic_manageiq import WaitTab


class TimeProfileForm(View):
    description = Input(id='description')
    scope = BootstrapSelect('profile_type')
    timezone = BootstrapSelect('profile_tz')
    days = BootstrapSwitch(name='all_days')
    hours = BootstrapSwitch(name='all_hours')
    cancel = Button('Cancel')
    help_block = Text('//span[contains(@class, "help-block")]')


class TimeProfileEntities(View):
    table = Table('//div[@id="main_div"]//table')
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h3')


class TimeProfileView(BaseLoggedInPage):
    entities = View.nested(TimeProfileEntities)
    configuration = Dropdown('Configuration')


class TimeProfileAddView(TimeProfileView):
    @View.nested
    class form(TimeProfileForm):    # noqa
        add = Button('Add')

    @property
    def is_displayed(self):
        return self.entities.title.text == 'Time Profile Information'


class TimeProfileEditView(TimeProfileView):
    @View.nested
    class form(TimeProfileForm):    # noqa
        reset = Button('Reset')
        save = Button('Save')

    @property
    def is_displayed(self):
        return 'Edit' in self.entities.breadcrumb.active_location


@attr.s
class TimeProfile(Updateable, BaseEntity):

    description = attr.ib(default=None)
    scope = attr.ib(default=None)
    days = attr.ib(default=True)
    hours = attr.ib(default=True)
    timezone = attr.ib(default=None)

    def update(self, updates):
        """
        This method is used for updating the time_profile

        Args:
            updates: It the object of the time_profile that we need to update.
        """
        view = navigate_to(self, 'Edit')
        changed = view.form.fill({
            'description': updates.get('description'),
            'scope': updates.get('scope'),
            'days': updates.get('days'),
            'hours': updates.get('hours'),
            'timezone': updates.get('timezone'),
        })
        if changed:
            view.form.save.click()
            view.flash.assert_no_error()

    def copy(self, description=None, cancel=False):
        """
        This method performs the copy of the provided time profile object.
        Args:
            description (str) : It's the descriptive name of the new copied time_profile.
            cancel (bool) : This variable performs cancel operation while copy.

        return: It returns the object of the copied time_profile.
        """

        view = navigate_to(self, 'Copy')
        if description is not None:
            new_time_profile = self.parent.instantiate(description=description, scope=self.scope)
            changed = view.form.fill({
                'description': description,
                'scope': self.scope,
            })
        else:
            new_time_profile = self.parent.instantiate(
                description="{} copy".format(self.description),
                scope=self.scope
            )
            changed = view.form.fill({
                'description': "{} copy".format(self.description),
                'scope': self.scope,
            })

        if not cancel and changed:
            view.form.add.click()
            view.flash.assert_no_error()
            return new_time_profile


@attr.s
class TimeProfileCollection(BaseCollection):

    ENTITY = TimeProfile

    def create(self, description=None, scope=None, days=True, hours=True,
               timezone=None, cancel=False):
        """
        Args:
            description (str): It's the descriptive name of the time_profile.
            scope: It's the option 'All User' or 'Current User' from dropdown.
            days (bool): It's the option to switch on or switch off the days Bootstrap switch.
            hours (bool): It's the option to switch on or switch off the hours Bootstrap switch.
            timezone: It's the required Time Zone for the time_profile.
            cancel (bool) : It's a flag used to cancel or not the create operation.

        return: It returns the object of the newly created time_profile object.
        """

        time_profile = self.instantiate(description, scope, days, hours, timezone)

        view = navigate_to(self, 'Add')
        view.form.fill({
            'description': description,
            'scope': scope,
            'days': days,
            'hours': hours,
            'timezone': timezone,
        })
        if not cancel:
            view.form.add.click()
            view.flash.assert_no_error()
            return time_profile

    def delete(self, cancel=False, *time_objs):
        """
        This method performs the delete operation.

        Args:
            cancel (bool) : It's a flag used for selecting Ok or Cancel from delete confirmation
             dialogue box
            time_objs : It's time profile object.
        """

        view = navigate_to(self, 'All')
        for time_obj in time_objs:
            view.entities.table.row(Description=time_obj.description)[0].check()
        view.configuration.item_select("Delete selected Time Profiles",
                                       handle_alert=not cancel)
        view.flash.assert_no_error()


class VisualForm(View):

    @View.nested
    class grid_tile_icons(View):    # noqa
        infra_provider_quad = BootstrapSwitch(VersionPicker({Version.lowest(): 'quadicons_ems',
                                                            '5.10': 'quadicons_infra_manager'}))
        cloud_provider_quad = BootstrapSwitch(VersionPicker(
            {Version.lowest(): 'quadicons_ems_cloud', '5.10': 'quadicons_cloud_manager'}))

        containers_provider_quad = BootstrapSwitch('quadicons_container_manager')
        host_quad = BootstrapSwitch('quadicons_host')
        datastore_quad = BootstrapSwitch('quadicons_storage')
        vm_quad = BootstrapSwitch('quadicons_vm')
        template_quad = BootstrapSwitch('quadicons_miq_template')
        long_text = BootstrapSelect('quad_truncate')

    @View.nested
    class start_page(View):    # noqa
        show_at_login = BootstrapSelect('start_page')

    @View.nested
    class default_items_per_page(View):  # noqa
        grid_view = BootstrapSelect('perpage_grid')
        tile_view = BootstrapSelect('perpage_tile')
        list_view = BootstrapSelect('perpage_list')
        reports = BootstrapSelect('perpage_reports')

    @View.nested
    class topology_default_items(View):     # noqa
        containers = BootstrapSelect('topology_containers_max_items')

    @View.nested
    class display_settings(View):   # noqa
        chart_theme = BootstrapSelect('display_reporttheme')
        time_zone = BootstrapSelect('display_timezone')
        locale = BootstrapSelect('display_locale')

    save = Button('Save')
    reset = Button('Reset')


class DefaultViewsForm(View):
    @View.nested
    class clouds(View):                                                                 # noqa
        flavors = ViewButtonGroup('Clouds', 'Flavors')
        instances = ViewButtonGroup('Clouds', 'Instances')
        availability_zones = ViewButtonGroup('Clouds', 'Availability Zones')
        images = ViewButtonGroup('Clouds', 'Images')
        providers = ViewButtonGroup('Clouds', 'Cloud Providers')
        stacks = ViewButtonGroup('Clouds', 'Stacks')

    @View.nested
    class general(View):                                                                # noqa
        compare = ViewButtonGroup('General', 'Compare')
        compare_mode = ViewButtonGroup('General', 'Compare Mode')

    @View.nested
    class infrastructure(View):                                                         # noqa
        infrastructure_providers = ViewButtonGroup('Infrastructure', 'Infrastructure Providers')
        configuration_management_providers = ViewButtonGroup('Infrastructure',
                                                             'Configuration Management Providers')
        vms = ViewButtonGroup('Infrastructure', 'VMs')

    @View.nested
    class services(View):                                                               # noqa
        my_services = ViewButtonGroup('Services', 'My Services')
        catalog_items = ViewButtonGroup('Services', 'Catalog Items')
        templates = ViewButtonGroup('Services', 'Templates & Images')
        vms_instances = ViewButtonGroup('Services', 'VMs & Instances')
        service_catalogs = ViewButtonGroup('Services', 'Service Catalogs')

    @View.nested
    class containers(View):                                                             # noqa
        providers = ViewButtonGroup('Containers', 'Containers Providers')
        nodes = ViewButtonGroup('Containers', 'Nodes')
        pods = ViewButtonGroup('Containers', 'Pods')
        services = ViewButtonGroup('Containers', 'Services')
        routes = ViewButtonGroup('Containers', 'Routes')
        containers = ViewButtonGroup('Containers', 'Containers')
        projects = ViewButtonGroup('Containers', 'Projects')
        replicators = ViewButtonGroup('Containers', 'Replicators')
        images = ViewButtonGroup('Containers', 'Images')
        image_registries = ViewButtonGroup('Containers', 'Image Registries')
        builds = ViewButtonGroup('Containers', 'Builds')
        volumes = ViewButtonGroup('Containers', 'Volumes')
        templates = ViewButtonGroup('Containers', 'Templates')

    @View.nested
    class vm_visibility(View):                                                          # noqa
        show_vms = BootstrapSwitch('display_vms')

    save = Button('Save')
    reset = Button('Reset')


class DefaultFiltersForm(View):
    tree = CheckableBootstrapTreeview('df_treebox')
    save = Button('Save')
    reset = Button('Reset')


class TimeProfilesView(BaseLoggedInPage):
    table = Table("//div[@id='main_div']//table")
    help_block = Text("//span[contains(@class, 'help-block')]")
    configuration = Dropdown('Configuration')


class Visual(Updateable, NavigatableMixin):

    def __init__(self, appliance, my_settings):
        self.appliance = appliance
        self.my_settings = my_settings

    @property
    def grid_view_limit(self):
        view = navigate_to(self.my_settings, 'Visual')
        value = re.findall(r'\d+', view.tabs.visual.default_items_per_page.grid_view.read())
        return int(value[0])

    @grid_view_limit.setter
    def grid_view_limit(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.default_items_per_page.grid_view.fill(str(value)):
            view.tabs.visual.save.click()

    @property
    def tile_view_limit(self):
        view = navigate_to(self.my_settings, 'Visual')
        value = re.findall(r'\d+', view.tabs.visual.default_items_per_page.tile_view.read())
        return int(value[0])

    @tile_view_limit.setter
    def tile_view_limit(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.default_items_per_page.tile_view.fill(str(value)):
            view.tabs.visual.save.click()

    @property
    def list_view_limit(self):
        view = navigate_to(self.my_settings, 'Visual')
        value = re.findall(r'\d+', view.tabs.visual.default_items_per_page.list_view.read())
        return int(value[0])

    @list_view_limit.setter
    def list_view_limit(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.default_items_per_page.list_view.fill(str(value)):
            view.tabs.visual.save.click()

    @property
    def report_view_limit(self):
        view = navigate_to(self.my_settings, 'Visual')
        value = re.findall(r'\d+', view.tabs.visual.default_items_per_page.reports.read())
        return int(value[0])

    @report_view_limit.setter
    def report_view_limit(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.default_items_per_page.reports.fill(str(value)):
            view.tabs.visual.save.click()

    @property
    def login_page(self):
        view = navigate_to(self.my_settings, 'Visual')
        return view.tabs.visual.start_page.show_at_login.read()

    @login_page.setter
    def login_page(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.start_page.show_at_login.fill(value):
            view.tabs.visual.save.click()

    @property
    def infra_provider_quad(self):
        view = navigate_to(self.my_settings, 'Visual')
        return view.tabs.visual.grid_tile_icons.infra_provider_quad.read()

    @infra_provider_quad.setter
    def infra_provider_quad(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.grid_tile_icons.infra_provider_quad.fill(value):
            view.tabs.visual.save.click()

    @property
    def host_quad(self):
        view = navigate_to(self.my_settings, 'Visual')
        return view.tabs.visual.grid_tile_icons.host_quad.read()

    @host_quad.setter
    def host_quad(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.grid_tile_icons.host_quad.fill(value):
            view.tabs.visual.save.click()

    @property
    def datastore_quad(self):
        view = navigate_to(self.my_settings, 'Visual')
        return view.tabs.visual.grid_tile_icons.datastore_quad.read()

    @datastore_quad.setter
    def datastore_quad(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.grid_tile_icons.datastore_quad.fill(value):
            view.tabs.visual.save.click()

    @property
    def vm_quad(self):
        view = navigate_to(self.my_settings, 'Visual')
        return view.tabs.visual.grid_tile_icons.vm_quad.read()

    @vm_quad.setter
    def vm_quad(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.grid_tile_icons.vm_quad.fill(value):
            view.tabs.visual.save.click()

    @property
    def template_quad(self):
        view = navigate_to(self.my_settings, 'Visual')
        return view.tabs.visual.grid_tile_icons.template_quad.read()

    @template_quad.setter
    def template_quad(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.grid_tile_icons.template_quad.fill(value):
            view.tabs.visual.save.click()

    @property
    def cloud_provider_quad(self):
        view = navigate_to(self.my_settings, 'Visual')
        return view.tabs.visual.grid_tile_icons.cloud_provider_quad.read()

    @cloud_provider_quad.setter
    def cloud_provider_quad(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.grid_tile_icons.cloud_provider_quad.fill(value):
            view.tabs.visual.save.click()

    @property
    def timezone(self):
        view = navigate_to(self.my_settings, 'Visual')
        return view.tabs.visual.display_settings.time_zone.read()

    @timezone.setter
    def timezone(self, value):
        view = navigate_to(self.my_settings, 'Visual')
        if view.tabs.visual.display_settings.time_zone.fill(value):
            view.tabs.visual.save.click()

    @property
    def grid_view_entities(self):
        view = navigate_to(self.my_settings, 'Visual')
        values = view.tabs.visual.default_items_per_page.grid_view.all_options
        text = [value.text for value in values]
        return text

    @property
    def tile_view_entities(self):
        view = navigate_to(self.my_settings, 'Visual')
        values = view.tabs.visual.default_items_per_page.tile_view.all_options
        text = [value.text for value in values]
        return text

    @property
    def list_view_entities(self):
        view = navigate_to(self.my_settings, 'Visual')
        values = view.tabs.visual.default_items_per_page.list_view.all_options
        text = [value.text for value in values]
        return text

    @property
    def report_view_entities(self):
        view = navigate_to(self.my_settings, 'Visual')
        values = view.tabs.visual.default_items_per_page.reports.all_options
        text = [value.text for value in values]
        return text


class DefaultViews(Updateable, NavigatableMixin):
    # Basic class for navigation to default views screen
    look_up = {
        'Flavors': ['clouds', 'flavors'],
        'Instances': ['clouds', 'instances'],
        'Availability Zones': ['clouds', 'availability_zones'],
        'Images': ['clouds', 'images'],
        'Cloud Providers': ['clouds', 'providers'],
        'Stacks': ['clouds', 'stacks'],
        'Compare': ['general', 'compare'],
        'Compare Mode': ['general', 'compare_mode'],
        'Infrastructure Providers': ['infrastructure', 'infrastructure_providers'],
        'Configuration Management Providers': ['infrastructure',
                                               'configuration_management_providers'],
        'VMs': ['infrastructure', 'vms'],
        'My Services': ['services', 'my_services'],
        'Service Catalogs': ['services', 'service_catalogs'],
        'Catalog Items': ['services', 'catalog_items'],
        'Templates & Images': ['services', 'templates'],
        'VMs & Instances': ['services', 'vms_instances'],
        'Containers Providers': ['containers', 'providers'],
        'Nodes': ['containers', 'nodes'],
        'Pods': ['containers', 'pods'],
        'Services': ['containers', 'services'],
        'Routes': ['containers', 'routes'],
        'Containers': ['containers', 'containers'],
        'Projects': ['containers', 'projects'],
        'Replicators': ['containers', 'replicators'],
        'Container Images': ['containers', 'images'],
        'Image Registries': ['containers', 'image_registries'],
        'Builds': ['containers', 'builds'],
        'Volumes': ['containers', 'volumes'],
        'Templates': ['containers', 'templates']
    }

    def __init__(self, appliance, my_settings):
        self.appliance = appliance
        self.my_settings = my_settings

    def set_default_view(self, button_group_names, defaults, fieldset=None):
        """This function sets default views for the objects.

        Args:
            button_group_names: either the name of the button_group_name
                                or list of the button groups to set the
                                default view for.
            defaults: the default view to set. in case that button_group_names
                     is a list, you can either set 1 view and it'll be set
                     for all the button_group_names or you can use a list
                     (default view per button_group_name).
        Raises:
            AssertionError
        """
        if not isinstance(button_group_names, (list, tuple)):
            button_group_names = [button_group_names]
        if not isinstance(defaults, (list, tuple)):
            defaults = [defaults] * len(button_group_names)
        assert len(button_group_names) == len(defaults)
        for button_group_name, default in zip(button_group_names, defaults):
            view = navigate_to(self.my_settings, 'DefaultViews')
            value = view.tabs.default_views
            for attribute in self.look_up[button_group_name]:
                value = getattr(value, attribute)
            if value.active_button != default:
                if value.fill(default):
                    view.tabs.default_views.save.click()

    def get_default_view(self, button_group_name, fieldset=None):
        view = navigate_to(self.my_settings, 'DefaultViews')
        value = view.tabs.default_views
        for attribute in self.look_up[button_group_name]:
            value = getattr(value, attribute)
        return value.active_button

    def set_default_view_switch_on(self):
        view = navigate_to(self.my_settings, 'DefaultViews')
        if view.tabs.default_views.vm_visibility.show_vms.fill(True):
            view.tabs.default_views.save.click()
        return True

    def set_default_view_switch_off(self):
        view = navigate_to(self.my_settings, 'DefaultViews')
        if view.tabs.default_views.vm_visibility.show_vms.fill(False):
            view.tabs.default_views.save.click()
        return True


class DefaultFilters(Updateable, Pretty, NavigatableMixin):

    pretty_attrs = ['name', 'filters']

    def __init__(self, appliance, my_settings, name=None, filters=None):
        self.appliance = appliance
        self.my_settings = my_settings
        self.name = name
        self.filters = filters or []

    def update(self, updates):
        """
        Args:
            updates: Dictionary containing 'filters' key. Values are tuples of ([path], bool)
                Where bool is whether to check or uncheck the filter

        Returns: None
        """
        view = navigate_to(self.my_settings, 'DefaultFilters')
        tree = view.tabs.default_filters.tree
        for path, check in updates['filters']:
            fill_value = tree.CheckNode(path) if check else tree.UncheckNode(path)
            if tree.fill(fill_value):
                view.tabs.default_filters.save.click()
            else:
                logger.info('No change to filter on update, not saving form.')


class TimeProfiles(Updateable, NavigatableMixin):

    def __init__(self, appliance, my_settings):
        self.appliance = appliance
        self.my_settings = my_settings


class MySettingsEntities(View):
    table = Table('//div[@id="main_div"]//table')
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h3')


class MySettingsView(BaseLoggedInPage):
    """The My Settings page"""
    entities = View.nested(MySettingsEntities)
    configuration = Dropdown('Configuration')

    @View.nested
    class tabs(View):  # noqa
        """The tabs on the page"""

        @View.nested
        class visual(WaitTab):  # noqa
            TAB_NAME = 'Visual'
            including_entities = View.include(VisualForm, use_parent=True)

        @View.nested
        class default_views(WaitTab):  # noqa
            TAB_NAME = 'Default Views'
            including_entities = View.include(DefaultViewsForm, use_parent=True)

        @View.nested
        class default_filters(WaitTab):  # noqa
            TAB_NAME = 'Default Filters'
            including_entities = View.include(DefaultFiltersForm, use_parent=True)

        @View.nested
        class time_profiles(WaitTab):  # noqa
            TAB_NAME = 'Time Profiles'
            including_entities = View.include(TimeProfilesView, use_parent=True)

    @property
    def is_displayed(self):
        return (
            self.tabs.visual.is_displayed and
            self.tabs.default_views.is_displayed and
            self.tabs.default_filters.is_displayed and
            self.tabs.time_profiles.is_displayed)


class MySettings(Updateable, NavigatableMixin):
    """The 'My Settings' page"""

    def __init__(self, appliance):
        self.appliance = appliance

    @property
    def visual(self):
        """The 'Visual' tab on the 'My Settings' page"""
        return Visual(self.appliance, self)

    @property
    def default_views(self):
        """The 'Default Views' tab on the 'My Settings' page"""
        return DefaultViews(self.appliance, self)

    @property
    def default_filters(self):
        """The 'Default Filters' tab on the 'My Settings' page"""
        return DefaultFilters(self.appliance, self)

    @property
    def time_profiles(self):
        """The 'Time Profiles' tab on the 'My Settings' page"""
        return TimeProfiles(self.appliance, self)


@navigator.register(MySettings, 'MySettings')
class MySettingsStep(CFMENavigateStep):
    VIEW = MySettingsView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        """Go to the My Settings view"""
        self.prerequisite_view.settings.select_item('My Settings')


@navigator.register(MySettings, 'Visual')
class VisualStep(CFMENavigateStep):
    VIEW = MySettingsView
    prerequisite = NavigateToSibling('MySettings')

    def step(self, *args, **kwargs):
        self.prerequisite_view.tabs.visual.select()

    def resetter(self, *args, **kwargs):
        self.view.tabs.visual.select()


@navigator.register(MySettings, 'DefaultViews')
class DefaultViewsStep(CFMENavigateStep):
    VIEW = MySettingsView
    prerequisite = NavigateToSibling('MySettings')

    def step(self, *args, **kwargs):
        self.prerequisite_view.tabs.default_views.select()

    def resetter(self, *args, **kwargs):
        self.view.tabs.default_views.select()


@navigator.register(MySettings, 'DefaultFilters')
class DefaultFiltersStep(CFMENavigateStep):
    VIEW = MySettingsView
    prerequisite = NavigateToSibling('MySettings')

    def step(self, *args, **kwargs):
        self.prerequisite_view.tabs.default_filters.select()

    def resetter(self, *args, **kwargs):
        self.view.tabs.default_filters.select()


@navigator.register(TimeProfileCollection, 'All')
class TimeProfileCollectionAll(CFMENavigateStep):
    VIEW = MySettingsView
    prerequisite = NavigateToAttribute('appliance.user.my_settings', 'MySettings')

    def step(self, *args, **kwargs):
        self.prerequisite_view.tabs.time_profiles.select()

    def resetter(self, *args, **kwargs):
        self.view.tabs.time_profiles.select()


@navigator.register(TimeProfileCollection, 'Add')
class TimeProfileAdd(CFMENavigateStep):
    VIEW = TimeProfileAddView
    prerequisite = NavigateToSibling('All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.tabs.time_profiles.select()
        self.prerequisite_view.configuration.item_select('Add a new Time Profile')


@navigator.register(TimeProfile, 'Edit')
class TimeProfileEdit(CFMENavigateStep):
    VIEW = TimeProfileEditView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.view.entities.table.row(Description=self.obj.description)[0].check()
        self.view.configuration.item_select('Edit selected Time Profile')


@navigator.register(TimeProfile, 'Copy')
class TimeProfileCopy(CFMENavigateStep):
    VIEW = TimeProfileAddView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.view.entities.table.row(Description=self.obj.description)[0].check()
        self.view.configuration.item_select('Copy selected Time Profile')

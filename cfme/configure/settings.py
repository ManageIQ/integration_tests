import re

from navmazing import NavigateToAttribute
from widgetastic_manageiq import Table, BootstrapSelect, BreadCrumb, Text, ViewButtonGroup
from widgetastic_patternfly import (BootstrapSwitch,
                                    Input, Button, CheckableBootstrapTreeview, Dropdown)
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import View
from cfme.base.ui import MySettingsView
from cfme.base.login import BaseLoggedInPage
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


class TimeProfileAddForm(View):
    description = Input(id='description')
    scope = BootstrapSelect('profile_type')
    timezone = BootstrapSelect('profile_tz')
    days = BootstrapSwitch(name='all_days')
    hours = BootstrapSwitch(name='all_hours')
    save_button = Button(VersionPick({Version.lowest(): 'Add',
                                          '5.8': 'Save'}))
    configuration = Dropdown('Configuration')
    table = Table("//div[@id='main_div']//table")
    save_edit_button = Button('Save')
    cancel_button = Button('Cancel')
    help_block = Text("//span[contains(@class, 'help-block')]")


class TimeprofileAddEntities(View):
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h3')


class TimeProfileAddFormView(BaseLoggedInPage):
    timeprofile_form = View.nested(TimeProfileAddForm)
    entities = View.nested(TimeprofileAddEntities)
    mysetting = View.nested(MySettingsView)


class Timeprofile(Updateable, Navigatable):
    def __init__(self, description=None, scope=None, days=None, hours=None, timezone=None,
                 appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.scope = scope
        self.days = days
        self.hours = hours
        self.timezone = timezone

    def create(self, cancel=False):
        view = navigate_to(self, 'All')
        view.timeprofile_form.configuration.item_select('Add a new Time Profile')
        view.timeprofile_form.fill({
            'description': self.description,
            'scope': self.scope,
            'days': self.days,
            'hours': self.hours,
            'timezone': self.timezone,
        })
        if not cancel:
            view.timeprofile_form.save_button.click()
            end = "saved" if self.appliance.version > '5.7' else "added"
            view.flash.assert_message('Time Profile "{}" was {}'.format(self.description, end))

    def update(self, updates):
        view = navigate_to(self, 'All')
        rows = view.timeprofile_form.table
        for row in rows:
            if row.description.text == self.description:
                row[0].check()
        view.timeprofile_form.configuration.item_select('Edit selected Time Profile')
        changed = view.timeprofile_form.fill({
            'description': updates.get('description'),
            'scope': updates.get('scope'),
            'days': updates.get('days'),
            'hours': updates.get('hours'),
            'timezone': updates.get('timezone'),
        })
        if changed:
            view.timeprofile_form.save_edit_button.click()
            view.flash.assert_message(
                'Time Profile "{}" was saved'.format(updates.get('description', self.description)))

    def copy(self, name=None):
        view = navigate_to(self, 'All')
        rows = view.timeprofile_form.table
        for row in rows:
            if row.description.text == self.description:
                row[0].check()
        view.timeprofile_form.configuration.item_select('Copy selected Time Profile')
        if name is not None:
            new_timeprofile = Timeprofile(description=name, scope=self.scope)
            changed = view.timeprofile_form.fill({
                'description': name,
                'scope': self.scope,
            })
        else:
            new_timeprofile = Timeprofile(description="{} copy".format(self.description),
                                          scope=self.scope)
            changed = view.timeprofile_form.fill({
                'description': "{} copy".format(self.description),
                'scope': self.scope,
            })

        if changed:
            view.timeprofile_form.save_button.click()
        return new_timeprofile

    def delete(self):
        view = navigate_to(self, 'All')
        rows = view.timeprofile_form.table
        for row in rows:
            if row.description.text == self.description:
                row[0].check()
        view.timeprofile_form.configuration.item_select("Delete selected "
                                                        "Time Profiles", handle_alert=True)


@navigator.register(Timeprofile, 'All')
class TimeprofileAll(CFMENavigateStep):
    VIEW = TimeProfileAddFormView
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        self.view.mysetting.tabs.time_profile.select()


class Visual(Updateable, Navigatable):
    @property
    def grid_view_limit(self):
        view = navigate_to(self, 'All')
        value = re.findall("\d+", view.visualitem.grid_view.read())
        return int(value[0])

    @grid_view_limit.setter
    def grid_view_limit(self, value):
        view = navigate_to(self, 'All')
        value_to_fill = str(value)
        if view.visualitem.grid_view.fill(value_to_fill):
            view.save.click()

    @property
    def tile_view_limit(self):
        view = navigate_to(self, 'All')
        value = re.findall("\d+", view.visualitem.tile_view.read())
        return int(value[0])

    @tile_view_limit.setter
    def tile_view_limit(self, value):
        view = navigate_to(self, 'All')
        value_to_fill = str(value)
        if view.visualitem.tile_view.fill(value_to_fill):
            view.save.click()

    @property
    def list_view_limit(self):
        view = navigate_to(self, 'All')
        value = re.findall("\d+", view.visualitem.list_view.read())
        return int(value[0])

    @list_view_limit.setter
    def list_view_limit(self, value):
        view = navigate_to(self, 'All')
        value_to_fill = str(value)
        if view.visualitem.list_view.fill(value_to_fill):
            view.save.click()

    @property
    def report_view_limit(self):
        view = navigate_to(self, 'All')
        value = re.findall("\d+", view.visualitem.reports.read())
        return int(value[0])

    @report_view_limit.setter
    def report_view_limit(self, value):
        view = navigate_to(self, 'All')
        value_to_fill = str(value)
        if view.visualitem.reports.fill(value_to_fill):
            view.save.click()

    @property
    def login_page(self):
        view = navigate_to(self, 'All')
        return view.visualstartpage.show_at_login.read()

    @login_page.setter
    def login_page(self, value):
        view = navigate_to(self, 'All')
        if view.visualstartpage.show_at_login.fill(value):
            view.save.click()

    @property
    def infra_provider_quad(self):
        view = navigate_to(self, 'All')
        return view.visualquadicons.infra_provider_quad.read()

    @infra_provider_quad.setter
    def infra_provider_quad(self, value):
        view = navigate_to(self, 'All')
        if view.visualquadicons.infra_provider_quad.fill(value):
            view.save.click()

    @property
    def host_quad(self):
        view = navigate_to(self, 'All')
        return view.visualquadicons.host_quad.read()

    @host_quad.setter
    def host_quad(self, value):
        view = navigate_to(self, 'All')
        if view.visualquadicons.host_quad.fill(value):
            view.save.click()

    @property
    def datastore_quad(self):
        view = navigate_to(self, 'All')
        return view.visualquadicons.datastore_quad.read()

    @datastore_quad.setter
    def datastore_quad(self, value):
        view = navigate_to(self, 'All')
        if view.visualquadicons.datastore_quad.fill(value):
            view.save.click()

    @property
    def vm_quad(self):
        view = navigate_to(self, 'All')
        return view.visualquadicons.vm_quad.read()

    @vm_quad.setter
    def vm_quad(self, value):
        view = navigate_to(self, 'All')
        if view.visualquadicons.vm_quad.fill(value):
            view.save.click()

    @property
    def template_quad(self):
        view = navigate_to(self, 'All')
        return view.visualquadicons.template_quad.read()

    @template_quad.setter
    def template_quad(self, value):
        view = navigate_to(self, 'All')
        if view.visualquadicons.template_quad.fill(value):
            view.save.click()

    @property
    def cloud_provider_quad(self):
        view = navigate_to(self, 'All')
        return view.visualquadicons.cloud_provider_quad.read()

    @cloud_provider_quad.setter
    def cloud_provider_quad(self, value):
        view = navigate_to(self, 'All')
        if view.visualquadicons.cloud_provider_quad.fill(value):
            view.save.click()

    @property
    def timezone(self):
        view = navigate_to(self, 'All')
        return view.visualdisplay.time_zone.read()

    @timezone.setter
    def timezone(self, value):
        view = navigate_to(self, 'All')
        if view.visualdisplay.time_zone.fill(value):
            view.save.click()

    @property
    def grid_view_entities(self):
        view = navigate_to(self, 'All')
        values = view.visualitem.grid_view.all_options
        text = [value.text for value in values]
        return text

    @property
    def tile_view_entities(self):
        view = navigate_to(self, 'All')
        values = view.visualitem.tile_view.all_options
        text = [value.text for value in values]
        return text

    @property
    def list_view_entities(self):
        view = navigate_to(self, 'All')
        values = view.visualitem.list_view.all_options
        text = [value.text for value in values]
        return text

    @property
    def report_view_entities(self):
        view = navigate_to(self, 'All')
        values = view.visualitem.reports.all_options
        text = [value.text for value in values]
        return text


visual = Visual()


class VisualTabForm(MySettingsView):

    @View.nested
    class visualitem(View):  # noqa
        grid_view = BootstrapSelect("perpage_grid")
        tile_view = BootstrapSelect("perpage_tile")
        list_view = BootstrapSelect("perpage_list")
        reports = BootstrapSelect("perpage_reports")

    @View.nested
    class visualstartpage(View):    # noqa
        show_at_login = BootstrapSelect("start_page")

    @View.nested
    class visualquadicons(View):    # noqa
        infra_provider_quad = BootstrapSwitch("quadicons_ems")
        cloud_provider_quad = BootstrapSwitch("quadicons_ems_cloud")
        host_quad = BootstrapSwitch("quadicons_host")
        datastore_quad = BootstrapSwitch("quadicons_storage")
        vm_quad = BootstrapSwitch("quadicons_vm")
        template_quad = BootstrapSwitch("quadicons_miq_template")
        long_text = BootstrapSelect("quad_truncate")

    @View.nested
    class visualdisplay(View):   # noqa
        chart_theme = BootstrapSelect("display_reporttheme")
        time_zone = BootstrapSelect("display_timezone")

    save = Button("Save")
    reset = Button("Reset")


@navigator.register(Visual, 'All')
class VisualAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')
    VIEW = VisualTabForm

    def step(self):
        self.view.tabs.visual_all.select()


class DefaultFilterForm(MySettingsView):
    tree = CheckableBootstrapTreeview('df_treebox')
    save = Button('Save')


class DefaultFilter(Updateable, Pretty, Navigatable):

    pretty_attrs = ['name', 'filters']

    def __init__(self, name=None, filters=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.filters = filters or []

    def update(self, updates):
        view = navigate_to(self, 'All')
        for value in updates['filters']:
            for path in value:
                if isinstance(path, list) and view.tree.fill(path):
                    view.save.click()


@navigator.register(DefaultFilter, 'All')
class DefaultFilterAll(CFMENavigateStep):
    VIEW = DefaultFilterForm
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        self.view.tabs.default_filter.select()


class DefaultViewForm(MySettingsView):
    flavors = ViewButtonGroup("Clouds", "Flavors")
    instances = ViewButtonGroup("Clouds", "Instances")
    availability_zones = ViewButtonGroup("Clouds", "Availability Zones")
    images = ViewButtonGroup("Clouds", "Images")
    cloud_providers = ViewButtonGroup("Clouds", "Cloud Providers")
    compare = ViewButtonGroup("General", "Compare")
    compare_mode = ViewButtonGroup("General", "Compare Mode")
    infrastructure_providers = ViewButtonGroup("Infrastructure", "Infrastructure Providers")
    configuration_management_providers = ViewButtonGroup('Infrastructure',
                                                         'Configuration Management Providers')
    my_services = ViewButtonGroup("Services", "My Services")
    catalog_items = ViewButtonGroup("Services", "Catalog Items")
    templates = ViewButtonGroup("Services", "Templates & Images")
    vms = ViewButtonGroup("Infrastructure", "VMs")
    vms_instances = ViewButtonGroup("Services", "VMs & Instances")
    cloud_stacks = ViewButtonGroup('Clouds', 'Stacks')

    containers_providers = ViewButtonGroup("Containers", "Containers Providers")
    container_nodes = ViewButtonGroup("Containers", "Nodes")
    container_pods = ViewButtonGroup("Containers", "Pods")
    container_services = ViewButtonGroup("Containers", "Services")
    container_routes = ViewButtonGroup("Containers", "Routes")
    container_containers = ViewButtonGroup("Containers", "Containers")
    container_projects = ViewButtonGroup("Containers", "Projects")
    container_replicators = ViewButtonGroup("Containers", "Replicators")
    container_images = ViewButtonGroup("Containers", "Images")
    container_image_registries = ViewButtonGroup("Containers", "Image Registries")
    container_builds = ViewButtonGroup("Containers", "Builds")
    container_volumes = ViewButtonGroup("Containers", "Volumes")
    container_templates = ViewButtonGroup("Containers", "Templates")
    vm_visibility = BootstrapSwitch("display_vms")
    save = Button("Save")


class DefaultView(Updateable, Navigatable):
    # Basic class for navigation to default views screen
    look_up = {'Flavors': "flavors",
               'Instances': "instances",
               'Availability Zones': "availability_zones",
               'Images': "images",
               'Cloud Providers': "cloud_providers",
               'Compare': "compare",
               'Compare Mode': "compare_mode",
               'Infrastructure Providers': "infrastructure_providers",
               'My Services': "my_services",
               'Catalog Items': "catalog_items",
               'Templates & Images': "templates",
               'VMs': "vms",
               'VMs & Instances': "vms_instances",
               'Containers Providers': 'containers_providers',
               'Nodes': 'container_nodes',
               'Pods': 'container_pods',
               'Services': 'container_services',
               'Routes': 'container_routes',
               'Containers': 'container_containers',
               'Projects': 'container_projects',
               'Replicators': 'container_replicators',
               'Container Images': 'container_images',
               'Image Registries': 'container_image_registries',
               'Builds': 'container_builds',
               'Volumes': 'container_volumes',
               'Templates': 'container_templates',
               'Configuration Management Providers': 'configuration_management_providers',
               'Stacks': 'cloud_stacks'
               }

    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance=appliance)

    @classmethod
    def set_default_view(cls, button_group_names, defaults, fieldset=None):
        """This function sets default views for the objects.

        Args:
            button_group_names: either the name of the button_group_name
                                or list of the button groups to set the
                                default view for.
            default: the default view to set. in case that button_group_names
                     is a list, you can either set 1 view and it'll be set
                     for all the button_group_names or you can use a list
                     (default view per button_group_name).
        """
        if not isinstance(button_group_names, (list, tuple)):
            button_group_names = [button_group_names]
        if not isinstance(defaults, (list, tuple)):
            defaults = [defaults] * len(button_group_names)
        assert len(button_group_names) == len(defaults)
        navigate_to(cls, 'All')
        for button_group_name, default in zip(button_group_names, defaults):
            view = navigate_to(cls, 'All')
            value = getattr(view, cls.look_up[button_group_name])
            if value.active_button != default:
                if value.fill(default):
                    view.save.click()

    @classmethod
    def get_default_view(cls, button_group_name, fieldset=None):
        view = navigate_to(cls, 'All')
        value = getattr(view, cls.look_up[button_group_name])
        return value.active_button

    @classmethod
    def set_default_view_switch_on(cls):
        view = navigate_to(cls, 'All')
        if view.vm_visibility.fill(True):
            view.save.click()
        return True

    @classmethod
    def set_default_view_switch_off(cls):
        view = navigate_to(cls, 'All')
        if view.vm_visibility.fill(False):
            view.save.click()
        return True


@navigator.register(DefaultView, 'All')
class DefaultViewAll(CFMENavigateStep):
    VIEW = DefaultViewForm
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        self.view.tabs.default_views.select()

# -*- coding: utf-8 -*-

""" Module dealing with Configure/My Setting section."""
from functools import partial

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_manageiq import Table, BootstrapSelect, BreadCrumb, Text
from widgetastic_patternfly import Dropdown, FlashMessages, BootstrapSwitch, Input, Button
from widgetastic.utils import VersionPick, Version
from widgetastic.widget import View

from cfme.base.ui import MySettingsView
from cfme.web_ui import match_location
# from utils.pretty import Pretty
from utils.update import Updateable
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
import re


match_page = partial(match_location, controller='configuration')


class SettingToolBar(View):
    configuration = Dropdown('Configuration')


class TimeProfileAddForm(MySettingsView):
    description = Input(id='description')
    scope = BootstrapSelect('profile_type')
    timezone = BootstrapSelect('profile_tz')
    days = BootstrapSwitch(name='all_days')
    hours = BootstrapSwitch(name='all_hours')
    save_button = Button(VersionPick({Version.lowest(): 'Add',
                                      '5.8': 'Save'}))
    save_edit_button = Button(VersionPick({Version.lowest(): 'Save changes',
                                           '5.8': 'Save'}))
    cancel_button = Button('Cancel')


class TimeProfileEntities(View):
    table = Table("//div[@id='main_div']//table")


class TimeprofileAddEntities(View):

    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h3')


class TimeProfileAddFormView(MySettingsView):

    form = View.nested(TimeProfileAddForm)
    entities = View.nested(TimeprofileAddEntities)


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
        view = navigate_to(self, 'Add')
        view.form.fill({
            'description': self.description,
            'scope': self.scope,
            'days': self.days,
            'hours': self.hours,
            'timezone': self.timezone,
        })

        if not cancel:
            view.form.save_button.click()
            end = "saved" if self.appliance.version > '5.7' else "added"
            FlashMessages('Time Profile "{}" was {}'.format(self.description, end))

    def update(self, updates):
        view = navigate_to(self, 'Edit')
        row = view.form.table.row()
        row[1].click()
        changed = view.form.fill({
            'scope': updates.get('scope'),
        })
        if changed:
            view.form.save_edit_button.click()
            view.flash.assert_message(
                'Time Profile "{}" was saved'.format(updates.get('description', self.description)))

    def copy(self):
        navigate_to(self, 'All')
        row = timeprofile_table.find_row_by_cells({'description': self.description})
        sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
        cfg_btn('Copy selected Time Profile')
        new_timeprofile = Timeprofile(description=self.description + "copy",
                         scope=self.scope)
        fill(self.timeprofile_form, {'description': new_timeprofile.description,
                              'scope': new_timeprofile.scope},
             action=self.save_button)
        end = "saved" if self.appliance.version > '5.7' else "added"
        flash.assert_success_message('Time Profile "{}" was {}'
                                     .format(new_timeprofile.description, end))
        return new_timeprofile

    def delete(self):
        navigate_to(self, 'All')
        row = timeprofile_table.find_row_by_cells({'description': self.description})
        sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
        cfg_btn('Delete selected Time Profiles', invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message(
            'Time Profile "{}": Delete successful'.format(self.description))


@navigator.register(Timeprofile, 'All')
class TimeprofileAll(CFMENavigateStep):
    VIEW = MySettingsView
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        self.view.tabs.time_profile.select()

    def am_i_here(self):
        return match_page(title='Configuration') and self.view.tabs.time_profile.is_active()


@navigator.register(Timeprofile, 'Add')
class TimeprofileNew(CFMENavigateStep):
    VIEW = TimeProfileAddFormView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select("Add a new Time Profile")


@navigator.register(Timeprofile, 'Edit')
class TimeprofileEdit(CFMENavigateStep):
    VIEW = TimeProfileAddFormView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit selected Time Profile")


class VisualFormView(MySettingsView):
    grid_view = BootstrapSelect('perpage_grid')
    tile_view = BootstrapSelect('perpage_tile')
    list_view = BootstrapSelect('perpage_list')
    reports = BootstrapSelect('perpage_reports')
    login_page = BootstrapSelect('start_page')
    infra_provider_quad = BootstrapSwitch('quadicons_ems')
    cloud_provider_quad = BootstrapSwitch('quadicons_ems_cloud')
    host_quad = BootstrapSwitch('quadicons_host')
    datastore_quad = BootstrapSwitch('quadicons_storage')
    datastoreitem_quad = Input('quadicons_storageitem')
    vm_quad = BootstrapSwitch('quadicons_vm')
    vmitem_quad = Input('quadicons_vmitem')
    template_quad = BootstrapSwitch('quadicons_miq_template')
    chart_theme = BootstrapSelect('display_reporttheme')
    time_zone = BootstrapSelect('display_timezone')
    save_button = Button("Add this Time Profile")


class Visual(Updateable, Navigatable):

    pretty_attrs = ['name']

    def __init__(self, grid_view=None, tile_view=None, list_view=None, reports=None,
     login_page=None, infra_provider_quad=None, cloud_provider_quad=None, host_quad=None,
     datastore_quad=None, datastoreitem_quad=None, vm_quad=None, vmitem_quad=None,
     template_quad=None, chart_theme=None, time_zone=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.grid_view = grid_view
        self.tile_view = tile_view
        self.list_view = list_view
        self.reports = reports
        self.login_page = login_page
        self.infra_provider_quad = infra_provider_quad
        self.cloud_provider_quad = cloud_provider_quad
        self.host_quad = host_quad
        self.datastore_quad = datastore_quad
        self.datastoreitem_quad = datastoreitem_quad
        self.vm_quad = vm_quad
        self.vmitem_quad = vmitem_quad
        self.template_quad = template_quad
        self.chart_theme = chart_theme
        self.time_zone = time_zone

    @property
    def grid_view_limit(self):
        view = navigate_to(self, 'All')
        return int(re.findall("\d+", view.grid_view.first_selected_option_text)[0])

    @grid_view_limit.setter
    def grid_view_limit(self, value):
        view = navigate_to(self, 'All')
        view.fill({'grid_view': str(value)})
        view.save_button.click()

    @property
    def tile_view_limit(self):
        navigate_to(self, 'All')
        return int(re.findall("\d+", self.item_form.tile_view.first_selected_option_text)[0])

    @tile_view_limit.setter
    def tile_view_limit(self, value):
        navigate_to(self, 'All')
        fill(self.item_form.tile_view, str(value))
        sel.click(form_buttons.save)

    @property
    def list_view_limit(self):
        navigate_to(self, 'All')
        return int(re.findall("\d+", self.item_form.list_view.first_selected_option_text)[0])

    @list_view_limit.setter
    def list_view_limit(self, value):
        navigate_to(self, 'All')
        fill(self.item_form.list_view, str(value))
        sel.click(form_buttons.save)

    @property
    def report_view_limit(self):
        navigate_to(self, 'All')
        return int(re.findall("\d+", self.item_form.reports.first_selected_option_text)[0])

    @report_view_limit.setter
    def report_view_limit(self, value):
        navigate_to(self, 'All')
        fill(self.item_form.reports, str(value))
        sel.click(form_buttons.save)

    @property
    def login_page(self):
        navigate_to(self, 'All')
        return self.startpage_form.login_page.first_selected_option_text

    @login_page.setter
    def login_page(self, value):
        navigate_to(self, 'All')
        fill(self.startpage_form.login_page, str(value))
        sel.click(form_buttons.save)

    @property
    def infra_provider_quad(self):
        navigate_to(self, 'All')
        return self.infra_provider_quad

    @infra_provider_quad.setter
    def infra_provider_quad(self, value):
        navigate_to(self, 'All')
        fill(self.quadicons_form.infra_provider_quad, value)
        sel.click(form_buttons.save)

    @property
    def host_quad(self):
        navigate_to(self, 'All')
        return self.host_quad

    @host_quad.setter
    def host_quad(self, value):
        navigate_to(self, 'All')
        fill(self.quadicons_form.host_quad, value)
        sel.click(form_buttons.save)

    @property
    def datastore_quad(self):
        navigate_to(self, 'All')
        return self.datastore_quad

    @datastore_quad.setter
    def datastore_quad(self, value):
        navigate_to(self, 'All')
        fill(self.quadicons_form.datastore_quad, value)
        sel.click(form_buttons.save)

    @property
    def vm_quad(self):
        navigate_to(self, 'All')
        return self.vm_quad

    @vm_quad.setter
    def vm_quad(self, value):
        navigate_to(self, 'All')
        fill(self.quadicons_form.vm_quad, value)
        sel.click(form_buttons.save)

    @property
    def template_quad(self):
        navigate_to(self, 'All')
        return self.template_quad

    @template_quad.setter
    def template_quad(self, value):
        navigate_to(self, 'All')
        fill(self.quadicons_form.template_quad, value)
        sel.click(form_buttons.save)

    def check_image_exists(self):
        name = Quadicon.get_first_quad_title()
        quad = Quadicon(name, None)
        return quad.check_for_single_quadrant_icon

    @property
    def cloud_provider_quad(self):
        navigate_to(self, 'All')
        return self.cloud_provider_quad

    @cloud_provider_quad.setter
    def cloud_provider_quad(self, value):
        navigate_to(self, 'All')
        fill(self.quadicons_form.cloud_provider_quad, value)
        sel.click(form_buttons.save)

    @property
    def timezone(self):
        navigate_to(self, 'All')
        return self.display_form.time_zone.first_selected_option_text

    @timezone.setter
    def timezone(self, value):
        navigate_to(self, 'All')
        fill(self.display_form.time_zone, str(value))
        sel.click(form_buttons.save)


visual = Visual()


@navigator.register(Visual, 'All')
class VisualAll(CFMENavigateStep):
    VIEW = VisualFormView
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        self.prerequisite_view.visual_all.select("Visual")


class DefaultFilter(Updateable, Pretty, Navigatable):
    filter_form = Form(
        fields=[
            ("filter_tree", {
                version.LOWEST: CheckboxTree("//div[@id='all_views_treebox']/ul"),
                '5.7': BootstrapTreeview('df_treebox')
            }),
        ]
    )

    pretty_attrs = ['name', 'filters']

    def __init__(self, name=None, filters=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.filters = filters or []

    def update(self, updates, expect_success=True):
        navigate_to(self, 'All')
        fill(self.filter_form, {'filter_tree': updates.get('filters')},
             action=form_buttons.save)
        if expect_success:
            flash.assert_success_message('Default Filters saved successfully')


@navigator.register(DefaultFilter, 'All')
class DefaultFilterAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        tabs.select_tab("Default Filters")


class DefaultView(Updateable, Navigatable):
    # Basic class for navigation to default views screen
    # TODO implement default views form with widgetastic to simplify setting views in tests

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

        Examples:
            - set_default_view('Containers Providers, 'List View') --> set
              'List View' default view to 'Containers Providers'
            - set_default_view(['Images', 'Projects', 'Routes'], 'Tile View')
              --> set 'Tile View' default view to 'Images', 'Projects' and 'Routes'
            - set_default_view(['Images', 'Projects', 'Routes'],
              ['Tile View', 'Tile View', 'Grid View']) -->
              set 'Tile View' default view to 'Images' and 'Projects' and 'Grid View'
              default view to 'Routes'
        """

        if not isinstance(button_group_names, (list, tuple)):
            button_group_names = [button_group_names]
        if not isinstance(defaults, (list, tuple)):
            defaults = [defaults] * len(button_group_names)
        assert len(button_group_names) == len(defaults)

        is_something_changed = False
        for button_group_name, default in zip(button_group_names, defaults):
            bg = ButtonGroup(button_group_name, fieldset=fieldset)
            navigate_to(cls, 'All')
            if bg.active != default:
                bg.choose(default)
                is_something_changed = True

        if is_something_changed:
            sel.click(form_buttons.save)

    @classmethod
    def get_default_view(cls, button_group_name, fieldset=None):
        bg = ButtonGroup(button_group_name, fieldset=fieldset)
        navigate_to(cls, 'All')
        return bg.active


@navigator.register(DefaultView, 'All')
class DefaultViewAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def am_i_here(self):
        if match_location(title='Configuration', controller='configuration'):
            return tabs.is_tab_selected('Default Views')

    def step(self, *args, **kwargs):
        tabs.select_tab('Default Views')

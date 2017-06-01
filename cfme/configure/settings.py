# -*- coding: utf-8 -*-

""" Module dealing with Configure/My Setting section."""

from functools import partial
import re

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.toolbar as tb
from cfme.web_ui import (
    AngularSelect, Form, Region, fill, form_buttons, flash, Table, ButtonGroup, Quadicon,
    CheckboxTree, Input, CFMECheckbox, BootstrapTreeview, match_location)
from navmazing import NavigateToSibling, NavigateToAttribute
from utils import version, deferred_verpick
from utils.pretty import Pretty
from utils.update import Updateable
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
timeprofile_table = Table("//div[@id='main_div']//table")


class Timeprofile(Updateable, Navigatable):
    timeprofile_form = Form(
        fields=[
            ("description", Input("description")),
            ("scope", AngularSelect("profile_type")),
            ("timezone", AngularSelect("profile_tz")),
            ("days", CFMECheckbox("all_days")),
            ("hours", CFMECheckbox("all_hours")),
        ]
    )
    save_edit_button = deferred_verpick({'5.7': form_buttons.FormButton('Save changes'),
                                         '5.8': form_buttons.FormButton('Save')})
    save_button = deferred_verpick({
        version.LOWEST: form_buttons.FormButton("Add this Time Profile"),
        '5.7': form_buttons.FormButton('Add'),
        '5.8': form_buttons.FormButton('Save')
    })

    def __init__(self, description=None, scope=None, days=None, hours=None, timezone=None,
            appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.scope = scope
        self.days = days
        self.hours = hours
        self.timezone = timezone

    def create(self, cancel=False):
        navigate_to(self, 'Add')
        fill(self.timeprofile_form, {'description': self.description,
                                     'scope': self.scope,
                                     'days': self.days,
                                     'hours': self.hours,
                                     'timezone': self.timezone,
                                     })
        if not cancel:
            sel.click(self.save_button)
            end = "saved" if self.appliance.version > '5.7' else "added"
            flash.assert_success_message('Time Profile "{}" was {}'
                                         .format(self.description, end))

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(self.timeprofile_form, {'description': updates.get('description'),
                                     'scope': updates.get('scope'),
                                     'timezone': updates.get('timezone')},
             action={version.LOWEST: form_buttons.save,
                     '5.7': self.save_edit_button})
        flash.assert_success_message(
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
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        tabs.select_tab("Time Profiles")


@navigator.register(Timeprofile, 'Add')
class TimeprofileNew(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        cfg_btn('Add a new Time Profile')


@navigator.register(Timeprofile, 'Edit')
class TimeprofileEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        timeprofile_table.click_cell("description", self.obj.description)


class Visual(Updateable, Navigatable):

    pretty_attrs = ['name']

    item_form = Form(
        fields=[
            ('grid_view', AngularSelect('perpage_grid')),
            ('tile_view', AngularSelect("perpage_tile")),
            ('list_view', AngularSelect("perpage_list")),
            ('reports', AngularSelect("perpage_reports")),
        ])

    startpage_form = Form(
        fields=[
            ('login_page', AngularSelect("start_page"))])

    quadicons_form = Form(
        fields=[
            ('infra_provider_quad', CFMECheckbox("quadicons_ems")),
            ('cloud_provider_quad', CFMECheckbox("quadicons_ems_cloud")),
            ('host_quad', CFMECheckbox("quadicons_host")),
            ('datastore_quad', CFMECheckbox("quadicons_storage")),
            ('datastoreitem_quad', Input("quadicons_storageitem")),
            ('vm_quad', CFMECheckbox("quadicons_vm")),
            ('vmitem_quad', Input("quadicons_vmitem")),
            ('template_quad', CFMECheckbox("quadicons_miq_template")),
        ])

    display_form = Form(
        fields=[
            ('chart_theme', AngularSelect("display_reporttheme")),
            ('time_zone', AngularSelect("display_timezone")),
        ])

    save_button = form_buttons.FormButton("Add this Time Profile")

    @property
    def grid_view_limit(self):
        navigate_to(self, 'All')
        return int(re.findall("\d+", self.item_form.grid_view.first_selected_option_text)[0])

    @grid_view_limit.setter
    def grid_view_limit(self, value):
        navigate_to(self, 'All')
        fill(self.item_form.grid_view, str(value))
        sel.click(form_buttons.save)

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
    prerequisite = NavigateToAttribute('appliance.server', 'MySettings')

    def step(self):
        tabs.select_tab("Visual")


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
            * button_group_names: either the name of the button_group_name
                                  or list of the button groups to set the
                                  default view for.
            * default: the default view to set. in case that button_group_names
                       is a list, you can either set 1 view and it'll be set
                       for all the button_group_names or you can use a list
                       (default view per button_group_name).
        Examples:
            * set_default_view('Containers Providers, 'List View') --> set
              'List View' default view to 'Containers Providers'
            * set_default_view(['Images', 'Projects', 'Routes'], 'Tile View')
              --> set 'Tile View' default view to 'Images', 'Projects' and 'Routes'
            * set_default_view(['Images', 'Projects', 'Routes'],
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

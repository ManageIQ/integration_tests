# -*- coding: utf-8 -*-

""" Module dealing with Configure/My Setting section."""

from functools import partial
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.toolbar as tb
from cfme.web_ui import (AngularSelect, Form, Region, Select, fill, form_buttons, flash, Table,
    ButtonGroup, Quadicon, CheckboxTree, Input, CFMECheckbox, BootstrapTreeview)
from cfme.web_ui.menu import nav
from navmazing import NavigateToSibling, NavigateToAttribute
from utils import version, deferred_verpick
from utils.blockers import BZ
from utils.pretty import Pretty
from utils.update import Updateable
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
timeprofile_table = Table("//div[@id='main_div']//table")


nav.add_branch(
    'my_settings',
    {

        'my_settings_default_views': [lambda _: tabs.select_tab("Default Views"), {}],
    }
)


class Timeprofile(Updateable, Navigatable):
    timeprofile_form = Form(
        fields=[
            ("description", Input("description")),
            ("scope", {
                version.LOWEST: Select("select#profile_type"),
                "5.5": AngularSelect("profile_type")}),
            ("timezone", {
                version.LOWEST: Select("select#profile_tz"),
                "5.5": AngularSelect("profile_tz")}),
            ("days", CFMECheckbox("all_days")),
            ("hours", CFMECheckbox("all_hours")),
        ]
    )

    save_button = deferred_verpick({
        version.LOWEST: form_buttons.FormButton("Add this Time Profile"),
        '5.7': form_buttons.FormButton('Add')
    })

    def __init__(self, description=None, scope=None, days=None, hours=None, timezone=None,
            appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.description = description
        self.scope = scope
        self.days = days
        self.hours = hours
        self.timezone = timezone

    def create(self):
        navigate_to(self, 'Add')
        fill(self.timeprofile_form, {'description': self.description,
                                     'scope': self.scope,
                                     'days': self.days,
                                     'hours': self.hours,
                                     'timezone': self.timezone,
                                     },
             action=self.save_button)
        tp_ui_bug = BZ(1334440, forced_streams=["5.6"])
        end = "saved" if version.current_version() > '5.7' else "added"
        if not tp_ui_bug.blocks:
            flash.assert_success_message('Time Profile "{}" was {}'.format(self.description, end))

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(self.timeprofile_form, {'description': updates.get('description'),
                                     'scope': updates.get('scope'),
                                     'timezone': updates.get('timezone')},
             action=form_buttons.save)
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
        flash.assert_success_message(
            'Time Profile "{}" was added'.format(new_timeprofile.description))
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
            ('grid_view', {
                version.LOWEST: Select('//select[@id="perpage_grid"]'),
                "5.5": AngularSelect('perpage_grid')}),
            ('tile_view', {
                version.LOWEST: Select('//select[@id="perpage_tile"]'),
                "5.5": AngularSelect("perpage_tile")}),
            ('list_view', {
                version.LOWEST: Select('//select[@id="perpage_list"]'),
                "5.5": AngularSelect("perpage_list")}),
            ('reports', {
                version.LOWEST: Select('//select[@id="perpage_reports"]'),
                "5.5": AngularSelect("perpage_reports")}),
        ])

    startpage_form = Form(
        fields=[
            ('login_page', {
                version.LOWEST: Select('//select[@id="start_page"]'),
                "5.5": AngularSelect("start_page")})])

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
            ('chart_theme', {
                version.LOWEST: Select('//select[@id="display_reporttheme"]'),
                "5.5": AngularSelect("display_reporttheme")}),
            ('time_zone', {
                version.LOWEST: Select('//select[@id="display_timezone"]'),
                "5.5": AngularSelect("display_timezone")}),
        ])

    save_button = form_buttons.FormButton("Add this Time Profile")

    @property
    def grid_view_limit(self):
        navigate_to(self, 'All')
        return int(self.item_form.grid_view.first_selected_option_text)

    @grid_view_limit.setter
    def grid_view_limit(self, value):
        navigate_to(self, 'All')
        fill(self.item_form.grid_view, str(value))
        sel.click(form_buttons.save)

    @property
    def tile_view_limit(self):
        navigate_to(self, 'All')
        return int(self.item_form.tile_view.first_selected_option_text)

    @tile_view_limit.setter
    def tile_view_limit(self, value):
        navigate_to(self, 'All')
        fill(self.item_form.tile_view, str(value))
        sel.click(form_buttons.save)

    @property
    def list_view_limit(self):
        navigate_to(self, 'All')
        return int(self.item_form.list_view.first_selected_option_text)

    @list_view_limit.setter
    def list_view_limit(self, value):
        navigate_to(self, 'All')
        fill(self.item_form.list_view, str(value))
        sel.click(form_buttons.save)

    @property
    def report_view_limit(self):
        navigate_to(self, 'All')
        return int(self.item_form.reports.first_selected_option_text)

    @report_view_limit.setter
    def report_view_limit(self, value):
        navigate_to(self, 'All')
        fill(self.item_form.reports, str(value))
        sel.click(form_buttons.save)

    @property
    def login_page(self):
        navigate_to(self, 'All')
        return int(self.startpage_form.login_page.first_selected_option_text)

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


def set_default_view(button_group_name, view):
    bg = ButtonGroup(button_group_name)
    sel.force_navigate("my_settings_default_views")
    default_view = bg.active
    if(default_view != view):
        bg.choose(view)
        sel.click(form_buttons.save)

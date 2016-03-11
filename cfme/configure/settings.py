# -*- coding: utf-8 -*-

""" Module dealing with Configure/My Setting section."""

from functools import partial
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.toolbar as tb
from cfme.web_ui import (AngularSelect, Form, Region, Select, fill, form_buttons, flash, Table,
    ButtonGroup, Quadicon, CheckboxTree, Input)
from cfme.web_ui.menu import nav
from utils import version
from utils.pretty import Pretty
from utils.update import Updateable


details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
timeprofile_table = Table("//div[@id='main_div']//table")


nav.add_branch(
    'my_settings',
    {
        'my_settings_time_profiles':
        [
            lambda _: tabs.select_tab("Time Profiles"),
            {
                "timeprofile_new":
                lambda _: cfg_btn('Add a new Time Profile'),

                "timeprofile_edit":
                lambda ctx: timeprofile_table.click_cell(
                    "description", ctx.timeprofile.description),

            }
        ],
        'my_settings_visual': [lambda _: tabs.select_tab("Visual"), {}],
        'my_settings_default_filters': [lambda _: tabs.select_tab("Default Filters"), {}],
        'my_settings_default_views': [lambda _: tabs.select_tab("Default Views"), {}],
    }
)


class Timeprofile(Updateable):
    timeprofile_form = Form(
        fields=[
            ("description", Input("description")),
            ("scope", {
                version.LOWEST: Select("select#profile_type"),
                "5.5": AngularSelect("profile_type")}),
            ("timezone", {
                version.LOWEST: Select("select#profile_tz"),
                "5.5": AngularSelect("profile_tz")}),
            ("days", Input("all_days")),
            ("hours", Input("all_hours")),
        ]
    )

    save_button = form_buttons.FormButton("Add this Time Profile")

    def __init__(self, description=None, scope=None, days=None, hours=None, timezone=None):
        self.description = description
        self.scope = scope
        self.days = days
        self.hours = hours
        self.timezone = timezone

    def create(self):
        sel.force_navigate('timeprofile_new')
        fill(self.timeprofile_form, {'description': self.description,
                                     'scope': self.scope,
                                     'days': self.days,
                                     'hours': self.hours,
                                     'timezone': self.timezone,
                                     },
             action=self.save_button)
        flash.assert_success_message('Time Profile "{}" was added'.format(self.description))

    def update(self, updates):
        sel.force_navigate("timeprofile_edit", context={"timeprofile": self})
        fill(self.timeprofile_form, {'description': updates.get('description'),
                                     'scope': updates.get('scope'),
                                     'timezone': updates.get('timezone')},
             action=form_buttons.save)
        flash.assert_success_message(
            'Time Profile "{}" was saved'.format(updates.get('description', self.description)))

    def copy(self):
        sel.force_navigate("my_settings_time_profiles")
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
        sel.force_navigate("my_settings_time_profiles")
        row = timeprofile_table.find_row_by_cells({'description': self.description})
        sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
        cfg_btn('Delete selected Time Profiles', invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message(
            'Time Profile "{}": Delete successful'.format(self.description))


class Visual(Updateable):

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
            ('infra_provider_quad', Input("quadicons_ems")),
            ('cloud_provider_quad', Input("quadicons_ems_cloud")),
            ('host_quad', Input("quadicons_host")),
            ('datastore_quad', Input("quadicons_storage")),
            ('datastoreitem_quad', Input("quadicons_storageitem")),
            ('vm_quad', Input("quadicons_vm")),
            ('vmitem_quad', Input("quadicons_vmitem")),
            ('template_quad', Input("quadicons_miq_template")),
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
        sel.force_navigate("my_settings_visual")
        return int(self.item_form.grid_view.first_selected_option_text)

    @grid_view_limit.setter
    def grid_view_limit(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.item_form.grid_view, str(value))
        sel.click(form_buttons.save)

    @property
    def tile_view_limit(self):
        sel.force_navigate("my_settings_visual")
        return int(self.item_form.tile_view.first_selected_option_text)

    @tile_view_limit.setter
    def tile_view_limit(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.item_form.tile_view, str(value))
        sel.click(form_buttons.save)

    @property
    def list_view_limit(self):
        sel.force_navigate("my_settings_visual")
        return int(self.item_form.list_view.first_selected_option_text)

    @list_view_limit.setter
    def list_view_limit(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.item_form.list_view, str(value))
        sel.click(form_buttons.save)

    @property
    def report_view_limit(self):
        sel.force_navigate("my_settings_visual")
        return int(self.item_form.reports.first_selected_option_text)

    @report_view_limit.setter
    def report_view_limit(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.item_form.reports, str(value))
        sel.click(form_buttons.save)

    @property
    def login_page(self):
        sel.force_navigate("my_settings_visual")
        return int(self.startpage_form.login_page.first_selected_option_text)

    @login_page.setter
    def login_page(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.startpage_form.login_page, str(value))
        sel.click(form_buttons.save)

    @property
    def infra_provider_quad(self):
        sel.force_navigate("my_settings_visual")
        return self.infra_provider_quad

    @infra_provider_quad.setter
    def infra_provider_quad(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.quadicons_form.infra_provider_quad, str(value))
        sel.click(form_buttons.save)

    @property
    def host_quad(self):
        sel.force_navigate("my_settings_visual")
        return self.host_quad

    @host_quad.setter
    def host_quad(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.quadicons_form.host_quad, str(value))
        sel.click(form_buttons.save)

    @property
    def datastore_quad(self):
        sel.force_navigate("my_settings_visual")
        return self.datastore_quad

    @datastore_quad.setter
    def datastore_quad(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.quadicons_form.datastore_quad, str(value))
        sel.click(form_buttons.save)

    @property
    def vm_quad(self):
        sel.force_navigate("my_settings_visual")
        return self.vm_quad

    @vm_quad.setter
    def vm_quad(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.quadicons_form.vm_quad, str(value))
        sel.click(form_buttons.save)

    @property
    def template_quad(self):
        sel.force_navigate("my_settings_visual")
        return self.template_quad

    @template_quad.setter
    def template_quad(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.quadicons_form.template_quad, str(value))
        sel.click(form_buttons.save)

    def check_image_exists(self):
        name = Quadicon.get_first_quad_title()
        quad = Quadicon(name, None)
        return quad.check_for_single_quadrant_icon

    @property
    def cloud_provider_quad(self):
        sel.force_navigate("my_settings_visual")
        return self.cloud_provider_quad

    @cloud_provider_quad.setter
    def cloud_provider_quad(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.quadicons_form.cloud_provider_quad, str(value))
        sel.click(form_buttons.save)

    @property
    def timezone(self):
        sel.force_navigate("my_settings_visual")
        return self.display_form.time_zone.first_selected_option_text

    @timezone.setter
    def timezone(self, value):
        sel.force_navigate("my_settings_visual")
        fill(self.display_form.time_zone, str(value))
        sel.click(form_buttons.save)

visual = Visual()


class DefaultFilter(Updateable, Pretty):
    filter_form = Form(
        fields=[
            ("filter_tree", CheckboxTree("//div[@id='all_views_treebox']/ul")),
        ]
    )

    pretty_attrs = ['name', 'filters']

    def __init__(self, name=None, filters=None):
        self.name = name
        self.filters = filters or []

    def update(self, updates, expect_success=True):
        sel.force_navigate("my_settings_default_filters", context=self)
        fill(self.filter_form, {'filter_tree': updates.get('filters')},
             action=form_buttons.save)
        if expect_success:
            flash.assert_success_message('Default Filters saved successfully')


def set_default_view(button_group_name, view):
    bg = ButtonGroup(button_group_name)
    sel.force_navigate("my_settings_default_views")
    default_view = bg.active
    if(default_view != view):
        bg.choose(view)
        sel.click(form_buttons.save)

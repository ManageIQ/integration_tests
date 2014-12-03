# -*- coding: utf-8 -*-

""" Module dealing with Configure/My Setting section."""

from functools import partial
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.toolbar as tb
from cfme.web_ui import Form, Region, Select, fill, form_buttons, flash, Table
from cfme.web_ui.menu import nav
from utils.update import Updateable


details_page = Region(infoblock_type='detail')

cfg_btn = partial(tb.select, 'Configuration')
timeprofile_table = Table("//div[@id='main_div']//table[@class='style3']")

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
                lambda ctx: timeprofile_table.click_cell("description", ctx.description),

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
            ("description", "//input[@id='description']"),
            ("scope", Select("//select[@id='profile_type']")),
            ("timezone", Select("//select[@id='profile_tz']")),
            ("days", "//input[@id='all_days']"),
            ("hours", "//input[@id='all_hours']"),
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
        sel.force_navigate("timeprofile_edit", context=self)
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
    item_form = Form(
        fields=[
            ('grid_view', Select('//select[@id="perpage_grid"]')),
            ('tile_view', Select('//select[@id="perpage_tile"]')),
            ('list_view', Select('//select[@id="perpage_list"]')),
            ('reports', Select('//select[@id="perpage_reports"]')),
        ])

    save_button = form_buttons.FormButton("Add this Time Profile")

    def __init__(self, grid_view=None, tile_view=None, list_view=None):
        self.grid_view = grid_view
        self.tile_view = tile_view
        self.list_view = list_view

    def updatesettings(self):
        sel.force_navigate("my_settings_visual")
        fill(self.item_form, {'grid_view': self.grid_view,
                              'tile_view': self.tile_view,
                              'list_view': self.list_view},
             action=form_buttons.save)
        flash.assert_success_message('User Interface settings saved for User Administrator')

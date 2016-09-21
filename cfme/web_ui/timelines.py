from datetime import datetime
from cfme.web_ui import flash, jstimelines, Form, AngularSelect, Calendar, fill

NONE_GROUP = 'NONE'

timelines_form = Form(
    fields=[
        ('event_type', AngularSelect('tl_show')),
        ('interval', AngularSelect('tl_typ')),
        ('date', Calendar('miq_date_1')),
        ('days_back', AngularSelect('tl_days')),
        ('level', AngularSelect('tl_fl_typ')),
        ('group1', AngularSelect('tl_fl_grp1')),
        ('group2', AngularSelect('tl_fl_grp2')),
        ('group3', AngularSelect('tl_fl_grp3')),
    ])


class Timelines(object):
    """ Represents Common UI Page for showing generated events
    of different Providers as a timeline.
    UI page contains several drop-down items which are doing filtering of displayed events.
    In this class, there are described several methods to change those filters.
    After each filter change, UI page is reloaded and the displayed events graphic is changed.
    And after each page reload, the displayed events are re-read by this class.
    The main purpose of this class is to check
    whether particular event is displayed or not in timelines page.

    Usage:
        timelines.change_interval('Hourly')
        timelines.change_event_groups('Application')
        timelines.change_level('Summary')
        timelines.contains_event('hawkular_deployment.ok')
    """

    def __init__(self, o):
        self._object = o
        self._events = []
        self.reload()

    def change_event_type(self, value):
        self._change_select_value('event_type', value)
        self._reload_events()

    def change_interval(self, value):
        self._change_select_value('interval', value)
        self._reload_events()

    def change_date(self, value):
        fill(timelines_form, {'date': value})
        self._reload_events()

    def change_days_back(self, value):
        self._change_select_value('days_back', value)
        self._reload_events()

    def change_level(self, value):
        self._change_select_value('level', value)
        self._reload_events()

    def change_event_groups(self, new_group1, new_group2=NONE_GROUP, new_group3=NONE_GROUP):
        # keep filling separetely, as page is reloaded after each select change
        self._change_select_value('group1', new_group1)
        self._change_select_value('group2', new_group2)
        self._change_select_value('group3', new_group3)
        self._reload_events()

    def contains_event(self, event_type, date_after=datetime.min):
        """Checks whether list of events contains provided particular
        'event_type' with data not earlier than provided 'date_after'.
        If 'date_after' is not provided, will use datetime.min.
        """
        if date_after and not isinstance(date_after, datetime):
            raise KeyError("'date_after' should be an instance of date")
        for event in self._events:
            if event['Event Type'] == event_type and datetime.strptime(
                    event['Date Time'], '%Y-%m-%d %H:%M:%S %Z') >= date_after:
                return True
        return False

    def _change_select_value(self, field, value):
        fill(timelines_form, {field: value})

    def reload(self):
        self._object.load_timelines_page()
        self._reload_events()

    def _reload_events(self):
        self._events = self._read_events()

    def _read_events(self):
        events = []
        # need first to check if timelines are loaded
        if not any(["No records found for this timeline"
                    in fm.message for fm in flash.get_messages()]):
            for event in jstimelines.events():
                events.append(event.block_info())
        return events

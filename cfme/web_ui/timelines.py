from datetime import datetime
from cfme.utils.appliance.implementations.ui import navigate_to

NONE_GROUP = 'NONE'


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
        timelines.change_interval('Days')
        timelines.select_event_category('Application')
        timelines.check_detailed_events(True)
        timelines.contains_event('hawkular_deployment.ok')
    """

    def __init__(self, o):
        self._object = o
        self._events = []
        self.reload()

    def change_event_type(self, value):
        self.timelines_view.filter.event_type.select_by_visible_text(value)
        self.timelines_view.filter.apply.click()
        self._reload_events()

    def change_interval(self, value):
        self.timelines_view.filter.time_range.select_by_visible_text(value)
        self.timelines_view.filter.apply.click()
        self._reload_events()

    def change_date(self, value):
        self.timelines_view.filter.time_position.select_by_visible_text(value)
        self.timelines_view.filter.apply.click()
        self._reload_events()

    def check_detailed_events(self, value):
        self.timelines_view.filter.detailed_events.fill(value)
        self.timelines_view.filter.apply.click()
        self._reload_events()

    def select_event_category(self, value):
        self.timelines_view.filter.event_category.select_by_visible_text(value)
        self.timelines_view.filter.apply.click()
        self._reload_events()

    def contains_event(self, event_type, date_after=datetime.min):
        """Checks whether list of events contains provided particular
        'event_type' with data not earlier than provided 'date_after'.
        If 'date_after' is not provided, will use datetime.min.
        """
        if date_after and not isinstance(date_after, datetime):
            raise KeyError("'date_after' should be an instance of date")
        for event in self._events:
            if event.event_type == event_type and datetime.strptime(
                    event.date_time, '%Y-%m-%d %H:%M:%S %Z') >= date_after:
                return True
        return False

    def reload(self):
        self.timelines_view = navigate_to(self._object, 'Timelines')
        self._reload_events()

    def _reload_events(self):
        self._events = self.timelines_view.chart.get_events()

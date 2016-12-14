import calendar
from datetime import datetime, timedelta
from functools import partial

import re
from cfme import web_ui
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Table, toolbar as tb, flash
from mgmtsystem.hawkular import MetricEnumCounter, MetricEnumGauge
from utils import attributize_string
from utils.browser import ensure_browser_open
from utils.units import Unit

mon_btn = partial(tb.select, 'Monitoring')
CHARTS = "//*[contains(@class, 'chart_parent')]"


def value_of(text_value, remove_comma=True):
    """Converts string value to Int, Float or String
    Args:
        remove_comma: When we set this value as True,
        removes all comma from the string. Default True
    """
    if remove_comma:
        text_value = text_value.replace(',', '')
    # Try parsing a number
    try:
        return int(text_value)
    except (ValueError, TypeError):
        try:
            return float(text_value)
        except (ValueError, TypeError):
            try:
                return Unit.parse(text_value)
            except ValueError:
                return text_value


def round_double(value, precision=2):
    """Round double value with precision limit"""
    if value:
        return round(value, precision)
    return value


class Utilization(object):
    """Utilization class is the top level class for chart management in Middleware.
     We have to create Utilization with reference of any page which has
     `Utilization >> Monitoring` tab. Reference page must have implemented
     `load_utilization_page()` function which will take to Monitoring page.
     """

    def __init__(self, o):
        self._object = o
        self._charts = []
        self.reload()

    def __repr__(self):
        return "<Utilization {}>".format(", ".join(self._charts))

    def load_utilization_page(self, refresh=True):
        ensure_browser_open()
        self._object.load_details(refresh=refresh)
        mon_btn("Utilization")

    @property
    def page(self):
        """Returns page object of caller"""
        return self._object

    def reload(self, force_reload=False):
        """Reload the entire page"""
        self.load_utilization_page(refresh=force_reload)
        self._reload(force_reload)

    def _reload(self, force_reload=False):
        if not force_reload and len(self._charts) > 0:
            return
        # remove old charts
        for chart_id in self._charts:
            try:
                delattr(self, chart_id)
            except AttributeError:
                pass
        self._charts = []
        # load available charts
        for chart in sel.elements(CHARTS):
            chart_text = sel.text_sane(chart.find_element_by_class_name('card-pf-title'))
            chart_id = attributize_string(chart_text.strip())
            chart_object = LineChart(chart_id=chart_id, name=chart_text, utilization_object=self)
            setattr(self, chart_id, chart_object)
            self._charts.append(chart_id)

    def __iter__(self):
        """This enables you to iterate through like it was a dictionary, just without .iteritems"""
        for chart_id in self._charts:
            yield (chart_id, getattr(self, chart_id))

    @property
    def charts(self):
        """Returns available charts on monitoring page"""
        return self._charts


class LineChart(object):
    """LineChart supports to do actions on line chart"""
    LEGENDS = "//*[name()='g']//*[contains(@class, 'c3-legend-item ') or @class='c3-legend-item']"
    # Map shorten UI key and table key
    # When we have long name in chart legend, name will be shorten with '...'.
    # In table header will be with full name. To map both places we have introduced this map
    # You have to put entry like, "shorten_name": "actual_name"
    key_ui_table_map = {
        "delivering_message": "delivering_message_count",
        "durable_subscripti": "durable_subscription_count",
        "non_durable_messag": "non_durable_messages_count",
        "non_durable_subscr": "non_durable_subscription_count",
    }

    @classmethod
    def _get_ui_key(cls, key):
        ui_key = cls.key_ui_table_map.get(key, None)
        if ui_key:
            return ui_key
        return key

    def __init__(self, chart_id, name, utilization_object):
        self.id = chart_id
        self.name = name
        self._utz_object = utilization_object
        self._legends = []
        self._c_lines = []
        self._c_object = None
        self._option = Option(o=self)

    def __repr__(self):
        return "<LineChart '{}':{}>".format(self.name, ", ".join(self._legends))

    @property
    def option(self):
        """Gives option object as property"""
        return self._option

    @property
    def is_on_chart_page(self):
        """Returns True we we are in detailed chart page, otherwise False"""
        if len(sel.text_sane(sel.elements(CHARTS))) == 0:
            return False
        if sel.text_sane(sel.element(CHARTS).find_element_by_tag_name('h2')) == self.name \
                and len(sel.elements(
                    "//table[contains(@class, 'table')]//th[normalize-space(.)='Date/Time']")) == 1:
            return True
        return False

    def load_chart_reference(self, force_reload=False):
        """Takes current page to chart detailed page"""
        if self.is_on_chart_page and not force_reload:
            return
        if not self.is_on_chart_page:
            self._utz_object.reload()
        self._c_object = None
        if not self.is_on_chart_page:
            root_objs = sel.elements(CHARTS)
            for root_obj in root_objs:
                if sel.text_sane(root_obj.find_element_by_tag_name('h2')) == self.name:
                    root_obj.find_element_by_tag_name("a").click()
                    sel.wait_for_ajax()
                    self._c_object = sel.element(CHARTS)
                    break
        else:
            self._c_object = sel.element(CHARTS)
        if self._c_object is None:
            raise RuntimeError("Unable to get detail page of '{}'".format(self.name))
        # remove old legends and load new legends
        for legend_id in self._legends:
            try:
                delattr(self, legend_id)
            except AttributeError:
                pass
        self._legends = []
        # load available legends
        for legend in sel.elements(self.LEGENDS):
            legend_text = sel.text_sane(legend)
            # changing legend name to full name with pre defined map
            legend_id = self._get_ui_key(attributize_string(legend_text.strip()))
            legend_object = Legend(name=legend_text, legend_object=legend)
            setattr(self, legend_id, legend_object)
            self._legends.append(legend_id)
        self._c_lines = self._c_object\
            .find_elements_by_xpath("//*[name()='g']//*[contains(@class, 'c3-target') "
                                    "and contains(@class, 'c3-chart-line')]")

    def __iter__(self):
        """This enables you to iterate through like it was a dictionary, just without .iteritems"""
        self.load_chart_reference()
        for legend_id in self._legends:
            yield (legend_id, getattr(self, legend_id))

    @property
    def legends(self):
        """Returns available legends on chart"""
        self.load_chart_reference()
        return self._legends

    def num_legend(self, only_enabled=True):
        """Returns number of available legends on chart
        Args:
            only_enabled: by default True, returns only enabled count when we pass True
        """
        self.load_chart_reference()
        if not only_enabled:
            return len(self._c_lines)
        num_line = 0
        for line in self._c_lines:
            if 'opacity: 1' in line.get_attribute('style'):
                num_line += 1
        return num_line

    @classmethod
    def _get_tooltip(cls, lines, circle_index):
        for line in lines:
            cir = line.find_elements_by_tag_name("circle")[circle_index]
            if 'opacity: 1' in cir.get_attribute('style'):
                sel.move_to_element(cir)
                return sel.element('//*[contains(@class, "c3-tooltip-container")]')
        return None

    @property
    def has_warning(self):
        self.load_chart_reference()
        for msg in flash.get_messages():
            if msg.level is "warning":
                return True
        return False

    def list_data_chart(self, raw=False):
        """Returns list of data from chart"""
        self.load_chart_reference()
        data = []
        lines = []
        if self.has_warning:
            return data
        if self.num_legend(only_enabled=True) == 0:
            raise RuntimeError("There is no legend enabled!")
        for _line in self._c_lines:
            if 'opacity: 1' in _line.get_attribute('style'):
                lines.append(_line)
        line = lines[0]
        # %m/%d/%Y %H:%M:%S %Z
        if self.option.get_interval(force_visible_text=True) == Option.IN_HOURLY:
            _date = self.option.get_date()
            date_format = "{} {}:00 UTC".format(_date, "{}")
        elif self.option.get_interval(force_visible_text=True) == Option.IN_MOST_RECENT_HOUR:
            _date = self.option.get_range().split(" ", 1)[0].split("-")
            date_format = "{}/{}/{} {} UTC".format(_date[1], _date[2], _date[0], "{}")
        elif self.option.get_interval(force_visible_text=True) == Option.IN_DAILY:
            _year = self.option.get_date().split('/')[-1]
            date_format = "{}/{} 00:00:00 UTC".format("{}", _year)
        else:
            raise RuntimeError("Unsupported interval:{}"
                               .format(self.option.get_interval(force_visible_text=True)))
        if raw:
            time_format = "datetime"
        else:
            time_format = "timestamp"
        for cir_index in range(len(line.find_elements_by_tag_name("circle"))):
            tp = self._get_tooltip(lines=lines, circle_index=cir_index)
            # NOTE: If all data in ZERO value(bottom of x axis),
            # tooltip is not working via "move_to_element", returns ''
            if tp and not sel.text_content(tp) == '':
                _date = sel.text_content(tp.find_element_by_tag_name('th'))
                if not raw:
                    # Format: %m/%d/%Y %H:%M:%S %Z
                    _date = self._timestamp(
                        datetime.strptime(date_format.format(_date), "%m/%d/%Y %H:%M:%S %Z"))
                _data = {time_format: _date}
                # ignore duplicate values for timestamp
                if not next((item for item in data if item.get(time_format) == _date), None):
                    for _row in tp.find_elements_by_xpath(
                            "//tr[contains(@class, 'c3-tooltip-name')]"):
                        _key = attributize_string(
                            sel.text_content(_row.find_element_by_class_name('name')))
                        # changing legend name to full name with pre defined map
                        _key = self._get_ui_key(_key)
                        _value = round_double(value_of(
                            sel.text_content(_row.find_element_by_class_name('value'))))
                        _data[_key] = _value
                    data.append(_data)
        return data

    def list_data_table(self, raw=False):
        """Returns list of data from table"""
        self.load_chart_reference()
        data = []
        if self.has_warning:
            return data
        table = Table(table_locator="//table[contains(@class, 'table')]")
        headers = []
        for header in table.headers:
            headers.append(attributize_string(sel.text_sane(header)))
        for row in table.rows():
            _data = {}
            for header in headers:
                if header == "datetime":
                    _datetime = sel.text_sane(row[header])
                    if raw:
                        _data[header] = _datetime
                    else:
                        # sample 10/19/16 15:23:38 UTC
                        _data['timestamp'] = self._timestamp(
                            datetime.strptime(_datetime, "%m/%d/%y %H:%M:%S %Z"))
                else:
                    _value = round_double(value_of(sel.text_sane(row[header])))
                    _data[header] = None if _value == '' else _value
            data.append(_data)
        return data

    @classmethod
    def _timestamp(cls, dt, end_time=False):
        """Returns UTC timestamp with milliseconds
        Args:
            dt: datetime object
            end_time: when you pass end_time True adds 999 milliseconds with final result
        """
        _timestamp = calendar.timegm(dt.utctimetuple()) * 1000
        if end_time:
            return _timestamp + 999
        return _timestamp

    @classmethod
    def _update_mgmt_data(cls, key, raw_data, pre_final_data=[]):
        final_data = []
        for _raw_data in raw_data:
            if not _raw_data.get('empty', True):
                _pre_dict = next((item for item in pre_final_data
                                  if item.get('timestamp') == _raw_data.get('start')),
                                 {'timestamp': _raw_data.get('start')})
                _pre_dict.update({key: round_double(_raw_data.get('avg', None))})
                final_data.append(_pre_dict)
        return final_data

    def list_data_mgmt(self):
        """Returns data from mgmtsystem for the chart option selected"""
        self.load_chart_reference()
        dt = datetime.now()
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.option.get_interval(force_visible_text=True) == Option.IN_DAILY:
            bucket_duration = "1d"
            # sample date: 10/25/2016
            t_dt = datetime.strptime(self.option.get_date(), '%m/%d/%Y')
            dt = dt.replace(year=t_dt.year, month=t_dt.month, day=t_dt.day)
            start_dt = dt - timedelta(days=int(self.option.get_week()))
            stop_dt = dt.replace(hour=23, minute=59, second=59) - timedelta(days=1)
        elif self.option.get_interval(force_visible_text=True) == Option.IN_HOURLY:
            bucket_duration = "1h"
            # sample date: 10/25/2016
            t_dt = datetime.strptime(self.option.get_date(), '%m/%d/%Y')
            start_dt = dt.replace(year=t_dt.year, month=t_dt.month, day=t_dt.day)
            stop_dt = start_dt.replace(hour=23, minute=59, second=59)
        elif self.option.get_interval(force_visible_text=True) == Option.IN_MOST_RECENT_HOUR:
            bucket_duration = "1mn"
            # sample date: 2016-10-26 07:15:48 UTC to 2016-10-26 07:30:48 UTC
            date_range = self.option.get_range().split("to")
            start_dt = datetime.strptime(date_range[0].strip(), "%Y-%m-%d %H:%M:%S %Z")
            stop_dt = datetime.strptime(date_range[1].strip(), "%Y-%m-%d %H:%M:%S %Z")
        start = self._timestamp(dt=start_dt)
        end = self._timestamp(dt=stop_dt, end_time=True)
        return self._list_data_mgmt(start=start, end=end, bucket_duration=bucket_duration)

    def _list_data_mgmt(self, start, end, bucket_duration):
        page = self._utz_object.page
        mgmt = page.provider.mgmt
        page_type = page.taggable_type
        if page_type == "MiddlewareServer":
            feed_id = page.feed
            server_name = page.name
            raw_gauge_server = partial(mgmt.metric.list_gauge_server, feed_id=feed_id,
                                       server_id=server_name, bucket_duration=bucket_duration,
                                       start=start, end=end)
            raw_counter_server = partial(mgmt.metric.list_counter_server, feed_id=feed_id,
                                         server_id=server_name, bucket_duration=bucket_duration,
                                         start=start, end=end)
        elif page_type == "MiddlewareDatasource":
            feed_id = page.server.feed
            server_name = page.server.name
            resource_id = re.search(r'Datasource \[(.*?)\]', page.name).group(1)
            raw_gauge_ds = partial(mgmt.metric.list_gauge_datasource, feed_id=feed_id,
                                   server_id=server_name, resource_id=resource_id,
                                   bucket_duration=bucket_duration, start=start, end=end)
        elif page_type == "MiddlewareMessaging":
            feed_id = page.server.feed
            server_name = page.server.name
            if page.name.startswith("JMS Topic"):
                resource_id = re.search(r'JMS Topic \[(.*?)\]', page.name).group(1)
                is_topic = True
            elif page.name.startswith("JMS Queue"):
                resource_id = re.search(r'JMS Queue \[(.*?)\]', page.name).group(1)
                is_topic = False
            raw_jms = partial(mgmt.metric.list_jms, feed_id=feed_id, server_id=server_name,
                              name=resource_id, bucket_duration=bucket_duration, start=start,
                              end=end)

        # MiddlewareServer
        if self.id == "jvm_heap_usage_bytes" and page_type == "MiddlewareServer":
            raw_used = raw_gauge_server(metric_enum=MetricEnumGauge.SVR_MEM_HEAP_USED)
            raw_max = raw_gauge_server(metric_enum=MetricEnumGauge.SVR_MEM_HEAP_MAX)
            raw_committed = raw_gauge_server(metric_enum=MetricEnumGauge.SVR_MEM_HEAP_COMMITTED)
            # merge all data
            final_data = self._update_mgmt_data(key='used', raw_data=raw_used)
            final_data = self._update_mgmt_data(key='maximum', raw_data=raw_max,
                                                pre_final_data=final_data)
            final_data = self._update_mgmt_data(key='committed', raw_data=raw_committed,
                                                pre_final_data=final_data)
            return final_data
        # MiddlewareServer
        elif self.id == 'jvm_non_heap_usage_bytes' and page_type == "MiddlewareServer":
            raw_used = raw_gauge_server(metric_enum=MetricEnumGauge.SVR_MEM_NON_HEAP_USED)
            raw_committed = raw_gauge_server(metric_enum=MetricEnumGauge.SVR_MEM_NON_HEAP_COMMITTED)
            # merge all data
            final_data = self._update_mgmt_data(key='used', raw_data=raw_used)
            final_data = self._update_mgmt_data(key='committed', raw_data=raw_committed,
                                                pre_final_data=final_data)
            return final_data
        # MiddlewareServer
        elif self.id == 'gc_duration_ms' and page_type == "MiddlewareServer":
            raw_duration = raw_counter_server(
                metric_enum=MetricEnumCounter.SVR_MEM_ACCUMULATED_GC_DURATION, rate=True)
            return self._update_mgmt_data(key='duration', raw_data=raw_duration)
        # MiddlewareServer
        elif self.id == 'web_sessions' and page_type == "MiddlewareServer":
            raw_active = raw_gauge_server(
                metric_enum=MetricEnumGauge.SVR_WEB_AGGREGATED_ACTIVE_WEB_SESSIONS)
            raw_expired = raw_counter_server(
                metric_enum=MetricEnumCounter.SVR_WEB_AGGREGATED_EXPIRED_WEB_SESSIONS)
            raw_rejected = raw_counter_server(
                metric_enum=MetricEnumCounter.SVR_WEB_AGGREGATED_REJECTED_WEB_SESSIONS)
            final_data = self._update_mgmt_data(key='active', raw_data=raw_active)
            final_data = self._update_mgmt_data(key='expired', raw_data=raw_expired,
                                                pre_final_data=final_data)
            final_data = self._update_mgmt_data(key='rejected', raw_data=raw_rejected,
                                                pre_final_data=final_data)
            return final_data
        # MiddlewareServer
        elif self.id == 'transactions' and page_type == "MiddlewareServer":
            raw_committed = raw_counter_server(
                metric_enum=MetricEnumCounter.SVR_TXN_NUMBER_OF_COMMITTED_TRANSACTIONS)
            raw_timedout = raw_counter_server(
                metric_enum=MetricEnumCounter.SVR_TXN_NUMBER_OF_TIMED_OUT_TRANSACTIONS)
            raw_heuristic = raw_counter_server(
                metric_enum=MetricEnumCounter.SVR_TXN_NUMBER_OF_HEURISTICS)
            raw_application_failure = raw_counter_server(
                metric_enum=MetricEnumCounter.SVR_TXN_NUMBER_OF_APPLICATION_ROLLBACKS)
            raw_aborted = raw_counter_server(
                metric_enum=MetricEnumCounter.SVR_TXN_NUMBER_OF_ABORTED_TRANSACTIONS)
            raw_resource_failure = raw_counter_server(
                metric_enum=MetricEnumCounter.SVR_TXN_NUMBER_OF_RESOURCE_ROLLBACKS)
            final_data = self._update_mgmt_data(key='committed', raw_data=raw_committed)
            final_data = self._update_mgmt_data(key='timedout', raw_data=raw_timedout,
                                                pre_final_data=final_data)
            final_data = self._update_mgmt_data(key='heuristic', raw_data=raw_heuristic,
                                                pre_final_data=final_data)
            final_data = self._update_mgmt_data(key='application_failure',
                                                raw_data=raw_application_failure,
                                                pre_final_data=final_data)
            final_data = self._update_mgmt_data(key='aborted', raw_data=raw_aborted,
                                                pre_final_data=final_data)
            final_data = self._update_mgmt_data(key='resource_failure',
                                                raw_data=raw_resource_failure,
                                                pre_final_data=final_data)
            return final_data
        # MiddlewareDatasource
        elif self.id == 'availability_connections' and page_type == "MiddlewareDatasource":
            raw_available = raw_gauge_ds(metric_enum=MetricEnumGauge.DS_POOL_AVAILABLE_COUNT)
            raw_in_use = raw_gauge_ds(metric_enum=MetricEnumGauge.DS_POOL_IN_USE_COUNT)
            raw_time_out = raw_gauge_ds(metric_enum=MetricEnumGauge.DS_POOL_TIMED_OUT)
            final_data = self._update_mgmt_data(key='available', raw_data=raw_available)
            final_data = self._update_mgmt_data(key='in_use', raw_data=raw_in_use,
                                                pre_final_data=final_data)
            final_data = self._update_mgmt_data(key='timeout', raw_data=raw_time_out,
                                                pre_final_data=final_data)
            return final_data
        # MiddlewareDatasource
        elif self.id == 'responsiveness_ms' and page_type == "MiddlewareDatasource":
            raw_get_time_avg = raw_gauge_ds(metric_enum=MetricEnumGauge.DS_POOL_AVERAGE_GET_TIME)
            raw_creation_time_avg = raw_gauge_ds(
                metric_enum=MetricEnumGauge.DS_POOL_AVERAGE_CREATION_TIME)
            raw_wait_time_max = raw_gauge_ds(metric_enum=MetricEnumGauge.DS_POOL_MAX_WAIT_TIME)
            final_data = self._update_mgmt_data(key='get_time_avg', raw_data=raw_get_time_avg)
            final_data = self._update_mgmt_data(key='creation_time_avg',
                                                raw_data=raw_creation_time_avg,
                                                pre_final_data=final_data)
            final_data = self._update_mgmt_data(key='wait_time_max', raw_data=raw_wait_time_max,
                                                pre_final_data=final_data)
            return final_data
        # MiddlewareMessaging
        elif self.id == 'messages' and page_type == "MiddlewareMessaging":
            if is_topic:
                raw_delivering_message_count = raw_jms(
                    metric_enum=MetricEnumGauge.JMS_TOPIC_DELIVERING_COUNT)
                raw_durable_message_count = raw_jms(
                    metric_enum=MetricEnumGauge.JMS_TOPIC_DURABLE_MESSAGE_COUNT)
                raw_messages_count = raw_jms(
                    metric_enum=MetricEnumGauge.JMS_TOPIC_MESSAGE_COUNT)
                raw_messages_added = raw_jms(
                    metric_enum=MetricEnumCounter.JMS_TOPIC_MESSAGES_ADDED)
                raw_non_durable_messages_count = raw_jms(
                    metric_enum=MetricEnumGauge.JMS_TOPIC_NON_DURABLE_MESSAGE_COUNT)
                final_data = self._update_mgmt_data(key='delivering_message_count',
                                                    raw_data=raw_delivering_message_count)
                final_data = self._update_mgmt_data(key='durable_message_count',
                                                    raw_data=raw_durable_message_count,
                                                    pre_final_data=final_data)
                final_data = self._update_mgmt_data(key='message_count',
                                                    raw_data=raw_messages_count,
                                                    pre_final_data=final_data)
                final_data = self._update_mgmt_data(key='messages_added',
                                                    raw_data=raw_messages_added,
                                                    pre_final_data=final_data)
                final_data = self._update_mgmt_data(key='non_durable_messages_count',
                                                    raw_data=raw_non_durable_messages_count,
                                                    pre_final_data=final_data)
                return final_data
            else:
                raw_delivering_message_count = raw_jms(
                    metric_enum=MetricEnumGauge.JMS_QUEUE_DELIVERING_COUNT)
                raw_messages_count = raw_jms(metric_enum=MetricEnumGauge.JMS_QUEUE_MESSAGE_COUNT)
                raw_messages_added = raw_jms(metric_enum=MetricEnumCounter.JMS_QUEUE_MESSAGES_ADDED)
                final_data = self._update_mgmt_data(key='delivering_message_count',
                                                    raw_data=raw_delivering_message_count)
                final_data = self._update_mgmt_data(key='message_count',
                                                    raw_data=raw_messages_count,
                                                    pre_final_data=final_data)
                final_data = self._update_mgmt_data(key='messages_added',
                                                    raw_data=raw_messages_added,
                                                    pre_final_data=final_data)
                return final_data
        # MiddlewareMessaging
        elif self.id == 'subscribers' and page_type == "MiddlewareMessaging":
            raw_durable_subscription_count = raw_jms(
                metric_enum=MetricEnumGauge.JMS_TOPIC_DURABLE_SUBSCRIPTION_COUNT)
            raw_non_durable_subscription_count = raw_jms(
                metric_enum=MetricEnumGauge.JMS_TOPIC_NON_DURABLE_SUBSCRIPTION_COUNT)
            raw_subscription_count = raw_jms(
                metric_enum=MetricEnumGauge.JMS_TOPIC_SUBSCRIPTION_COUNT)
            final_data = self._update_mgmt_data(key='durable_subscription_count',
                                                raw_data=raw_durable_subscription_count)
            final_data = self._update_mgmt_data(key='non_durable_subscription_count',
                                                raw_data=raw_non_durable_subscription_count,
                                                pre_final_data=final_data)
            final_data = self._update_mgmt_data(key='subscription_count',
                                                raw_data=raw_subscription_count,
                                                pre_final_data=final_data)
            return final_data
        # MiddlewareMessaging
        elif self.id == 'consumers' and page_type == "MiddlewareMessaging":
            raw_consumers_count = raw_jms(metric_enum=MetricEnumGauge.JMS_QUEUE_CONSUMER_COUNT)
            final_data = self._update_mgmt_data(key='consumers_count',
                                                raw_data=raw_consumers_count)
            return final_data
        else:
            raise RuntimeError("For this chart list_data_mgmt, not implemented")


class Option(object):
    """Option class used to control options on chart page"""
    DD_BASE = "//dt[normalize-space(.)='{}']/following-sibling::dd"
    RANGE = DD_BASE.format("Range")
    TIME_PROFILE = DD_BASE.format("Time Profile")

    # Interval options
    IN_DAILY = "Daily"
    IN_HOURLY = "Hourly"
    IN_MOST_RECENT_HOUR = "Most Recent Hour"

    # Week options
    WK_1_WEEK = "1 Week"
    WK_2_WEEK = "2 Weeks"
    WK_3_WEEK = "3 Weeks"
    WK_4_WEEK = "4 Weeks"

    # Minute options
    MN_10_MINUTE = "10 Minutes"
    MN_15_MINUTE = "15 Minutes"
    MN_30_MINUTE = "30 Minutes"
    MN_45_MINUTE = "45 Minutes"
    MN_60_MINUTE = "1 Hour"

    def __init__(self, o):
        self._object = o
        self._interval = web_ui.AngularSelect(loc="perf_typ")
        self._date = web_ui.Calendar(name="miq_date_1")
        self._week = web_ui.AngularSelect(loc="perf_days")
        self._minute = web_ui.AngularSelect(loc="perf_minutes")

    def get_date(self):
        """Returns selected date from options"""
        self._object.load_chart_reference()
        if sel.is_displayed(self._date):
            return sel.value(self._date)
        return None

    def _get_value(self, element, force_visible_text):
        self._object.load_chart_reference()
        if not sel.is_displayed(element):
            return None
        if force_visible_text:
            return element.first_selected_option_text
        return element.first_selected_option.value

    def get_interval(self, force_visible_text=False):
        """
        Returns selected interval from options

        Args:
            force_visible_text: default it is False and returns internal value. If you want to get
               visible text pass this value as True
        """

        return self._get_value(element=self._interval, force_visible_text=force_visible_text)

    def get_minute(self, force_visible_text=False):
        """
        Returns selected minute from options

        Args:
            force_visible_text: default it is False and returns internal value. If you want to get
               visible text pass this value as True
        """

        return self._get_value(element=self._minute, force_visible_text=force_visible_text)

    def get_week(self, force_visible_text=False):
        """
        Returns selected week from options

        Args:
            force_visible_text: default it is False and returns internal value. If you want to get
               visible text pass this value as True
        """

        return self._get_value(element=self._week, force_visible_text=force_visible_text)

    def _get_dd(self, element_xpath):
        self._object.load_chart_reference()
        if len(sel.elements(element_xpath)) == 0:
            return None
        return sel.element(element_xpath).text

    def get_range(self):
        """Returns selected range from options"""
        return self._get_dd(element_xpath=self.RANGE)

    def get_time_profile(self):
        """Returns selected time profile from options"""
        return self._get_dd(element_xpath=self.TIME_PROFILE)

    def to_string(self):
        """Returns selected options as string"""
        if self.get_interval() == self.IN_DAILY:
            return "interval:{}, date:{}, week:{}, time_profile:{}".format(self.get_interval(),
                                                                           self.get_date(),
                                                                           self.get_week(True),
                                                                           self.get_time_profile())
        elif self.get_interval() == self.IN_HOURLY:
            return "interval:{}, date:{}, time_profile:{}".format(self.get_interval(),
                                                                  self.get_date(),
                                                                  self.get_time_profile())
        elif self.get_interval() == self.IN_MOST_RECENT_HOUR:
            return "interval:{}, date:{}, minute:{}, time_profile:{}"\
                .format(self.get_interval(), self.get_date(), self.get_minute(),
                        self.get_time_profile())
        else:
            raise RuntimeError("Unknown interval:[{}]".format(self.get_interval()))

    def _set(self, op_interval=None, op_date=None, op_week=None, op_minute=None,
             force_by_text=False):
        self._object.load_chart_reference()
        if op_interval and op_interval != self.get_interval(force_visible_text=force_by_text):
            if force_by_text:
                self._interval.select_by_visible_text(op_interval)
            else:
                self._interval.select_by_value(op_interval)
            sel.wait_for_ajax()
        if op_date and op_date != self.get_date():
            web_ui.fill(self._date, op_date)
            sel.wait_for_ajax()
        if op_week and op_week != self.get_week(force_visible_text=force_by_text):
            if force_by_text:
                self._week.select_by_visible_text(op_week)
            else:
                self._week.select_by_value(op_week)
            sel.wait_for_ajax()
        if op_minute and op_minute != self.get_minute(force_visible_text=force_by_text):
            if force_by_text:
                self._minute.select_by_visible_text(op_minute)
            else:
                self._minute.select_by_value(op_minute)
            sel.wait_for_ajax()
        self._object.load_chart_reference(force_reload=True)

    def set_by_visible_text(self, op_interval=None, op_date=None, op_week=None, op_minute=None):
        """Set options by visible text
        Args:
            op_minute: Minute option
            op_date: Date option, date format should be as 'MM/DD/YYYY', ie: 11/21/2016
            op_interval: Set interval
            op_week: Set week
        """
        self._set(op_interval=op_interval, op_date=op_date, op_week=op_week, op_minute=op_minute,
                  force_by_text=True)

    def set_by_value(self, op_interval=None, op_date=None, op_week=None, op_minute=None):
        """Set options by internal value
        Args:
            op_minute: Minute option
            op_date: Date option, date format should be as 'MM/DD/YYYY', ie: 11/21/2016
            op_interval: Set interval
            op_week: Set week
        """
        self._set(op_interval=op_interval, op_date=op_date, op_week=op_week, op_minute=op_minute,
                  force_by_text=False)


class Legend(object):
    """This class used to control/read legends """

    def __init__(self, name, legend_object):
        self._name = name
        self._l_object = legend_object

    def __repr__(self):
        return "<Legend '{}'>".format(self._name)

    @property
    def name(self):
        """User friendly name of the legend"""
        return self._name

    @property
    def is_active(self):
        """Returns True if the legend is on active state, otherwise False"""
        return 'c3-legend-item-hidden' not in self._l_object.get_attribute('class')

    def set_active(self, active=True):
        """Enable or Disable legend

        Args:
            active: When we set True, Enables the legend. When we set False disables the legend.
              Default True
        """

        if active is not self.is_active:
            self._l_object.click()

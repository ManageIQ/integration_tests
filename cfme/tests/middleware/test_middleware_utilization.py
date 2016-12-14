import pytest
from cfme.middleware.datasource import MiddlewareDatasource
from cfme.middleware.messaging import MiddlewareMessaging
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.server import MiddlewareServer
from cfme.web_ui.utilization import Option
from random_methods import get_random_object
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate([HawkularProvider], scope="function")


@pytest.mark.parametrize("object_type", [MiddlewareServer,
                                         MiddlewareDatasource,
                                         MiddlewareMessaging])
def test_object_utilization(provider, object_type):
    """Tests utilization charts in all pages that has utilization charts

    Steps:
        * Select a utilization object of provided object_type randomly from database
        * Run `validate_utilization` with `utilization_obj` input
    """
    utilization_obj = get_random_object(provider=provider, objecttype=object_type, load_from="db")
    validate_utilization(utilization_obj=utilization_obj.utilization)


def validate_utilization(utilization_obj):
    """Gets data from chart, table, mgmt and compare between"""
    for chart_id in utilization_obj.charts:
        chart = getattr(utilization_obj, chart_id)
        # validate legends
        if not chart.has_warning:
            validate_legends(chart=chart)
        # validate data for Daily with different week durations
        for op_week in [Option.WK_1_WEEK, Option.WK_2_WEEK, Option.WK_3_WEEK, Option.WK_4_WEEK]:
            chart.option.set_by_visible_text(op_interval=Option.IN_DAILY, op_week=op_week)
            if chart.has_warning:
                break
            else:
                validate_data(chart=chart)
        # validate data for Hourly
        chart.option.set_by_visible_text(op_interval=Option.IN_HOURLY)
        if not chart.has_warning:
            validate_data(chart=chart)
        # validate data for Most recent hour with different minute durations
        for op_minute in [Option.MN_10_MINUTE, Option.MN_15_MINUTE, Option.MN_30_MINUTE,
                          Option.MN_45_MINUTE, Option.MN_60_MINUTE]:
            chart.option.set_by_visible_text(op_interval=Option.IN_MOST_RECENT_HOUR,
                                             op_minute=op_minute)
            if chart.has_warning:
                break
            else:
                validate_data(chart=chart)


def validate_legends(chart):
    for legend_id in chart.legends:
        legend = getattr(chart, legend_id)
        legend.set_active(active=False)
        assert not legend.is_active, "Unable to disable legend[{}] on chart[{}]"\
            .format(legend.name, chart.name)
        legend.set_active(active=True)
        assert legend.is_active, "Unable to enable legend[{}] on chart[{}]"\
            .format(legend.name, chart.name)


def validate_data(chart):
    """Validate chart data"""
    list_chart_data = chart.list_data_chart()
    list_table_data = chart.list_data_table()
    list_mgmt_data = chart.list_data_mgmt()
    # find very recent reading from hourly data to ignore
    ignore_ts = 0
    if chart.option.get_interval(force_visible_text=True) is Option.IN_HOURLY:
        for item in list_mgmt_data:
            if ignore_ts < item.get('timestamp'):
                ignore_ts = item.get('timestamp')
    for mgmt_data in list_mgmt_data:
        if ignore_ts == mgmt_data.get('timestamp'):
            continue
        ts = mgmt_data.get('timestamp')
        chart_data = next((item for item in list_chart_data if item.get('timestamp') == ts),
                          {'timestamp': ts})
        table_data = next((item for item in list_table_data if item.get('timestamp') == ts),
                          {'timestamp': ts})
        for key in mgmt_data:
            # verify UI, Table and Mgmt
            d_value = None
            # if mgmt has 0.0, change default value as 0
            if mgmt_data.get(key, None) == 0:
                d_value = 0
            assert mgmt_data.get(key, d_value) == chart_data.get(key, d_value) == table_data\
                .get(key, d_value), "data mismatch for the timestamp[{}], data[chart:{}, " \
                                    "table:{}, mgmt:{}], chart[name:{}, options:({})]"\
                .format(ts, chart_data, table_data, mgmt_data, chart.name, chart.option.to_string())

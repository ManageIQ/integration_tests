# -*- coding: utf-8 -*-
import pytest

timelines_reports = ('hosts', 'vm_operation', 'policy_events', 'policy_events2')


@pytest.mark.manual
@pytest.mark.parametrize('report', timelines_reports)
def test_default_reports_with_timelines(report):
    pass


@pytest.mark.manual
@pytest.mark.parametrize('report', timelines_reports)
def test_custom_reports_with_timelines(report):
    pass

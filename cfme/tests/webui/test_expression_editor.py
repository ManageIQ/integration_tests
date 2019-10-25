import fauxfactory
import pytest

from cfme import test_requirements
from cfme.services.myservice import MyService
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator

pytestmark = [test_requirements.filtering]
filter_value = 'beautifulpotato'
filter_option = "Cloud Volume : Name"


@pytest.mark.meta(automates=[BZ(1720216)])
@pytest.mark.parametrize("operator", ["not", "and", "or"])
# remove NOT is 5.11 feature, see BZ(1720216)
@pytest.mark.uncollectif(lambda operator, appliance:
                         operator == "not" and appliance.version < "5.11")
def test_exp_editor_delete_operator(appliance, operator):
    """
    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/30h
    """
    view = navigate_to(appliance.collections.volumes, "All")  # any collection with advanced search
    name = fauxfactory.gen_alphanumeric()
    view.entities.search.save_filter(f'''
        fill_field({filter_option}, =, {filter_value});
        select_expression_text;
        click_{operator};
        {f"fill_field({filter_option}, =, {filter_value});" if operator != "not" else ""}
        select_expression_text;
        click_remove;''', name)
    editor = view.search.advanced_search_form.search_exp_editor
    assert editor.expression_text == f'{filter_option} = "{filter_value}"'
    view.entities.search.delete_filter()
    view.entities.search.close_advanced_search()


@pytest.mark.meta(automates=[1741243, 1761525], blockers=[BZ(1741243)])
def test_apply_after_save():
    """
    Bugzilla:
        1741243
        1761525

    There are a few ways to reproduce this BZ but this is the most reliable

    Polarion:
        assignee: anikifor
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/10h
    """
    filter_name = fauxfactory.gen_alphanumeric()
    view = navigate_to(MyService, 'All')
    view.entities.search.save_filter("fill_field(Service : Custom 1, =, value)", filter_name)
    with LogValidator("/var/www/miq/vmdb/log/production.log",
                      failure_patterns=[".*FATAL.*"]).waiting(timeout=60):
        assert view.entities.search.apply_filter()
        assert view.wait_displayed("10s")  # in case of error it's not displayed properly

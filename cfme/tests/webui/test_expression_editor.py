import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

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

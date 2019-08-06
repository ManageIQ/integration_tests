import fauxfactory
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ


class TestDeleteExpressions(object):
    filter_value = 'beautifulpotato'
    filt = "Cloud Volume : Name"
    collection = "volumes"  # any collection with advanced search
    destination = "All"

    def _delete_operator(self, appliance, operator):
        view = navigate_to(
            getattr(
                appliance.collections,
                self.collection),
            self.destination)
        name = fauxfactory.gen_alphanumeric()
        view.entities.search.save_filter(
            f'fill_field({self.filt}, =, {self.filter_value});'
            f'select_expression_text;'
            f'click_{operator};'
            f'{f"fill_field({self.filt}, =, {self.filter_value});" if operator != "not" else ""}'
            f'select_expression_text;'
            f'click_remove;',
            name)
        editor = view.search.advanced_search_form.search_exp_editor
        assert editor.expression_text == f'{self.filt} = "{self.filter_value}"'
        view.entities.search.delete_filter()
        view.entities.search.close_advanced_search()

    @pytest.mark.meta(automates=[BZ(1720216)])
    @pytest.mark.ignore_stream("5.10")
    def test_delete_not(self, appliance):
        """
        Polarion:
            assignee: anikifor
            casecomponent: WebUI
            caseimportance: medium
            initialEstimate: 1/30h
        """
        self._delete_operator(appliance, "not")

    def test_delete_and(self, appliance):
        """
        Polarion:
            assignee: anikifor
            casecomponent: WebUI
            caseimportance: medium
            initialEstimate: 1/30h
        """
        self._delete_operator(appliance, "and")

    def test_delete_or(self, appliance):
        """
        Polarion:
            assignee: anikifor
            casecomponent: WebUI
            caseimportance: medium
            initialEstimate: 1/30h
        """
        self._delete_operator(appliance, "or")

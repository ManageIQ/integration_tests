from time import sleep

import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

NOT = "NOT"
AND = "and"
OR = "or"


class TestDeleteExpressions(object):
    filter_value = 'beautifulpotato'
    view = None
    editor = None
    filt = "Cloud Volume : Name"
    collection = "volumes"  # any collection with advanced search
    destination = "All"

    def _exp_click(self, expression):
        funcs = {NOT: self.editor.click_not,
                 OR: self.editor.click_or,
                 AND: self.editor.click_and}
        if expression not in funcs:
            raise ValueError('"{}" is not a valid expression'.format(expression))
        funcs[expression]()

    def _fill_expr(self):
        self.editor.fill_field(self.filt, '=', self.filter_value)
        sleep(1)

    def _delete_operator(self, appliance, operator):
        self.view = navigate_to(
            getattr(
                appliance.collections,
                self.collection),
            self.destination)  # _navigation(param, appliance)
        self.view.search.open_advanced_search()
        self.editor = self.view.search.advanced_search_form.search_exp_editor
        # create first expression
        self._fill_expr()
        self.editor.select_first_expression()
        self._exp_click(operator)
        if operator != NOT:
            # for boolean operator we need another one
            self._fill_expr()
        assert operator in self.editor.expression_text
        self.editor.select_first_expression()
        # delete first expression which causes deletion of the operator
        self.editor.click_remove()
        assert self.editor.expression_text == '{} = "{}"'.format(self.filt, self.filter_value)
        # cleanup
        self.view.search.reset_filter()
        self.view.search.close_advanced_search()

    @pytest.mark.meta(automates=[BZ(1720216)])
    @pytest.mark.uncollectif(lambda appliance: appliance.version < "5.11")
    def test_delete_not(self, appliance):
        """
        Polarion:
            assignee: psimovec
            casecomponent: WebUI
            caseimportance: medium
            initialEstimate: 1/30h
        """
        self._delete_operator(appliance, NOT)

    def test_delete_and(self, appliance):
        """
        Polarion:
            assignee: psimovec
            casecomponent: WebUI
            caseimportance: medium
            initialEstimate: 1/30h
        """
        self._delete_operator(appliance, AND)

    def test_delete_or(self, appliance):
        """
        Polarion:
            assignee: psimovec
            casecomponent: WebUI
            caseimportance: medium
            initialEstimate: 1/30h
        """
        self._delete_operator(appliance, OR)

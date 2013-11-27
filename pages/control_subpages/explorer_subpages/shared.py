# -*- encoding: utf-8 -*-
""" File with shared classes of UI artifacts appearing similarly in more locations.

@author: Milan Falešník <mfalesni@redhat.com>
"""

from pages.regions.expression_editor_mixin import ExpressionEditorMixin
from pages.regions.refresh_mixin import RefreshMixin
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from pages.regions.taskbar.taskbar import TaskbarMixin


class ConditionEditor(ExpressionEditorMixin):
    """ General editing class, used for inheriting

    Enhances ExpressionEditorMixin with switching between scope or expression contexts.

    """
    _edit_this_expression_locator = (By.CSS_SELECTOR,
                                     "#form_expression_div img[alt='Edit this Expression']")
    _edit_this_scope_locator = (By.CSS_SELECTOR, "#form_scope_div img[alt='Edit this Scope']")

    _description_input_locator = (By.CSS_SELECTOR, "input#description")
    _notes_textarea_locator = (By.CSS_SELECTOR, "textarea#notes")

    @property
    def add_button(self):
        return self.selenium.find_element(*self._add_button_locator)

    @property
    def cancel_button(self):
        return self.selenium.find_element(*self._cancel_button_locator)

    @property
    def description_input(self):
        return self.selenium.find_element(*self._description_input_locator)

    @property
    def notes_textarea(self):
        return self.selenium.find_element(*self._notes_textarea_locator)

    @property
    def edit_expression_button(self):
        return self.selenium.find_element(*self._edit_this_expression_locator)

    @property
    def edit_scope_button(self):
        return self.selenium.find_element(*self._edit_this_scope_locator)

    @property
    def is_editing_expression(self):
        return not self.is_element_visible(*self._edit_this_expression_locator)

    @property
    def is_editing_scope(self):
        return not self.is_element_visible(*self._edit_this_scope_locator)

    def edit_expression(self):
        """ Switches the editing of the Expression on.

        """
        if not self.is_editing_expression:
            self.edit_expression_button.click()
            self._wait_for_results_refresh()

    def edit_scope(self):
        """ Switches the editing of the Scope on.

        """
        if not self.is_editing_scope:
            self.edit_scope_button.click()
            self._wait_for_results_refresh()

    @property
    def notes(self):
        """ Returns contents of the notes textarea

        """
        return self.notes_textarea.text.strip()

    @notes.setter
    def notes(self, value):
        """ Sets the contents of the notes textarea

        """
        self.notes_textarea.clear()
        self.notes_textarea.send_keys(value)

    @property
    def description(self):
        """ Returns description

        """
        return self.description_input.get_attribute("value").strip()

    @description.setter
    def description(self, value):
        """ Sets description

        """
        self.description_input.clear()
        self.description_input.send_keys(value)

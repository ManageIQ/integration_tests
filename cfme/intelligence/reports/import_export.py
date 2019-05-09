# -*- coding: utf-8 -*-
from widgetastic.widget import ClickableMixin
from widgetastic.widget import FileInput
from widgetastic.widget import Select
from widgetastic.widget import Text
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from . import CloudIntelReportsView


class InputButton(Input, ClickableMixin):
    pass


class ImportExportCommonForm(CloudIntelReportsView):

    title = Text("#explorer_title_text")
    subtitle = Text(locator=".//div[@id='main_div']/h2")
    upload_file = FileInput(id="upload_file")
    items_for_export = Select(id="choices_chosen")

    upload_button = InputButton("commit")
    export_button = Button(value="Export")

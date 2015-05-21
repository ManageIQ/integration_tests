# -*- coding: utf-8 -*-
import re

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import fill, Form, Select, Table, toolbar, form_buttons, flash
from xml.sax.saxutils import quoteattr

tag_form = Form(
    fields=[
        ('category', Select('//select[@id="tag_cat"]')),
        ('tag', Select('//select[@id="tag_add"]'))
    ])

tag_table = Table("//div[@id='assignments_div']//table")


def add_tag(tag, single_value=False, navigate=True):
    if navigate:
        toolbar.select('Policy', 'Edit Tags')
    if isinstance(tag, (list, tuple)):
        fill_d = {
            "category": tag[0] if not single_value else "{} *".format(tag[0]),
            "tag": tag[1]
        }
    else:
        fill_d = {"tag": tag.display_name}
        if tag.category.single_value:
            fill_d["category"] = "{} *".format(tag.category.display_name)
        else:
            fill_d["category"] = tag.category.display_name
    fill(tag_form, fill_d)
    form_buttons.save()
    flash.assert_success_message('Tag edits were successfully saved')


def remove_tag(tag):
    toolbar.select('Policy', 'Edit Tags')
    if isinstance(tag, (tuple, list)):
        category, tag_name = tag
    else:
        category = tag.category.display_name
        tag_name = tag.display_name
    row = tag_table.find_row_by_cells({'category': category, 'assigned_value': tag_name},
                                      partial_check=True)
    sel.click(row[0])
    form_buttons.save()
    flash.assert_success_message('Tag edits were successfully saved')


def get_tags(tag="My Company Tags"):
    tags = []
    for row in sel.elements(
            "//*[(self::th or self::td) and normalize-space(.)={}]/../.."
            "//td[img[contains(@src, 'smarttag')]]".format(
                quoteattr(tag))):
        tags.append(sel.text(row).strip())
    return tags


screen_splitter = (
    "//div[contains(@class, 'dhtmlxLayoutObject')]"
    "//td[contains(@class, 'dhtmlxLayoutPolySplitterVer')]")
left_half = (
    "//table[contains(@class, 'dhtmlxLayoutPolyContainer_dhx_blue')]/tbody/tr"
    "/td[contains(@class, 'dhtmlxLayoutSinglePoly') and "
    "following-sibling::td[contains(@class, 'dhtmlxLayoutPolySplitterVer')]]")


def pull_splitter(x):
    """Pulls the vertical separator between accordion and detail view.

    Args:
        x: Negative values move left, positive right.
    """
    sel.drag_and_drop_by_offset(screen_splitter, x)


def left_half_size():
    if not sel.is_displayed(screen_splitter) or not sel.is_displayed(left_half):
        return None
    style = sel.get_attribute(left_half, "style")
    match = re.search(r"width:\s*(\d+)px", style)
    if match is None:
        return None
    return int(match.groups()[0])

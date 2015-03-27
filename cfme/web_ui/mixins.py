from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import fill, Form, Select, Table, toolbar, form_buttons, flash

tag_form = Form(
    fields=[
        ('category', Select('//select[@id="tag_cat"]')),
        ('tag', Select('//select[@id="tag_add"]'))
    ])

tag_table = Table("//div[@id='assignments_div']//table")


def add_tag(tag, single_value=False):
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

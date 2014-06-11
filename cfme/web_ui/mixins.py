from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import fill, Form, Select, Table, toolbar, form_buttons, flash

tag_form = Form(
    fields=[
        ('category', Select('//select[@id="tag_cat"]')),
        ('tag', Select('//select[@id="tag_add"]'))
    ])

tag_table = Table("//div[@id='assignments_div']//table[@class='style3']")


def add_tag(tag):
    toolbar.select('Policy', 'Edit Tags')
    if tag.category.single_value:
        display_name = "{} *".format(tag.category.display_name)
    else:
        display_name = tag.category.display_name
    fill(tag_form, {'category': display_name,
                    'tag': tag.display_name})
    form_buttons.save()
    flash.assert_success_message('Tag edits were successfully saved')


def remove_tag(tag):
    toolbar.select('Policy', 'Edit Tags')
    display_name = tag.category.display_name
    row = tag_table.find_row_by_cells({'category': display_name,
                                       'assigned_value': tag.display_name},
                                      partial_check=True)
    sel.click(row[0])
    form_buttons.save()
    flash.assert_success_message('Tag edits were successfully saved')

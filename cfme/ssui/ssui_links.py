import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.flash as flash
from cfme import web_ui
from cfme.web_ui import Input, form_buttons


edit_service_btn = "//div[contains(@class, 'ss-details-header__actions__inner')]"
"//button[contains(@class, 'btn btn-primary']"

edit_service_form = web_ui.Form(
    fields=[('name_text', Input("name")),
            ('description_text', "//textarea[@id='description']"),
            ('save_button', form_buttons.save)])


def go_to(page_name):
    sel.click('//ul[contains(@class, "list-group")]/li'
        '//span[normalize-space(.)="{}"]'.format(page_name))
    sel.wait_for_ajax()
    # time.sleep(5)
    flash.assert_no_errors()


def find_row(cells):
    sel.click('//div[contains(@class,"data-list-pf")]//div[contains(@class,"row")]'
    '//span[normalize-space(.)="{}"]'.format(cells))
    sel.wait_for_ajax()


def find_service_card(cells):
    sel.click('//div[contains(@class,"ss-card-view")]//div[contains(@class,"ss-card")]'
    '/h3[normalize-space(.)="{}"]'.format(cells))
    sel.wait_for_ajax()


def edit_service(service_name):
    # find_row(service_name)
    sel.click(edit_service_btn)
    sel.wait_for_ajax()
    web_ui.fill(edit_service_form, {'description_text': "edited"},
               action=edit_service_form.save_button)

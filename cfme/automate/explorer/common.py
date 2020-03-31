from widgetastic.utils import Fillable
from widgetastic.widget import Checkbox
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button

from cfme.utils.appliance.implementations.ui import navigate_to
from widgetastic_manageiq import Input


class CopyViewBase(View):
    title = Text('#explorer_title_text')
    to_domain_select = BootstrapSelect('domain')
    to_domain_text = Text('.//div[./label[normalize-space(.)="To Domain"]]/div/p[not(.//button)]')
    new_name = Input(name='new_name')
    override_source = Checkbox(name='override_source')
    override_existing = Checkbox(name='override_existing')
    namespace = Input(name='namespace')

    copy_button = Button('Copy')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')


class Copiable:
    # TODO: Namespace!
    def copy_to(self, domain, new_name=None, replace=None, cancel=False):
        copy_page = navigate_to(self, 'Copy')
        fill_values = {'override_existing': replace, 'new_name': new_name}
        if domain is not None:
            d = Fillable.coerce(domain)
            if copy_page.to_domain_text.is_displayed:
                if copy_page.to_domain_text.text != d:
                    raise ValueError('Wanted to select {} but the only domain possible is {}'
                                     .format(copy_page.to_domain_text.text, d))
            else:
                fill_values['to_domain_select'] = d

        copy_page.fill(fill_values)
        if not cancel:
            copy_page.copy_button.click()
            # Attention! Now we should be on a different page but the flash message is the same!
            copy_page.flash.assert_no_error()
        else:
            copy_page.cancel_button.click()
            # Attention! Now we should be on a different page but the flash message is the same!
            copy_page.flash.assert_no_error()

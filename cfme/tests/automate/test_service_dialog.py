import pytest
import cfme.web_ui.flash as flash
import utils.randomness as rand
from cfme.automate.service_dialogs import ServiceDialog

pytestmark = [pytest.mark.usefixtures("logged_in")]


def test_create_service_dialog():
    dialog = ServiceDialog(label=rand.generate_random_string(),
                  description="my dialog", submit=True, cancel=True,
                  tab_label="tab_" + rand.generate_random_string(), tab_desc="my tab desc",
                  box_label="box_" + rand.generate_random_string(), box_desc="my box desc",
                  ele_label="ele_" + rand.generate_random_string(),
                  ele_name=rand.generate_random_string(),
                  ele_desc="my ele desc", choose_type="Text Box", default_text_box="default value")
    dialog.create()
    flash.assert_no_errors()

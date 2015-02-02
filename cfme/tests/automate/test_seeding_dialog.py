import pytest
import utils.randomness as rand
from cfme.automate.service_dialogs import ServiceDialog
from cfme.automate.seeding_dialogs import SeedingDialog

pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.fixture(scope="function")
def create_service_dialog():
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc",
                           ele_label="ele_" + rand.generate_random_string(),
                           ele_name=rand.generate_random_string(),
                           ele_desc="my ele desc", choose_type="Text Box",
                           default_text_box="default value")
    dialog.create()
    return dialog.label


def test_seeding_dialog(create_service_dialog):
    sdialog = SeedingDialog(create_service_dialog)
    sdialog.export_dialog()

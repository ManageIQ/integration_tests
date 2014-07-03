import pytest
import utils.randomness as rand
from utils.update import update
from utils import error, version
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


def test_update_service_dialog():
    dialog = ServiceDialog(label=rand.generate_random_string(),
                  description="my dialog", submit=True, cancel=True)
    dialog.create()
    with update(dialog):
        dialog.description = "my edited description"


def test_delete_service_dialog():
    dialog = ServiceDialog(label=rand.generate_random_string(),
                  description="my dialog", submit=True, cancel=True)
    dialog.create()
    dialog.delete()


def test_service_dialog_duplicate_name():
    dialog = ServiceDialog(label=rand.generate_random_string(),
                  description="my dialog", submit=True, cancel=True)
    dialog.create()
    error_msg = version.pick({
        version.LOWEST: "Dialog Label has already been taken",
        '5.3': "Label has already been taken"
    })
    with error.expected(error_msg):
        dialog.create()

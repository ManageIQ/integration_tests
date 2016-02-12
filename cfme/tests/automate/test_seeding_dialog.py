import pytest
import shutil
import utils.randomness as rand
from utils.appliance import IPAppliance
from cfme.automate.service_dialogs import ServiceDialog
from cfme.automate.seeding_dialog import SeedingDialog

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
    return dialog


def copyfile(src, dest):
    try:
        shutil.copy2(src, dest)
    except shutil.Error as e:
        print('Error: %s' % e)


def reboot_appliance(ssh_client):
    copy_kwargs = ssh_client._connect_kwargs
    hostname = copy_kwargs['hostname']
    ip_a = IPAppliance(hostname)
    ip_a.reboot()


# The name of downloaded file on exporting dialog consists of current timestamp
# after downlaoding the file , it needs to be copied to the appliance at
# /var/www/miq/vmdb/product/dialogs/service_dialogs/red_hat/ .
def test_seeding_dialog(create_service_dialog, ssh_client, tmpdir):
    sdialog = SeedingDialog(create_service_dialog.label)
    ts = sdialog.export_dialog()
    # filename contains timestamp
    filename = "dialog_export_" + ts + ".yml"
    # delete the dialog
    create_service_dialog.delete()
    # copy the downloaded dialog to a temp dir
    tmpfile = tmpdir.mkdir("sub").join(filename)
    source = "/home/shveta/Downloads/" + filename
    dest = tmpdir + "/sub" + "/" + filename
    copyfile(str(source), str(dest))
    # copy dialog to appliance
    ssh_client.put_file(str(tmpfile), '/var/www/miq/vmdb/product/dialogs/service_dialogs/red_hat/')
    exit_status, output = ssh_client.run_command("ls /tmp/%s" % tmpfile.basename)
    assert tmpfile.basename in output
    # reboot appliance
    # reboot_appliance(ssh_client)
    # check if the dialog is seeded in appliance after reboot

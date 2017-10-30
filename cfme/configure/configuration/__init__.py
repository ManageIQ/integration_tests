# -*- coding: utf-8 -*-
from cfme.base.ui import Region
from cfme.web_ui import Form, InfoBlock, Input, Region as UIRegion, fill, form_buttons
from cfme.web_ui.form_buttons import change_stored_password
from cfme.utils import conf
from cfme.utils.appliance import current_appliance
from cfme.utils.appliance.implementations.ui import navigate_to

replication_worker = Form(
    fields=[
        ('database', Input("replication_worker_dbname")),
        ('port', Input("replication_worker_port")),
        ('username', Input("replication_worker_username")),
        ('password', Input("replication_worker_password")),
        ('password_verify', Input("replication_worker_verify")),
        ('host', Input("replication_worker_host")),
    ]
)

replication_process = UIRegion(locators={
    "status": InfoBlock("Replication Process", "Status"),
    "current_backlog": InfoBlock("Replication Process", "Current Backlog"),
})


def set_replication_worker_host(host, port='5432'):
    """ Set replication worker host on Configure / Configuration pages.

    Args:
        host: Address of the hostname to replicate to.
    """
    navigate_to(current_appliance.server, 'Workers')
    change_stored_password()
    fill(
        replication_worker,
        dict(host=host,
             port=port,
             username=conf.credentials['database']['username'],
             password=conf.credentials['database']['password'],
             password_verify=conf.credentials['database']['password']),
        action=form_buttons.save
    )


def get_replication_status(navigate=True):
    """ Gets replication status from Configure / Configuration pages.

    Returns: bool of whether replication is Active or Inactive.
    """
    if navigate:

        navigate_to(Region, 'Replication')
    return replication_process.status.text == "Active"


def get_replication_backlog(navigate=True):
    """ Gets replication backlog from Configure / Configuration pages.

    Returns: int representing the remaining items in the replication backlog.
    """
    if navigate:
        navigate_to(Region, 'Replication')
    return int(replication_process.current_backlog.text)

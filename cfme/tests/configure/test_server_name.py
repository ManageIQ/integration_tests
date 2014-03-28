# -*- coding: utf-8 -*-

from cfme.configure.configuration import BasicInformation
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import flash, InfoBlock


def test_server_name():
    '''Tests that changing the server name updates the about page'''
    form_infoblocks = InfoBlock('form')
    flash_msg = 'Configuration settings saved for CFME Server "{}'

    sel.force_navigate('cfg_settings_currentserver_server')
    old_server_name = sel.value(BasicInformation.basic_information.appliance_name)
    new_server_name = old_server_name + "-CFME"
    settings_pg = BasicInformation(appliance_name=new_server_name)
    settings_pg.update()
    flash.assert_message_contain(flash_msg.format(new_server_name))

    sel.force_navigate('about')
    assert new_server_name == form_infoblocks.text('Session Information', 'Server Name'),\
        "Server name in About section does not match the new name"

    settings_pg = BasicInformation(appliance_name=old_server_name)
    settings_pg.update()
    flash.assert_message_contain(flash_msg.format(old_server_name))

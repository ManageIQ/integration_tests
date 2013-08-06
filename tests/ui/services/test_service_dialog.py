'''
Created on July 25th, 2013

@author: Shveta
'''

import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
class TestServiceDialog:
    '''Service Dialog test cases'''
    def test_create_service_dialog(
            self,
            automate_customization_pg,
            random_string):
        '''Create service dialog'''
        new_dialog_pg = automate_customization_pg\
                .click_on_service_dialog_accordion().add_new_service_dialog()
        service_dialog_name = "auto_dialog_" + random_string
        new_dialog_pg.create_service_dialog(service_dialog_name)
        Assert.true(new_dialog_pg.flash.message.startswith(
                'Dialog "%s" was added' % service_dialog_name))

'''
Created on July 25th, 2013

@author: Shveta
'''

import pytest
from unittestzero import Assert
import time

@pytest.mark.nondestructive
class TestServiceDialog:
    '''Service Dialog test cases'''
    
    def _create_dialog(self, page, random):
        dialog_name = "auto_dialog_" + random
        descr = "descr-" + random
        new_dialog_pg = page\
                .click_on_service_dialog_accordion().add_new_service_dialog()
        new_dialog_pg.create_service_dialog(dialog_name, descr)
        Assert.true(new_dialog_pg.flash.message.startswith(
                'Dialog "%s" was added' % dialog_name))
        return page, dialog_name
    
    def test_create_and_edit_service_dialog(
            self,
            automate_customization_pg,
            random_string):
        '''Create service dialog , select dialog and edit'''
        dialog_page, name = self._create_dialog(automate_customization_pg, random_string)
        edit_pg = dialog_page.click_on_service_dialog_accordion().\
             click_on_service_dialog(name)
        edited_dialog = name+"_edit"
        show_sd_pg = edit_pg.edit_service_dialog(edited_dialog)
        Assert.true(show_sd_pg.flash.message.startswith(
                'Dialog "%s" was saved' % edited_dialog))
        
        
    def test_create_and_delete_service_dialog(
            self,
            automate_customization_pg,
            random_string):
         '''Create service dialog , select dialog and delete'''
         dialog_page, name = self._create_dialog(automate_customization_pg, random_string)
         dialog_del_pg = dialog_page.click_on_service_dialog_accordion().\
             click_on_service_dialog(name)
         del_pg = dialog_del_pg.delete_service_dialog()
         Assert.equal(del_pg.flash.message,
            'Dialog "%s": Delete successful' % name)
        
         
    def test_create_blank_label(
            self,
            automate_customization_pg,
            random_string):
        '''Create service dialog , select dialog and edit'''
        new_dialog_pg = automate_customization_pg\
                .click_on_service_dialog_accordion().add_new_service_dialog()
        new_dialog_pg.add_label_to_dialog("","")
        new_dialog_pg.save_dialog()
        time.sleep(5)
        Assert.equal(new_dialog_pg.flash.message,
            'Dialog Label is required')
       
    
    def test_create_blank_tab(
            self,
            automate_customization_pg,
            random_string):
        '''Create service dialog , select dialog and edit'''
        new_dialog_pg = automate_customization_pg\
                .click_on_service_dialog_accordion().add_new_service_dialog()
        new_dialog_pg.add_label_to_dialog("label_name","desc")
        new_dialog_pg.add_tab_to_dialog(" ","")
        new_dialog_pg.save_dialog()
        time.sleep(5)
        Assert.equal(new_dialog_pg.flash.message,
            'Tab Label is required')
        
    def test_create_blank_box(
            self,
            automate_customization_pg,
            random_string):
        '''Create service dialog , select dialog and edit'''
        new_dialog_pg = automate_customization_pg\
                .click_on_service_dialog_accordion().add_new_service_dialog()
        new_dialog_pg.add_label_to_dialog("label_name","desc")
        new_dialog_pg.add_tab_to_dialog("tab","tab_desc")
        new_dialog_pg.add_box_to_dialog(" ","")
        new_dialog_pg.save_dialog()
        time.sleep(5)
        Assert.equal(new_dialog_pg.flash.message,
            'Box Label is required')
        
    def test_create_duplicate_dialog(
            self,
            automate_customization_pg,
            random_string):
        '''Create service dialog , select dialog and edit'''
        new_dialog_pg = automate_customization_pg\
                .click_on_service_dialog_accordion().add_new_service_dialog()
        dialog_name = "dialog_label_"+random_string
        new_dialog_pg.add_label_to_dialog(dialog_name,"desc")
        new_dialog_pg.save_dialog()
        Assert.equal(new_dialog_pg.flash.message,
            'Dialog "%s" was added' % dialog_name)
        time.sleep(5)
        dup_dialog_pg = new_dialog_pg.click_on_service_dialog("All Dialogs")
        time.sleep(5)
        dup_dialog_pg.add_new_service_dialog()
        dup_dialog_pg.add_label_to_dialog(dialog_name,"desc")
        dup_dialog_pg.save_dialog()
        Assert.equal(dup_dialog_pg.flash.message,
            'Label has already been taken')
        dup_dialog_pg.add_tab_to_dialog("tab","desc")
        dup_dialog_pg.save_dialog()
        Assert.equal(dup_dialog_pg.flash.message,
            'Label has already been taken')
        dup_dialog_pg.add_box_to_dialog("box","desc")
        dup_dialog_pg.save_dialog()
        Assert.equal(dup_dialog_pg.flash.message,
            'Label has already been taken')
       

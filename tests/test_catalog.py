'''
Created on July 25, 2013

@author: Shveta
'''
import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
class TestCatalogs:
    '''Catalog test cases'''
    _catalog_name = "auto_cat"

    def test_create_catalog(self, svc_catalogs_pg):
        '''create catalog'''
        new_cat_pg = svc_catalogs_pg.click_on_catalogs_accordion()\
                .add_new_catalog()
        show_cat_pg = new_cat_pg.fill_basic_info_tab(self._catalog_name)
        Assert.true(show_cat_pg.flash.message.startswith(
                'ServiceTemplateCatalog "%s" was saved' % self._catalog_name))
        return show_cat_pg

    def test_edit_catalog(self, svc_catalogs_pg):
        '''Edit catalog'''
        edit_pg = svc_catalogs_pg.click_on_catalogs_accordion()\
                .click_on_catalog(self._catalog_name)
        edited_cat = self._catalog_name+"_edit"
        show_cat_pg = edit_pg.edit_catalog(edited_cat)
        Assert.true(show_cat_pg.flash.message.startswith(
                'ServiceTemplateCatalog "%s" was saved' % edited_cat))
        return show_cat_pg

    def test_delete_catalog(self, svc_catalogs_pg):
        '''Delete catalog'''
        del_cat = self._catalog_name+"_edit"
        delete_pg = svc_catalogs_pg.click_on_catalogs_accordion()\
                .click_on_catalog(del_cat)
        show_cat_pg = delete_pg.delete_catalog()
        Assert.true(show_cat_pg.flash.message.startswith(
            'Catalog "%s": Delete successful' % del_cat))
        return show_cat_pg

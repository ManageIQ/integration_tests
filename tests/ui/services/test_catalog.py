'''
Created on July 25, 2013

@author: Shveta
'''
import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
class TestCatalogs:
    '''Catalog test cases'''
    _catalog_name = "auto_cat_"

    def _create_cat(self, page, random):
        name = self._catalog_name + "-" + random
        descr = "descr-" + random
        add_pg = page.click_on_catalogs_accordion().add_new_catalog()
        show_cat_pg = add_pg.fill_basic_info_tab(name, descr)
        Assert.true(show_cat_pg.flash.message.startswith(
            'ServiceTemplateCatalog "%s" was saved' % name))
        return page, name, descr

    def _delete_cat(self, page, name, descr):
        delete_pg = page.click_on_catalogs_accordion().\
                    click_on_catalog(name)
        show_cat_pg = delete_pg.delete_catalog()
        Assert.true(show_cat_pg.flash.message.startswith(
            'Catalog "%s": Delete successful' % descr))

    def test_create_and_delete_catalog(self, svc_catalogs_pg, random_string):
        '''Create and delete catalog'''
        cat_page, name, descr = self._create_cat(svc_catalogs_pg, random_string)
        self._delete_cat(cat_page, name, descr);
        
    def test_edit_catalog(self, svc_catalogs_pg, random_string):
        '''Edit catalog'''
        #create
        cat_page, name, descr = self._create_cat(svc_catalogs_pg, random_string)
        #edit
        edit_pg = cat_page.click_on_catalogs_accordion().\
             click_on_catalog(name)
        edited_cat = name+"_edit"
        show_cat_pg = edit_pg.edit_catalog(edited_cat)
        Assert.true(show_cat_pg.flash.message.startswith(
             'ServiceTemplateCatalog "%s" was saved' % edited_cat))
        #clean up
        self._delete_cat(cat_page, edited_cat, descr);


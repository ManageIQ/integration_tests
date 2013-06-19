
import pytest
import time
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestConfigurationSettingsRegion:
    def test_cap_and_util_all_clusters(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        cap_and_util_pg = config_pg.click_on_settings().click_on_first_region().click_on_cap_and_util()
        current_clusters_checkbox = cap_and_util_pg.cluster_checkbox.get_attribute("checked")
        if (current_clusters_checkbox == "true"):
            cap_and_util_pg.uncheck_all_clusters()
            cap_and_util_pg.click_on_save()
            Assert.true(cap_and_util_pg.flash.message.startswith("Capacity and Utilization Collection settings saved"))
        else:
            cap_and_util_pg.check_all_clusters()
            cap_and_util_pg.click_on_save()
            Assert.true(cap_and_util_pg.flash.message.startswith("Capacity and Utilization Collection settings saved"))        
        current_clusters_checkbox = cap_and_util_pg.cluster_checkbox.get_attribute("checked")
        if (current_clusters_checkbox == "true"):
            cap_and_util_pg.uncheck_all_clusters()
            cap_and_util_pg.click_on_reset()
            Assert.true(cap_and_util_pg.flash.message.startswith("All changes have been reset"))
        else:
            cap_and_util_pg.check_all_clusters()
            cap_and_util_pg.click_on_reset()
            Assert.true(cap_and_util_pg.flash.message.startswith("All changes have been reset"))

    def test_cap_and_util_specific_clusters(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        cap_and_util_pg = config_pg.click_on_settings().click_on_first_region().click_on_cap_and_util()
        cap_and_util_pg.uncheck_all_clusters()
        Assert.true(cap_and_util_pg.check_all_clusters_checkbox.get_attribute("checked") != "true")
        cap_and_util_pg.check_specific_cluster("Default")
        cap_and_util_pg.uncheck_specific_cluster("Default")
        cap_and_util_pg.check_specific_cluster("qeblade21asdasd")
        cap_and_util_pg.click_on_reset()
        Assert.true(cap_and_util_pg.flash.message.startswith("All changes have been reset"))

    def test_cap_and_util_datastores(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        cap_and_util_pg = config_pg.click_on_settings().click_on_first_region().click_on_cap_and_util()
        current_datastores_checkbox = cap_and_util_pg.datastore_checkbox.get_attribute("checked")
        if (current_datastores_checkbox == "true"):
            cap_and_util_pg.uncheck_all_datastores()
            cap_and_util_pg.click_on_save()
            Assert.true(cap_and_util_pg.flash.message.startswith("Capacity and Utilization Collection settings saved"))
        else:
            cap_and_util_pg.check_all_datastores()
            cap_and_util_pg.click_on_save()
            Assert.true(cap_and_util_pg.flash.message.startswith("Capacity and Utilization Collection settings saved"))        
        current_datastores_checkbox = cap_and_util_pg.datastore_checkbox.get_attribute("checked")
        if (current_datastores_checkbox == "true"):
            cap_and_util_pg.uncheck_all_datastores()
            cap_and_util_pg.click_on_reset()
            Assert.true(cap_and_util_pg.flash.message.startswith("All changes have been reset"))
        else:
            cap_and_util_pg.check_all_datastores()
            cap_and_util_pg.click_on_reset()
            Assert.true(cap_and_util_pg.flash.message.startswith("All changes have been reset"))

    def test_cap_and_util_specific_datastores(self, mozwebqa, home_page_logged_in):
        home_pg = home_page_logged_in
        config_pg = home_pg.header.site_navigation_menu("Configuration").sub_navigation_menu("Configuration").click()
        Assert.true(config_pg.is_the_current_page)
        cap_and_util_pg = config_pg.click_on_settings().click_on_first_region().click_on_cap_and_util()
        cap_and_util_pg.uncheck_all_datastores()
        Assert.true(cap_and_util_pg.check_all_datastores_checkbox.get_attribute("checked") != "true")
        cap_and_util_pg.check_specific_datastore("datastore1 [50328aff-adaef710-7a6c-5cf3fc1c8656]")
        cap_and_util_pg.uncheck_specific_datastore("datastore1 [50328aff-adaef710-7a6c-5cf3fc1c8656]")
        cap_and_util_pg.check_specific_datastore("iso [qeblade21.rhq.lab.eng.bos.redhat.com:/home/rhev/iso]")
        cap_and_util_pg.click_on_reset()
        Assert.true(cap_and_util_pg.flash.message.startswith("All changes have been reset"))


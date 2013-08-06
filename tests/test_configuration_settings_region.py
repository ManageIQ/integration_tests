
import pytest
from unittestzero import Assert

@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
class TestConfigurationSettingsRegion:
    def test_cap_and_util_all_clusters(self, cnf_configuration_pg):
        Assert.true(cnf_configuration_pg.is_the_current_page)
        cap_and_util_pg = cnf_configuration_pg.click_on_settings()\
                .click_on_first_region().click_on_cap_and_util()
        current_clusters_checkbox = cap_and_util_pg.cluster_checkbox\
                .get_attribute("checked")
        if (current_clusters_checkbox == "true"):
            cap_and_util_pg.uncheck_all_clusters()
            cap_and_util_pg.click_on_save()
            Assert.true(cap_and_util_pg.flash.message.startswith(
                    "Capacity and Utilization Collection settings saved"))
            cap_and_util_pg.check_all_clusters()
            cap_and_util_pg.click_on_save()
        else:
            cap_and_util_pg.check_all_clusters()
            cap_and_util_pg.click_on_save()
            Assert.true(cap_and_util_pg.flash.message.startswith(
                    "Capacity and Utilization Collection settings saved"))
            cap_and_util_pg.uncheck_all_clusters()
            cap_and_util_pg.click_on_save()
        if (current_clusters_checkbox == "true"):
            cap_and_util_pg.uncheck_all_clusters()
            cap_and_util_pg.click_on_reset()
            Assert.true(cap_and_util_pg.flash.message.startswith(
                    "All changes have been reset"))
        else:
            cap_and_util_pg.check_all_clusters()
            cap_and_util_pg.click_on_reset()
            Assert.true(cap_and_util_pg.flash.message.startswith(
                    "All changes have been reset"))

    def test_cap_and_util_all_datastores(self, cnf_configuration_pg):
        Assert.true(cnf_configuration_pg.is_the_current_page)
        cap_and_util_pg = cnf_configuration_pg.click_on_settings()\
                .click_on_first_region().click_on_cap_and_util()
        current_datastores_checkbox = cap_and_util_pg.datastore_checkbox\
                .get_attribute("checked")
        if (current_datastores_checkbox == "true"):
            cap_and_util_pg.uncheck_all_datastores()
            cap_and_util_pg.click_on_save()
            Assert.true(cap_and_util_pg.flash.message.startswith(
                    "Capacity and Utilization Collection settings saved"))
            cap_and_util_pg.check_all_datastores()
            cap_and_util_pg.click_on_save()
        else:
            cap_and_util_pg.check_all_datastores()
            cap_and_util_pg.click_on_save()
            Assert.true(cap_and_util_pg.flash.message.startswith(
                    "Capacity and Utilization Collection settings saved"))
            cap_and_util_pg.uncheck_all_datastores()
            cap_and_util_pg.click_on_save()
        if (current_datastores_checkbox == "true"):
            cap_and_util_pg.uncheck_all_datastores()
            cap_and_util_pg.click_on_reset()
            Assert.true(cap_and_util_pg.flash.message.startswith(
                    "All changes have been reset"))
        else:
            cap_and_util_pg.check_all_datastores()
            cap_and_util_pg.click_on_reset()
            Assert.true(cap_and_util_pg.flash.message.startswith(
                    "All changes have been reset"))



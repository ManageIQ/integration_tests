import pytest
from unittestzero import Assert

class TestSearch:

    @pytest.mark.nondestructive
    def test_search_zero_results(self, infra_vms_pg):
        infra_vms_pg.search.search_by_name('not_found')
        body = infra_vms_pg.selenium.find_element_by_tag_name("body");
        Assert.true("Names with \"not_found\"" in body.text)
        Assert.true("No Records Found" in body.text)

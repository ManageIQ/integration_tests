import pytest

@pytest.mark.usefixtures("selenium")
class TestFoo: 
    def test_footest(self):
        pass

    def test_mytest(self, selenium):
        selenium.get("http://google.com")

from cfme.web_ui import Region
from selenium.webdriver.common.by import By
import fixtures.pytest_selenium as sel

# TODO - flash apparently can show more than one message, so
# we should return a list

# TODO - can also dismiss flash messages currently to reveal more
# this is a design problem IMO.  Maybe see if we can support that
# but get dev to fix

flash_area = Region(locators=
                    {'message': (By.XPATH, "//div[@id='flash_text_div' or @id='flash_div']")})


def get_message():
    if sel.is_displayed(flash_area.message):
        return sel.text(flash_area.message)
    else:
        return None

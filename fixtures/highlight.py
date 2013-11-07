'''
Created on May 13, 2013

@author: bcrochet
'''
def pytest_addoption(parser):
    group = parser.getgroup('cfme', 'cfme')
    group._addoption('--highlight',
                     action='store_true',
                     dest='highlight',
                     default=False,
                     help='whether to turn on highlighting of elements')

def highlight(element):
    """Highlights (blinks) a Webdriver element.
        In pure javascript, as suggested by https://github.com/alp82.
    """
    driver = element._parent
    driver.execute_script("""
            element = arguments[0];
            original_style = element.getAttribute('style');
            element.setAttribute('style', original_style + "; background: yellow;");
            setTimeout(function(){
                element.setAttribute('style', original_style);
            }, 30);
            """, element)

def pytest_configure(config):
    from selenium.webdriver.remote.webelement import WebElement
    def _execute(self, command, params=None):
        highlight(self)
        return self._old_execute(command, params)

    # Let's add highlight as a method to WebDriver so we can call it arbitrarily
    WebElement.highlight = highlight

    if (config.option.highlight):
        WebElement._old_execute = WebElement._execute
        WebElement._execute = _execute


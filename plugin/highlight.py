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
    def _execute(self, command, params=None):
        highlight(self)
        return self._old_execute(command, params)

    if (config.option.highlight):
        from selenium.webdriver.remote.webelement import WebElement
        WebElement._old_execute = WebElement._execute
        WebElement._execute = _execute


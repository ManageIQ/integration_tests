"""
Module containing classes with common behaviour for consoles of both VMs and Instances of all types.
"""
import base64
import re
import tempfile
import time

from PIL import Image
from PIL import ImageFilter
from pytesseract import image_to_string
from selenium.webdriver.common.keys import Keys
from wait_for import TimedOutError
from wait_for import wait_for

from cfme.exceptions import ItemNotFound
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty


class ConsoleMixin(object):
    """
    A mixin to provide methods to get a vm console object
    """

    @classmethod
    def console_handle(cls, browser):
        """
        The basic algorithm for getting the consoles window handle is to get the
        appliances window handle and then iterate through the window_handles till we find
        one that is not the appliances window handle.   Once we find this check that it has
        a canvas widget with a specific ID
        """
        br_wt = browser.widgetastic
        appliance_handle = br_wt.window_handle
        cur_handles = br_wt.selenium.window_handles
        logger.info("Current Window Handles:  {}".format(cur_handles))

        for handle in cur_handles:
            if handle != appliance_handle:
                # FIXME: Add code to verify the tab has the correct widget
                #      for a console tab.
                return handle
        else:
            raise ValueError("Console handle should not be None")

    @property
    def vm_console(self):
        """Get the consoles window handle, and then create a VMConsole object, and store
        the VMConsole object aside.
        """
        console_handle = self.console_handle(self.appliance.browser)

        appliance_handle = self.appliance.browser.widgetastic.window_handle
        logger.info("Creating VMConsole:")
        logger.info("   appliance_handle: {}".format(appliance_handle))
        logger.info("     console_handle: {}".format(console_handle))
        logger.info("               name: {}".format(self.name))

        return VMConsole(appliance_handle=appliance_handle,
                         console_handle=console_handle,
                         vm=self)


class VMConsole(Pretty):
    """Class to manage the VM Console. Presently, only support HTML5/WebMKS Console."""

    pretty_attrs = ['appliance_handle', 'browser', 'console_handle', 'name']

    def __init__(self, vm, console_handle, appliance_handle):
        self.name = vm.name
        self.selenium = vm.appliance.browser.widgetastic.selenium
        self.console_handle = console_handle
        self.appliance_handle = appliance_handle
        self.provider = vm.provider

    ###
    # Methods
    #
    def get_banner(self):
        """Get the text of the banner above the console screen."""
        self.switch_to_console()
        # We know the widget may or may not be available right away
        # so we do this in a try-catch to ensure the code is not stopped
        # due to an exception being thrown.
        try:
            text = self.provider.get_console_connection_status()
        except ItemNotFound:
            logger.exception('Could not find banner element.')
            return None
        finally:
            self.switch_to_appliance()

        logger.info('Read following text from console banner: %s', text)
        return text

    def get_screen(self, timeout=15):
        """
        Retrieve the bit map from the canvas widget that represents the console screen.

        Returns it as a binary string.

        Implementation:
        The canvas tag has a method toDataURL() which one can use in javascript to
        obtain the canvas image  base64 encoded.   Examples of how to do this can be
        seen here:

            https://qxf2.com/blog/selenium-html5-canvas-verify-what-was-drawn/
            https://stackoverflow.com/questions/38316402/how-to-save-a-canvas-as-png-in-selenium
        """
        # Internal function to use in wait_for().   We need to try to get the
        # canvas element within a try-catch, that is in within a wait_for() so
        # we can handle it not showing up right away as it is wont to do on
        # at least RHV providers.
        def _get_canvas_element(provider):
            try:
                canvas = provider.get_remote_console_canvas()
            except ItemNotFound:
                logger.exception('Could not find canvas element.')
                return False

            return canvas

        self.switch_to_console()

        # Get the canvas element
        canvas, wait = wait_for(func=_get_canvas_element, func_args=[self.provider],
                          delay=1, handle_exceptions=True,
                          num_sec=timeout)
        logger.info("canvas: {}\n".format(canvas))

        # Now run some java script to get the contents of the canvas element
        # base 64 encoded.
        image_base64_url = self.selenium.execute_script(
            "return (document.getElementById('mainCanvas') ||"
            "document.getElementsByTagName('canvas')[0]).toDataURL('image/jpeg',1);",
            canvas
        )

        # The results will look like:
        #
        #   data:image/jpeg;base64,iVBORw0KGgoAAAANSUhEUgAAAfQAAABkCAYAAABwx8J9AA...
        #
        # So parse out the data from the non image data from the URL:
        image_base64 = image_base64_url.split(",")[1]

        # Now convert to binary:
        image_jpeg = base64.b64decode(image_base64)

        self.switch_to_appliance()
        return image_jpeg

    def get_screen_text(self):
        """
        Return the text from a text console.

        Uses OCR to scrape the text from the console image taken at the time of the call.
        """
        image_str = self.get_screen()

        # Write the image string to a file as pytesseract requires
        # a file, and doesn't take a string.
        tmp_file = tempfile.NamedTemporaryFile(suffix='.jpeg')
        tmp_file.write(image_str)
        tmp_file.flush()
        tmp_file_name = tmp_file.name
        # Open Image file, resize it to high resolution, sharpen it for clearer text
        # and then run image_to_string operation which returns unicode that needs to
        # be converted to utf-8 which gives us text [typr(text) == 'str']
        # higher resolution allows tesseract to recognize text correctly
        text = (image_to_string(((Image.open(tmp_file_name)).resize((7680, 4320),
         Image.ANTIALIAS)).filter(ImageFilter.SHARPEN), lang='eng',
                                config='--user-words eng.user-words'))
        tmp_file.close()

        logger.info('screen text:{}'.format(text))
        return text

    def is_connected(self):
        """Wait for the banner on the console to say the console is connected."""
        banner = self.get_banner()
        if banner is None:
            return False
        return re.match('Connected', banner) is not None

    def send_keys(self, text):
        """Send text to the console."""
        self.switch_to_console()
        canvas = self.provider.get_remote_console_canvas()
        canvas.click()
        logger.info("Sending following Keys to Console {}".format(text))
        for character in text:
            canvas.send_keys(character)
            # time.sleep() is used as a short delay between two keystrokes.
            # If keys are sent to canvas any faster, canvas fails to receive them.
            time.sleep(0.3)
        canvas.send_keys(Keys.ENTER)
        self.switch_to_appliance()

    def send_ctrl_alt_delete(self):
        """Press the ctrl-alt-delete button in the console tab."""
        self.switch_to_console()
        ctrl_alt_del_btn = self.provider.get_console_ctrl_alt_del_btn()
        logger.info("Sending following Keys to Console CTRL+ALT+DEL")
        ctrl_alt_del_btn.click()
        self.switch_to_appliance()

    def send_fullscreen(self):
        """Press the fullscreen button in the console tab."""
        self.switch_to_console()
        fullscreen_btn = self.provider.get_console_fullscreen_btn()
        logger.info("Sending following Keys to Console Toggle Fullscreen")
        before_height = self.selenium.get_window_size()['height']
        fullscreen_btn.click()
        after_height = self.selenium.get_window_size()['height']
        fullscreen_btn.click()
        self.switch_to_console()
        logger.info("Height before fullscreen: {}\n Height after fullscreen:{}\n".format(
            before_height, after_height))
        if after_height > before_height:
            return True
        return False

    def switch_to_appliance(self):
        """Switch focus to appliance tab/window."""
        logger.info("Switching to appliance: window handle = {}".format(self.appliance_handle))
        self.selenium.switch_to_window(self.appliance_handle)

    def switch_to_console(self):
        """Switch focus to console tab/window."""
        logger.info("Switching to console: window handle = {}".format(self.console_handle))
        self.selenium.switch_to_window(self.console_handle)

    def wait_for_connect(self, timeout=30):
        """Wait for as long as the specified/default timeout for the console to be connected."""
        try:
            logger.info('Waiting for console connection (timeout={})'.format(timeout))
            wait_for(func=lambda: self.is_connected(),
                     delay=1, handle_exceptions=True,
                     num_sec=timeout)
            return True
        except TimedOutError:
            return False

    def close_console_window(self):
        """Attempt to close Console window at the end of test."""
        if self.console_handle is not None:
            self.switch_to_console()
            self.selenium.close()
            logger.info("Browser window/tab containing Console was closed.")
            self.switch_to_appliance()

    def find_text_on_screen(self, text_to_find, current_line=False):
        """Find particular text is present on Screen.

        This function uses get_screen_text function to get string containing
        the text on the screen and then tries to match it against the 'text_to_find'.

        Args:
            text_to_find: This is what re.search will try to search for on screen.
        Returns:
            If the match is found returns True else False.
        """
        # With provider RHOS7-GA, VMs spawned from Cirros template goes into screensaver mode
        # sometimes, and shows a blank black screen, which causes test failures. To avoid that,
        # and wake Cirros up from screensaver, following check is applied ,"\n" is sent if required.
        if not self.get_screen_text():
            self.send_keys("\n")
        if current_line:
            return re.search(text_to_find, self.get_screen_text().split('\n')[-1]) is not None
        return re.search(text_to_find, self.get_screen_text()) is not None

    def wait_for_text(self, timeout=45, text_to_find="", to_disappear=False):
        """Wait for as long as the specified/default timeout for the 'text' to show up on screen.

        Args:
            timeout: Wait Time before wait_for function times out.
            text_to_find: value passed to find_text_on_screen function
            to_disappear: if set to True, function will wait for text_to_find to disappear
                          from screen.
        """
        if not text_to_find:
            return None
        try:
            if to_disappear:
                logger.info("Waiting for {} to disappear from screen".format(text_to_find))
            result = wait_for(func=lambda: to_disappear != self.find_text_on_screen(text_to_find),
                     delay=5,
                     num_sec=timeout)
            return result.out
        except TimedOutError:
            return None

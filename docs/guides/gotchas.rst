Gotchas
=======

Selenium has a few quirks which have caused us immense amounts of debugging time. If you
are facing strange issues with Selenium that you can't explain and this usually boils down
to "Selenium is lying to me", please check this page first before spending vast amounts of
time debugging .

Selenium is not clicking on the element it says it is
-----------------------------------------------------

Sometimes, under certain circumstances, Selenium doesn't click on the element you tell it to.
The symptoms of this include having a WebElement that gives a certain value when queried with
``.text()`` and then Selenium actually clicking on the wrong element. This has been observed
happening when there is a frame or some other element where horizontal scrolling has been
introduced. A typical example would be in the left hand tree items in the System Image Type
under the ``Infrastructure > PXE`` menu. If one system image name is 256 characters, this causes
the problem to manifest.

Selenium is not sending the keys I tell it to, or is filling the box with junk
------------------------------------------------------------------------------

This should not be happening now since framework is configured to be more intelligent than Selenium
and it detects whether the element filled is a file input or not. Because Selenium can be running
remotely, if you want to upload a file, Selenium first needs to upload the file to the remote
executor and then it changes the string accordingly. This happens in default Selenium configuration,
as the :py:class:`selenium.webdriver.remote.file_detector.LocalFileDetector` is used by default for
all keyboard input. Framework now sets it up so the
:py:class:`selenium.webdriver.remote.file_detector.UselessFileDetector` is used by default and if
the element filled is an input with type file, then the file detector is actually used.

When getting the text of the element, Selenium returns an empty string
----------------------------------------------------------------------
Stop using the ``.text`` property of the ``WebElement`` and use
:py:func:`cfme.fixtures.pytest_selenium.text`, which solves this issue. The thing is, when an
element is eg. obscured, Selenium can't read it. So the ``text`` function first tries to scroll the
page so the element is visible, and if that does not help, it uses a bit of JavaScript to pull the
text out.

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

If you have a file in the root of your project which has the same name as an item of text that
you are trying to send to an input element. Selenium tries to be clever and replaces this text
with a path, representing that file as it believes you are trying to upload it. Currently we
do not have a way to disable this with the Python bindings, so just be wary of naming files
that have the same name as text you may want to use further down the line. This was first
discovered when a menu.php file used to exist in the root dir for checking PXE. When the menu
filename box was due to be filled in with ``menu.php`` it was instead filled in with
``/tmp/288762525-2350923r09u2-29u2o3ur23/23982986498264928file/menu.php`` which caused the PXE
refreshes to fail every time ;)

manageiq.tests
==============

ManageIQ Tests

Setup:

1. Copy credentials.yaml.template, mozwebqa.cfg.template, pytest.ini.template from cfme_pages project, and remove the .template extension.
2. Edit to reflect your environment (these should NOT be checked in to source control)
3. Create a virtualenv to run pytest from
4. pip install -Ur /path/to/cfme_pages/requirements.txt
5. PYTHONPATH=/path/to/cfme_pages py.test --driver=firefox --credentials=credentials.yaml --untrusted
6. Some of the items in the previous step can be put into your environment, and into pytest.ini so you can then just run py.test. That exercise is left for the reader.

To setup up for chrome:

1. Download from http://code.google.com/p/chromedriver/downloads/list. Use the latest available for your arch. There is currently a problem with the chromedriver2, so use the latest that is NOT chromedriver2.
2. Unzip that file to somewhere on your path.
3. Substitue --driver=firefox with --driver=chrome


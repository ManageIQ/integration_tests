manageiq.tests
==============

ManageIQ Tests

Setup:

1. Copy credentials.yaml and mozwebqa.cfg from manageiq.pages submodule
2. Edit both to reflect your environment (these should NOT be checked in to source control)
3. Create a virtualenv to run pytest from
4. pip install -Ur manageiq.pages/requirements.txt
5. PYTHONPATH=manageiq.pages py.test --driver=firefox --credentials=credentials.yaml --untrusted

NOTE:

Currently, the navigation doesn't work with Firefox. Fix is in progress. To setup up for chrome:

1. Download from http://code.google.com/p/chromedriver/downloads/list. Use the latest available for your arch.
2. Unzip that file to somewhere on your path.
3. Substitue --driver=firefox with --driver=chrome



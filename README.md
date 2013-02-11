manageiq.tests
==============

ManageIQ Tests

Setup:

Copy credentials.yaml and mozwebqa.cfg from manageiq.pages submodule
Edit both to reflect your environment (these should NOT be checked in to source control)
Create a virtualenv to run pytest from
pip install -Ur manageiq.pages/requirements.txt
PYTHONPATH=manageiq.pages py.test --driver=firefox --credentials=credentials.yaml --untrusted



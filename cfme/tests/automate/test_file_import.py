import pytest

from cfme import test_requirements
from cfme.fixtures.automate import DatastoreImport

pytestmark = [test_requirements.automate, pytest.mark.tier(3)]


@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1715396.zip", "BZ_1715396", None, None)],
    ids=["sample_domain"],
)
def test_domain_import_file(import_datastore, import_data):
    """This test case Verifies that a domain can be imported from file.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/6h
        caseimportance: medium
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        testSteps:
            1. Navigate to Automation > Automate > Import/Export
            2. Upload zip datastore file
            3. Select domain which like to import
        expectedResults:
            1.
            2.
            3. Import should work. Check imported or not.
    """
    assert import_datastore.exists

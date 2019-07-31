import pytest

from cfme import test_requirements

pytestmark = [test_requirements.automate, pytest.mark.tier(3)]


def test_domain_import_file(import_datastore):
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
    domain = import_datastore(file_name="bz_1715396.zip", from_domain="BZ_1715396")
    assert domain.exists

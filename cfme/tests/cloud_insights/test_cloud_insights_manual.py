import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.tier(0),
    test_requirements.access,
    pytest.mark.manual
]


def test_red_hat_cloud_services_overview():
    """
    Verification of the Red Hat Cloud Services Page

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: CloudIntegration
        initialEstimate: 1h
        testSteps:
            1. On a CloudForms appliance, navigate to Red Hat Cloud->Services
            2. Examine the header
            3. Examine the sub-text
            4. Examine the cloud.redhat.com URL in the subtext.
            5. Examine the "Take me there" button
        expectedResults:
            1. Verify the Services page is rendered
            2. Verify the header is titled "Services"
            3. Verify the subtext is
                "Explore our Software-as-a-Services offerings at cloud.redhat.com."
            4. Verify the URL is hyperlinked and clicking the link redirects the user to
                cloud.redhat.com
            5. Verify the button is displayed and clicking the button redirects the user to
                cloud.redhat.com
    """
    pass


def test_red_hat_cloud_providers_overview():
    """
     Verification of the Red Hat Cloud Providers Page

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: CloudIntegration
        initialEstimate: 1h
        setup:
            1. Register the CloudForms appliance to RHSM and Insights
            2. Add any of the supported providers (OSP, vSphere, RHEV)
        testSteps:
            1. On a CloudForms appliance, navigate to Red Hat Cloud->Providers
            2. Examine the headers on the page
            3. Examine the sub-text on the page
            4. Examine the "Synchronize this Platform to Cloud" button.
            5. Examine the Provider Synchronization table
            6. Examine the widgets within the table
            7. Examine the providers in the table
        expectedResults:
            1. Verify the Providers page is rendered
            2. Verify the two headers are "Global Synchronization" and "Provider Synchronization"
            3. Verify the two subtext are
                "Synchronize your CloudForms data to Red Hat Cloud Services." under the Global
                Sync header and "Synchronize your CloudForms data for selected providers." under
                the Provider Sync header
            4. Verify the button exists
            5. Verify the table exists, contains 4 columns (no title, Name, Type, Action),
                is sortable for name and type
            6. Verify the following widgets exists:
                - Filter dropdown with Name and Type option
                - Filter box
                - Table Paginator
                - Global table Synchronize (enabled once a provider is checked)
                - Synchronize action button for each entry in the table
                - Checkboxes for each entry in the table that are clickable
            7. All providers appear in the table that were added in setup
    """
    pass


def test_cloud_insights_sync():
    """
    Synchronize CloudForms data to Red Hat Cloud Services.

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: CloudIntegration
        initialEstimate: 1h
        setup:
            1. Register the CloudForms appliance to RHSM and Insights
            2. Add any of the supported providers (OSP, vSphere, RHEV)
        testSteps:
            1. On a CloudForms appliance, navigate to Red Hat Cloud->Providers
            2. Click "Synchronize this Platform to the Cloud"
            3. For each provider in the table, one by one click the "Synchronize" action
            4. Use the checkboxes in the table to select one provider in the table and click
            "Synchronize"
            5. Use the checkboxes in the table to select multiple provider in the table  and click
            "Synchronize"
        expectedResults:
            1. Verify the Services page is rendered
            2. Verify the info message "Synchronization task has been initiated.", watch the
                logs for a successful upload and verify on the insights side the data was received
            3. Verify for each provider sync, watch the logs for a successful upload and
                verify on the insights side the data was received
            4. Watch the logs and verify a successful upload and
                verify on the insights side the data was received
            5. Same as 4
    """
    pass

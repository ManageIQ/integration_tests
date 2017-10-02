from cfme.utils.wait import wait_for

import pytest


@pytest.mark.tier(3)
def test_send_test_email(smtp_test, random_string, appliance):
    """ This test checks whether the mail sent for testing really arrives. """
    e_mail = random_string + "@email.test"
    appliance.server.settings.send_test_email(email=e_mail)
    wait_for(lambda: len(smtp_test.get_emails(to_address=e_mail)) > 0, num_sec=60)

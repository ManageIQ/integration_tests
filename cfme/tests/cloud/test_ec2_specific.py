import pytest
from utils.providers import get_mgmt
from utils import conf
from manageiq_client.api import ManageIQClient as API
import fauxfactory
import time

SNS_TEST_REGIONS = ["ec2_sa-east-1"]


@pytest.mark.parametrize("sns_test_region", SNS_TEST_REGIONS)
def test_ec2_create_sns_topic(sns_test_region):
    provider_name = fauxfactory.gen_alphanumeric(5)
    provider_mgmt = get_mgmt(sns_test_region)
    topic_arn = provider_mgmt.get_arn_if_topic_exists("AWSConfig_topic")
    if topic_arn:
        provider_mgmt.delete_topic(topic_arn)
    time.sleep(5)
    srv_addr = conf.env.get('base_url')
    region = conf.cfme_data.management_systems.get(sns_test_region)
    appl_credentials = conf.credentials.default
    credentials = conf.credentials.get('aws_iam')
    api = API('{}/api'.format(srv_addr.rstrip('/')), (appl_credentials.get(
        'username'), appl_credentials.get('password')), verify_ssl=False)
    api.collections.providers.action.create(name=provider_name,
                                            provider_region=region.get("region"),
                                            type="ManageIQ::Providers::Amazon::CloudManager",
                                            credentials={"userid": credentials.get('username'),
                                                         "password": credentials.get('password')})
    time.sleep(120)
    if not provider_mgmt.get_arn_if_topic_exists("AWSConfig_topic"):
        pytest.fail("SNS topic was not automatically created!")

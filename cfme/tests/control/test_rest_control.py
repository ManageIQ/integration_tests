"""This module contains control REST API specific tests."""
import fauxfactory
import pytest
from manageiq_client.api import APIException

from cfme import test_requirements
from cfme.rest.gen_data import conditions as _conditions
from cfme.rest.gen_data import policies as _policies
from cfme.rest.gen_data import policy_profiles as _policy_profiles
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.rest import query_resource_attributes
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.rest,
]


class TestConditionsRESTAPI:
    @pytest.fixture(scope='function')
    def conditions(self, request, appliance):
        num_conditions = 2
        response = _conditions(request, appliance, num=num_conditions)
        assert_response(appliance)
        assert len(response) == num_conditions
        return response

    def test_query_condition_attributes(self, conditions, soft_assert):
        """Tests access to condition attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: medium
            initialEstimate: 1/4h
        """
        query_resource_attributes(conditions[0], soft_assert=soft_assert)

    def test_create_conditions(self, appliance, conditions):
        """Tests create conditions.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        for condition in conditions:
            record = appliance.rest_api.collections.conditions.get(id=condition.id)
            assert record.description == condition.description

    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_conditions_from_detail(self, conditions, method):
        """Tests delete conditions from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(conditions, method=method, num_sec=100, delay=5)

    def test_delete_conditions_from_collection(self, conditions):
        """Tests delete conditions from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(conditions, num_sec=100, delay=5)

    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_edit_conditions(self, conditions, appliance, from_detail):
        """Tests edit conditions.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        num_conditions = len(conditions)
        uniq = [fauxfactory.gen_alphanumeric(5) for _ in range(num_conditions)]
        new = [{'description': f'Edited Test Condition {u}'} for u in uniq]
        if from_detail:
            edited = []
            for index in range(num_conditions):
                edited.append(conditions[index].action.edit(**new[index]))
                assert_response(appliance)
        else:
            for index in range(num_conditions):
                new[index].update(conditions[index]._ref_repr())
            edited = appliance.rest_api.collections.conditions.action.edit(*new)
            assert_response(appliance)
        assert len(edited) == num_conditions
        for index, condition in enumerate(conditions):
            record, __ = wait_for(
                lambda: appliance.rest_api.collections.conditions.find_by(
                    description=new[index]['description']) or False,
                num_sec=100,
                delay=5,
                message="Find a test condition"
            )
            condition.reload()
            assert condition.description == edited[index].description == record[0].description


class TestPoliciesRESTAPI:
    @pytest.fixture(scope='function')
    def policies(self, request, appliance):
        num_policies = 2
        response = _policies(request, appliance, num=num_policies)
        assert_response(appliance)
        assert len(response) == num_policies
        return response

    def test_query_policy_attributes(self, policies, soft_assert):
        """Tests access to policy attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        query_resource_attributes(policies[0], soft_assert=soft_assert)

    def test_create_policies(self, appliance, policies):
        """Tests create policies.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        for policy in policies:
            record = appliance.rest_api.collections.policies.get(id=policy.id)
            assert record.description == policy.description

    def test_delete_policies_from_detail_post(self, policies):
        """Tests delete policies from detail using POST method.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(policies, method='POST', num_sec=100, delay=5)

    def test_delete_policies_from_detail_delete(self, policies):
        """Tests delete policies from detail using DELETE method.

        Bugzilla:
            1435773

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(policies, method='DELETE', num_sec=100, delay=5)

    def test_delete_policies_from_collection(self, policies):
        """Tests delete policies from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(policies, num_sec=100, delay=5)

    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_edit_policies(self, policies, appliance, from_detail):
        """Tests edit policies.

        Testing BZ 1435777

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        num_policies = len(policies)
        uniq = [fauxfactory.gen_alphanumeric(5) for _ in range(num_policies)]
        new = [{'description': f'Edited Test Policy {u}'} for u in uniq]
        if from_detail:
            edited = []
            for index in range(num_policies):
                edited.append(policies[index].action.edit(**new[index]))
                assert_response(appliance)
        else:
            for index in range(num_policies):
                new[index].update(policies[index]._ref_repr())
            edited = appliance.rest_api.collections.policies.action.edit(*new)
            assert_response(appliance)
        assert len(edited) == num_policies
        for index, policy in enumerate(policies):
            record, __ = wait_for(
                lambda: appliance.rest_api.collections.policies.find_by(
                    description=new[index]['description']) or False,
                num_sec=100,
                delay=5,
                message="Find a policy"
            )
            policy.reload()
            assert policy.description == edited[index].description == record[0].description

    def test_create_invalid_policies(self, appliance):
        """
        This test case checks policy creation with invalid data.

        Bugzilla:
            1435780

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: high
            initialEstimate: 1/30h
        """
        policy_name = fauxfactory.gen_alphanumeric(5)
        data = {
            "name": f"test_policy_{policy_name}",
            "description": f"Test Policy {policy_name}",
            "mode": "bar",
            "towhat": "baz",
            "conditions_ids": [2000, 3000],
            "policy_contents": [{
                "event_id": 2,
                "actions": [{"action_id": 1, "opts": {"qualifier": "failure"}}]
            }],
        }

        with pytest.raises(APIException, match="Api::BadRequestError"):
            appliance.rest_api.collections.policies.action.create(data)


@pytest.mark.meta(automates=[1806702])
class TestPolicyProfilesRESTAPI:
    @pytest.fixture(scope="function")
    def policy_profiles(self, appliance, request):
        policy_profiles = _policy_profiles(request, appliance, num=2)
        assert_response(appliance)
        return policy_profiles

    def test_query_policy_attributes(self, policy_profiles, soft_assert):
        """Tests access to policy profile attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        query_resource_attributes(policy_profiles[0], soft_assert=soft_assert)

    def test_create_policy_profiles(self, appliance, policy_profiles):
        """
        Bugzilla:
            1806702

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        for policy_profile in policy_profiles:
            pp = appliance.rest_api.collections.policy_profiles.get(id=policy_profile.id)
            assert pp.description == policy_profile.description
            assert pp.name == policy_profile.name

    @pytest.mark.parametrize("from_detail", (True, False), ids=["from_detail", "from_collection"])
    def test_edit_policy_profiles(self, appliance, policy_profiles, from_detail):
        """
        Bugzilla:
            1806702

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        new = [
            fauxfactory.gen_alpha(start="Edited pp ", length=13)
            for _ in range(len(policy_profiles))
        ]
        if from_detail:
            for index, pp in enumerate(policy_profiles):
                pp.action.edit(**{"description": new[index]})
                assert_response(appliance)
        else:
            appliance.rest_api.collections.policy_profiles.action.edit(
                *[
                    {"description": new[index], **pp._ref_repr()}
                    for index, pp in enumerate(policy_profiles)
                ]
            )
            assert_response(appliance)

        for index, pp in enumerate(policy_profiles):
            pp.reload()
            description = new[index]
            policy_profile = appliance.rest_api.collections.policy_profiles.get(
                description=description
            )
            assert pp.description == description == policy_profile.description

    def test_edit_read_only_policy_profile(self, appliance):
        """
        Bugzilla:
            1806702

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        # Currently it's not possible to delete a policy_profile with read_only set to True.
        policy_profile = appliance.rest_api.collections.policy_profiles.action.create(
            {
                "description": fauxfactory.gen_alpha(start="PP description ", length=17),
                "name": fauxfactory.gen_alpha(start="test_pp_name_", length=17),
                "read_only": True,
            }
        )[0]
        assert_response(appliance)
        with pytest.raises(APIException, match="Api::ForbiddenError: Api::ForbiddenError"):
            policy_profile.action.edit(
                {"name": fauxfactory.gen_alpha(start="updated_pp_name_", length=20)}
            )

    @pytest.mark.parametrize("method", ["POST", "DELETE"])
    def test_delete_policy_profiles_from_detail(self, policy_profiles, method):
        """
        Bugzilla:
            1806702

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(policy_profiles, method=method)

    def test_delete_policy_profiles_from_collection(self, policy_profiles):
        """
        Bugzilla:
            1806702

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(policy_profiles, not_found=True)

    def test_read_only_policy_profile_delete(self, appliance):
        """
        Bugzilla:
            1806702

        Polarion:
            assignee: pvala
            casecomponent: Control
            caseimportance: low
            initialEstimate: 1/4h
        """
        # Currently it's not possible to delete a policy_profile with read_only set to True.
        policy_profile = appliance.rest_api.collections.policy_profiles.action.create(
            {
                "description": fauxfactory.gen_alpha(start="PP description ", length=17),
                "name": fauxfactory.gen_alpha(start="test_pp_name_", length=17),
                "read_only": True,
            }
        )[0]
        assert_response(appliance)
        assert policy_profile.read_only
        with pytest.raises(APIException, match="Api::ForbiddenError: Api::ForbiddenError"):
            delete_resources_from_detail([policy_profile], method="DELETE", check_response=False)

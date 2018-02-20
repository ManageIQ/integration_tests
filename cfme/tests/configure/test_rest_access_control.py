# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import (
    _creating_skeleton,
    groups as _groups,
    roles as _roles,
    tenants as _tenants,
    users as _users,
)
from cfme.utils import error
from cfme.utils.blockers import BZ
from cfme.utils.rest import (
    assert_response,
    delete_resources_from_collection,
    query_resource_attributes,
)
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.auth
]


class TestTenantsViaREST(object):
    @pytest.fixture(scope="function")
    def tenants(self, request, appliance):
        num_tenants = 3
        response = _tenants(request, appliance.rest_api, num=num_tenants)
        assert_response(appliance)
        assert len(response) == num_tenants
        return response

    @pytest.mark.tier(3)
    def test_query_tenant_attributes(self, tenants, soft_assert):
        """Tests access to tenant attributes.

        Metadata:
            test_flag: rest
        """
        query_resource_attributes(tenants[0], soft_assert=soft_assert)

    @pytest.mark.tier(3)
    def test_create_tenants(self, appliance, tenants):
        """Tests creating tenants.

        Metadata:
            test_flag: rest
        """
        for tenant in tenants:
            record = appliance.rest_api.collections.tenants.get(id=tenant.id)
            assert_response(appliance)
            assert record.name == tenant.name

    @pytest.mark.tier(2)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_tenants(self, appliance, tenants, multiple):
        """Tests editing tenants.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.tenants
        tenants_len = len(tenants)
        new = []
        for _ in range(tenants_len):
            new.append(
                {'name': 'test_tenants_{}'.format(fauxfactory.gen_alphanumeric().lower())})
        if multiple:
            for index in range(tenants_len):
                new[index].update(tenants[index]._ref_repr())
            edited = collection.action.edit(*new)
            assert_response(appliance)
        else:
            edited = []
            for index in range(tenants_len):
                edited.append(tenants[index].action.edit(**new[index]))
                assert_response(appliance)
        assert tenants_len == len(edited)
        for index, tenant in enumerate(tenants):
            record, _ = wait_for(
                lambda: collection.find_by(name=new[index]['name']) or False,
                num_sec=180,
                delay=10,
            )
            tenant.reload()
            assert record[0].id == edited[index].id == tenant.id
            assert record[0].name == edited[index].name == tenant.name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_tenants_from_detail(self, appliance, tenants, method):
        """Tests deleting tenants from detail.

        Metadata:
            test_flag: rest
        """
        for tenant in tenants:
            del_action = getattr(tenant.action.delete, method.upper())
            del_action()
            assert_response(appliance)

            tenant.wait_not_exists(num_sec=10, delay=2)
            with error.expected("ActiveRecord::RecordNotFound"):
                del_action()
            assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    def test_delete_tenants_from_collection(self, appliance, tenants):
        """Tests deleting tenants from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.tenants
        delete_resources_from_collection(collection, tenants)


class TestRolesViaREST(object):
    @pytest.fixture(scope="function")
    def roles(self, request, appliance):
        num_roles = 3
        response = _roles(request, appliance.rest_api, num=num_roles)
        assert_response(appliance)
        assert len(response) == num_roles
        return response

    @pytest.mark.tier(3)
    def test_query_role_attributes(self, roles, soft_assert):
        """Tests access to role attributes.

        Metadata:
            test_flag: rest
        """
        query_resource_attributes(roles[0], soft_assert=soft_assert)

    @pytest.mark.tier(3)
    def test_create_roles(self, appliance, roles):
        """Tests creating roles.

        Metadata:
            test_flag: rest
        """
        for role in roles:
            record = appliance.rest_api.collections.roles.get(id=role.id)
            assert_response(appliance)
            assert record.name == role.name

    @pytest.mark.tier(2)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_roles(self, appliance, roles, multiple):
        """Tests editing roles.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.roles
        roles_len = len(roles)
        new = []
        for _ in range(roles_len):
            new.append(
                {'name': 'test_role_{}'.format(fauxfactory.gen_alphanumeric())})
        if multiple:
            for index in range(roles_len):
                new[index].update(roles[index]._ref_repr())
            edited = collection.action.edit(*new)
            assert_response(appliance)
        else:
            edited = []
            for index in range(roles_len):
                edited.append(roles[index].action.edit(**new[index]))
                assert_response(appliance)
        assert roles_len == len(edited)
        for index, role in enumerate(roles):
            record, _ = wait_for(
                lambda: collection.find_by(name=new[index]['name']) or False,
                num_sec=180,
                delay=10,
            )
            role.reload()
            assert record[0].id == edited[index].id == role.id
            assert record[0].name == edited[index].name == role.name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_roles_from_detail(self, appliance, roles, method):
        """Tests deleting roles from detail.

        Metadata:
            test_flag: rest
        """
        for role in roles:
            del_action = getattr(role.action.delete, method.upper())
            del_action()
            assert_response(appliance)

            role.wait_not_exists(num_sec=10, delay=2)
            with error.expected("ActiveRecord::RecordNotFound"):
                del_action()
            assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    def test_delete_roles_from_collection(self, appliance, roles):
        """Tests deleting roles from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.roles
        delete_resources_from_collection(collection, roles)

    @pytest.mark.tier(3)
    def test_add_delete_role(self, appliance):
        """Tests adding role using "add" action and deleting it.

        Metadata:
            test_flag: rest
        """
        role_data = {"name": "role_name_{}".format(fauxfactory.gen_alphanumeric())}
        role = appliance.rest_api.collections.roles.action.add(role_data)[0]
        assert_response(appliance)
        assert role.name == role_data["name"]
        wait_for(
            lambda: appliance.rest_api.collections.roles.find_by(name=role.name) or False,
            num_sec=180,
            delay=10,
        )
        found_role = appliance.rest_api.collections.roles.get(name=role.name)
        assert found_role.name == role_data["name"]
        role.action.delete()
        assert_response(appliance)
        with error.expected("ActiveRecord::RecordNotFound"):
            role.action.delete()
        assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    def test_role_assign_and_unassign_feature(self, appliance, roles):
        """Tests assigning and unassigning feature to a role.

        Metadata:
            test_flag: rest
        """
        feature = appliance.rest_api.collections.features.get(name="Everything")
        role = roles[0]
        role.reload()
        role.features.action.assign(feature)
        assert_response(appliance)
        role.reload()
        # This verification works because the created roles don't have assigned features
        assert feature.id in [f.id for f in role.features.all]
        role.features.action.unassign(feature)
        assert_response(appliance)
        role.reload()
        assert feature.id not in [f.id for f in role.features.all]


class TestGroupsViaREST(object):
    @pytest.fixture(scope="function")
    def tenants(self, request, appliance):
        return _tenants(request, appliance.rest_api, num=1)

    @pytest.fixture(scope="function")
    def roles(self, request, appliance):
        return _roles(request, appliance.rest_api, num=1)

    @pytest.fixture(scope="function")
    def groups(self, request, appliance, roles, tenants):
        num_groups = 3
        response = _groups(request, appliance.rest_api, roles, tenants, num=num_groups)
        assert_response(appliance)
        assert len(response) == num_groups
        return response

    @pytest.mark.tier(3)
    def test_query_group_attributes(self, groups, soft_assert):
        """Tests access to group attributes.

        Metadata:
            test_flag: rest
        """
        query_resource_attributes(groups[0], soft_assert=soft_assert)

    @pytest.mark.tier(3)
    def test_create_groups(self, appliance, groups):
        """Tests creating groups.

        Metadata:
            test_flag: rest
        """
        for group in groups:
            record = appliance.rest_api.collections.groups.get(id=group.id)
            assert_response(appliance)
            assert record.description == group.description

    @pytest.mark.tier(2)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_groups(self, appliance, groups, multiple):
        """Tests editing groups.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.groups
        groups_len = len(groups)
        new = []
        for _ in range(groups_len):
            new.append(
                {'description': 'group_description_{}'.format(fauxfactory.gen_alphanumeric())})
        if multiple:
            for index in range(groups_len):
                new[index].update(groups[index]._ref_repr())
            edited = collection.action.edit(*new)
            assert_response(appliance)
        else:
            edited = []
            for index in range(groups_len):
                edited.append(groups[index].action.edit(**new[index]))
                assert_response(appliance)
        assert groups_len == len(edited)
        for index, group in enumerate(groups):
            record, _ = wait_for(
                lambda: collection.find_by(description=new[index]['description']) or False,
                num_sec=180,
                delay=10,
            )
            group.reload()
            assert record[0].id == edited[index].id == group.id
            assert record[0].description == edited[index].description == group.description

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_groups_from_detail(self, appliance, groups, method):
        """Tests deleting groups from detail.

        Metadata:
            test_flag: rest
        """
        for group in groups:
            del_action = getattr(group.action.delete, method.upper())
            del_action()
            assert_response(appliance)

            group.wait_not_exists(num_sec=10, delay=2)
            with error.expected("ActiveRecord::RecordNotFound"):
                del_action()
            assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    def test_delete_groups_from_collection(self, appliance, groups):
        """Tests deleting groups from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.groups
        delete_resources_from_collection(collection, groups, not_found=True)


class TestUsersViaREST(object):
    @pytest.fixture(scope="function")
    def users_data(self, request, appliance, num=3):
        num_users = num
        response, prov_data = _users(request, appliance.rest_api, num=num_users)
        assert_response(appliance)
        assert len(response) == num
        return response, prov_data

    @pytest.fixture(scope='function')
    def user_auth(self, request, appliance):
        users, prov_data = self.users_data(request, appliance, num=1)
        return users[0].userid, prov_data[0]['password']

    @pytest.fixture(scope='function')
    def users(self, request, appliance):
        users, __ = self.users_data(request, appliance)
        return users

    @pytest.mark.tier(3)
    def test_query_user_attributes(self, users, soft_assert):
        """Tests access to user attributes.

        Metadata:
            test_flag: rest
        """
        query_resource_attributes(users[0], soft_assert=soft_assert)

    @pytest.mark.tier(3)
    def test_create_users(self, appliance, users_data):
        """Tests creating users.

        Metadata:
            test_flag: rest
        """
        users, prov_data = users_data
        for index, user in enumerate(users):
            record = appliance.rest_api.collections.users.get(id=user.id)
            assert_response(appliance)
            assert record.name == user.name
            user_auth = (user.userid, prov_data[index]['password'])
            assert appliance.new_rest_api_instance(auth=user_auth)

    @pytest.mark.tier(3)
    @pytest.mark.meta(blockers=[BZ(1547445, forced_streams=['5.8'])])
    def test_create_uppercase_user(self, request, appliance):
        """Tests creating user with userid containing uppercase letters.

        Metadata:
            test_flag: rest
        """
        uniq = fauxfactory.gen_alphanumeric(4).upper()
        data = {
            "userid": "rest_{}".format(uniq),
            "name": "REST User {}".format(uniq),
            "password": fauxfactory.gen_alphanumeric(),
            "email": "user@example.com",
            "group": {"description": "EvmGroup-user_self_service"}
        }

        user = _creating_skeleton(request, appliance.rest_api, 'users', [data])[0]
        assert_response(appliance)
        user_auth = (user.userid, data['password'])
        assert appliance.new_rest_api_instance(auth=user_auth)

    @pytest.mark.tier(2)
    def test_edit_user_password(self, appliance, users):
        """Tests editing user password.

        Metadata:
            test_flag: rest
        """
        user = users[0]
        new_password = fauxfactory.gen_alphanumeric()
        user.action.edit(password=new_password)
        assert_response(appliance)
        new_user_auth = (user.userid, new_password)
        assert appliance.new_rest_api_instance(auth=new_user_auth)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_user_name(self, appliance, users, multiple):
        """Tests editing user name.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.users
        users_len = len(users)
        new = []
        for _ in range(users_len):
            new.append(
                {'name': 'user_name_{}'.format(fauxfactory.gen_alphanumeric())})
        if multiple:
            for index in range(users_len):
                new[index].update(users[index]._ref_repr())
            edited = collection.action.edit(*new)
            assert_response(appliance)
        else:
            edited = []
            for index in range(users_len):
                edited.append(users[index].action.edit(**new[index]))
                assert_response(appliance)
        assert users_len == len(edited)
        for index, user in enumerate(users):
            record, _ = wait_for(
                lambda: collection.find_by(name=new[index]['name']) or False,
                num_sec=180,
                delay=10,
            )
            user.reload()
            assert record[0].id == edited[index].id == user.id
            assert record[0].name == edited[index].name == user.name

    @pytest.mark.tier(3)
    def test_change_password_as_user(self, appliance, user_auth):
        """Tests that users can update their own password.

        Metadata:
            test_flag: rest
        """
        new_password = fauxfactory.gen_alphanumeric()
        new_user_auth = (user_auth[0], new_password)

        user = appliance.rest_api.collections.users.get(userid=user_auth[0])
        user_api = appliance.new_rest_api_instance(auth=user_auth)
        user_api.post(user.href, action='edit', resource={'password': new_password})
        assert_response(user_api)

        # login using new password
        assert appliance.new_rest_api_instance(auth=new_user_auth)
        # try to login using old password
        with error.expected('Authentication failed'):
            appliance.new_rest_api_instance(auth=user_auth)

    @pytest.mark.tier(3)
    def test_change_email_as_user(self, appliance, user_auth):
        """Tests that users can update their own email.

        Metadata:
            test_flag: rest
        """
        new_email = 'new@example.com'

        user = appliance.rest_api.collections.users.get(userid=user_auth[0])
        user_api = appliance.new_rest_api_instance(auth=user_auth)
        user_api.post(user.href, action='edit', resource={'email': new_email})
        assert_response(user_api)

        user.reload()
        assert user.email == new_email

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_users_from_detail(self, appliance, users, method):
        """Tests deleting users from detail.

        Metadata:
            test_flag: rest
        """
        for user in users:
            del_action = getattr(user.action.delete, method.upper())
            del_action()
            assert_response(appliance)

            user.wait_not_exists(num_sec=10, delay=2)
            with error.expected("ActiveRecord::RecordNotFound"):
                del_action()
            assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    def test_delete_users_from_collection(self, appliance, users):
        """Tests deleting users from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.users
        delete_resources_from_collection(collection, users)

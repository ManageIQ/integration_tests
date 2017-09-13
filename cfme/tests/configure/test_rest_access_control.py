# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.configure.access_control import User
from cfme.rest.gen_data import (
    _creating_skeleton,
    groups as _groups,
    roles as _roles,
    tenants as _tenants,
    users as _users,
)
from cfme.utils import error
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.auth
]


class TestTenantsViaREST(object):
    @pytest.fixture(scope="function")
    def tenants(self, request, appliance):
        num_tenants = 3
        response = _tenants(request, appliance.rest_api, num=num_tenants)
        assert appliance.rest_api.response.status_code == 200
        assert len(response) == num_tenants
        return response

    @pytest.mark.tier(3)
    def test_create_tenants(self, appliance, tenants):
        """Tests creating tenants.

        Metadata:
            test_flag: rest
        """
        for tenant in tenants:
            record = appliance.rest_api.collections.tenants.get(id=tenant.id)
            assert appliance.rest_api.response.status_code == 200
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
            assert appliance.rest_api.response.status_code == 200
        else:
            edited = []
            for index in range(tenants_len):
                edited.append(tenants[index].action.edit(**new[index]))
                assert appliance.rest_api.response.status_code == 200
        assert tenants_len == len(edited)
        for index in range(tenants_len):
            record, _ = wait_for(
                lambda: collection.find_by(name=new[index]['name']) or False,
                num_sec=180,
                delay=10,
            )
            assert record[0].id == edited[index].id
            assert record[0].name == edited[index].name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_tenants_from_detail(self, appliance, tenants, method):
        """Tests deleting tenants from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for tenant in tenants:
            tenant.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                tenant.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_tenants_from_collection(self, appliance, tenants):
        """Tests deleting tenants from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.tenants.action.delete(*tenants)
        assert appliance.rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.tenants.action.delete(*tenants)
        assert appliance.rest_api.response.status_code == 404


class TestRolesViaREST(object):
    @pytest.fixture(scope="function")
    def roles(self, request, appliance):
        num_roles = 3
        response = _roles(request, appliance.rest_api, num=num_roles)
        assert appliance.rest_api.response.status_code == 200
        assert len(response) == num_roles
        return response

    @pytest.mark.tier(3)
    def test_create_roles(self, appliance, roles):
        """Tests creating roles.

        Metadata:
            test_flag: rest
        """
        for role in roles:
            record = appliance.rest_api.collections.roles.get(id=role.id)
            assert appliance.rest_api.response.status_code == 200
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
            assert appliance.rest_api.response.status_code == 200
        else:
            edited = []
            for index in range(roles_len):
                edited.append(roles[index].action.edit(**new[index]))
                assert appliance.rest_api.response.status_code == 200
        assert roles_len == len(edited)
        for index in range(roles_len):
            record, _ = wait_for(
                lambda: collection.find_by(name=new[index]['name']) or False,
                num_sec=180,
                delay=10,
            )
            assert record[0].id == edited[index].id
            assert record[0].name == edited[index].name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_roles_from_detail(self, appliance, roles, method):
        """Tests deleting roles from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for role in roles:
            role.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                role.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_roles_from_collection(self, appliance, roles):
        """Tests deleting roles from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.roles.action.delete(*roles)
        assert appliance.rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.roles.action.delete(*roles)
        assert appliance.rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_add_delete_role(self, appliance):
        """Tests adding role using "add" action and deleting it.

        Metadata:
            test_flag: rest
        """
        role_data = {"name": "role_name_{}".format(format(fauxfactory.gen_alphanumeric()))}
        role = appliance.rest_api.collections.roles.action.add(role_data)[0]
        assert appliance.rest_api.response.status_code == 200
        assert role.name == role_data["name"]
        wait_for(
            lambda: appliance.rest_api.collections.roles.find_by(name=role.name) or False,
            num_sec=180,
            delay=10,
        )
        found_role = appliance.rest_api.collections.roles.get(name=role.name)
        assert found_role.name == role_data["name"]
        role.action.delete()
        assert appliance.rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            role.action.delete()
        assert appliance.rest_api.response.status_code == 404

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
        assert appliance.rest_api.response.status_code == 200
        role.reload()
        # This verification works because the created roles don't have assigned features
        assert feature.id in [f.id for f in role.features.all]
        role.features.action.unassign(feature)
        assert appliance.rest_api.response.status_code == 200
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
        assert appliance.rest_api.response.status_code == 200
        assert len(response) == num_groups
        return response

    @pytest.mark.tier(3)
    def test_create_groups(self, appliance, groups):
        """Tests creating groups.

        Metadata:
            test_flag: rest
        """
        for group in groups:
            record = appliance.rest_api.collections.groups.get(id=group.id)
            assert appliance.rest_api.response.status_code == 200
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
            assert appliance.rest_api.response.status_code == 200
        else:
            edited = []
            for index in range(groups_len):
                edited.append(groups[index].action.edit(**new[index]))
                assert appliance.rest_api.response.status_code == 200
        assert groups_len == len(edited)
        for index in range(groups_len):
            record, _ = wait_for(
                lambda: collection.find_by(description=new[index]['description']) or False,
                num_sec=180,
                delay=10,
            )
            assert record[0].id == edited[index].id
            assert record[0].description == edited[index].description

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_groups_from_detail(self, appliance, groups, method):
        """Tests deleting groups from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for group in groups:
            group.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                group.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_groups_from_collection(self, appliance, groups):
        """Tests deleting groups from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.groups.action.delete(*groups)
        assert appliance.rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.groups.action.delete(*groups)
        assert appliance.rest_api.response.status_code == 404


class TestUsersViaREST(object):
    @pytest.fixture(scope="function")
    def users(self, request, appliance):
        num_users = 3
        response = _users(request, appliance.rest_api, num=num_users)
        assert appliance.rest_api.response.status_code == 200
        assert len(response) == 3
        return response

    @pytest.fixture(scope='function')
    def user_auth(self, request, appliance):
        password = fauxfactory.gen_alphanumeric()
        data = [{
            "userid": "rest_{}".format(fauxfactory.gen_alphanumeric(3).lower()),
            "name": "REST User {}".format(fauxfactory.gen_alphanumeric()),
            "password": password,
            "email": "user@example.com",
            "group": {"description": "EvmGroup-user_self_service"}
        }]

        user = _creating_skeleton(request, appliance.rest_api, 'users', data)[0]
        assert_response(appliance)
        return user.userid, password

    @pytest.mark.tier(3)
    def test_create_users(self, appliance, users):
        """Tests creating users.

        Metadata:
            test_flag: rest
        """
        for user in users:
            record = appliance.rest_api.collections.users.get(id=user.id)
            assert appliance.rest_api.response.status_code == 200
            assert record.name == user.name

    @pytest.mark.tier(2)
    def test_edit_user_password(self, request, appliance, users):
        """Tests editing user password.

        Metadata:
            test_flag: rest
        """
        request.addfinalizer(appliance.server.login_admin)
        user = users[0]
        new_password = fauxfactory.gen_alphanumeric()
        user.action.edit(password=new_password)
        assert appliance.rest_api.response.status_code == 200
        cred = Credential(principal=user.userid, secret=new_password)
        new_user = User(credential=cred)
        appliance.server.login(new_user)

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
            assert appliance.rest_api.response.status_code == 200
        else:
            edited = []
            for index in range(users_len):
                edited.append(users[index].action.edit(**new[index]))
                assert appliance.rest_api.response.status_code == 200
        assert users_len == len(edited)
        for index in range(users_len):
            record, _ = wait_for(
                lambda: collection.find_by(name=new[index]['name']) or False,
                num_sec=180,
                delay=10,
            )
            assert record[0].id == edited[index].id
            assert record[0].name == edited[index].name

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
        status = 204 if method == "delete" else 200
        for user in users:
            user.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                user.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_users_from_collection(self, appliance, users):
        """Tests deleting users from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.users.action.delete(*users)
        assert appliance.rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.users.action.delete(*users)
        assert appliance.rest_api.response.status_code == 404

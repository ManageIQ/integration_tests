# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.credential import Credential
from cfme import test_requirements
from cfme.configure.access_control import User
from cfme.login import login, login_admin
from cfme.rest.gen_data import groups as _groups
from cfme.rest.gen_data import roles as _roles
from cfme.rest.gen_data import tenants as _tenants
from cfme.rest.gen_data import users as _users
from utils.wait import wait_for
from utils import error


pytestmark = [
    test_requirements.auth
]


class TestTenantsViaREST(object):
    @pytest.fixture(scope="function")
    def tenants(self, request, rest_api):
        num_tenants = 3
        response = _tenants(request, rest_api, num=num_tenants)
        assert rest_api.response.status_code == 200
        assert len(response) == num_tenants
        return response

    @pytest.mark.tier(3)
    def test_create_tenants(self, rest_api, tenants):
        """Tests creating tenants.

        Metadata:
            test_flag: rest
        """
        for tenant in tenants:
            record = rest_api.collections.tenants.get(id=tenant.id)
            assert rest_api.response.status_code == 200
            assert record.name == tenant.name

    @pytest.mark.tier(2)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_tenants(self, rest_api, tenants, multiple):
        """Tests editing tenants.

        Metadata:
            test_flag: rest
        """
        if multiple:
            new_names = []
            tenants_data_edited = []
            for tenant in tenants:
                new_name = "test_tenants_{}".format(fauxfactory.gen_alphanumeric().lower())
                new_names.append(new_name)
                tenant.reload()
                tenants_data_edited.append({
                    "href": tenant.href,
                    "name": new_name,
                })
            rest_api.collections.tenants.action.edit(*tenants_data_edited)
            assert rest_api.response.status_code == 200
            for new_name in new_names:
                wait_for(
                    lambda: rest_api.collections.tenants.find_by(name=new_name),
                    num_sec=180,
                    delay=10,
                )
        else:
            tenant = rest_api.collections.tenants.get(name=tenants[0].name)
            new_name = "test_tenant_{}".format(fauxfactory.gen_alphanumeric().lower())
            tenant.action.edit(name=new_name)
            assert rest_api.response.status_code == 200
            wait_for(
                lambda: rest_api.collections.tenants.find_by(name=new_name),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_tenants_from_detail(self, rest_api, tenants, method):
        """Tests deleting tenants from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for tenant in tenants:
            tenant.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                tenant.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_tenants_from_collection(self, rest_api, tenants):
        """Tests deleting tenants from collection.

        Metadata:
            test_flag: rest
        """
        rest_api.collections.tenants.action.delete(*tenants)
        assert rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.tenants.action.delete(*tenants)
        assert rest_api.response.status_code == 404


class TestRolesViaREST(object):
    @pytest.fixture(scope="function")
    def roles(self, request, rest_api):
        num_roles = 3
        response = _roles(request, rest_api, num=num_roles)
        assert rest_api.response.status_code == 200
        assert len(response) == num_roles
        return response

    @pytest.mark.tier(3)
    def test_create_roles(self, rest_api, roles):
        """Tests creating roles.

        Metadata:
            test_flag: rest
        """
        for role in roles:
            record = rest_api.collections.roles.get(id=role.id)
            assert rest_api.response.status_code == 200
            assert record.name == role.name

    @pytest.mark.tier(2)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_roles(self, rest_api, roles, multiple):
        """Tests editing roles.

        Metadata:
            test_flag: rest
        """
        if multiple:
            new_names = []
            roles_data_edited = []
            for role in roles:
                new_name = "role_name_{}".format(fauxfactory.gen_alphanumeric())
                new_names.append(new_name)
                role.reload()
                roles_data_edited.append({
                    "href": role.href,
                    "name": new_name,
                })
            rest_api.collections.roles.action.edit(*roles_data_edited)
            assert rest_api.response.status_code == 200
            for new_name in new_names:
                wait_for(
                    lambda: rest_api.collections.roles.find_by(name=new_name),
                    num_sec=180,
                    delay=10,
                )
        else:
            role = rest_api.collections.roles.get(name=roles[0].name)
            new_name = "role_name_{}".format(fauxfactory.gen_alphanumeric())
            role.action.edit(name=new_name)
            assert rest_api.response.status_code == 200
            wait_for(
                lambda: rest_api.collections.roles.find_by(name=new_name),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_roles_from_detail(self, rest_api, roles, method):
        """Tests deleting roles from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for role in roles:
            role.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                role.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_roles_from_collection(self, rest_api, roles):
        """Tests deleting roles from collection.

        Metadata:
            test_flag: rest
        """
        rest_api.collections.roles.action.delete(*roles)
        assert rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.roles.action.delete(*roles)
        assert rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_add_delete_role(self, rest_api):
        """Tests adding role using "add" action and deleting it.

        Metadata:
            test_flag: rest
        """
        role_data = {"name": "role_name_{}".format(format(fauxfactory.gen_alphanumeric()))}
        role = rest_api.collections.roles.action.add(role_data)[0]
        assert rest_api.response.status_code == 200
        assert role.name == role_data["name"]
        wait_for(
            lambda: rest_api.collections.roles.find_by(name=role.name),
            num_sec=180,
            delay=10,
        )
        found_role = rest_api.collections.roles.get(name=role.name)
        assert found_role.name == role_data["name"]
        role.action.delete()
        assert rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            role.action.delete()
        assert rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_role_assign_and_unassign_feature(self, rest_api, roles):
        """Tests assigning and unassigning feature to a role.

        Metadata:
            test_flag: rest
        """
        feature = rest_api.collections.features.get(name="Everything")
        role = roles[0]
        role.reload()
        role.features.action.assign(feature)
        assert rest_api.response.status_code == 200
        role.reload()
        # This verification works because the created roles don't have assigned features
        assert feature.id in [f.id for f in role.features.all]
        role.features.action.unassign(feature)
        assert rest_api.response.status_code == 200
        role.reload()
        assert feature.id not in [f.id for f in role.features.all]


class TestGroupsViaREST(object):
    @pytest.fixture(scope="function")
    def tenants(self, request, rest_api):
        return _tenants(request, rest_api, num=1)

    @pytest.fixture(scope="function")
    def roles(self, request, rest_api):
        return _roles(request, rest_api, num=1)

    @pytest.fixture(scope="function")
    def groups(self, request, rest_api, roles, tenants):
        num_groups = 3
        response = _groups(request, rest_api, roles, tenants, num=num_groups)
        assert rest_api.response.status_code == 200
        assert len(response) == num_groups
        return response

    @pytest.mark.tier(3)
    def test_create_groups(self, rest_api, groups):
        """Tests creating groups.

        Metadata:
            test_flag: rest
        """
        for group in groups:
            record = rest_api.collections.groups.get(id=group.id)
            assert rest_api.response.status_code == 200
            assert record.description == group.description

    @pytest.mark.tier(2)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_groups(self, rest_api, groups, multiple):
        """Tests editing groups.

        Metadata:
            test_flag: rest
        """
        if multiple:
            new_descriptions = []
            groups_data_edited = []
            for group in groups:
                new_description = "group_descripton_{}".format(fauxfactory.gen_alphanumeric())
                new_descriptions.append(new_description)
                group.reload()
                groups_data_edited.append({
                    "href": group.href,
                    "description": new_description,
                })
            rest_api.collections.groups.action.edit(*groups_data_edited)
            assert rest_api.response.status_code == 200
            for description in new_descriptions:
                wait_for(
                    lambda: rest_api.collections.groups.find_by(description=description),
                    num_sec=180,
                    delay=10,
                )
        else:
            group = rest_api.collections.groups.get(description=groups[0].description)
            new_description = "group_description_{}".format(fauxfactory.gen_alphanumeric())
            group.action.edit(description=new_description)
            assert rest_api.response.status_code == 200
            wait_for(
                lambda: rest_api.collections.groups.find_by(description=new_description),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_groups_from_detail(self, rest_api, groups, method):
        """Tests deleting groups from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for group in groups:
            group.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                group.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_groups_from_collection(self, rest_api, groups):
        """Tests deleting groups from collection.

        Metadata:
            test_flag: rest
        """
        rest_api.collections.groups.action.delete(*groups)
        assert rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.groups.action.delete(*groups)
        assert rest_api.response.status_code == 404


class TestUsersViaREST(object):
    @pytest.fixture(scope="function")
    def users(self, request, rest_api):
        num_users = 3
        response = _users(request, rest_api, num=num_users)
        assert rest_api.response.status_code == 200
        assert len(response) == 3
        return response

    @pytest.mark.tier(3)
    def test_create_users(self, rest_api, users):
        """Tests creating users.

        Metadata:
            test_flag: rest
        """
        for user in users:
            record = rest_api.collections.users.get(id=user.id)
            assert rest_api.response.status_code == 200
            assert record.name == user.name

    @pytest.mark.tier(2)
    def test_edit_user_password(self, request, rest_api, users):
        """Tests editing user password.

        Metadata:
            test_flag: rest
        """
        request.addfinalizer(login_admin)
        user = users[0]
        new_password = fauxfactory.gen_alphanumeric()
        user.action.edit(password=new_password)
        assert rest_api.response.status_code == 200
        cred = Credential(principal=user.userid, secret=new_password)
        new_user = User(credential=cred)
        login(new_user)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_user_name(self, rest_api, users, multiple):
        """Tests editing user name.

        Metadata:
            test_flag: rest
        """
        if multiple:
            new_names = []
            users_data_edited = []
            for user in users:
                new_name = "user_name_{}".format(fauxfactory.gen_alphanumeric())
                new_names.append(new_name)
                user.reload()
                users_data_edited.append({
                    "href": user.href,
                    "name": new_name,
                })
            rest_api.collections.users.action.edit(*users_data_edited)
            assert rest_api.response.status_code == 200
            for new_name in new_names:
                wait_for(
                    lambda: rest_api.collections.users.find_by(name=new_name),
                    num_sec=180,
                    delay=10,
                )
        else:
            user = users[0]
            new_name = 'user_{}'.format(fauxfactory.gen_alphanumeric())
            user.action.edit(name=new_name)
            assert rest_api.response.status_code == 200
            wait_for(
                lambda: rest_api.collections.users.find_by(name=new_name),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_users_from_detail(self, rest_api, users, method):
        """Tests deleting users from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for user in users:
            user.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                user.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_users_from_collection(self, rest_api, users):
        """Tests deleting users from collection.

        Metadata:
            test_flag: rest
        """
        rest_api.collections.users.action.delete(*users)
        assert rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.users.action.delete(*users)
        assert rest_api.response.status_code == 404

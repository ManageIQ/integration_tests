# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import fauxfactory
import pytest

from cfme import Credential
from cfme.configure.access_control import User
from cfme.login import login
from cfme.rest import groups as _groups
from cfme.rest import roles as _roles
from cfme.rest import tenants as _tenants
from cfme.rest import users as _users
from utils.wait import wait_for
from utils import error

pytestmark = [pytest.mark.ignore_stream("5.4")]


class TestTenantsViaREST(object):
    @pytest.fixture(scope="function")
    def tenants(self, request, rest_api):
        return _tenants(request, rest_api, num=3)

    @pytest.mark.tier(2)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_tenants(self, rest_api, tenants, multiple):
        if multiple:
            new_names = []
            tenants_data_edited = []
            for tenant in tenants:
                new_name = fauxfactory.gen_alphanumeric().lower()
                new_names.append(new_name)
                tenant.reload()
                tenants_data_edited.append({
                    "href": tenant.href,
                    "name": "test_tenants_{}".format(new_name),
                })
            rest_api.collections.tenants.action.edit(*tenants_data_edited)
            for new_name in new_names:
                wait_for(
                    lambda: rest_api.collections.tenants.find_by(name=new_name),
                    num_sec=180,
                    delay=10,
                )
        else:
            tenant = rest_api.collections.tenants.get(name=tenants[0].name)
            new_name = 'test_tenant_{}'.format(fauxfactory.gen_alphanumeric().lower())
            tenant.action.edit(name=new_name)
            wait_for(
                lambda: rest_api.collections.tenants.find_by(name=new_name),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_delete_tenants(self, rest_api, tenants, multiple):
        if multiple:
            rest_api.collections.tenants.action.delete(*tenants)
            with error.expected("ActiveRecord::RecordNotFound"):
                rest_api.collections.tenants.action.delete(*tenants)
        else:
            tenant = tenants[0]
            tenant.action.delete()
            with error.expected("ActiveRecord::RecordNotFound"):
                tenant.action.delete()


class TestRolesViaREST(object):
    @pytest.fixture(scope="function")
    def roles(self, request, rest_api):
        return _roles(request, rest_api, num=3)

    @pytest.mark.tier(2)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_roles(self, rest_api, roles, multiple):
        if "edit" not in rest_api.collections.roles.action.all:
            pytest.skip("Edit roles action is not implemented in this version")

        if multiple:
            new_names = []
            roles_data_edited = []
            for role in roles:
                new_name = fauxfactory.gen_alphanumeric()
                new_names.append(new_name)
                role.reload()
                roles_data_edited.append({
                    "href": role.href,
                    "name": "role_name_{}".format(new_name),
                })
            rest_api.collections.roles.action.edit(*roles_data_edited)
            for new_name in new_names:
                wait_for(
                    lambda: rest_api.collections.roles.find_by(name=new_name),
                    num_sec=180,
                    delay=10,
                )
        else:
            role = rest_api.collections.roles.get(name=roles[0].name)
            new_name = 'role_name_{}'.format(fauxfactory.gen_alphanumeric())
            role.action.edit(name=new_name)
            wait_for(
                lambda: rest_api.collections.roles.find_by(name=new_name),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(3)
    def test_delete_roles(self, rest_api, roles):
        if "delete" not in rest_api.collections.roles.action.all:
            pytest.skip("Delete roles action is not implemented in this version")

        rest_api.collections.roles.action.delete(*roles)
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.roles.action.delete(*roles)

    @pytest.mark.tier(3)
    def test_add_delete_role(self, rest_api):
        if "add" not in rest_api.collections.roles.action.all:
            pytest.skip("Add roles action is not implemented in this version")

        role_data = {"name": "role_name_{}".format(format(fauxfactory.gen_alphanumeric()))}
        role = rest_api.collections.roles.action.add(role_data)[0]
        wait_for(
            lambda: rest_api.collections.roles.find_by(name=role.name),
            num_sec=180,
            delay=10,
        )
        role.action.delete()
        with error.expected("ActiveRecord::RecordNotFound"):
            role.action.delete()

    @pytest.mark.tier(3)
    def test_role_assign_and_unassign_feature(self, rest_api, roles):
        feature = rest_api.collections.features.get(name="Everything")
        role = roles[0]
        role.reload()
        role.features.action.assign(feature)
        role.reload()
        # This verification works because the created roles don't have assigned features
        assert feature.id in [f.id for f in role.features.all]
        role.features.action.unassign(feature)
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
        return _groups(request, rest_api, roles, tenants, num=3)

    @pytest.mark.tier(2)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_groups(self, rest_api, groups, multiple):
        if multiple:
            new_names = []
            groups_data_edited = []
            for group in groups:
                new_name = fauxfactory.gen_alphanumeric()
                new_names.append(new_name)
                group.reload()
                groups_data_edited.append({
                    "href": group.href,
                    "description": "group_descripton_{}".format(new_name),
                })
            rest_api.collections.groups.action.edit(*groups_data_edited)
            for new_name in new_names:
                wait_for(
                    lambda: rest_api.collections.groups.find_by(description=new_name),
                    num_sec=180,
                    delay=10,
                )
        else:
            group = rest_api.collections.groups.get(description=groups[0].description)
            new_name = 'group_description_{}'.format(fauxfactory.gen_alphanumeric())
            group.action.edit(description=new_name)
            wait_for(
                lambda: rest_api.collections.groups.find_by(description=new_name),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_delete_groups(self, rest_api, groups, multiple):
        if multiple:
            rest_api.collections.groups.action.delete(*groups)
            with error.expected("ActiveRecord::RecordNotFound"):
                rest_api.collections.groups.action.delete(*groups)
        else:
            group = groups[0]
            group.action.delete()
            with error.expected("ActiveRecord::RecordNotFound"):
                group.action.delete()


class TestUsersViaREST(object):
    @pytest.fixture(scope="function")
    def users(self, request, rest_api):
        return _users(request, rest_api, num=3)

    @pytest.mark.tier(2)
    def test_edit_user_password(self, rest_api, users):
        if "edit" not in rest_api.collections.users.action.all:
            pytest.skip("Edit action for users is not implemented in this version")
        user = users[0]
        new_password = fauxfactory.gen_alphanumeric()
        user.action.edit(password=new_password)
        cred = Credential(principal=user.userid, secret=new_password)
        new_user = User(credential=cred)
        login(new_user)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_edit_user_name(self, rest_api, users, multiple):
        if "edit" not in rest_api.collections.users.action.all:
            pytest.skip("Edit action for users is not implemented in this version")
        if multiple:
            new_names = []
            users_data_edited = []
            for user in users:
                new_name = fauxfactory.gen_alphanumeric()
                new_names.append(new_name)
                user.reload()
                users_data_edited.append({
                    "href": user.href,
                    "name": "user_name_{}".format(new_name),
                })
            rest_api.collections.users.action.edit(*users_data_edited)
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
            wait_for(
                lambda: rest_api.collections.users.find_by(name=new_name),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("multiple", [False, True], ids=["one_request", "multiple_requests"])
    def test_delete_user(self, rest_api, users, multiple):
        if multiple:
            rest_api.collections.users.action.delete(*users)
            with error.expected("ActiveRecord::RecordNotFound"):
                rest_api.collections.users.action.delete(*users)
        else:
            user = users[0]
            user.action.delete()
            with error.expected("ActiveRecord::RecordNotFound"):
                user.action.delete()

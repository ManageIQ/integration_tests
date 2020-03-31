import fauxfactory
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import groups as _groups
from cfme.rest.gen_data import roles as _roles
from cfme.rest.gen_data import tenants as _tenants
from cfme.rest.gen_data import users as _users
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.rest import query_resource_attributes
from cfme.utils.wait import wait_for

pytestmark = [test_requirements.rest]


class TestTenantsViaREST:
    @pytest.fixture(scope="function")
    def tenants(self, request, appliance):
        num_tenants = 3
        response = _tenants(request, appliance, num=num_tenants)
        assert_response(appliance)
        assert len(response) == num_tenants
        return response

    @pytest.mark.tier(3)
    def test_query_tenant_attributes(self, tenants, soft_assert):
        """Tests access to tenant attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: medium
            initialEstimate: 1/4h
        """
        query_resource_attributes(tenants[0], soft_assert=soft_assert)

    @pytest.mark.tier(3)
    def test_create_tenants(self, appliance, tenants):
        """Tests creating tenants.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        for tenant in tenants:
            record = appliance.rest_api.collections.tenants.get(id=tenant.id)
            assert_response(appliance)
            assert record.name == tenant.name

    @pytest.mark.tier(2)
    @pytest.mark.parametrize(
        "multiple", [False, True], ids=["one_request", "multiple_requests"]
    )
    def test_edit_tenants(self, appliance, tenants, multiple):
        """Tests editing tenants.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/3h
        """
        collection = appliance.rest_api.collections.tenants
        tenants_len = len(tenants)
        new = []
        for _ in range(tenants_len):
            new.append(
                {
                    "name": "test_tenants_{}".format(
                        fauxfactory.gen_alphanumeric().lower()
                    )
                }
            )
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
                lambda: collection.find_by(name=new[index]["name"]) or False,
                num_sec=180,
                delay=10,
            )
            tenant.reload()
            assert record[0].id == edited[index].id == tenant.id
            assert record[0].name == edited[index].name == tenant.name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_tenants_from_detail(self, tenants, method):
        """Tests deleting tenants from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(tenants, method=method)

    @pytest.mark.tier(3)
    def test_delete_tenants_from_collection(self, tenants):
        """Tests deleting tenants from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(tenants)


class TestRolesViaREST:
    @pytest.fixture(scope="function")
    def roles(self, request, appliance):
        num_roles = 3
        response = _roles(request, appliance, num=num_roles)
        assert_response(appliance)
        assert len(response) == num_roles
        return response

    @pytest.mark.tier(3)
    def test_query_role_attributes(self, roles, soft_assert):
        """Tests access to role attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        query_resource_attributes(roles[0], soft_assert=soft_assert)

    @pytest.mark.tier(3)
    def test_create_roles(self, appliance, roles):
        """Tests creating roles.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        for role in roles:
            record = appliance.rest_api.collections.roles.get(id=role.id)
            assert_response(appliance)
            assert record.name == role.name

    @pytest.mark.tier(2)
    @pytest.mark.parametrize(
        "multiple", [False, True], ids=["one_request", "multiple_requests"]
    )
    def test_edit_roles(self, appliance, roles, multiple):
        """Tests editing roles.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/3h
        """
        collection = appliance.rest_api.collections.roles
        roles_len = len(roles)
        new = []
        for _ in range(roles_len):
            new.append({"name": fauxfactory.gen_alphanumeric(15, start="test_role_")})
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
                lambda: collection.find_by(name=new[index]["name"]) or False,
                num_sec=180,
                delay=10,
            )
            role.reload()
            assert record[0].id == edited[index].id == role.id
            assert record[0].name == edited[index].name == role.name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_roles_from_detail(self, roles, method):
        """Tests deleting roles from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(roles, method=method)

    @pytest.mark.tier(3)
    def test_delete_roles_from_collection(self, roles):
        """Tests deleting roles from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(roles)

    @pytest.mark.tier(3)
    def test_add_delete_role(self, appliance):
        """Tests adding role using "add" action and deleting it.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/3h
        """
        role_data = {"name": fauxfactory.gen_alphanumeric(15, start="role_name_")}
        role = appliance.rest_api.collections.roles.action.add(role_data)[0]
        assert_response(appliance)
        assert role.name == role_data["name"]
        wait_for(
            lambda: appliance.rest_api.collections.roles.find_by(name=role.name)
            or False,
            num_sec=180,
            delay=10,
        )
        found_role = appliance.rest_api.collections.roles.get(name=role.name)
        assert found_role.name == role_data["name"]
        role.action.delete()
        assert_response(appliance)
        with pytest.raises(Exception, match="ActiveRecord::RecordNotFound"):
            role.action.delete()
        assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    def test_role_assign_and_unassign_feature(self, appliance, roles):
        """Tests assigning and unassigning feature to a role.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/3h
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


class TestGroupsViaREST:
    @pytest.fixture(scope="function")
    def tenants(self, request, appliance):
        return _tenants(request, appliance, num=1)

    @pytest.fixture(scope="function")
    def roles(self, request, appliance):
        return _roles(request, appliance, num=1)

    @pytest.fixture(scope="function")
    def groups(self, request, appliance, roles, tenants):
        num_groups = 3
        response = _groups(request, appliance, roles, num=num_groups, tenant=tenants)
        assert_response(appliance)
        assert len(response) == num_groups
        return response

    @pytest.mark.tier(3)
    def test_query_group_attributes(self, groups, soft_assert):
        """Tests access to group attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        query_resource_attributes(groups[0], soft_assert=soft_assert)

    @pytest.mark.tier(3)
    def test_create_groups(self, appliance, groups):
        """Tests creating groups.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        for group in groups:
            record = appliance.rest_api.collections.groups.get(id=group.id)
            assert_response(appliance)
            assert record.description == group.description

    @pytest.mark.tier(2)
    @pytest.mark.parametrize(
        "multiple", [False, True], ids=["one_request", "multiple_requests"]
    )
    def test_edit_groups(self, appliance, groups, multiple):
        """Tests editing groups.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/3h
        """
        collection = appliance.rest_api.collections.groups
        groups_len = len(groups)
        new = []
        for _ in range(groups_len):
            new.append(
                {
                    "description": "group_description_{}".format(
                        fauxfactory.gen_alphanumeric()
                    )
                }
            )
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
                lambda: collection.find_by(description=new[index]["description"])
                or False,
                num_sec=180,
                delay=10,
            )
            group.reload()
            assert record[0].id == edited[index].id == group.id
            assert (
                record[0].description == edited[index].description == group.description
            )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_groups_from_detail(self, groups, method):
        """Tests deleting groups from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(groups, method=method)

    @pytest.mark.tier(3)
    def test_delete_groups_from_collection(self, groups):
        """Tests deleting groups from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(groups, not_found=True)


class TestUsersViaREST:
    @pytest.fixture(scope="function")
    def users_data(self, request, appliance):
        def _users_data(num=3):
            num_users = num
            response, prov_data = _users(request, appliance, num=num_users)
            assert_response(appliance)
            assert len(response) == num
            return response, prov_data
        return _users_data

    @pytest.fixture(scope="function")
    def user_auth(self, users_data):
        users, prov_data = users_data(num=1)
        return users[0].userid, prov_data[0]["password"]

    @pytest.fixture(scope="function")
    def users(self, users_data):
        users, __ = users_data()
        return users

    @pytest.mark.tier(3)
    def test_query_user_attributes(self, users, soft_assert):
        """Tests access to user attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        query_resource_attributes(users[0], soft_assert=soft_assert)

    @pytest.mark.tier(3)
    def test_create_users(self, appliance, users_data):
        """Tests creating users.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        users, prov_data = users_data()
        for index, user in enumerate(users):
            record = appliance.rest_api.collections.users.get(id=user.id)
            assert_response(appliance)
            assert record.name == user.name
            user_auth = (user.userid, prov_data[index]["password"])
            assert appliance.new_rest_api_instance(auth=user_auth)

    @pytest.mark.tier(3)
    def test_create_uppercase_user(self, request, appliance):
        """Tests creating user with userid containing uppercase letters.

        Bugzilla:
            1486041

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        uniq = fauxfactory.gen_alphanumeric(4).upper()
        data = {
            "userid": f"rest_{uniq}",
            "name": f"REST User {uniq}",
            "password": fauxfactory.gen_alphanumeric(),
            "email": "user@example.com",
            "group": "EvmGroup-user_self_service",
        }
        user, _ = _users(request, appliance, **data)
        assert_response(appliance)
        user_auth = (user[0].userid, data["password"])
        assert appliance.new_rest_api_instance(auth=user_auth)

    @pytest.mark.tier(2)
    def test_edit_user_password(self, appliance, users):
        """Tests editing user password.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/3h
        """
        user = users[0]
        new_password = fauxfactory.gen_alphanumeric()
        user.action.edit(password=new_password)
        assert_response(appliance)
        new_user_auth = (user.userid, new_password)
        assert appliance.new_rest_api_instance(auth=new_user_auth)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "multiple", [False, True], ids=["one_request", "multiple_requests"]
    )
    def test_edit_user_name(self, appliance, users, multiple):
        """Tests editing user name.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/3h
        """
        collection = appliance.rest_api.collections.users
        users_len = len(users)
        new = []
        for _ in range(users_len):
            new.append({"name": fauxfactory.gen_alphanumeric(15, "user_name_")})
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
                lambda: collection.find_by(name=new[index]["name"]) or False,
                num_sec=180,
                delay=10,
            )
            user.reload()
            assert record[0].id == edited[index].id == user.id
            assert record[0].name == edited[index].name == user.name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("group_by", ["id", "href", "description"])
    def test_edit_user_groups(self, appliance, users, group_by):
        """Tests editing user group.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        group_descriptions = ["EvmGroup-user_limited_self_service", "EvmGroup-approver"]
        groups = [
            appliance.rest_api.collections.groups.get(description=desc)
            for desc in group_descriptions
        ]
        group_handles = [{"href": groups[0].href}]
        for group in groups[1:]:
            if group_by == "id":
                group_handle = {"id": group.id}
            elif group_by == "href":
                group_handle = {"href": group.href}
            elif group_by == "description":
                group_handle = {"description": group.description}
            group_handles.append(group_handle)

        users_len = len(users)
        new = []
        for _ in range(users_len):
            new.append({"miq_groups": group_handles})
        edited = []
        for index in range(users_len):
            edited.append(users[index].action.edit(**new[index]))
            assert_response(appliance)
        assert users_len == len(edited)

        def _updated(user):
            user.reload(attributes="miq_groups")
            descs = []
            for group in user.miq_groups:
                descs.append(group["description"])
            return all(desc in descs for desc in group_descriptions)

        for index, user in enumerate(users):
            wait_for(lambda: _updated(user), num_sec=20, delay=2)
            user.reload()
            assert edited[index].id == user.id

    @pytest.mark.tier(3)
    def test_edit_current_group(self, request, appliance, users_data):
        """Tests that editing current group using "edit" action is not supported.

        Testing BZ 1549086

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        group_descriptions = ["EvmGroup-user_limited_self_service", "EvmGroup-approver"]
        groups = [
            appliance.rest_api.collections.groups.get(description=desc)
            for desc in group_descriptions
        ]
        group_handles = [{"href": group.href} for group in groups]
        users, __ = users_data(num=1)
        user = users[0]
        user.action.edit(miq_groups=group_handles)
        assert_response(appliance)
        user.reload()
        assert user.current_group.id == groups[0].id
        with pytest.raises(Exception, match="BadRequestError: Invalid attribute"):
            user.action.edit(current_group=group_handles[1])
        assert_response(appliance, http_status=400)

    @pytest.mark.tier(3)
    def test_change_current_group_as_admin(self, request, appliance, users_data):
        """Tests that it's possible to edit current group.

        Testing BZ 1549086

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        group_descriptions = ["EvmGroup-user_limited_self_service", "EvmGroup-approver"]
        groups = [
            appliance.rest_api.collections.groups.get(description=desc)
            for desc in group_descriptions
        ]
        group_handles = [{"href": group.href} for group in groups]
        users, __ = users_data(num=1)
        user = users[0]
        user.action.edit(miq_groups=group_handles)
        assert_response(appliance)
        user.reload()
        assert user.current_group.id == groups[0].id
        with pytest.raises(
            Exception, match="Can only edit authenticated user's current group"
        ):
            user.action.set_current_group(current_group=group_handles[1])
        assert_response(appliance, http_status=400)

    @pytest.mark.tier(3)
    def test_change_current_group_as_user(self, request, appliance, users_data):
        """Tests that users can update their own group.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: medium
            initialEstimate: 1/4h
        """
        group_descriptions = ["EvmGroup-user_limited_self_service", "EvmGroup-approver"]
        groups = [
            appliance.rest_api.collections.groups.get(description=desc)
            for desc in group_descriptions
        ]
        group_handles = [{"href": group.href} for group in groups]
        users, data = users_data(num=1)
        user = users[0]
        user.action.edit(miq_groups=group_handles)
        assert_response(appliance)
        user.reload()
        assert user.current_group.id == groups[0].id
        user_auth = (user.userid, data[0]["password"])
        user_api = appliance.new_rest_api_instance(auth=user_auth)
        user_api.post(
            user.href, action="set_current_group", current_group=group_handles[1]
        )
        assert_response(user_api)

    @pytest.mark.tier(3)
    def test_change_unassigned_group_as_user(self, request, appliance, users_data):
        """Tests that users can't update their own group to a group they don't belong to.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: medium
            initialEstimate: 1/4h
        """
        group_descriptions = ["EvmGroup-user_limited_self_service", "EvmGroup-approver"]
        groups = [
            appliance.rest_api.collections.groups.get(description=desc)
            for desc in group_descriptions
        ]
        group_handles = [{"href": group.href} for group in groups]
        users, data = users_data(num=1)
        user = users[0]
        user.action.edit(miq_groups=group_handles[:1])
        assert_response(appliance)
        user.reload()
        assert user.current_group.id == groups[0].id
        user_auth = (user.userid, data[0]["password"])
        user_api = appliance.new_rest_api_instance(auth=user_auth)
        with pytest.raises(Exception, match="User must belong to group"):
            user_api.post(
                user.href, action="set_current_group", current_group=group_handles[1]
            )

    @pytest.mark.tier(3)
    def test_change_password_as_user(self, appliance, user_auth):
        """Tests that users can update their own password.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: medium
            initialEstimate: 1/4h
        """
        new_password = fauxfactory.gen_alphanumeric()
        new_user_auth = (user_auth[0], new_password)

        user = appliance.rest_api.collections.users.get(userid=user_auth[0])
        user_api = appliance.new_rest_api_instance(auth=user_auth)
        user_api.post(user.href, action="edit", resource={"password": new_password})
        assert_response(user_api)

        # login using new password
        assert appliance.new_rest_api_instance(auth=new_user_auth)
        # try to login using old password
        with pytest.raises(Exception, match="Authentication failed"):
            appliance.new_rest_api_instance(auth=user_auth)

    @pytest.mark.tier(3)
    def test_change_email_as_user(self, appliance, user_auth):
        """Tests that users can update their own email.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: medium
            initialEstimate: 1/4h
        """
        new_email = "new@example.com"

        user = appliance.rest_api.collections.users.get(userid=user_auth[0])
        user_api = appliance.new_rest_api_instance(auth=user_auth)
        user_api.post(user.href, action="edit", resource={"email": new_email})
        assert_response(user_api)

        user.reload()
        assert user.email == new_email

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_users_from_detail(self, users, method):
        """Tests deleting users from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(users, method=method)

    @pytest.mark.tier(3)
    def test_delete_users_from_collection(self, users):
        """Tests deleting users from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(users)


COMMON_FEATURES = [
    "Services",
    "Compute",
    "Configuration",
    "Networks",
    "Storage",
    "Control",
    "Automation",
    "Monitor",
    "Help",
    "API",
    "Service UI",
]

FEATURES_511 = COMMON_FEATURES + [
    "Overview",
    "Migration",
    "User Settings",
    "All VM and Instance Access Rules",
    "Main Configuration",
]

FEATURES_510 = COMMON_FEATURES + [
    "Cloud Intel",
    "Optimize",
    "Access Rules for all Virtual Machines",
]


@pytest.fixture(params=[True, False], ids=["individual", "everything"])
def create_role(appliance, request):
    if request.param:
        features = FEATURES_511 if appliance.version > "5.11" else FEATURES_510
        product_features = [[["Everything", feature], True] for feature in features]
    else:
        product_features = [[["Everything"], True]]

    role = appliance.collections.roles.create(
        name=fauxfactory.gen_alpha(15, start="API-role-"),
        product_features=[[["Everything"], False]] + product_features,
    )

    yield appliance.rest_api.collections.roles.get(name=role.name)

    role.delete_if_exists()


@pytest.fixture
def role_api(appliance, request, create_role):
    group = _groups(request, appliance, create_role)
    user, user_data = _users(request, appliance, group=group.description)

    yield appliance.new_rest_api_instance(
        entry_point=appliance.rest_api._entry_point,
        auth=(user[0].userid, user_data[0]["password"]),
    )


@pytest.mark.tier(2)
@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1727948, 1731157])
def test_create_picture_with_role(role_api):
    """
    Bugzilla:
        1727948
        1731157

    Polarion:
        assignee: pvala
        caseimportance: high
        casecomponent: Rest
        initialEstimate: 1/4h
        setup:
            1. Create role by
                i. selecting every role individually.
                ii. checking every role by clicking on `Everything`.
            2. Create a group and user with the new role.
        testSteps:
            1. Send a POST request to create a picture and check the response.
        expectedResults:
            1. Picture must be created without any error.
                Check for `Use of Action create is forbidden` in response.
    """
    picture = role_api.collections.pictures.action.create(
        {
            "extension": "png",
            "content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcS"
            "JAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        }
    )[0]
    assert_response(role_api)
    assert picture.exists

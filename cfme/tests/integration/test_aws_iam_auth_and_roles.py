import pytest
from deepdiff import DeepDiff

from cfme import test_requirements
from cfme.roles import role_access_ui_510z
from cfme.roles import role_access_ui_511z
from cfme.utils.appliance import ViaUI
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker


def pytest_generate_tests(metafunc):
    """
    Build a list of tuples containing (group_name, context)
    Returns:
        tuple containing (group_name, context)
        where group_name is a string and context is ViaUI/SSUI
    """
    parameter_list = []
    id_list = []
    # TODO: Include SSUI role_access dict and VIASSUI context
    role_access_ui = VersionPicker(
        {Version.lowest(): role_access_ui_510z, "5.11": role_access_ui_511z}
    ).pick()
    logger.info('Using the role access dict: %s', role_access_ui)
    roles_and_context = [(
        role_access_ui, ViaUI)
    ]
    for role_access, context in roles_and_context:
        for group in role_access.keys():
            parameter_list.append((group, role_access, context))
            id_list.append('{}-{}'.format(group, context))
    metafunc.parametrize('group_name, role_access, context', parameter_list)


@pytest.mark.tier(2)
@pytest.mark.uncollectif(lambda appliance: appliance.is_dev,
                         reason="Test not valid for dev server")
@pytest.mark.meta(automates=[BZ(1530683)])
@pytest.mark.serial
@test_requirements.auth
def test_group_roles(temp_appliance_preconfig_modscope_rhevm, setup_aws_auth_provider, group_name,
                     role_access, context, soft_assert):
    """Basic default AWS_IAM group role auth + RBAC test

    Validates expected menu and submenu names are present for default
    AWS IAM groups

    NOTE: Only tests vertical navigation tree at the moment, not accordions within the page

    Polarion:
        assignee: jdupuy
        caseimportance: medium
        casecomponent: Auth
        initialEstimate: 1/4h
        tags: rbac
    """
    group_access = role_access[group_name]

    try:
        iam_group_name = group_name + '_aws_iam'
        username = credentials[iam_group_name]['username']
        password = credentials[iam_group_name]['password']
        fullname = credentials[iam_group_name]['fullname']
    except KeyError:
        pytest.fail('No match in credentials file for group "{}"'.format(iam_group_name))

    with temp_appliance_preconfig_modscope_rhevm.context.use(context):
        # fullname overrides user.name attribute, but doesn't impact login with username credential
        user = temp_appliance_preconfig_modscope_rhevm.collections.users.simple_user(
            username, password, fullname=fullname
        )
        with user:
            view = navigate_to(temp_appliance_preconfig_modscope_rhevm.server, 'LoggedIn')
            assert temp_appliance_preconfig_modscope_rhevm.server.current_full_name() == user.name
            assert group_name.lower() in [
                name.lower() for name
                in temp_appliance_preconfig_modscope_rhevm.server.group_names()
            ]
            nav_visible = view.navigation.nav_item_tree()

            # RFE BZ 1526495 shows up as an extra requests link in nav
            for area in group_access.keys():
                # using .get() on nav_visibility because it may not have `area` key
                diff = DeepDiff(group_access[area], nav_visible.get(area, {}),
                                verbose_level=0,  # If any higher, will flag string vs unicode
                                ignore_order=True)

                soft_assert(diff == {}, '{g} RBAC mismatch (expected first) for {a}: {d}'
                                        .format(g=group_name, a=area, d=diff))

        temp_appliance_preconfig_modscope_rhevm.server.login_admin()
        assert user.exists

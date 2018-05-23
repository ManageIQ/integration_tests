import pytest
from deepdiff import DeepDiff

from cfme.roles import role_access_ui_58z, role_access_ui_59z, role_access_ssui
from cfme.utils.appliance import ViaUI, find_appliance
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.log import logger


def pytest_generate_tests(metafunc):
    """
    Build a list of tuples containing (group_name, context)
    Returns:
        tuple containing (group_name, context)
        where group_name is a string and context is ViaUI/SSUI
    """
    appliance = find_appliance(metafunc)
    parameter_list = []
    # TODO: Include SSUI role_access dict and VIASSUI context
    roles_and_context = [(
        role_access_ui_59z if appliance.version >= '5.9' else role_access_ui_58z, ViaUI)
    ]
    for group_dict, context in roles_and_context:
        parameter_list.extend([(group, context) for group in group_dict.keys()])
    metafunc.parametrize('group_name, context', parameter_list)


@pytest.mark.tier(2)
@pytest.mark.uncollectif(lambda appliance: appliance.is_dev, reason="Is a rails server")
@pytest.mark.meta(blockers=[
    BZ(1530683,
       unblock=lambda group_name: group_name not in
       ['evmgroup-user', 'evmgroup-approver', 'evmgroup-auditor', 'evmgroup-operator',
        'evmgroup-support', 'evmgroup-security'])
])
def test_group_roles(appliance, setup_aws_auth_provider, group_name, context, soft_assert):
    """Basic default AWS_IAM group role auth + RBAC test

    Validates expected menu and submenu names are present for default
    AWS IAM groups

    NOTE: Only tests vertical navigation tree at the moment, not accordions within the page

    Polarion:
        assignee: llasmith
        casecomponent: config
        initialEstimate: 1/4h
        testtype: integration
    """
    if context.__name__ == 'ViaUI':
        role_dict = role_access_ui_59z if appliance.version >= '5.9' else role_access_ui_58z
    else:
        role_dict = role_access_ssui
    group_access = role_dict[group_name]

    try:
        iam_group_name = group_name + '_aws_iam'
        username = credentials[iam_group_name]['username']
        password = credentials[iam_group_name]['password']
        fullname = credentials[iam_group_name]['fullname']
    except KeyError:
        pytest.fail('No match in credentials file for group "{}"'.format(iam_group_name))

    with appliance.context.use(context):
        # fullname overrides user.name attribute, but doesn't impact login with username credential
        user = appliance.collections.users.simple_user(username, password, fullname=fullname)
        with user:
            view = navigate_to(appliance.server, 'LoggedIn', wait_for_view=True)
            assert appliance.server.current_full_name() == user.name
            assert group_name.lower() in [name.lower() for name in appliance.server.group_names()]
            nav_visible = view.navigation.nav_item_tree()

            # RFE BZ 1526495 shows up as an extra requests link in nav
            bz = BZ(1526495,
                    forced_streams=['5.8', '5.9'],
                    unblock=lambda group_name: group_name not in
                    ['evmgroup-user', 'evmgroup-approver', 'evmgroup-desktop', 'evmgroup-vm_user',
                     'evmgroup-administrator', 'evmgroup-super_administrator'])
            for area in group_access.keys():
                # using .get() on nav_visibility because it may not have `area` key
                diff = DeepDiff(group_access[area], nav_visible.get(area, {}),
                                verbose_level=0,  # If any higher, will flag string vs unicode
                                ignore_order=True)
                nav_extra = diff.get('iterable_item_added')

                if nav_extra and 'Requests' in nav_extra.values() and bz.blocks:
                    logger.warning('Skipping RBAC verification for group "%s" due to %r',
                                   group_name, bz)
                    continue
                else:
                    soft_assert(diff == {}, '{g} RBAC mismatch for {a}: {d}'
                                            .format(g=group_name, a=area, d=diff))

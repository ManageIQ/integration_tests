import fauxfactory
import pytest


from cfme.control import explorer
from cfme import test_requirements

pytestmark = [
    test_requirements.control
]


CONTROL_POLICIES = [
    explorer.ReplicatorControlPolicy,
]


EVENTS = [
    "Replicator Failed Creating Pod",
    "Replicator Successfully Created Pod"
]

action_name = "Send an E-mail3"
policy_name = "ReplicatorPolicy2"


@pytest.fixture(params=CONTROL_POLICIES, ids=lambda policy_class: policy_class.__name__)
def policy_class(request):
    return request.param


@pytest.yield_fixture(params=CONTROL_POLICIES, ids=lambda policy_class: policy_class.__name__)
def control_policy(request):
    scope = explorer.ReplicatorControlPolicy(
        fauxfactory.gen_alphanumeric(),
        scope="fill_count(Replicator.Pods, >, 1)"

    )
    scope.create()
    yield scope


def test_action_crud(control_policy, request):
    # Create an E-mail action
    action = explorer.Action(
        description=action_name,
        action_type="Send an E-mail",
        action_values={"to": "someone@redhat.com"}
    )
    action.create()
    control_policy.assign_events(*EVENTS)
    action.delete()

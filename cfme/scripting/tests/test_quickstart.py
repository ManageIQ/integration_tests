# using subprocess because its a better docker api
# than the docker-py 1.10 we hard depend on
import subprocess

import pytest

from cfme.utils import path

PYTHON_DEB = 'apt-get -y update && apt-get -y install python3'
PYTHON_RPM = '{cmd} -yq update && {cmd} -yq install python3'
IMAGE_SPEC = [
    ('fedora:28', PYTHON_RPM.format(cmd="dnf")),
    ('fedora:29', PYTHON_RPM.format(cmd="dnf")),
    ('fedora:30', PYTHON_RPM.format(cmd="dnf")),
    ('centos:7', PYTHON_RPM.format(cmd="yum")),
    ('debian:stable', PYTHON_DEB),
    ('ubuntu:16.04', PYTHON_DEB),  # travis python3.7 image
    ('ubuntu:artful', PYTHON_DEB),
    ('ubuntu:bionic', PYTHON_DEB),
]


@pytest.fixture(scope='module')
def check_docker():
    try:
        subprocess.check_call("docker info", shell=True)
    except Exception:
        pytest.xfail('docker missing or missconfigured\n'
                     ' - testing quickstart needs a functional docker cli')


@pytest.fixture
def root_volume():
    return path.project_path


@pytest.fixture(scope='module')
def yamls_volume():
    volume = path.project_path.join('../cfme-qe-yamls')
    if not volume.check(dir=1):
        pytest.xfail('qe yaml data not at the expected location')
    return volume


@pytest.mark.parametrize('image, prepare', IMAGE_SPEC, ids=[x[0] for x in IMAGE_SPEC])
@pytest.mark.parametrize('python',
                         [pytest.param('python3')])
@pytest.mark.long_running
def test_quickstart_run(image, python, prepare, root_volume, yamls_volume, check_docker):
    cmd = ("docker run --rm "
           "--volume {root_volume}:/cfme/cfme_tests "
           "--volume {yamls_volume}:/cfme/cfme-qe-yamls "
           "--tty -w /cfme/cfme_tests "
           "--privileged "
           "-e DEBIAN_FRONTEND=noninteractive "
           "-e CFME_QUICKSTART_DEBUG=1 "
           ""
           "{image} "
           "bash -c '{prepare} && "
           "{python} -m cfme.scripting.quickstart --mk-virtualenv ../test_venv'").format(**locals())
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        pytest.fail(str(e))


@pytest.mark.parametrize("old, new, expected_changes", [
    ({}, {'a': 1}, [('a', 'missing', 1)]),
    ({'a': 0}, {'a': 1}, [('a', 0, 1)]),
    ({'a': 1}, {}, [('a', 1, 'removed')]),
    ({'a': 1}, {'a': 1}, []),
])
def test_quickstart_version_changed(old, new, expected_changes):
    # if we put this import at the top of the module unsupported system won't be able to run the
    # tests
    from cfme.scripting import quickstart
    changes = list(quickstart.version_changes(old, new))
    assert changes == expected_changes

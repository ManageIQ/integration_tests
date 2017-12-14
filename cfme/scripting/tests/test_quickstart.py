# using subprocess because its a better docker api
# than the docker-py 1.10 we hard depend on
import subprocess
from cfme.utils import path
import pytest


IMAGE_SPEC = [
    ('fedora:24', 'python3'),
    ('fedora:25', 'python3'),
    ('fedora:26', 'python3'),
    ('fedora:27', 'python3'),
    pytest.param('centos:7', 'python2', marks=pytest.mark.xfail(
        run=False, reason='bad centos packageset')),
]


@pytest.fixture(autouse=True, scope='module')
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


@pytest.mark.parametrize('image, python', IMAGE_SPEC)
@pytest.mark.long_running
def test_quickstart_run(image, python, root_volume, yamls_volume):
    subprocess.check_call(
        "docker run "
        "--volume {root_volume}:/cfme/cfme_tests "
        "--volume {yamls_volume}:/cfme/cfme-qe-yamls "
        "--tty -w /cfme/cfme_tests "
        ""
        "{image} "
        "bash -c '"
        "{python} -m cfme.scripting.quickstart && "
        "{python} -m cfme.scripting.quickstart'"

        .format(**locals()),
        shell=True)

# using subprocess because its a better docker api
# than the docker-py 1.10 we hard depend on
import subprocess
from cfme.utils import path
import pytest


IMAGE_SPEC = [
    ('fedora:23', 'python3'),
    ('fedora:24', 'python3'),
    ('fedora:25', 'python3'),
    ('centos:7', 'python2'),
]


@pytest.fixture(autouse=True)
def check_docker():
    try:
        subprocess.call("docker info", shell=True)
    except Exception:
        pytest.xfail('docker missing - testing quickstart needs docker')


@pytest.fixture
def root_volume():
    return path.project_path


@pytest.fixture
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

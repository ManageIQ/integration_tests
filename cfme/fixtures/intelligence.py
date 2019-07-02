import os

import pytest

from cfme.utils.conf import cfme_data
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.ftp import FTPException
from cfme.utils.log import logger


@pytest.fixture
def yaml_path(request, yaml_name):
    try:
        fs = FTPClientWrapper(cfme_data.ftpserver.entities.reports)
        file_path = fs.download(yaml_name, os.path.join("/tmp", yaml_name))
    except FTPException:
        logger.exception(
            "FTP download or YAML lookup of %s failed, defaulting to local", yaml_name
        )
    return file_path

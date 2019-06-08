import os
import re

from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.ftp import FTPClient
from cfme.utils.ftp import FTPException


class FileServer(object):
    """
    This class is for remote file management with FTP. It is useful to make a collection of raw
    files related to customer BZ testing directly or indirectly. This will help to easily download
    testing related files in a runtime environment.

    The base directory is `miq` and under that, we have directories as per the automation entities;
    which can be set at initialization.

    Directory Structure:
    /-miq/
        /-Database/
        /-Datastores/
        /-Dialogs/
        /-Others/
        /-Reports/

    Args:
        entity: entity which you want to access like `Datastores`, `Dialogs`, etc.
        entrypoint: FTP server entry point
        host: FTP server host
        user: FTP user
        passwd: FTP password

    Usage:
        .. code-block:: python
          # Entities
          fs = FileServer()
          fs.directories    # list of current available entities
          fs.mkdir("Dialogs")   # create new entity type
          fs.rmd("Dialogs")     # delete created entity type

          fs = FileServer("Dialogs")
          fs.upload("foo.zip") # upload local file
          fs.files  # return list of available file objects
          fs.download("foo.zip") # It will download foo.zip file

          f = fs.get_file("foo.zip")
          f.path  # gives remote file path; can be used to download with 'wget'
          f.download()  # download file
    """

    def __init__(self, entity=None, entrypoint=None, host=None, user=None, passwd=None):
        ftp_data = cfme_data.ftpserver

        self.entity = entity
        self.host = host if host else ftp_data.host
        self.user = user if user else credentials[ftp_data.credentials]["username"]
        self.passwd = passwd if passwd else credentials[ftp_data.credentials]["password"]
        self.entrypoint = entrypoint or ftp_data.entrypoint

        self.client = FTPClient(self.host, self.user, self.passwd, time_diff=False)
        self.cwd = os.path.join(self.entrypoint, "miq", self.entity if entity else "")
        self.client.cwd(self.cwd)

    @property
    def _entities(self):
        result = {"files": [], "dirs": []}

        def _checks(line):
            entity = re.split(r"\s+", line, maxsplit=8)[-1]
            if line.startswith("d"):
                result["dirs"].append(entity)
            else:
                result["files"].append(entity)

        self.client.ftp.dir(_checks)
        return result

    @property
    def files(self):
        """List of FTP file objects"""
        return [File(name=f, client=self) for f in self._entities["files"]]

    def get_file(self, name):
        """
        Arg:
            name: name of remote file
        Returns:
            FTP file object
        """

        if name in self._entities["files"]:
            return File(name=name, client=self)
        else:
            raise FTPException("{} not found".format(name))

    def rm(self, name):
        """ Remove or Delete remote FTP file
        Arg:
            name: name of remote file
        Returns:
            Success of the action
        """
        return self.client.dele(name)

    def upload(self, path, name=None):
        """ Upload FTP file
        Arg:
            path: path of local file
            name: set name of file default it will consider original name of uploading file
        Returns:
            Success of the action
        """

        name = name or os.path.basename(path)
        if name in self._entities["files"]:
            raise FTPException("{} already available in {}".format(name, self.entity))
        with open(path, "rb") as f:
            return self.client.storbinary(name, f)

    def download(self, name, target=None):
        """ Download FTP file
        Arg:
            name: remote file name
            target: local path for download else it will consider current working path
        Returns:
            target path
        """

        target = target if target else os.path.join("/tmp", name)
        if name not in self._entities["files"]:
            raise FTPException("{} not found in {}".format(name, self.entity))

        with open(target, "wb") as output:
            self.client.retrbinary(name, output.write)
            return target

    @property
    def directories(self):
        """ List remote FTP directories"""
        return self._entities["dirs"]

    def mkdir(self, name):
        """ Create remote FTP directory
        Arg:
            name: name of remote directory
        Returns:
            Success of the action
        """
        return self.client.mkd(name)

    def rmd(self, name):
        """ Remove or Delete remote FTP directory
        Arg:
            name: name of remote directory
        Returns:
            Success of the action
        """
        return self.client.rmd(name)


class File(object):
    """FTP Remote files

    Arg:
        name: remote file name
        client: FTP client
    """

    def __init__(self, name, client):
        self.name = name
        self.client = client

    @property
    def path(self):
        """Remote FTP file url"""
        p = os.path.join(self.client.cwd, self.name)
        return p.replace(self.client.entrypoint, self.client.host)

    def download(self, target=None):
        """
        Arg:
            target: local path for download else it will consider current working path
        Returns:
            target path
        """
        return self.client.download(self.name, target)

    def __repr__(self):
        return "<FilesServerFile: {}>".format(self.name)

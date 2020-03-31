""" FTP manipulation library

@author: Milan Falešník <mfalesni@redhat.com>
"""
import ftplib
import os
import re
from datetime import datetime
from io import BytesIO
from time import mktime
from time import strptime

import fauxfactory

from cfme.utils.conf import cfme_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger


try:
    Pattern = re.Pattern
except AttributeError:
    Pattern = re._pattern_type


class FTPException(Exception):
    pass


class FTPDirectory:
    """ FTP FS Directory encapsulation

    This class represents one directory.
    Contains pointers to all child directories (self.directories)
    and also all files in current directory (self.files)

    """
    def __init__(self, client, name, items, parent_dir=None, time=None):
        """ Constructor

        Args:
            client: ftplib.FTP instance
            name: Name of this directory
            items: Content of this directory
            parent_dir: Pointer to a parent directory to maintain hierarchy. None if root
            time: Time of this object
        """
        self.client = client
        self.parent_dir = parent_dir
        self.time = time
        self.name = name
        self.files = []
        self.directories = []
        for item in items:
            if isinstance(item, dict):  # Is a directory
                self.directories.append(FTPDirectory(self.client,
                                                     item["dir"],
                                                     item["content"],
                                                     parent_dir=self,
                                                     time=item["time"]))
            else:
                self.files.append(FTPFile(self.client, item[0], self, item[1]))

    @property
    def path(self):
        """
        Returns:
            whole path for this directory

        """
        return os.path.join(self.parent_dir.path if self.parent_dir else "", self.name)

    def __repr__(self):
        return f"<FTPDirectory {self.path}>"

    def cd(self, path):
        """ Change to a directory

        Changes directory to a path specified by parameter path. There are three special cases:
        / - climbs by self.parent_dir up in the hierarchy until it reaches root element.
        . - does nothing
        .. - climbs one level up in hierarchy, if present, otherwise does the same as preceeding.

        Args:
            path: Path to change

            """
        if path == ".":
            return self
        elif path == "..":
            result = self
            if result.parent_dir:
                result = result.parent_dir
            return result
        elif path == "/":
            result = self
            while result.parent_dir:
                result = result.parent_dir
            return result

        enter = path.strip("/").split("/", 1)
        remainder = None
        if len(enter) == 2:
            enter, remainder = enter
        for item in self.directories:
            if item.name == enter:
                if remainder:
                    return item.cd("/".join(remainder))
                else:
                    return item
        raise FTPException(f"Directory {self.path}{enter} does not exist!")

    def search(self, by, files=True, directories=True):
        """ Recursive search by string or regexp.

        Searches throughout all the filesystem structure from top till the bottom until
        it finds required files or dirctories.
        You can specify either plain string or regexp. String search does classic ``in``,
        regexp matching is done by exact matching (by.match).

        Args:
            by: Search string or regexp
            files: Whether look for files
            directories: Whether look for directories
        Returns:
            List of all objects found in FS

        """

        def _scan(what, in_what):
            if isinstance(what, Pattern):
                return what.match(in_what) is not None
            else:
                return what in in_what

        results = []
        if files:
            for f in self.files:
                if _scan(by, f.name):
                    results.append(f)
        for d in self.directories:
            if directories:
                if _scan(by, d.name):
                    results.append(d)
            results.extend(d.search(by, files=files, directories=directories))
        return results


class FTPFile:
    """ FTP FS File encapsulation

    This class represents one file in the FS hierarchy.
    It encapsulates mainly its position in FS and adds the possibility
    of downloading the file.
    """
    def __init__(self, client, name, parent_dir, time=None):
        """ Constructor

        Args:
            client: ftplib.FTP instance
            name: File name (without path)
            parent_dir: Directory in which this file is (FTPDirectory or path)
            time: Time to match local computer's timezone
        """
        self.client = client
        self.parent_dir = parent_dir
        self.name = name
        self.time = time

    @property
    def path(self):
        """
        Returns:
            whole path for this file

        """
        parent_dir = (
            self.parent_dir.path if isinstance(self.parent_dir, FTPDirectory) else self.parent_dir
        )
        return os.path.join(parent_dir, self.name)

    @property
    def local_time(self):
        """
        Returns:
            time modified to match local computer's time zone

        """
        return self.client.dt + self.time

    def __repr__(self):
        return f"<FTPFile {self.path}>"

    def retr(self, callback):
        """ Retrieve file

        Wrapper around ftplib.FTP.retrbinary().
        This function cd's to the directory where this file is present, then calls the
        FTP's retrbinary() function with provided callable and then cd's back where it started
        to keep it consistent.

        Args:
            callback: Any callable that accepts one parameter as the data

        Raises:
            AssertionError: When any of the CWD or CDUP commands fail.
            ftplib.error_perm: When retrbinary call of ftplib fails
        """
        dirs, f = self.path.rsplit("/", 1)
        dirs = dirs.lstrip("/").split("/")
        # Dive in
        for d in dirs:
            assert self.client.cwd(d), f"Could not change into the directory {d}!"
        self.client.retrbinary(f, callback)
        # Dive out
        for d in dirs:
            assert self.client.cdup(), f"Could not get out of directory {d}!"

    def download(self, target=None):
        """ Download file into this machine

        Wrapper around self.retr function. It downloads the file from remote filesystem
        into local filesystem. Name is either preserved original, or can be changed.

        Args:
            target: Target file name (None to preserver the original)
        """
        if target is None:
            target = self.name
        with open(target, "wb") as output:
            self.retr(output.write)


class FTPClient:
    """ FTP Client encapsulation

    This class provides basic encapsulation around ftplib's FTP class.
    It wraps some methods and allows to easily delete whole directory or walk
    through the directory tree.

    Usage:

        >>> from utils.ftp import FTPClient
        >>> ftp = FTPClient("host", "user", "password")
        >>> only_files_with_EVM_in_name = ftp.filesystem.search("EVM", directories=False)
        >>> only_files_by_regexp = ftp.filesystem.search(re.compile("regexp"), directories=False)
        >>> some_directory = ftp.filesystem.cd("a/b/c") # cd's to this directory
        >>> root = some_directory.cd("/")

    Always going through filesystem property is a bit slow as it parses the structure on each use.
    If you are sure that the structure will remain intact between uses, you can do as follows
    to save the time::

        >>> fs = ftp.filesystem

    Let's download some files::

        >>> for f in ftp.filesystem.search("IMPORTANT_FILE", directories=False):
        ...     f.download()    # To pickup its original name
        ...     f.download("custom_name")

    We finished the testing, so we don't need the content of the directory::

        >>> ftp.recursively_delete()

    And it's gone.

    """

    def __init__(self, host, login, password, upload_dir="/", time_diff=True):
        """ Constructor

        Args:
            host: FTP server host
            login: FTP login
            password: FTP password
            time_diff: Server and client time diff management
        """
        self.host = host
        self.login = login
        self.password = password
        self.ftp = None
        self.dt = None
        self.upload_dir = upload_dir
        self.connect()
        if time_diff:
            self.update_time_difference()

    def connect(self):
        self.ftp = ftplib.FTP(self.host)
        self.ftp.login(self.login, self.password)
        logger.info("FTP Server login successful")

    def update_time_difference(self):
        """ Determine the time difference between the FTP server and this computer.

        This is done by uploading a fake file, reading its time and deleting it.
        Then the self.dt variable captures the time you need to ADD to the remote
        time or SUBTRACT from local time.

        The FTPFile object carries this automatically as it has .local_time property
        which adds the client's .dt to its time.

        """
        TIMECHECK_FILE_NAME = fauxfactory.gen_alphanumeric(length=16)
        void_file = BytesIO(b'random_example')
        self.cwd(self.upload_dir)
        assert "Transfer complete" in self.storbinary(TIMECHECK_FILE_NAME, void_file),\
            f"Could not upload a file for time checking with name {TIMECHECK_FILE_NAME}!"
        void_file.close()
        now = datetime.now()
        for d, name, time in self.ls():
            if name == TIMECHECK_FILE_NAME:
                self.dt = now - time
                self.dele(TIMECHECK_FILE_NAME)
                self.cwd("/")
                return True
        raise FTPException("The timecheck file was not found in the current FTP directory")

    def ls(self):
        """ Lists the content of a directory.


        Returns:
            List of all items in current directory
            Return format is [(is_dir?, "name", remote_time), ...]

        """
        result = []

        def _callback(line):
            is_dir = line.upper().startswith("D")
            # Max 8, then the final is file which can contain something blank
            fields = re.split(r"\s+", line, maxsplit=8)
            # This is because how information in LIST are presented
            # `Nov 11 12:34 filename (from the end)` for current year files
            # `Nov 11 2019 filename (from the end)` for back year files
            yr = datetime.now().year if ":" in fields[-2] else fields[-2]
            time = fields[-2] if ":" in fields[-2] else "00:00"
            date = strptime(f"{yr} {fields[-4]} {fields[-3]} {time}", "%Y %b %d %H:%M")
            # convert time.struct_time into datetime
            date = datetime.fromtimestamp(mktime(date))
            result.append((is_dir, fields[-1], date))

        self.ftp.dir(_callback)
        return result

    def pwd(self):
        """ Get current directory

        Returns:
            Current directory

        Raises:
            AssertionError: PWD command fails
        """
        result = self.ftp.sendcmd("PWD")
        assert "is the current directory" in result, "PWD command failed"
        x, d, y = result.strip().split("\"")
        return d.strip()

    def cdup(self):
        """ Goes one level up in directory hierarchy (cd ..)

        """
        return self.ftp.sendcmd("CDUP")

    def mkd(self, d):
        """ Create a directory

        Args:
            d: Directory name

        Returns:
            Success of the action

        """
        try:
            return self.ftp.sendcmd(f"MKD {d}").startswith("250")
        except ftplib.error_perm:
            return False

    def rmd(self, d):
        """ Remove a directory

        Args:
            d: Directory name

        Returns:
            Success of the action

        """
        try:
            return self.ftp.sendcmd(f"RMD {d}").startswith("250")
        except ftplib.error_perm:
            return False

    def dele(self, f):
        """ Remove a file

        Args:
            f: File name

        Returns:
            Success of the action

        """
        try:
            return self.ftp.sendcmd(f"DELE {f}").startswith("250")
        except ftplib.error_perm:
            return False

    def cwd(self, d):
        """ Enter a directory

        Args:
            d: Directory name

        Returns:
            Success of the action

        """
        try:
            return self.ftp.sendcmd(f"CWD {d}").startswith("250")
        except ftplib.error_perm:
            return False

    def close(self):
        """ Finish work and close connection

        """
        self.ftp.quit()
        self.ftp.close()
        self.ftp = None

    def retrbinary(self, f, callback):
        """ Download file

        You need to specify the callback function, which accepts one parameter
        (data), to be processed.

        Args:
            f: Requested file name
            callback: Callable with one parameter accepting the data
        """
        return self.ftp.retrbinary(f"RETR {f}", callback)

    def storbinary(self, f, file_obj):
        """ Store file

        You need to specify the file object.

        Args:
            f: Requested file name
            file_obj: File object to be stored
        """
        return self.ftp.storbinary(f"STOR {f}", file_obj)

    def recursively_delete(self, d=None):
        """ Recursively deletes content of pwd

        WARNING: Destructive!

        Args:
            d: Directory to enter (None for not entering - root directory)
            d: str or None

        Raises:
            AssertionError: When some of the FTP commands fail.
        """
        # Enter the directory
        if d:
            assert self.cwd(d), f"Could not enter directory {d}"
        # Work in it
        for isdir, name, time in self.ls():
            if isdir:
                self.recursively_delete(name)
            else:
                assert self.dele(name), f"Could not delete {name}!"
        # Go out of it
        if d:
            # Go to parent directory
            assert self.cdup(), f"Could not go to parent directory of {d}!"
            # And delete it
            assert self.rmd(d), f"Could not remove directory {d}!"

    def tree(self, d=None):
        """ Walks the tree recursively and creates a tree

        Base structure is a list. List contains directory content and the type decides whether
        it's a directory or a file:
        - tuple: it's a file, therefore it represents file's name and time
        - dict: it's a directory. Then the dict structure is as follows::

            dir: directory name
            content: list of directory content (recurse)

        Args:
            d: Directory to enter(None for no entering - root directory)

        Returns:
            Directory structure in lists nad dicts.

        Raises:
            AssertionError: When some of the FTP commands fail.
        """
        # Enter the directory
        items = []
        if d:
            assert self.cwd(d), f"Could not enter directory {d}"
        # Work in it
        for isdir, name, time in self.ls():
            if isdir:
                items.append({"dir": name, "content": self.tree(name), "time": time})
            else:
                items.append((name, time))
        # Go out of it
        if d:
            # Go to parent directory
            assert self.cdup(), f"Could not go to parent directory of {d}!"
        return items

    @property
    def filesystem(self):
        """ Returns the object structure of the filesystem

        Returns:
            Root directory

        """
        return FTPDirectory(self, "/", self.tree())

    # Context management methods
    def __enter__(self):
        """ Entering the context does nothing, because the client is already connected

        """
        return self

    def __exit__(self, type, value, traceback):
        """ Exiting the context means just calling .close() on the client.

        """
        self.close()


class FTPClientWrapper(FTPClient):
    """
    This class is for miq remote file management with FTP. It is useful to make a collection of raw
    files related to customer BZ testing directly or indirectly. This will help to easily download
    testing related files in a runtime environment.

    Args:
        entity_path: entity which you want to access like `Datastores`, `Dialogs`.
        entrypoint: FTP server entry point
        host: FTP server host
        login: FTP user
        password: FTP password

    Usage:
        .. code-block:: python

          fs = FileServer("miq")
          fs.directory_names    # list of current available entities
          fs.mkd("Dialogs")   # create new entity type
          fs.rmd("Dialogs")     # delete created entity type

          fs = FileServer("miq/Reports")
          fs.upload("foo.zip") # upload local file
          fs.file_names # return list of available files
          fs.files()  # return list of available file objects
          download_path = fs.download("foo.zip") # It will download foo.zip file

          f = fs.get_file("foo.zip")
          f.path    # It will return file storage path
          f.link    # gives remote file link; can be used to download with 'wget'
          f.download()  # download file
    """

    def __init__(self, entity_path=None, entrypoint=None, host=None, login=None, password=None):
        ftp_data = cfme_data.ftpserver
        host = host or ftp_data.host
        login = login or credentials[ftp_data.credentials]["username"]
        password = password or credentials[ftp_data.credentials]["password"]

        self.entrypoint = entrypoint or ftp_data.entrypoint
        self.entity_path = entity_path

        super().__init__(
            host=host, login=login, password=password, time_diff=False
        )

        # Change working directory as per entity_path if provided
        self.cwd(os.path.join(self.entrypoint, self.entity_path if entity_path else ""))

    @property
    def file_names(self):
        """List of remote FTP file names"""
        return [name for is_dir, name, _ in self.ls() if not is_dir]

    def get_file(self, name):
        """
        Arg:
            name: name of remote file
        Returns:
            FTP file object
        """

        if name in self.file_names:
            return FTPFileWrapper(self, name=name, parent_dir=self.pwd())
        else:
            raise FTPException(f"{name} not found")

    def files(self):
        """List of FTP file objects"""
        current_dir = self.pwd()
        return [FTPFileWrapper(self, name=name, parent_dir=current_dir) for name in self.file_names]

    def download(self, name, target=None):
        """ Download FTP file
        Arg:
            name: remote file name
            target: local path for download else it will consider current working path
        Returns:
            target path
        """

        target = target if target else os.path.join("/tmp", name)
        if name not in self.file_names:
            raise FTPException("{} not found in {}".format(name, self.pwd()))

        with open(target, "wb") as output:
            self.retrbinary(name, output.write)
            logger.info("'%s' successfully downloaded to '%s'", name, target)
            return target

    def upload(self, path, name=None):
        """ Upload FTP file
        Arg:
            path: path of local file
            name: set name of file default it will consider original name of uploading file
        Returns:
            Success of the action
        """

        name = name or os.path.basename(path)
        if name in self.file_names:
            raise FTPException("{} already available in {}".format(name, self.pwd()))
        with open(path, "rb") as f:
            return self.storbinary(name, f)

    @property
    def directory_names(self):
        """ List remote FTP directories"""
        return [name for is_dir, name, _ in self.ls() if is_dir]


class FTPFileWrapper(FTPFile):
    """This is simple FTPFile class wrapper for FTPClientWrapper"""

    @property
    def link(self):
        """Remote FTP file url"""
        return self.path.replace(self.client.entrypoint, self.client.host)

    def download(self, target=None):
        """
        Arg:
            target: local path for download else it will consider current working path
        Returns:
            target path
        """
        return self.client.download(self.name, target)

    @property
    def filesize(self):
        """Return file size"""
        size = ''
        try:
            # Switch to Binary mode
            self.client.ftp.sendcmd("TYPE i")
            size = self.client.ftp.size(self.path)
        except Exception:
            logger.exception("Failed to get the file size due to exception ")
        finally:
            # switch back to ASCII
            self.client.ftp.sendcmd("TYPE A")
            return size

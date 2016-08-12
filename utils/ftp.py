# -*- coding: utf-8 -*-
""" FTP manipulation library

@author: Milan Falešník <mfalesni@redhat.com>
"""
from __future__ import unicode_literals
import fauxfactory
import ftplib
import re
from datetime import datetime
from time import strptime, mktime
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class FTPException(Exception):
    pass


class FTPDirectory(object):
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
        if self.parent_dir:
            return self.parent_dir.path + self.name + "/"
        else:
            return self.name

    def __repr__(self):
        return "<FTPDirectory {}>".format(self.path)

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
        raise FTPException("Directory {}{} does not exist!".format(self.path, enter))

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
            if isinstance(what, re._pattern_type):
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


class FTPFile(object):
    """ FTP FS File encapsulation

    This class represents one file in the FS hierarchy.
    It encapsulates mainly its position in FS and adds the possibility
    of downloading the file.
    """
    def __init__(self, client, name, parent_dir, time):
        """ Constructor

        Args:
            client: ftplib.FTP instance
            name: File name (without path)
            parent_dir: Directory in which this file is
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
        if self.parent_dir:
            return self.parent_dir.path + self.name
        else:
            return self.name

    @property
    def local_time(self):
        """
        Returns:
            time modified to match local computer's time zone

        """
        return self.client.dt + self.time

    def __repr__(self):
        return "<FTPFile {}>".format(self.path)

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
            assert self.client.cwd(d), "Could not change into the directory {}!".format(d)
        self.client.retrbinary(f, callback)
        # Dive out
        for d in dirs:
            assert self.client.cdup(), "Could not get out of directory {}!".format(d)

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


class FTPClient(object):
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

    def __init__(self, host, login, password, upload_dir="/"):
        """ Constructor

        Args:
            host: FTP server host
            login: FTP login
            password: FTP password
        """
        self.host = host
        self.login = login
        self.password = password
        self.ftp = None
        self.dt = None
        self.upload_dir = upload_dir
        self.connect()
        self.update_time_difference()

    def connect(self):
        self.ftp = ftplib.FTP(self.host)
        self.ftp.login(self.login, self.password)

    def update_time_difference(self):
        """ Determine the time difference between the FTP server and this computer.

        This is done by uploading a fake file, reading its time and deleting it.
        Then the self.dt variable captures the time you need to ADD to the remote
        time or SUBTRACT from local time.

        The FTPFile object carries this automatically as it has .local_time property
        which adds the client's .dt to its time.

        """
        TIMECHECK_FILE_NAME = fauxfactory.gen_alphanumeric(length=16)
        void_file = StringIO(fauxfactory.gen_alpha())
        self.cwd(self.upload_dir)
        assert "Transfer complete" in self.storbinary(TIMECHECK_FILE_NAME, void_file),\
            "Could not upload a file for time checking with name {}!".format(TIMECHECK_FILE_NAME)
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
            # This is because how informations in LIST are presented
            # Nov 11 12:34 filename (from the end)
            date = strptime(str(datetime.now().year) + " " + fields[-4] + " " + fields[-3] + " " +
                            fields[-2],
                            "%Y %b %d %H:%M")
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
            return self.ftp.sendcmd("MKD {}".format(d)).startswith("250")
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
            return self.ftp.sendcmd("RMD {}".format(d)).startswith("250")
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
            return self.ftp.sendcmd("DELE {}".format(f)).startswith("250")
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
            return self.ftp.sendcmd("CWD {}".format(d)).startswith("250")
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
        return self.ftp.retrbinary("RETR {}".format(f), callback)

    def storbinary(self, f, file_obj):
        """ Store file

        You need to specify the file object.

        Args:
            f: Requested file name
            file_obj: File object to be stored
        """
        return self.ftp.storbinary("STOR {}".format(f), file_obj)

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
            assert self.cwd(d), "Could not enter directory {}".format(d)
        # Work in it
        for isdir, name, time in self.ls():
            if isdir:
                self.recursively_delete(name)
            else:
                assert self.dele(name), "Could not delete {}!".format(name)
        # Go out of it
        if d:
            # Go to parent directory
            assert self.cdup(), "Could not go to parent directory of {}!".format(d)
            # And delete it
            assert self.rmd(d), "Could not remove directory {}!".format(d)

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
            assert self.cwd(d), "Could not enter directory {}".format(d)
        # Work in it
        for isdir, name, time in self.ls():
            if isdir:
                items.append({"dir": name, "content": self.tree(name), "time": time})
            else:
                items.append((name, time))
        # Go out of it
        if d:
            # Go to parent directory
            assert self.cdup(), "Could not go to parent directory of {}!".format(d)
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

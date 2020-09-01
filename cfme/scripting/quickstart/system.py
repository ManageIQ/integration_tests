import os
import re
import time

from cfme.scripting.quickstart import run_cmd_or_exit

IS_ROOT = os.getuid() == 0
REDHAT_RELEASE_FILE = '/etc/redhat-release'

HAS_DNF = os.path.exists('/usr/bin/dnf')
HAS_YUM = os.path.exists('/usr/bin/yum')
HAS_APT = os.path.exists('/usr/bin/apt-get')

OS_RELEASE_FILE = '/etc/os-release'
OS_NAME_REGEX = r'^NAME="?([\w\s\/]*?)"?$'
OS_VERSION_REGEX = r'^VERSION_ID="?([\S]*?)"?$'

REQUIRED_PACKAGES = None
INSTALL_COMMAND = None
# FIXME define install commands separately in config/ini file
DEBUG_INSTALL_COMMAND = None

# Concerning debuginfo-install, on dnf has it as plugin,
# whereas yum has completely separate command that calls yum.
if HAS_DNF:
    INSTALL_COMMAND = 'dnf install -y'
    DEBUG_INSTALL_COMMAND = 'dnf debuginfo-install -y'
elif HAS_YUM:
    INSTALL_COMMAND = 'yum install -y'
    DEBUG_INSTALL_COMMAND = 'debuginfo-install -y'
elif HAS_APT:
    INSTALL_COMMAND = 'apt-get install -y'
    # No separate debuginfo for apt
else:
    INSTALL_COMMAND = ''

if not IS_ROOT:
    INSTALL_COMMAND = 'sudo ' + INSTALL_COMMAND
    DEBUG_INSTALL_COMMAND = 'sudo ' + DEBUG_INSTALL_COMMAND if DEBUG_INSTALL_COMMAND else None

OS_NAME = "unknown"
OS_VERSION = "unknown"

if os.path.exists(OS_RELEASE_FILE):
    with open(OS_RELEASE_FILE) as os_release:
        for var in os_release.readlines():
            name = re.match(OS_NAME_REGEX, var)
            if name:
                OS_NAME = name.group(1).rstrip('\n')
            version = re.match(OS_VERSION_REGEX, var)
            if version:
                OS_VERSION = version.group(1).rstrip('\n')

print(f'OS_NAME: {OS_NAME}, OS_VERSION: {OS_VERSION}')

RH_BASE = (
    " gcc postgresql-devel libxml2-devel libxslt-devel"
    " zeromq3-devel libcurl-devel redhat-rpm-config gcc-c++ openssl-devel"
    " libffi-devel python3 python3-pip python3-devel tesseract freetype-devel"
    " python3-debuginfo git"
)

RH_BASE_NEW = RH_BASE.replace("zeromq3-devel", "zeromq-devel")
DNF_EXTRA = " 'dnf-command(debuginfo-install)'"
YUM_EXTRA = " yum-utils"
# These package specs include debuginfo packages, which have to be processed out
REDHAT_PACKAGES_SPECS = [
    ("Fedora release 24", "nss", RH_BASE + DNF_EXTRA),
    ("Fedora release 25", "nss", RH_BASE + DNF_EXTRA),
    ("Fedora release 26", "nss", RH_BASE_NEW + DNF_EXTRA),
    ("Fedora release 27", "openssl", RH_BASE_NEW + DNF_EXTRA),
    ("Fedora release 28", "openssl", RH_BASE_NEW + DNF_EXTRA),
    ("Fedora release 29", "openssl", RH_BASE_NEW + DNF_EXTRA),
    ("Fedora release 30", "openssl", RH_BASE_NEW + DNF_EXTRA),
    ("Fedora release 31", "openssl", RH_BASE_NEW + DNF_EXTRA),
    ("Fedora release 32", "openssl", RH_BASE_NEW + DNF_EXTRA),
    ("CentOS Linux release 7", "nss", RH_BASE + YUM_EXTRA),
    ("Red Hat Enterprise Linux Server release 7", "nss", RH_BASE + YUM_EXTRA),
    ("Red Hat Enterprise Linux Workstation release 7", "nss",
     RH_BASE + YUM_EXTRA)
]


DEB_PKGS = (
    " python3-venv gcc gnutls-dev postgresql libxml2-dev"
    " libxslt1-dev libzmq3-dev libcurl4-openssl-dev"
    " g++ openssl libffi-dev python3-dev libtesseract-dev"
    " libpng-dev libfreetype6-dev libssl-dev python3-dbg git"
)

OS_PACKAGES_SPECS = [
    # Extend this
    ("Ubuntu", "16.04.3 LTS (Xenial Xerus)", "openssl", DEB_PKGS),
    ("Ubuntu", "16.04", "openssl", DEB_PKGS),  # as it appears in travis
    ("Ubuntu", "16.04.4 LTS (Xenial Xerus)", "openssl", DEB_PKGS),
    ("Ubuntu", "17.10 (Artful Aardvark)", "openssl", DEB_PKGS),
    ("Ubuntu", "18.04", "openssl", DEB_PKGS),  # as it appears in travis
    ("Ubuntu", "18.04.1 LTS (Bionic Beaver)", "openssl", DEB_PKGS),
    ("Debian GNU/Linux", "9 (stretch)", "openssl", DEB_PKGS),
]

# Holder for processed -debuginfo packages
DEBUG_PACKAGES = []

if os.path.exists(REDHAT_RELEASE_FILE):
    with open(REDHAT_RELEASE_FILE) as fp:
        release_string = fp.read()
    for release, curl_ssl, packages in REDHAT_PACKAGES_SPECS:
        if release_string.startswith(release):
            # Look for *-debuginfo package names, separate them
            for p in packages.lstrip().split(' '):
                if '-debuginfo' in p:
                    DEBUG_PACKAGES.append(p.replace('-debuginfo', ''))
                    packages = packages.replace(p, '')  # remove *-debuginfo package from main list
            REQUIRED_PACKAGES = packages
            os.environ['PYCURL_SSL_LIBRARY'] = curl_ssl
            break

    if not REQUIRED_PACKAGES:
        print(
            '{} not known. '
            'Please ensure you have the required packages installed.'.format(release_string)
        )
        print('$ [dnf/yum] install -y {}'.format(REDHAT_PACKAGES_SPECS[-1][-1]))

elif os.path.exists(OS_RELEASE_FILE):

    for os_name, os_version, curl_ssl, packages in OS_PACKAGES_SPECS:
        if os_name == OS_NAME and os_version == OS_VERSION:
            REQUIRED_PACKAGES = packages
            os.environ['PYCURL_SSL_LIBRARY'] = curl_ssl
            break

    if not REQUIRED_PACKAGES:
        print(
            '{} {} not known. '
            'Please ensure you have the required packages installed.'.format(OS_NAME, OS_VERSION)
        )
        print('$ apt install -y {}'.format(OS_PACKAGES_SPECS[-1][-1]))

else:
    INSTALL_COMMAND = None
    REQUIRED_PACKAGES = None


def retry_install_once(command, shell):
    try:
        run_cmd_or_exit(command, shell=shell)
    except SystemExit:
        print("Hit error during yum/dnf install or debuginfo-install, re-trying...")
        time.sleep(5)
        run_cmd_or_exit(command, shell=shell)


def install_system_packages(debuginfo_install=False):
    installed = False
    if INSTALL_COMMAND and REQUIRED_PACKAGES:
        retry_install_once(INSTALL_COMMAND + REQUIRED_PACKAGES, shell=True)
        installed = True
    if DEBUG_INSTALL_COMMAND and DEBUG_PACKAGES and debuginfo_install:
        retry_install_once('{} {}'.format(DEBUG_INSTALL_COMMAND, ' '.join(DEBUG_PACKAGES)),
                           shell=True)
        installed = True
    if not installed:
        print("WARNING: unknown distribution,",
              "please ensure you have the required packages installed")
        print("INFO: on redhat based systems this is the equivalent of:")
        print("$ dnf install -y", REDHAT_PACKAGES_SPECS[-1][-1])
        print("INFO: on non-redhat based systems this is the equivalent of:")
        print("$ apt install -y", OS_PACKAGES_SPECS[-1][-1])

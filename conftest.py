import pytest

def add_cfme_pages_to_path():
    try:
        import pages.page
    except ImportError:
        import os
        import sys
        HOMEDIR = os.environ['HOME']
        pages_dirs = ["cfme_pages",
                "../cfme_pages",
                "%s/workspace/cfme_pages" % (HOMEDIR),
                "%s/cfme_pages" % (HOMEDIR)]
        for pages_dir in pages_dirs:
            oldpath = sys.path
            try:
                sys.path.append(pages_dir)
                import pages.page
                break
            except ImportError:
                sys.path.remove(pages_dir)
                continue
        if not 'pages.page' in sys.modules:
            print '''Could not find cfme_pages. Please clone to one of the
            standard locations, or set PYTHONPATH'''
            raise ImportError

add_cfme_pages_to_path()

pytest_plugins = 'plugin.highlight', 'fixtures.cfmedata', 'fixtures.cfmedb', \
        'fixtures.server_roles'


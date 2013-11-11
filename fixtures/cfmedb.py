'''


Created on Jun 14, 2013

@author: bcrochet

'''
# -*- coding: utf-8 -*-
# pylint: disable=C0103
# pylint: disable=E1101
import pytest
from urlparse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import ConfigParser

def pytest_addoption(parser):
    '''Create the options for py.test'''
    config = ConfigParser.ConfigParser(defaults={
        'cfmedburl': ''
    })
    config.read('cfme.cfg')

    group = parser.getgroup('cfme', 'cfme')
    group.addoption('--cfmedburl',
                     action='store',
                     dest='cfme_db_url',
                     default=config.get('DEFAULT', 'cfmedburl'),
                     metavar='url',
                     help='url for CFME database to connect to')

def pytest_sessionstart(session):
    '''Setup run for tests'''
    import db
    db.cfme_db_url = session.config.option.cfme_db_url
    if not db.cfme_db_url:
        # Let's try to figure it out
        baseurl = session.config.option.baseurl
        baseip = urlparse(baseurl).hostname
        db.cfme_db_url = "postgres://root:smartvm@%s:5432/vmdb_production" \
                % baseip
    db.engine = create_engine(db.cfme_db_url)

@pytest.fixture
def db_session():
    '''Creates a database session based on the db url passed on the CLI

    Usage example:

    This is a SQLalchemy (http://www.sqlalchemy.org/) session. You can make
    queries and create new rows in the database with this session.

    The available classes are dynamically generated from the database. Consult
    db/__init__.py for a list of available class -> table mappings.

    An example test:

    @pytest.mark.nondestructive
    def test_that_tries_for_db(db_session):
        import db
        session = db_session
        for instance in session.query(db.ExtManagementSystem).order_by(
            db.ExtManagementSystem.id):
        print instance.name, instance.hostname

    This 'test' prints the management systems from the database.
    '''
    import db
    Session = sessionmaker(bind=db.engine)
    return Session()


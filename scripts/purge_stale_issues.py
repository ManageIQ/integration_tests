#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The aim of this script is to automate some routine jira tasks
like purging stale cards
"""
import logging
import argparse
import sys
from os import getenv
from jira import JIRA
from datetime import datetime, timedelta

url = 'https://projects.engineering.redhat.com'
project_name = 'RHCFQE'
default_version_name = 'purge for week {week} {year}'
base_filter = 'project = "Red Hat CloudForms QE" ' \
              'AND (fixVersion in unreleasedVersions() OR fixVersion is EMPTY) ' \
              'AND status = Done ' \
              'AND status was Done before "{date}"'


def get_connection(user, pswd):
    options = {'verify': False}  # this setting turns off checking ssl cert
    return JIRA(url, options=options,
                basic_auth=(user, pswd))


def get_cards(filter):
    logger.debug('the following filter will be used: {}'.format(filter))
    cards = conn.search_issues(filter)
    if len(cards) > 0:
        logger.info('the following issues will be purged:\n {}'.format(
            '\n'.join([card.fields.summary for card in cards])))
    else:
        logger.info('no cards found')
    return cards


if __name__ == '__main__':
    # parsing args
    description = """
    this script does the following atm:
    1. creates new version
    2. finds all cards in Done status older than <tbd> weeks
    3. assigns those cards to just created version
    4. releases the version
    5. send email with release notes
    6. archive the version

    As a results those cards disappear.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-d', '--debug', help='enable debug output', action='store_true')
    parser.add_argument('-u', '--user', help='jira user', default=getenv('JIRA_USER'))
    parser.add_argument('-p', '--password', help='jira password', default=getenv('JIRA_PASSWORD'))
    parser.add_argument('-w', '--weeks-back', help='allows to change purge period. '
                                                   'accepts number of weeks', type=int, default=2)
    args = parser.parse_args()

    # setup basic logger
    if args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.ERROR

    logging.basicConfig(format="%(asctime)s %(levelname)s %(funcName)s\t%(message)s",
                        level=log_level)
    logger = logging.getLogger(__file__)

    # connecting to jira
    if not args.user or not args.password:
        raise ValueError('jira user/password is not passed')
    logger.info("connecting to server {}".format(url))
    conn = get_connection(args.user, args.password)

    # creating new project version
    weeks_back = args.weeks_back
    today = datetime.today()
    version_name = default_version_name.format(
        week=str(datetime.today().isocalendar()[1] - weeks_back),
        year=today.year)
    logger.info('creating new project version {}'.format(version_name))
    new_version = conn.create_version(version_name, project_name)

    # looking for issues to purge
    purge_before = (today + timedelta(days=7 - today.isoweekday())) - timedelta(weeks=weeks_back)
    found_cards = get_cards(base_filter.format(date=purge_before.strftime('%Y/%m/%d')))

    # assigning found cards/issues to this version
    for card in found_cards:
        logger.debug('card {} will be assigned to {}'.format(card.key, new_version.name))
        card.update(fields={'fixVersions': [{'id': new_version.id}]})

    # releasing that version
    # expected fmt u'releaseDate': u'2016-09-16'
    logger.info('releasing version {}'.format(new_version.name))
    release_date = purge_before.strftime('%Y-%m-%d')
    new_version.update(releaseDate=release_date, released=True)

    # todo: to prepare and send email here
    pass

    # archiving that version
    logger.info('archiving version {}'.format(new_version.name))
    new_version.update(archived=True)
    sys.exit(0)

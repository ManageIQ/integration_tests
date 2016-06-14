from utils.conf import cfme_data
from utils.log import logger


def _remove_page(roles, group, pages):
    if group in roles:
        for page in pages:
            if page in roles[group]:
                roles[group].remove(page)
            else:
                logger.info("Page %s attempted to be removed from role %s, "
                            "but isn't in there anyway", page, group)
    else:
        logger.info("Attempted to remove a page from role %s, but role "
                    "doesn't exist", group)


def _remove_from_all(roles, r_page):
    for group in roles:
        for page in roles[group]:
            if page == r_page:
                roles[group].remove(page)
            else:
                logger.info("Page %s attempted to be removed from role %s, "
                            "but isn't in there anyway", page, group)


def group_data():
    roles = cfme_data.get('group_roles', {})
    return roles

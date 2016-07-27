

from debtcollector.removals import remove


removed_selenium = remove(
    message="it is replaced by the browser endpoint api",
    removal_version="framework 3.0",
)

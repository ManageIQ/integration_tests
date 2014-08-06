import utils.db as db
import utils.version as ver


def cache_reset():
    ver.current_version.cache_clear()
    ver.appliance_build_datetime.cache_clear()
    ver.appliance_is_downstream.cache_clear()
    db.cfmedb = db.Db()

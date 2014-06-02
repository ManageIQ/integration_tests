from riggerlib import RiggerBasePlugin
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import sys


class ArtifactorBasePlugin(RiggerBasePlugin):
    """A sub from RiggerBasePlugin"""


def start_session(run_id=None):
    """
    Convenience fire_hook for built in hook
    """
    return None, {'run_id': run_id}


def parse_setup_dir(test_name, test_location, artifactor_config, log_dir, run_id):
    """
    Convenience fire_hook for built in hook
    """
    if test_name and test_location:
        run_type = artifactor_config.get('per_run', None)
        overwrite = artifactor_config.get('reuse_dir', False)
        path = setup_artifact_dir(root_dir=log_dir, test_name=test_name,
                                  test_location=test_location, run_type=run_type,
                                  run_id=run_id, overwrite=overwrite)
    else:
        raise Exception('Not enough information to create artifact')
    return {'artifact_path': path}, None


def setup_artifact_dir(root_dir=None, test_name=None, test_location=None,
                       run_type=None, run_id=None, overwrite=True):
    """
    Sets up the artifact dir and returns it.
    """
    test_name = re.sub(r"[^a-zA-Z0-9_.\-\[\]]", "_", test_name)
    test_name = re.sub(r"[/]", "_", test_name)
    test_name = re.sub(r"__+", "_", test_name)
    orig_path = os.path.abspath(root_dir)

    if run_id:
        run_id = str(run_id)

    if run_type == "run" and run_id:
        path = os.path.join(orig_path, run_id, test_location, test_name)
    elif run_type == "test" and run_id:
        path = os.path.join(orig_path, test_location, test_name, run_id)
    else:
        path = os.path.join(orig_path, test_location, test_name)

    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == 17:
            if overwrite:
                pass
            else:
                print "Directories already existed and overwrite is set to False"
                sys.exit(127)
        else:
            raise

    return path


def create_logger(logger_name, filename):
    """Creates and returns the named logger

    If the logger already exists, it will be destroyed and recreated
    with the current config in env.yaml

    """
    # If the logger already exists, destroy it
    if logger_name in logging.root.manager.loggerDict:
        del(logging.root.manager.loggerDict[logger_name])

    log_file = filename

    file_formatter = logging.Formatter('%(asctime)-15s [%(levelname).1s] %(message)s')
    file_handler = RotatingFileHandler(log_file, maxBytes=2048, encoding='utf8')
    file_handler.setFormatter(file_formatter)

    logger = logging.getLogger(logger_name)
    logger.addHandler(file_handler)

    logger.setLevel('DEBUG')
    return logger

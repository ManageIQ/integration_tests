#!/usr/bin/env python2

from artifactor import Artifactor, initialize
import argparse
from artifactor.plugins import merkyl, logger, video, filedump, reporter, post_result, softassert
from artifactor import parse_setup_dir
from utils.conf import env
from utils.path import log_path

import bottle
bottle.BaseRequest.MEMFILE_MAX = 1073741824


def run(port, run_id=None):
    art_config = env.get('artifactor', {})
    art_config['server_port'] = int(port)
    art = Artifactor(None)

    if 'log_dir' not in art_config:
        art_config['log_dir'] = log_path.strpath
    if 'artifact_dir' not in art_config:
        art_config['artifact_dir'] = log_path.join('artifacts').strpath
    art.set_config(art_config)

    art.register_plugin(merkyl.Merkyl, "merkyl")
    art.register_plugin(logger.Logger, "logger")
    art.register_plugin(video.Video, "video")
    art.register_plugin(filedump.Filedump, "filedump")
    art.register_plugin(softassert.SoftAssert, "softassert")
    art.register_plugin(reporter.Reporter, "reporter")
    art.register_plugin(post_result.PostResult, "post-result")
    art.register_hook_callback('filedump', 'pre', parse_setup_dir,
                               name="filedump_dir_setup")

    initialize(art)

    art.configure_plugin('merkyl')
    art.configure_plugin('logger')
    art.configure_plugin('video')
    art.configure_plugin('filedump')
    art.configure_plugin('softassert')
    art.configure_plugin('reporter')
    art.configure_plugin('post-result')
    art.fire_hook('start_session', run_id=run_id)

    # Stash this where slaves can find it
    # log.logger.info('artifactor listening on port %d', art_config['server_port'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--run-id', default=None)
    parser.add_argument('--port')
    args = parser.parse_args()
    run(args.port, args.run_id)

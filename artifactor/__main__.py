#!/usr/bin/env python3
import bottle
import click

from artifactor import Artifactor
from artifactor import initialize
from artifactor.plugins import filedump
from artifactor.plugins import logger
from artifactor.plugins import ostriz
from artifactor.plugins import post_result
from artifactor.plugins import reporter
from artifactor.plugins import video
from cfme.utils.conf import env
from cfme.utils.net import random_port
from cfme.utils.path import log_path

bottle.BaseRequest.MEMFILE_MAX = 1073741824


def run(port, run_id=None):
    art_config = env.get("artifactor", {})
    art_config["server_port"] = int(port)
    art = Artifactor(None)

    if "log_dir" not in art_config:
        art_config["log_dir"] = log_path.strpath
    if "artifact_dir" not in art_config:
        art_config["artifact_dir"] = log_path.join("artifacts").strpath
    art.set_config(art_config)

    art.register_plugin(logger.Logger, "logger")
    art.register_plugin(video.Video, "video")
    art.register_plugin(filedump.Filedump, "filedump")
    art.register_plugin(reporter.Reporter, "reporter")
    art.register_plugin(post_result.PostResult, "post-result")
    art.register_plugin(ostriz.Ostriz, "ostriz")

    initialize(art)

    art.configure_plugin("logger")
    art.configure_plugin("video")
    art.configure_plugin("filedump")
    art.configure_plugin("reporter")
    art.configure_plugin("post-result")
    art.configure_plugin("ostriz")
    art.fire_hook("start_session", run_id=run_id)

    # Stash this where slaves can find it
    # log.logger.info('artifactor listening on port %d', art_config['server_port'])


@click.command(help="Starts an artifactor server manually")
@click.option("--run-id", default=None)
@click.option("--port", default=None)
def main(run_id, port):
    """Main function for running artifactor server"""
    port = port if port else random_port()
    try:
        run(port, run_id)
        print("Artifactor server running on port: ", port)
    except Exception as e:
        import traceback
        import sys

        with log_path.join("artifactor_crash.log").open("w") as f:
            print(e, file=f)
            print(e, file=sys.stderr)
            tb = "\n".join(traceback.format_tb(sys.exc_info()[2]))
            print(tb, file=f)
            print(tb, file=sys.stderr)


if __name__ == "__main__":
    main()

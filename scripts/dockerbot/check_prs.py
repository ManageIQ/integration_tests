#!/usr/bin/env python
from datetime import datetime

import fauxfactory
import traceback
import dockerbot
import json
import requests
import pika
import logging
from utils.conf import docker as docker_conf
from utils.appliance import Appliance
from utils.trackerbot import api
from utils.log import create_logger
from slumber.exceptions import HttpClientError


token = docker_conf['gh_token']
owner = docker_conf['gh_owner']
repo = docker_conf['gh_repo']

tapi = api()

CONT_LIMIT = docker_conf['workers']
DEBUG = docker_conf.get('debug', False)

logger = create_logger('check_prs', 'prt.log')

# Disable pika logs
logging.getLogger("pika").propagate = False


def send_message_to_bot(msg):

    required_fields = set(['rabbitmq_url', 'gh_queue', 'gh_channel', 'gh_message_type'])
    if not required_fields.issubset(docker_conf.viewkeys()):
        logger.warn("Skipping - docker.yaml doesn't have {}".format(required_fields))
        return

    logger.info("Github PR bot: about to send '{}'".format(msg))
    url = docker_conf['rabbitmq_url']
    queue = docker_conf['gh_queue']
    irc_channel = docker_conf['gh_channel']
#    message_type = docker_conf['gh_message_type']
    params = pika.URLParameters(url)
    params.socket_timeout = 5
    connection = pika.BlockingConnection(params)  # Connect to CloudAMQP
    try:
        channel = connection.channel()
        message = {"channel": irc_channel, "body": msg}
        channel.basic_publish(exchange='', routing_key=queue,
                              body=json.dumps(message, ensure_ascii=True))
    except Exception:
        output = traceback.format_exc()
        logger.warn("Exception while sending a message to the bot: {}".format(output))
    finally:
        connection.close()


def perform_request(url):
    """ Simple function to assist in performing GET requests from github

    Runs if there is a token, else just spits out a blank dict

    Args:
        url: The url to process, which is anything after the "...repos/"

    """
    out = {}
    if token:
        headers = {'Authorization': 'token {}'.format(token)}
        full_url = "https://api.github.com/repos/{}/{}/{}".format(owner, repo, url)
        r = requests.get(full_url, headers=headers)
        out = r.json()
    return out


def set_invalid_runs(db_pr):
    """ Iterates the runs and sets all pending tasks to be Invalid

    Args:
        db_pr: The database pr_object, which will be a JSON
        pr: The GitHub PR object
    """
    for run in db_pr['runs']:
        if run['result'] == "pending":
            run_db = tapi.run(run['id']).get()
            for task in run_db['tasks']:
                tapi.task(task['tid']).put({'result': 'invalid', 'cleanup': False})


def create_run(db_pr, pr):
    """ Creates a new run

    This function takes the database PR object and the PR object from GitHub
    and creates from them a Run in the database along with the associated tasks.
    One task is created for each stream available from the template tracker.

    Args:
        db_pr: The database pr_object, which will be a JSON
        pr: The GitHub PR object
    """
    logger.info(' Creating new run for {}'.format(db_pr['number']))

    new_run = dict(pr="/api/pr/{}/".format(db_pr['number']),
                   datestamp=str(datetime.now()),
                   commit=pr['head']['sha'])
    tasks = []
    for group in tapi.group.get(stream=True)['objects']:
        stream = group['name']
        logger.info('  Adding task stream {}...'.format(stream))
        tasks.append(dict(output="",
                          tid=fauxfactory.gen_alphanumeric(8),
                          result="pending",
                          stream=stream,
                          datestamp=str(datetime.now())))
    new_run['tasks'] = tasks
    if tasks:
        tapi.run.post(new_run)


def check_prs():
    """ Checks the PRs

    Iterates over each PR and runs the check_pr functon on it.
    """
    json_data = perform_request('pulls?per_page=100')
    numbers = []
    for pr in json_data:
        numbers.append(pr['number'])
        if pr['state'] == 'open':
            check_pr(pr)

    prs = tapi.pr.get(closed=False, limit=0)['objects']
    for pr in prs:
        if pr['number'] not in numbers:
            logger.info("PR {} closed".format(pr['number']))
            tapi.pr(pr['number']).put({'closed': True})


def run_tasks():
    """ Runs the pending tasks

    This function first checks the number of dockerbot containers which are running the
    py_test_base image running and stores this count. If the count is lower than the threshold,
    it proceeds to grab a pending task from the list and provision an appliance. The appliance
    is then configured before being handed off to Dockerbot for the running of the PR.
    """
    cont_count = 0
    for container in dockerbot.dc.containers():
        if "py_test_base" in container['Image']:
            cont_count += 1
    while cont_count < CONT_LIMIT:
        tasks = tapi.task().get(limit=1, result='pending')['objects']
        if tasks:
            task = tasks[0]
            stream = task['stream']
            try:
                # Get the latest available template and provision/configure an appliance
                # template_obj = tapi.group(stream).get()
                # providers = template_obj['latest_template_providers']
                # if providers:
                #     for provider in docker_conf['provider_prio']:
                #         if provider in providers:
                #             break
                #     else:
                #         provider = providers[0]
                # else:
                #     raise Exception('No template for stream')
                # template = template_obj['latest_template']
                # vm_name = 'dkb-{}'.format(task['tid'])
                provider = "Sprout"
                vm_name = "Sprout"
                template = "Sprout"
                tapi.task(task['tid']).put({'result': 'running', 'vm_name': vm_name,
                                            'provider': provider, 'template': template})

                # Create a dockerbot instance and run the PR test
                dockerbot.DockerBot(dry_run=DEBUG,
                                    auto_gen_test=True,
                                    use_wharf=True,
                                    prtester=True,
                                    test_id=task['tid'],
                                    nowait=True,
                                    pr=task['pr_number'],
                                    sprout=True,
                                    sprout_stream=stream,
                                    sprout_description=task['tid'])
                cont_count += 1
                tapi.task(task['tid']).put({'result': 'running', 'vm_name': vm_name,
                                            'provider': provider, 'template': template})
            except Exception:
                output = traceback.format_exc()
                tapi.task(task['tid']).put({'result': 'failed', 'output': output})
        else:
            # No tasks to process - Happy Days!
            break


def vm_reaper():
    """ Iterates through each task in the db which has not yet been cleaned and runs the reaper

    This function iterates through each task. If the task is either failed or passed, ie, the
    task has completed, then the VM is cleaned up and then the docker container. If both of
    these operations occur, then the cleanup is set to True.
    """
    tasks = tapi.task().get(cleanup=False)['objects']
    for task in tasks:
        if task['result'] in ["failed", "passed", "invalid"]:
            vm_cleanup = False
            docker_cleanup = False

            if task['provider'] == "Sprout" and task['vm_name'] == "Sprout":
                vm_cleanup = True
            else:
                if task['provider'] and task['vm_name']:
                    logger.info('Cleaning up {} on {}'.format(task['vm_name'], task['provider']))
                    if task['vm_name'] == "None":
                        vm_cleanup = True
                    else:
                        appliance = Appliance(task['provider'], task['vm_name'])
                        try:
                            if appliance.does_vm_exist():
                                logger.info("Destroying {}".format(appliance.vm_name))
                                appliance.destroy()
                            vm_cleanup = True
                        except Exception:
                            logger.info('Exception occured cleaning up')

            containers = dockerbot.dc.containers(all=True)
            for container in containers:
                if task['tid'] in container['Names'][0]:
                    logger.info('Cleaning up docker container {}'.format(container['Id']))
                    dockerbot.dc.remove_container(container['Id'], force=True)
                    docker_cleanup = True
                    break
            else:
                docker_cleanup = True

            if docker_cleanup and vm_cleanup:
                tapi.task(task['tid']).put({'cleanup': True})


def set_status(commit, status, context):
    """ Puts a status for a given commit to GitHub

    This function takes a commit hash, a status, and a description and posts them to GitHub.

    Args:
        commit: The commit SHA
        status: One of either "failure", "success", "pending" or "error"
        description: A description to describe the status

    """
    data = {
        "state": status,
        "description": status,
        "context": "ci/{}".format(context)
    }
    data_json = json.dumps(data)

    headers = {'Authorization': 'token {}'.format(token)}
    requests.post("https://api.github.com/repos/{}/{}/commits/{}/statuses".format(
        owner, repo, commit), data=data_json, headers=headers)


def check_status(pr):
    """ Checks the status of a given PR and updates if necessary

    This function checks to see if there are any current statuses associated with the given
    commit. If the status differs, a new status will be posted, else nothing will happen.

    Args:
        pr: The PR object from GitHub (json)
    """
    if DEBUG:
        return

    db_pr = tapi.pr(pr['number']).get()

    if db_pr['wip']:
        return

    if db_pr['runs']:
        commit = db_pr['runs'][0]['commit']
        run_id = db_pr['runs'][0]['id']
    else:
        return

    states = {'pending': 'pending',
              'failed': 'failure',
              'invalid': 'error',
              'passed': 'success',
              'running': 'pending'}

    task_updated_states = {}

    try:
        tasks = tapi.task.get(run=run_id)['objects']
        statuses = perform_request("commits/{}/statuses".format(commit))
        for task in tasks:
            for status in statuses:
                if status['context'] == "ci/{}".format(task['stream']):
                    if status['state'] == states[task['result']]:
                        break
                    else:
                        logger.info('Setting task {} for pr {} to {}'
                                    .format(task['stream'], pr['number'], states[task['result']]))
                        task_updated_states[task['stream']] = states[task['result']]
                        set_status(commit, states[task['result']], task['stream'])
                        break
            else:
                logger.info('Setting task {} for pr {} to {}'
                            .format(task['stream'], pr['number'], states[task['result']]))
                set_status(commit, states[task['result']], task['stream'])
    except HttpClientError:
        pass

    failed_states = ['pending', 'invalid', 'running']
    if task_updated_states and not any(x in failed_states for x in task_updated_states.values()):
        # There are no pending, invalid or running states in the run_id
        if 'failed' in task_updated_states.values():
            failed_streams = [x.key() for x in task_updated_states if x.value() == 'failed']
            send_message_to_bot("Tests PR #{} failed on streams {}".format(
                pr['number'], failed_streams))
        else:
            send_message_to_bot("Tests for PR #{} passed".format(pr['number']))


def check_pr(pr):
    """ Checks through a PR and spawns runs if necessary

    This function begins by interrogating the database for a PR. If the PR exists,
    it checks to see if the commit head matches the database state. If they differ
    a new commit has been added to the PR and a new test run is required.

    If tasks are already pending for this PR, then they will be set to invalid.

    If [WIP] is in the title of the PR, then new runs are not issued and instead it is just
    stored in the DB.

    If the PR does not exist in the database a new PR record is created, and a new run is
    prepared.
    """

    commit = pr['head']['sha']
    wip = False
    try:
        db_pr = tapi.pr(pr['number']).get()
        last_run = tapi.run().get(pr__number=pr['number'], order_by='-datestamp',
                                  limit=1)['objects']
        if last_run:
            if last_run[0]['retest'] is True and "[WIP]" not in pr['title']:
                logger.info('Re-testing PR {}'.format(pr['number']))
                set_invalid_runs(db_pr)
                create_run(db_pr, pr)
            elif last_run[0]['commit'] != commit and "[WIP]" not in pr['title']:
                logger.info('New commit ({}) detected for PR {}'.format(commit, pr['number']))
                set_invalid_runs(db_pr)
                create_run(db_pr, pr)
        elif "[WIP]" not in pr['title']:
            logger.info('First run ({}) for PR {}'.format(commit, pr['number']))
            create_run(db_pr, pr)
        else:
            wip = True
        tapi.pr(pr['number']).put({'current_commit_head': commit,
                                   'wip': wip,
                                   'title': pr['title'],
                                   'description': pr['body']})
    except HttpClientError:
        logger.info('PR {} not found in database, creating...'.format(pr['number']))

        new_pr = {'number': pr['number'],
                  'description': pr['body'],
                  'current_commit_head': commit,
                  'title': pr['title']}
        tapi.pr().post(new_pr)
        if "[WIP]" not in pr['title']:
            create_run(new_pr, pr)
        elif "[WIP]" in pr['title']:
            new_pr['wip'] = True
        tapi.pr(pr['number']).put(new_pr)
        send_message_to_bot("New PR: #{} {}".format(pr['number'], pr['title']))

    check_status(pr)

if __name__ == "__main__":
    if docker_conf['pr_enabled']:

        # First we check through the PRs from GitHub
        check_prs()

        # Next we run any tasks that are pending up to the queue limit
        run_tasks()

        # Finally we clean up any leftover artifacts
        if not DEBUG:
            vm_reaper()

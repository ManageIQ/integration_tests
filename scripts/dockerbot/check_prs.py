#!/usr/bin/env python
from datetime import datetime

import traceback
import dockerbot
import json
import requests
from utils.conf import docker as docker_conf
from utils.appliance import provision_appliance, Appliance
from utils.randomness import generate_random_string
from utils.trackerbot import api
from slumber.exceptions import HttpClientError

token = docker_conf['gh_token']
owner = docker_conf['gh_owner']
repo = docker_conf['gh_repo']

tapi = api()

CONT_LIMIT = 3


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
                tapi.task(task['tid']).put({'result': 'invalid', 'cleanup': True})


def create_run(db_pr, pr):
    """ Creates a new run

    This function takes the database PR object and the PR object from GitHub
    and creates from them a Run in the database along with the associated tasks.
    One task is created for each stream available from the template tracker.

    Args:
        db_pr: The database pr_object, which will be a JSON
        pr: The GitHub PR object
    """
    new_run = dict(pr="/api/pr/{}/".format(db_pr['number']),
                   datestamp=str(datetime.now()),
                   commit=pr['head']['sha'])
    tasks = []
    for group in tapi.group.get(stream=True)['objects']:
        stream = group['name']
        tasks.append(dict(output="",
                          tid=generate_random_string(size=8),
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
    json_data = perform_request('pulls'.format(owner, repo))
    for pr in json_data:
        if pr['number'] == 1030:
            check_pr(pr)


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
                template_obj = tapi.group(stream).get()
                providers = template_obj['latest_template_providers']
                if providers:
                    for provider in docker_conf['provider_prio']:
                        if provider in providers:
                            break
                    else:
                        provider = providers[0]
                else:
                    raise Exception('No template for stream')
                template = template_obj['latest_template']
                tapi.task(task['tid']).put({'result': 'provisioning', 'provider': provider,
                                            'template': template})
                appliance = provision_appliance(template=template, provider_name=provider,
                                                vm_name='dkb-{}'.format(task['tid']))
                appliance.configure()
                address = appliance.address

                tapi.task(task['tid']).put({'result': 'running', 'vm_name': appliance.vm_name})
                # Create a dockerbot instance and run the PR test
                dockerbot.DockerBot(appliance='https://{}/'.format(address),
                                    auto_gen_test=True,
                                    use_wharf=True,
                                    prtester=True,
                                    test_id=task['tid'],
                                    nowait=True,
                                    pr=task['pr_number'])
                cont_count += 1
                tapi.task(task['tid']).put({'result': 'running', 'vm_name': appliance.vm_name})
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
        if task['result'] == "failed" or task['result'] == "passed":
            vm_cleanup = False
            docker_cleanup = False
            if task['provider'] and task['vm_name']:
                if task['vm_name'] == "None":
                    vm_cleanup = True
                else:
                    appliance = Appliance(task['provider'], task['vm_name'])
                    if appliance.does_vm_exist():
                        print "Destroying {}".format(appliance.vm_name)
                        appliance.destroy()
                    vm_cleanup = True
                    tapi.task(task['tid']).put({'cleanup': True})

            containers = dockerbot.dc.containers(all=True)
            for container in containers:
                if task['tid'] in container['Names'][0]:
                    dockerbot.dc.remove_container(container['Id'])
                    docker_cleanup = True
                    break

            if docker_cleanup and vm_cleanup:
                tapi.task(task['tid']).put({'cleanup': True})


def set_status(commit, status, description):
    """ Puts a status for a given commit to GitHub

    This function takes a commit hash, a status, and a description and posts them to GitHub.

    Args:
        commit: The commit SHA
        status: One of either "failure", "success", "pending" or "error"
        description: A description to describe the status

    """
    data = {
        "state": status,
        "description": description,
        "context": "ci/prtester"
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
    db_pr = tapi.pr(pr['number']).get()

    if db_pr['wip']:
        return

    commit = pr['head']['sha']
    statuses = perform_request("commits/{}/statuses".format(commit))
    state = "pending"
    if "failed" in db_pr['status']:
        state = "failure"
    elif "passed" in db_pr['status']:
        state = "success"
    elif "pending" in db_pr['status']:
        state = "pending"
    elif "invalid" in db_pr['status']:
        state = "error"

    if not statuses:
        set_status(commit, state, db_pr['status'])
    else:
        if statuses[0]['state'] != state:
            set_status(commit, state, db_pr['status'])
        else:
            return


def check_pr(pr):
    """ Checks through a PR and spawns runs if necessary

    This function begins by interrogating the database for a PR. If the PR exists,
    it checks to see if the commit head matches the database state. If they differ
    a new commit has been added to the PR and a new test run is required.

    If tasks are already pending for this PR, then they will be set to invalid.

    If WIP is in the title of the PR, then new runs are not issued and instead it is just
    stored in the DB.

    If the PR does not exist in the database a new PR record is created, and a new run is
    prepared.
    """
    # labels = []
    # raw_labels = perform_request("issues/{}/labels".format(pr['number']))

    # for label in raw_labels:
    #    labels.append(label['name'])

    commit = pr['head']['sha']
    wip = False

    try:
        db_pr = tapi.pr(pr['number']).get()
        if db_pr['current_commit_head'] != commit and \
           "WIP" not in pr['title']:
                for run in db_pr['runs']:
                    if run['commit'] == commit:
                        break
                else:
                    set_invalid_runs(db_pr)
                    create_run(db_pr, pr)
        elif "WIP" in pr['title']:
            wip = True
        tapi.pr(pr['number']).put({'current_commit_head': commit, 'wip': wip})
        check_status(pr)
    except HttpClientError:
        pass
        new_pr = {'number': pr['number'],
                  'description': pr['body'],
                  'current_commit_head': commit}
        tapi.pr().post(new_pr)
        if "WIP" not in pr['title']:
            create_run(new_pr, pr)
        elif "WIP" in pr['title']:
            new_pr['wip'] = True
        tapi.pr(pr['number']).put(new_pr)
        check_status(pr)

if __name__ == "__main__":
    if docker_conf['pr_enabled']:

        # First we check through the PRs from GitHub
        check_prs()

        # Next we run any tasks that are pending up to the queue limit
        run_tasks()

        # Finally we clean up any leftover artifacts
        vm_reaper()

#!/bin/env python3

# Usage: $ ./csv2elastic.py <sample cfme result result root dir>
#
# Example:
# ./postprocess/csv2elastic.py results/20170105161527-workload-cap-and-util-5.7.0.1/

# WIP: [csv2elastic] issues on github/cfme-performance/issues/

import os
import re
import io
import csv
import sys
import time
import json
import glob
import hashlib
from datetime import datetime
from collections import defaultdict
from urllib3 import exceptions as ul_excs, Timeout
from elasticsearch import VERSION, Elasticsearch, helpers, exceptions as es_excs

if VERSION < (5, 0, 0):
    msg = """At least v5.0.0 of the ElasticSearch Python client is required.\n
             Found %r""" % (VERSION)
    quit(msg)

_NAME_ = 'cfme_csv2elastic'
_VERSION_ = "1.1.0-0"
_DEBUG = 1

INDEX_PREFIX = 'cfme-run'
# for batch processing actions in bulk_upload to avoid
# nginx's 413 Request Entity Too Large. (that is if ES hosted as such)
# INDEXING_THRESHOLD = 14
INDEXING_THRESHOLD = 3000

# ES config
host = "10.12.23.122"
port = 9201
auth = ('admin', 'admin')

_op_type = 'create'
_read_timeout = 120
timeoutobj = Timeout(total=1200, connect=10, read=_read_timeout)


def tstos(ts=None):
    return time.strftime("%Y-%m-%dT%H:%M:%S-%Z", time.localtime(ts))


class ElasticIndexer(object):
    '''
    creates a connection to ES and indexes data
    '''

    def __init__(self, host, port, creds=[]):
        self.actions = []
        self.successes = 0
        self.duplicates = 0
        self.errors = 0
        self.exceptions = 0
        self.endpoint = [dict(host=host, port=port, timeout=timeoutobj),]
        try:
            if creds:
                self.ES = Elasticsearch(self.endpoint,
                                        max_retries=0,
                                        http_auth=creds)
            else:
                self.ES = Elasticsearch(self.endpoint,
                                        max_retries=0)
            # print(self.ES.info())
        except Exception as E:
            quit("ERROR: %s" % E)

    def gen_action(self, **kwargs):
        """
        single ES doc that gets consumed inside bulk uploads
        """
        action = {
            "_op_type": _op_type,
            "_index": kwargs['index_name'],
            "_type": kwargs['doc_type'],
            "_id": kwargs['uid'],
            # "@timestamp": kwargs['timestamp'],
            "_source": kwargs['data']
        }
        return action

    def upload_doc(self, **kwargs):
        """
        uploads single doc
        """
        try:
            # avoid usage of timestamps fields as it's not supported in 5.x
            # keep it here, for usage, if backporting needed.
            # timestamp=kwargs['timestamp'],
            self.ES.index(
                index=kwargs['index_name'],
                doc_type=kwargs['doc_type'],
                id=kwargs['uid'],
                body=kwargs['data'],
            )
        except Exception as E:
            quit("ERROR: %s" % E)

    def delete_doc(self, **kwargs):
        """
        stub; for single doc deletion.
        """
        self.ES.delete(
            index=kwargs['index_name'],
            doc_type=kwargs['doc_type'],
            id=kwargs['md5']
        )

    def _dump_actions(self):
        """
        if failure happens, dump related ES docs
        """
        for act in self.actions:
            print(json.dumps(act, indent=4, sort_keys=True))
        # If we are dumping the actions out, we are consuming them
        del self.actions[0:len(self.actions)]

    def bulk_upload(self):
        """
        handles bulk uploads and generate a report at the end..
        """
        if _DEBUG > 1:
            self._dump_actions()
        if len(self.actions) == 0:
            print('0 actions found..')

        beg, end = time.time(), None
        start = beg
        if _DEBUG > 0:
            print("\tbulk index (beg ts: %s) ..." % tstos(beg))
        delay = _read_timeout
        tries = 20
        good_results = 0
        try:
            while True:
                try:
                    res = helpers.bulk(self.ES, self.actions)
                except es_excs.ConnectionError as err:
                    end = time.time()
                    if isinstance(err.info, ul_excs.ReadTimeoutError):
                        tries -= 1
                        if tries > 0:
                            print("\t\tWARNING (end ts: %s, duration: %.2fs):"
                                  " read timeout, delaying %d seconds before"
                                  " retrying (%d attempts remaining)..." %
                                        (tstos(end), end - beg, delay, tries))
                            time.sleep(delay)
                            delay *= 2
                            beg, end = time.time(), None
                            print("\t\tWARNING (beg ts: %s): retrying..." %
                                    (tstos(beg)))
                            continue
                    if _DEBUG > 8:
                        import pdb; pdb.set_trace()
                    print("\tERROR (end ts: %s, duration: %.2fs): %s" %
                                            (tstos(end), end - start, err))
                    self.exceptions += 1
                except helpers.BulkIndexError as err:
                    end = time.time()
                    if _DEBUG > 8:
                        import pdb; pdb.set_trace()
                    for error in err.errors:
                        sts = error[_op_type]['status']
                        if sts not in (200, 201):
                            self.duplicates += 1
                        else:
                            print(error[_op_type]['error'])
                            self.exceptions += 1
                except Exception as err:
                    end = time.time()
                    if _DEBUG > 8:
                        import pdb; pdb.set_trace()
                    print("\tERROR (end ts: %s, duration: %.2fs): %s" %
                                (tstos(end), end - start, err))
                    self.exceptions += 1
                else:
                    end = time.time()
                    lcl_successes = res[0]
                    self.successes += lcl_successes
                    lcl_duplicates = 0
                    lcl_errors = 0
                    len_res1 = len(res[1])
                    for idx, ires in enumerate(res[1]):
                        sts = ires[_op_type]['status']
                        if sts not in (200, 201):
                            if _op_type == 'create' and sts == 409:
                                self.duplicates += 1
                                lcl_duplicates += 1
                            else:
                                print("\t\tERRORS (%d of %d): %r" %
                                        (idx, len_res1, ires[_op_type]['error']))
                                self.errors += 1
                                lcl_errors += 1
                        else:
                            self.successes += 1
                            lcl_successes += 1
                    if _DEBUG > 0 or lcl_errors > 0:
                        print("\tdone (end ts: %s, duration: %.2fs,"
                              " success: %d, duplicates: %d, errors: %d,  exceptions: %d)" %
                                    (tstos(end), end - start, self.successes,
                                  self.duplicates, self.errors, self.exceptions))
                    good_results = 1
                break
        finally:
            if not good_results:
                if _DEBUG > 0 or lcl_errors > 0:
                    end = time.time()
                    print("\tdone (end ts: %s, duration: %.2fs,"
                          " success: %d, duplicates: %d, errors: %d, exceptions: %d)" %
                                (tstos(end), end - start, self.successes,
                              self.duplicates, self.errors, self.exceptions))
            del self.actions[0:len(self.actions)]

    def init_upload(self, docs):
        """
        2 kinds of uploads happen here:
        1. cfme-run.summary
        2. cfme-run.smem
        """
        # upload metadata first
        index_names = {
            'summary': '%s.summary-%s'%(INDEX_PREFIX, docs['date']),
            'smem': '%s.smem-%s'%(INDEX_PREFIX, docs['date'])
        }

        # helper statements
        # self.ES.indices.delete(index=index_names['smem'], ignore=[400, 404])
        # self.ES.indices.delete(index=index_names['summary'], ignore=[400, 404])

        # ib_data = self.gen_action(
        #     index_name=index_names['summary'],
        #     doc_type='metadata',
        #     uid=docs['metadata']['cfme_run_md5'],
        #     data=docs['metadata'],
        # )
        # self.actions.append(ib_data)
        # FIXME: indexing for summary data along with smem isn't tested atm.
        # use other alternative to index metadata separately for now
        self.upload_doc(
            index_name=index_names['summary'],
            doc_type='metadata',
            uid=docs['metadata']['cfme_run_md5'],
            data=docs['metadata']
        )
        print('\t..indexed metata successfully.')
        print('\t..Now uploading summary data. This will take a short while')
        count = 0

        for summary in docs['summary_data']:
            for key in summary:
                if key == "provider" or key == "scenario_name":
                    continue
                for item in summary[key]:
                    run_uid = docs['metadata']['cfme_run_md5'] + str(count)
                    count = count + 1
                    md5 = hashlib.md5((run_uid).encode('utf-8')).hexdigest()

                    # total memory data is different from USS/PSS/etc. data
                    if key == "total_memory":
                        ib_data1 = self.gen_action(
                            index_name=index_names['summary'],
                            doc_type="total_memory",
                            uid=md5,
                            # timestamp=docs['metadata']['timestamp'],
                            data=item,
                        )
                        self.actions.append(ib_data1)
                        if len(self.actions) > INDEXING_THRESHOLD:
                            self.bulk_upload()
                        continue

                    ib_data1 = self.gen_action(
                        index_name=index_names['summary'],
                        doc_type="summary_data",
                        uid=md5,
                        # timestamp=docs['metadata']['timestamp'],
                        data=item,
                    )
                    self.actions.append(ib_data1)

                    # for cfme docs, INDEXING_THRESHOLD=14 doesn't results in a 413 'Request Entity Too Large'
                    # we could change elasticsearch instance's default params, but to avoid that,
                    # we're batch processing actions here.
                    if len(self.actions) > INDEXING_THRESHOLD:
                        self.bulk_upload()

        print('\t..Now uploading smem data. This could take some time')

        # Now, upload smem data
        for scenario in docs['smem_data']:
            for csv_kind in docs['smem_data'][scenario]:
                for item in docs['smem_data'][scenario][csv_kind]:
                    # calculate per process '_id', to be used while indexing in ES
                    if csv_kind == 'processes':
                        run_uid = docs['metadata']['cfme_run_md5'] + scenario + csv_kind + item['pid'] + item['TimeStamp']
                    elif csv_kind == 'appliance_memory':
                        run_uid = docs['metadata']['cfme_run_md5'] + scenario + csv_kind + item['TimeStamp']
                    else:
                        run_uid = docs['metadata']['cfme_run_md5'] + scenario + csv_kind
                    md5 = hashlib.md5((run_uid).encode('utf-8')).hexdigest()
                    # avoid usage of timestamps fields as it's not supported in 5.x
                    ib_data = self.gen_action(
                        index_name=index_names['smem'],
                        doc_type=csv_kind,
                        uid=md5,
                        # timestamp=docs['metadata']['timestamp'],
                        data=item,
                    )
                    self.actions.append(ib_data)

                    # for cfme docs, INDEXING_THRESHOLD=14 doesn't results in a 413 'Request Entity Too Large'
                    # we could change elasticsearch instance's default params, but to avoid that,
                    # we're batch processing actions here.
                    if len(self.actions) > INDEXING_THRESHOLD:
                        self.bulk_upload()

        # index last bundle
        if len(self.actions) > 0:
            self.bulk_upload()


class CfmeResultsParser(object):
    '''
    takes in a dir path and converts csvs to dict formatted output
    '''
    def __init__(self, results_dir):
        self.results_dir = os.path.abspath(os.path.normpath(results_dir))

    def __find_csvs(self, scenario):
        res = []
        given_path = os.path.join(self.results_dir, scenario)
        for path, subdirs, files in os.walk(given_path):
            os.chdir(path)
            for f in glob.glob("*.csv"):
                res.append(os.path.join(path, f))
        return res

    def __get_params(self, dirname):
        """
        parses results root dir for metadata.
        example str:- '20170105161527-workload-cap-and-util-5.7.0.1'
        """
        timestamp = re.search('^[0-9]+', dirname).group()
        timestamp = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
        workload_name = re.search('(?i)[a-z-]+', dirname)
        workload_name = workload_name.group().strip('-').replace('workload-','')
        version = re.search('-[0-9\.]+', dirname).group().strip('-')
        return [timestamp, workload_name, version]

    def process_version_info(self, csv_bundle):
        """
        handles installed package versions on CFME appliance
        """
        version_dict = {}
        for current_csv in csv_bundle:
            csv_name = os.path.splitext(os.path.basename(current_csv))[0]
            csv_stream = csv.reader(open(current_csv))
            if csv_name == 'system':
                versions = {}
                for row in csv_stream:
                    if row:
                        versions[row[0].strip()] = row[1].strip()
            else:
                versions = []
                for row in csv_stream:
                    if row:
                        package_details = {
                            'package': row[0].strip(),
                            'version': row[1].strip(),
                        }
                        versions.append(package_details)
            version_dict[csv_name] = versions
        return version_dict

    def csv_sanitizer(self, csv_contents=[], type=''):
        csv_contents = list(csv_contents)
        if type == 'summary':
            for item in csv_contents:
                item['start_of_test'] = float(item['start_of_test'])
                item['end_of_test'] = float(item['end_of_test'])
        elif type == 'appliance' or type == 'processes':
            for item in csv_contents:
                # TimeStamp -> timestamp and it's value to indexing format
                # tstamp = item.pop('TimeStamp')
                tstamp = datetime.strptime(
                    item.pop('TimeStamp'),
                    "%Y-%m-%d %H:%M:%S.%f"
                )
                # import pdb; pdb.set_trace()
                for mem_type in item:
                    item[mem_type] = float(item[mem_type])
                item['TimeStamp'] = tstamp.strftime("%Y-%m-%d %H:%M:%S")
        return csv_contents

    def process_summary_csv(self, csv_path, scenario, md5, indexing_params):
        """
        cleans up and processes *-summary.csv files in a scenario
        """
        metadata_dict = { 'scenario_name': scenario }
        summary = open(csv_path).read()
        # cleanup summary (not a pure csv!)
        summary = re.sub('(-)+\n.*\n(-)+', '', summary)
        summary = re.sub('(?i)Start of test','start_of_test', summary)
        summary = re.sub('(?i)End of test','end_of_test', summary)
        summary = re.sub('(?i)Process/Worker Type','process_worker_type', summary)
        groups = re.split('\n\s*\n', summary)
        # groups[0] --> version/provider + total memory
        scenario_metadata = re.compile(r'(?i)^Version.*\n').search(groups[0]).group()
        scenario_metadata = scenario_metadata.strip().split(',')

        # we're already handling CFME version in __get_params
        # metadata_dict['cfme_version'] = scenario_metadata[0].split()[-1]
        metadata_dict['provider'] = scenario_metadata[1].split()[-1]
        memory_str = re.sub(r'(?i)^Version.*\n', '', groups[0])
        metadata_dict['total_memory'] = self.csv_sanitizer(
            csv_contents=csv.DictReader(io.StringIO(memory_str)),
            type='summary')
        final_result = []
        for item in metadata_dict['total_memory']:
            datum = dict(
                scenario_name = scenario,
                cfme_run_md5 = md5,
                cfme_version = indexing_params[2],
                workload_type = indexing_params[1],
                provider = metadata_dict['provider'],
                TimeStamp = indexing_params[0].strftime("%Y-%m-%d %H:%M:%S")
            )
            datum.update(item)
            final_result.append(datum)
        metadata_dict['total_memory'] = final_result
        final_result = []
        count = 0
        dtype = ""
        for group in groups[1:]:
            if count == 0:
                dtype = "RSS"
            elif count == 1:
                dtype  = "PSS"
            elif count == 2:
                dtype = "USS"
            elif count == 3:
                dtype = "VSS"
            elif count == 4:
                dtype = "SWAP"
            else:
                break
            count = count+1
            sanitized_data = self.csv_sanitizer(
                csv_contents=csv.DictReader(io.StringIO(group)),
                type='summary')
            for item in sanitized_data:
                datum = dict(
                    scenario_name = scenario,
                    memory_data_type = dtype,
                    cfme_run_md5 = md5,
                    cfme_version = indexing_params[2],
                    workload_type = indexing_params[1],
                    provider = metadata_dict['provider'],
                    TimeStamp = indexing_params[0].strftime("%Y-%m-%d %H:%M:%S")
                )
                datum.update(item)
                final_result.append(datum)
        metadata_dict['per_process_memory'] = final_result
        return metadata_dict

    def handle_scenario(self, csv_bundle, scenerio, md5, indexing_params):
        """
        3 kinds of scenarios:
            - scenario_summary [{}]
            - appliance_memory [{}]
            - processes [{}]

        @csv_bundle: list of csv file paths per scenario
        """
        scenario_data = defaultdict(list)
        for current_csv in csv_bundle:
            csv_name = os.path.basename(current_csv)
            if re.match('.*-summary.csv', csv_name):
                scenario_data['scenario_summary'] = self.process_summary_csv(current_csv, scenerio, md5, indexing_params)
                continue
            elif re.match('appliance.csv', csv_name):
                reader_obj = csv.DictReader(open(current_csv))
                csv_contents = self.csv_sanitizer(csv_contents=reader_obj, type='appliance')
                for record in csv_contents:
                    datum = dict(
                        scenario=scenerio,
                        cfme_run_md5=md5,
                    )
                    datum.update(record)
                    scenario_data['appliance_memory'].append(datum)
            else:
                reader_obj = csv.DictReader(open(current_csv))
                # pid-name.csv -> [pid, name]
                pid_name = os.path.splitext(csv_name)[0].split('-')
                csv_contents = self.csv_sanitizer(csv_contents=reader_obj, type='processes')
                for record in csv_contents:
                    datum = dict(
                        name=pid_name[1],
                        pid=pid_name[0],
                        scenario=scenerio,
                        cfme_run_md5=md5,
                    )
                    datum.update(record)
                    scenario_data['processes'].append(datum)
        return scenario_data

    def process_results(self):
        """
        main function that walks through results directory and converts csv files.
        """
        results_data = defaultdict(dict)

        results_data['metadata']['generated-by'] = _NAME_
        results_data['metadata']['generated-by-version'] = _VERSION_

        self.run_name = os.path.basename(self.results_dir)
        indexing_params = self.__get_params(self.run_name)
        tstamp = indexing_params[0].strftime("%Y-%m-%d %H:%M:%S")
        run_uid = self.run_name + tstamp
        md5 = hashlib.md5((run_uid).encode('utf-8')).hexdigest()
        shared_info = dict(TimeStamp=tstamp, cfme_run_md5=md5)

        results_data['date'] = indexing_params[0].strftime("%Y.%m.%d")
        results_data['metadata'].update(shared_info)
        results_data['metadata']['workload_type'] = indexing_params[1]
        results_data['metadata']['cfme_version'] = indexing_params[2]
        results_data['metadata']['run_dirname'] = self.run_name
        results_data["summary_data"] = []

        for component in os.listdir(self.results_dir):
            if os.path.isdir(os.path.join(self.results_dir, component)):
                csv_bundle = self.__find_csvs(component)
                if component == 'version_info':
                    results_data['metadata']['version_info'] = self.process_version_info(csv_bundle)
                else:
                    handled_data = self.handle_scenario(csv_bundle, component, md5, indexing_params)
                    results_data['summary_data'].append(handled_data.pop('scenario_summary'))
                    results_data['smem_data'][component] = handled_data.copy()
                    del handled_data
        return results_data


if __name__=="__main__":
    if len(sys.argv)>1:
        CRP = CfmeResultsParser(sys.argv[1])
        ESx = ElasticIndexer(host, port, auth)
        docs = CRP.process_results()
        ESx.init_upload(docs)
    else:
        print("Usage: $ ./csv2elastic.py <sample cfme result result root dir>")

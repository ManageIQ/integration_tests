# -*- coding: utf-8 -*
"""Set of functions for performance analysis/charting of the backend messages.
"""
from utils.log import logger
from utils.path import log_path
from datetime import datetime
import dateutil.parser as du_parser
from datetime import timedelta
from time import time
import csv
import numpy
import os
import pygal
import subprocess
import re

# Regular Expressions to capture relevant information from each log line:

# [----] I, [2014-03-04T08:11:14.320377 #3450:b15814]  INFO -- : ....
log_stamp = re.compile(r'\[----\]\s[IWE],\s\[([0-9\-]+)T([0-9\:\.]+)\s#([0-9]+):[0-9a-z]+\]')
# [----] .* MIQ( * )
miqmsg = re.compile(r'\[----\].*MIQ\(([a-zA-Z0-9\._]*)\)')
# Command: [ * ]
miqmsg_cmd = re.compile(r'Command:\s\[([a-zA-Z0-9\._\:]*)\]')
# Message id: [ * ]
miqmsg_id = re.compile(r'Message\sid:\s\[([0-9]*)\]')
# Args: [ *]
miqmsg_args = re.compile(
    r'Args:\s\[([A-Za-z0-9\{\}\(\)\[\]\s\\\-\:\"\'\,\=\<\>\_\/\.\@\?\%\&\#]*)\]')
# Dequeued in: [ * ] seconds
miqmsg_deq = re.compile(r'Dequeued\sin:\s\[([0-9\.]*)\]\sseconds')
# Delivered in [ * ] seconds
miqmsg_del = re.compile(r'Delivered\sin\s\[([0-9\.]*)\]\sseconds')

# Worker related regular expressions:
# MIQ(PriorityWorker) ID [15], PID [6461]
miqwkr = re.compile(r'MIQ\(([A-Za-z]*)\)\sID\s\[([0-9]*)\],\sPID\s\[([0-9]*)\]')
# with ID: [21]
miqwkr_id = re.compile(r'with\sID:\s\[([0-9]*)\]')
# For use with workers exiting, such as authentication failures:
miqwkr_id_2 = re.compile(r'ID\s\[([0-9]*)\]')
# PID PPID USER PR NI VIRT RES SHR S %CPU %MEM TIME+  COMMAND
# 17526 2320 root 30 10 324m 9.8m 2444 S 0.0 0.2 0:09.38 /var/www/miq/vmdb/lib/workers/bin/worker.rb
miq_top = re.compile(r'([0-9]+)\s+[0-9]+\s+[A-Za-z0-9]+\s+[0-9]+\s+[0-9\-]+\s+([0-9\.mg]+)\s+'
    r'([0-9\.mg]+)\s+([0-9\.mg]+)\s+[SRD]\s+([0-9\.]+)\s+([0-9\.]+)')


def collect_log(ssh_client, log_prefix, local_file_name, strip_whitespace=False):
    log_dir = '/var/www/miq/vmdb/log/'

    log_file = '{}{}.log'.format(log_dir, log_prefix)
    dest_file = '{}{}.perf.log'.format(log_dir, log_prefix)
    dest_file_gz = '{}{}.perf.log.gz'.format(log_dir, log_prefix)

    ssh_client.run_command('rm -f {}'.format(dest_file_gz))

    status, out = ssh_client.run_command('ls {}-*'.format(log_file))
    if status == 0:
        files = out.strip().split('\n')
        for lfile in sorted(files):
            ssh_client.run_command('cp {} {}-2.gz'.format(lfile, lfile))
            ssh_client.run_command('gunzip {}-2.gz'.format(lfile))
            if strip_whitespace:
                ssh_client.run_command('sed -i  \'s/^ *//; s/ *$//; /^$/d; /^\s*$/d\' '
                    '{}-2'.format(lfile))
            ssh_client.run_command('cat {}-2 >> {}'.format(lfile, dest_file))
            ssh_client.run_command('rm {}-2'.format(lfile))

    ssh_client.run_command('cp {} {}-2'.format(log_file, log_file))
    if strip_whitespace:
        ssh_client.run_command('sed -i  \'s/^ *//; s/ *$//; /^$/d; /^\s*$/d\' '
            '{}-2'.format(log_file))
    ssh_client.run_command('cat {}-2 >> {}'.format(log_file, dest_file))
    ssh_client.run_command('rm {}-2'.format(log_file))
    ssh_client.run_command('gzip {}{}.perf.log'.format(log_dir, log_prefix))

    ssh_client.get_file(dest_file_gz, local_file_name)
    ssh_client.run_command('rm -f {}'.format(dest_file_gz))


# Converts Memory Unit to MiB
def convert_mem_to_mib(top_mem):
    if top_mem[-1:] == 'm':
        num = float(top_mem[:-1])
    elif top_mem[-1:] == 'g':
        num = float(top_mem[:-1]) * 1024
    else:
        num = float(top_mem) / 1024
    return num


def evm_to_messages(evm_file, filters):
    test_start = ''
    test_end = ''
    line_count = 0
    messages = {}
    msg_cmds = {}

    runningtime = time()
    evmlogfile = open(evm_file, 'r')
    evm_log_line = evmlogfile.readline()
    while evm_log_line:
        line_count += 1
        evm_log_line = evm_log_line.strip()

        miqmsg_result = miqmsg.search(evm_log_line)
        if miqmsg_result:

            # Obtains the first timestamp in the log file
            if test_start == '':
                ts, pid = get_msg_timestamp_pid(evm_log_line)
                test_start = ts

            # A message was first put on the queue, this starts its queuing time
            if (miqmsg_result.group(1) == 'MiqQueue.put'):

                msg_cmd = get_msg_cmd(evm_log_line)
                msg_id = get_msg_id(evm_log_line)
                if msg_id:
                    ts, pid = get_msg_timestamp_pid(evm_log_line)
                    test_end = ts
                    messages[msg_id] = MiqMsgStat()
                    messages[msg_id].msg_id = msg_id
                    messages[msg_id].msg_id = '\'' + msg_id + '\''
                    messages[msg_id].msg_cmd = msg_cmd
                    messages[msg_id].pid_put = pid
                    messages[msg_id].puttime = ts
                    msg_args = get_msg_args(evm_log_line)
                    if msg_args is False:
                        logger.debug('Could not obtain message args line #: {}'.format(line_count))
                    else:
                        messages[msg_id].msg_args = msg_args
                else:
                    logger.error('Could not obtain message id, line #: {}'.format(line_count))

            elif (miqmsg_result.group(1) == 'MiqQueue.get_via_drb'):
                msg_id = get_msg_id(evm_log_line)
                if msg_id:
                    if msg_id in messages:
                        ts, pid = get_msg_timestamp_pid(evm_log_line)
                        test_end = ts
                        messages[msg_id].pid_get = pid
                        messages[msg_id].gettime = ts
                        messages[msg_id].deq_time = get_msg_deq(evm_log_line)
                    else:
                        logger.error('Message ID not in dictionary: {}'.format(msg_id))
                else:
                    logger.error('Could not obtain message id, line #: {}'.format(line_count))

            elif (miqmsg_result.group(1) == 'MiqQueue.delivered'):
                msg_id = get_msg_id(evm_log_line)
                if msg_id:
                    ts, pid = get_msg_timestamp_pid(evm_log_line)
                    test_end = ts
                    if msg_id in messages:
                        messages[msg_id].del_time = get_msg_del(evm_log_line)
                        messages[msg_id].total_time = messages[msg_id].deq_time + \
                            messages[msg_id].del_time
                    else:
                        logger.error('Message ID not in dictionary: {}'.format(msg_id))
                else:
                    logger.error('Could not obtain message id, line #: {}'.format(line_count))

        if (line_count % 100000) == 0:
            timediff = time() - runningtime
            runningtime = time()
            logger.info('Count {} : Parsed 100000 lines in {}'.format(line_count, timediff))

        evm_log_line = evmlogfile.readline()

    # I tried to avoid two loops but this reduced the complexity of filtering on messages.
    # By filtering over messages, we can better display what is occuring under the covers, as a
    # daily rollup is picked up off the queue different than a hourly rollup, etc
    for msg in messages:
        msg_args = messages[msg].msg_args
        # Determine if the pattern matches and append to the command if it does
        for p_filter in filters:
            results = filters[p_filter].search(msg_args.strip())
            if results:
                messages[msg].msg_cmd = '{}{}'.format(messages[msg].msg_cmd, p_filter)
                break
        msg_cmd = messages[msg].msg_cmd
        if msg_cmd not in msg_cmds:
            msg_cmds[msg_cmd] = {}
            msg_cmds[msg_cmd]['total'] = []
            msg_cmds[msg_cmd]['queue'] = []
            msg_cmds[msg_cmd]['execute'] = []
        if messages[msg].total_time != 0:
            msg_cmds[msg_cmd]['total'].append(round(messages[msg].total_time, 2))
            msg_cmds[msg_cmd]['queue'].append(round(messages[msg].deq_time, 2))
            msg_cmds[msg_cmd]['execute'].append(round(messages[msg].del_time, 2))

    return messages, msg_cmds, test_start, test_end, line_count


def evm_to_workers(evm_file):
    # Use grep to reduce # of lines to sort through
    p = subprocess.Popen(['grep', 'Interrupt\\|MIQ([A-Za-z]*) ID\\|"evm_worker_uptime_exceeded\\|'
            '"evm_worker_memory_exceeded\\|"evm_worker_stop\\|Worker exiting.', evm_file],
            stdout=subprocess.PIPE)
    greppedevmlog, err = p.communicate()
    greppedevmlog = greppedevmlog.strip()

    evmlines = greppedevmlog.split('\n')

    workers = {}
    wkr_upt_exc = 0
    wkr_mem_exc = 0
    wkr_stp = 0
    wkr_int = 0
    wkr_ext = 0
    for evm_log_line in evmlines:
        ts, pid = get_msg_timestamp_pid(evm_log_line)

        miqwkr_result = miqwkr.search(evm_log_line)
        if miqwkr_result:
            workerid = int(miqwkr_result.group(2))
            if workerid not in workers:
                workers[workerid] = MiqWorker()
                workers[workerid].worker_type = miqwkr_result.group(1)
                workers[workerid].pid = miqwkr_result.group(3)
                workers[workerid].worker_id = int(workerid)
                workers[workerid].start_ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
        elif 'evm_worker_uptime_exceeded' in evm_log_line:
            miqwkr_id_result = miqwkr_id.search(evm_log_line)
            if miqwkr_id_result:
                workerid = int(miqwkr_id_result.group(1))
                if workerid in workers:
                    if not workers[workerid].terminated:
                        wkr_upt_exc += 1
                        workers[workerid].terminated = 'evm_worker_uptime_exceeded'
                        workers[workerid].end_ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
        elif 'evm_worker_memory_exceeded' in evm_log_line:
            miqwkr_id_result = miqwkr_id.search(evm_log_line)
            if miqwkr_id_result:
                workerid = int(miqwkr_id_result.group(1))
                if workerid in workers:
                    if not workers[workerid].terminated:
                        wkr_mem_exc += 1
                        workers[workerid].terminated = 'evm_worker_memory_exceeded'
                        workers[workerid].end_ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
        elif 'evm_worker_stop' in evm_log_line:
            miqwkr_id_result = miqwkr_id.search(evm_log_line)
            if miqwkr_id_result:
                workerid = int(miqwkr_id_result.group(1))
                if workerid in workers:
                    if not workers[workerid].terminated:
                        wkr_stp += 1
                        workers[workerid].terminated = 'evm_worker_stop'
                        workers[workerid].end_ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
        elif 'Interrupt' in evm_log_line:
            for workerid in workers:
                if not workers[workerid].end_ts:
                    wkr_int += 1
                    workers[workerid].terminated = 'Interrupted'
                    workers[workerid].end_ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
        elif 'Worker exiting.' in evm_log_line:
            miqwkr_id_2_result = miqwkr_id_2.search(evm_log_line)
            if miqwkr_id_2_result:
                workerid = int(miqwkr_id_2_result.group(1))
                if workerid in workers:
                    if not workers[workerid].terminated:
                        wkr_ext += 1
                        workers[workerid].terminated = 'Worker Exited'
                        workers[workerid].end_ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')

    return workers, wkr_mem_exc, wkr_upt_exc, wkr_stp, wkr_int, wkr_ext, len(evmlines)


def generate_hourly_charts_and_csvs(hourly_buckets, charts_dir):
    for cmd in sorted(hourly_buckets):
        current_csv = 'hourly_' + cmd + '.csv'
        csv_rawdata_path = log_path.join('csv_output', current_csv)

        logger.info('Writing {} csvs/charts'.format(cmd))
        output_file = csv_rawdata_path.open('w', ensure=True)
        csvwriter = csv.DictWriter(output_file, fieldnames=MiqMsgBucket().headers,
            delimiter=',', quotechar='\'', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writeheader()
        for dt in sorted(hourly_buckets[cmd].keys()):
            linechartxaxis = []
            avgdeqtimings = []
            mindeqtimings = []
            maxdeqtimings = []
            avgdeltimings = []
            mindeltimings = []
            maxdeltimings = []
            cmd_put = []
            cmd_get = []

            sortedhr = sorted(hourly_buckets[cmd][dt].keys())
            for hr in sortedhr:
                linechartxaxis.append(str(hr))
                bk = hourly_buckets[cmd][dt][hr]

                avgdeqtimings.append(round(bk.avg_deq, 2))
                mindeqtimings.append(round(bk.min_deq, 2))
                maxdeqtimings.append(round(bk.max_deq, 2))
                avgdeltimings.append(round(bk.avg_del, 2))
                mindeltimings.append(round(bk.min_del, 2))
                maxdeltimings.append(round(bk.max_del, 2))
                cmd_put.append(bk.total_put)
                cmd_get.append(bk.total_get)
                bk.date = dt
                bk.hour = hr
                csvwriter.writerow(dict(bk))

            lines = {}
            lines['Put ' + cmd] = cmd_put
            lines['Get ' + cmd] = cmd_get
            line_chart_render(cmd + ' Command Put/Get Count', 'Hour during ' + dt,
                '# Count of Commands', linechartxaxis, lines,
                charts_dir.join('/{}-{}-cmdcnt.svg'.format(cmd, dt)))

            lines = {}
            lines['Average Dequeue Timing'] = avgdeqtimings
            lines['Min Dequeue Timing'] = mindeqtimings
            lines['Max Dequeue Timing'] = maxdeqtimings
            line_chart_render(cmd + ' Dequeue Timings', 'Hour during ' + dt, 'Time (s)',
                linechartxaxis, lines, charts_dir.join('/{}-{}-dequeue.svg'.format(cmd, dt)))

            lines = {}
            lines['Average Deliver Timing'] = avgdeltimings
            lines['Min Deliver Timing'] = mindeltimings
            lines['Max Deliver Timing'] = maxdeltimings
            line_chart_render(cmd + ' Deliver Timings', 'Hour during ' + dt, 'Time (s)',
                linechartxaxis, lines, charts_dir.join('/{}-{}-deliver.svg'.format(cmd, dt)))
        output_file.close()


def generate_raw_data_csv(rawdata_dict, csv_file_name):
    csv_rawdata_path = log_path.join('csv_output', csv_file_name)
    output_file = csv_rawdata_path.open('w', ensure=True)
    csvwriter = csv.DictWriter(output_file, fieldnames=rawdata_dict[rawdata_dict.keys()[0]].headers,
        delimiter=',', quotechar='\'', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writeheader()
    sorted_rd_keys = sorted(rawdata_dict.keys())
    for key in sorted_rd_keys:
        csvwriter.writerow(dict(rawdata_dict[key]))


def generate_statistics(the_list):
    if len(the_list) == 0:
        return '0,0,0,0,0,0'
    else:
        return '{},{},{},{},{},{}'.format(len(the_list), numpy.amin(the_list), numpy.amax(the_list),
            round(numpy.average(the_list), 2), round(numpy.std(the_list), 2),
            numpy.percentile(the_list, 90))


def generate_total_time_charts(msg_cmds, charts_dir):
    for cmd in sorted(msg_cmds):
        logger.info('Generating Total Time Chart for {}'.format(cmd))
        lines = {}
        lines['Total Time'] = msg_cmds[cmd]['total']
        lines['Queue'] = msg_cmds[cmd]['queue']
        lines['Execute'] = msg_cmds[cmd]['execute']
        line_chart_render(cmd + ' Total Time', 'Message #', 'Time (s)', [], lines,
            charts_dir.join('/{}-total.svg'.format(cmd)))


def generate_worker_charts(workers, top_workers, charts_dir):
    for worker in top_workers:
        logger.info('Generating Charts for Worker: {} Type: {}'.format(worker,
            workers[worker].worker_type))
        worker_name = '{}-{}'.format(worker, workers[worker].worker_type)

        lines = {}
        lines['Virt Mem'] = top_workers[worker]['virt']
        lines['Res Mem'] = top_workers[worker]['res']
        lines['Shared Mem'] = top_workers[worker]['share']
        line_chart_render(worker_name, 'Date Time', 'Memory in MiB',
            top_workers[worker]['datetimes'], lines,
            charts_dir.join('/{}-Memory.svg'.format(worker_name)))

        lines = {}
        lines['CPU %'] = top_workers[worker]['cpu_per']
        line_chart_render(worker_name, 'Date Time', 'CPU Usage', top_workers[worker]['datetimes'],
            lines, charts_dir.join('/{}-CPU.svg'.format(worker_name)))


def get_msg_args(log_line):
    miqmsg_args_result = miqmsg_args.search(log_line)
    if miqmsg_args_result:
        return miqmsg_args_result.group(1)
    else:
        return False


def get_msg_cmd(log_line):
    miqmsg_cmd_result = miqmsg_cmd.search(log_line)
    if miqmsg_cmd_result:
        return miqmsg_cmd_result.group(1)
    else:
        return False


def get_msg_del(log_line):
    miqmsg_del_result = miqmsg_del.search(log_line)
    if miqmsg_del_result:
        return float(miqmsg_del_result.group(1))
    else:
        return False


def get_msg_deq(log_line):
    miqmsg_deq_result = miqmsg_deq.search(log_line)
    if miqmsg_deq_result:
        return float(miqmsg_deq_result.group(1))
    else:
        return False


def get_msg_id(log_line):
    miqmsg_id_result = miqmsg_id.search(log_line)
    if miqmsg_id_result:
        return miqmsg_id_result.group(1)
    else:
        return False


def get_msg_timestamp_pid(log_line):
    # Obtains the timestamp and pid
    ts_result = log_stamp.search(log_line)
    if ts_result:
        dt_evm = '{} {}'.format(ts_result.group(1), ts_result.group(2))
        return dt_evm, ts_result.group(3)
    else:
        return False, 0


def hour_bucket_init(init):
    if init:
        return MiqMsgBucket()
    else:
        return {}


def line_chart_render(title, xtitle, ytitle, x_labels, lines, fname):
    line_chart = pygal.Line()
    line_chart.title = title
    line_chart.x_title = xtitle
    line_chart.y_title = ytitle
    line_chart.title_font_size = 8
    line_chart.legend_font_size = 8
    line_chart.truncate_legend = 26
    line_chart.x_labels = x_labels
    sortedlines = sorted(lines.keys())
    for line in sortedlines:
        line_chart.add(line, lines[line])
    line_chart.render_to_file(str(fname))


def messages_to_hourly_buckets(messages, test_start, test_end):
    hr_bkt = {}
    # Hour buckets look like: hr_bkt[msg_cmd][msg_date][msg_hour] = MiqMsgBucket()
    for msg in messages:
        # put on queue, deals with queuing:
        msg_cmd = messages[msg].msg_cmd
        putdate = messages[msg].puttime[:10]
        puthour = messages[msg].puttime[11:13]
        if msg_cmd not in hr_bkt:
            hr_bkt[msg_cmd] = provision_hour_buckets(test_start, test_end)

        hr_bkt[msg_cmd][putdate][puthour].total_put += 1
        hr_bkt[msg_cmd][putdate][puthour].sum_deq += messages[msg].deq_time
        if (hr_bkt[msg_cmd][putdate][puthour].min_deq == 0 or
                hr_bkt[msg_cmd][putdate][puthour].min_deq > messages[msg].deq_time):
            hr_bkt[msg_cmd][putdate][puthour].min_deq = messages[msg].deq_time
        if (hr_bkt[msg_cmd][putdate][puthour].max_deq == 0 or
                hr_bkt[msg_cmd][putdate][puthour].max_deq < messages[msg].deq_time):
            hr_bkt[msg_cmd][putdate][puthour].max_deq = messages[msg].deq_time
        hr_bkt[msg_cmd][putdate][puthour].avg_deq = \
            hr_bkt[msg_cmd][putdate][puthour].sum_deq / hr_bkt[msg_cmd][putdate][puthour].total_put

        # Get time is when the message is delivered
        getdate = messages[msg].gettime[:10]
        gethour = messages[msg].gettime[11:13]

        hr_bkt[msg_cmd][getdate][gethour].total_get += 1
        hr_bkt[msg_cmd][getdate][gethour].sum_del += messages[msg].del_time
        if (hr_bkt[msg_cmd][getdate][gethour].min_del == 0 or
                hr_bkt[msg_cmd][getdate][gethour].min_del > messages[msg].del_time):
            hr_bkt[msg_cmd][getdate][gethour].min_del = messages[msg].del_time
        if (hr_bkt[msg_cmd][getdate][gethour].max_del == 0 or
                hr_bkt[msg_cmd][getdate][gethour].max_del < messages[msg].del_time):
            hr_bkt[msg_cmd][getdate][gethour].max_del = messages[msg].del_time

        hr_bkt[msg_cmd][getdate][gethour].avg_del = \
            hr_bkt[msg_cmd][getdate][gethour].sum_del / hr_bkt[msg_cmd][getdate][gethour].total_get
    return hr_bkt


def messages_to_statistics_csv(messages, statistics_file_name):
    all_statistics = []
    for msg_id in messages:
        msg = messages[msg_id]

        added = False
        if len(all_statistics) > 0:
            for msg_statistics in all_statistics:
                if msg_statistics.cmd == msg.msg_cmd:

                    if msg.del_time > 0:
                        msg_statistics.delivertimes.append(float(msg.del_time))
                        msg_statistics.gets += 1
                    msg_statistics.dequeuetimes.append(float(msg.deq_time))
                    msg_statistics.totaltimes.append(float(msg.total_time))
                    msg_statistics.puts += 1
                    added = True
                    break

        if not added:
            msg_statistics = MiqMsgLists()
            msg_statistics.cmd = msg.msg_cmd
            if msg.del_time > 0:
                msg_statistics.delivertimes.append(float(msg.del_time))
                msg_statistics.gets = 1
            msg_statistics.dequeuetimes.append(float(msg.deq_time))
            msg_statistics.totaltimes.append(float(msg.total_time))
            msg_statistics.puts = 1
            all_statistics.append(msg_statistics)

    csvdata_path = log_path.join('csv_output', statistics_file_name)
    outputfile = csvdata_path.open('w', ensure=True)
    outputfile.write('cmd,puts,gets,'
        'deq_time_samples,deq_time_min,deq_time_max,deq_time_avg,deq_time_std,deq_time_90,'
        'del_time_samples,del_time_min,del_time_max,del_time_avg,del_time_std,del_time_90,'
        'tot_time_samples,tot_time_min,tot_time_max,tot_time_avg,tot_time_std,tot_time_90\n')

    # Contents of CSV
    for msg_statistics in sorted(all_statistics, key=lambda x: x.cmd):
        if msg_statistics.gets > 1:
            logger.debug('Samples/Avg/90th/Std: {} : {} : {} : {},Cmd: {}'.format(
                str(len(msg_statistics.totaltimes)).rjust(7),
                str(round(numpy.average(msg_statistics.totaltimes))).rjust(7),
                str(round(numpy.percentile(msg_statistics.totaltimes, 90))).rjust(7),
                str(round(numpy.std(msg_statistics.totaltimes))).rjust(7),
                msg_statistics.cmd))
        stats = '{},{},{},{},{},{}\n'.format(msg_statistics.cmd,
            msg_statistics.puts, msg_statistics.gets,
            generate_statistics(numpy.array(msg_statistics.dequeuetimes)),
            generate_statistics(numpy.array(msg_statistics.delivertimes)),
            generate_statistics(numpy.array(msg_statistics.totaltimes)))
        outputfile.write(stats)
    outputfile.close()


def provision_hour_buckets(test_start, test_end, init=True):
    buckets = {}
    start_date = datetime.strptime(test_start[:10], '%Y-%m-%d')
    end_date = datetime.strptime(test_end[:10], '%Y-%m-%d')
    start_hr = int(test_start[11:13])
    end_hr = int(test_end[11:13]) + 1

    delta_date = end_date - start_date
    for dates in range(delta_date.days + 1):
        new_date = start_date + timedelta(days=dates)
        buckets[new_date.strftime('%Y-%m-%d')] = {}

    sorteddt = sorted(buckets.keys())
    for date in sorteddt:
        if date == test_start[:10]:
            if date == test_end[:10]:
                for hr in range(start_hr, end_hr):
                    buckets[date][str(hr).zfill(2)] = hour_bucket_init(init)
            else:
                for hr in range(start_hr, 24):
                    buckets[date][str(hr).zfill(2)] = hour_bucket_init(init)
        elif date == test_end[:10]:
            for hr in range(end_hr):
                buckets[date][str(hr).zfill(2)] = hour_bucket_init(init)
        else:
            for hr in range(24):
                buckets[date][str(hr).zfill(2)] = hour_bucket_init(init)
    if init:
        buckets[''] = {}
        buckets[''][''] = MiqMsgBucket()
    return buckets


def top_to_workers(workers, top_file):
    # Find first miqtop log line
    p = subprocess.Popen(['grep', '-m', '1', '^miqtop\:', top_file], stdout=subprocess.PIPE)
    greppedtop, err = p.communicate()
    str_start = greppedtop.index('is->')
    miqtop_time = du_parser.parse(greppedtop[str_start:], fuzzy=True, ignoretz=True)
    timezone_offset = int(greppedtop[str_start + 34:str_start + 37])
    miqtop_time = miqtop_time - timedelta(hours=timezone_offset)
    # Time zones are also difficult to deal with here
    logger.debug('Timezone Offset: {}'.format(timezone_offset))
    logger.debug('Starting miqtop time: {}'.format(miqtop_time))

    runningtime = time()
    grep_pids = ''
    for wkr in workers:
        grep_pids = '{}^{}\s\\|'.format(grep_pids, workers[wkr].pid)
    grep_pattern = '{}^top\s\-\s\\|^miqtop\:'.format(grep_pids)
    # Use grep to reduce # of lines to sort through
    p = subprocess.Popen(['grep', grep_pattern, top_file], stdout=subprocess.PIPE)
    greppedtop, err = p.communicate()
    timediff = time() - runningtime
    logger.info('Grepped top_output for pids & time data in {}'.format(timediff))

    # This is very ugly because miqtop does include the date but top does not
    # Also pids can be duplicated, so careful attention to detail on when a pid starts and ends
    top_lines = greppedtop.strip().split('\n')
    line_count = 0
    top_workers = {}
    cur_time = None
    miqtop_ahead = True
    runningtime = time()
    for top_line in top_lines:
        line_count += 1
        if 'top - ' in top_line:
            # top - 11:00:43
            cur_hour = int(top_line[6:8])
            cur_min = int(top_line[9:11])
            cur_sec = int(top_line[12:14])
            if miqtop_ahead:
                # Have not found miqtop time yet so we must rely on miqtop time "ahead"
                if cur_hour <= miqtop_time.hour:
                    cur_time = miqtop_time.replace(hour=cur_hour, minute=cur_min, second=cur_sec) \
                        - timedelta(hours=timezone_offset)
                else:
                    # miqtop_time is ahead by date
                    logger.info('miqtop_time is ahead by one day')
                    cur_time = miqtop_time - timedelta(days=1)
                    cur_time = cur_time.replace(hour=cur_hour, minute=cur_min, second=cur_sec) \
                        - timedelta(hours=timezone_offset)
            else:
                cur_time = miqtop_time.replace(hour=cur_hour, minute=cur_min, second=cur_sec) \
                    - timedelta(hours=timezone_offset)

        elif 'miqtop: ' in top_line:
            miqtop_ahead = False
            # miqtop which includes the date
            # miqtop: timesync: date time is-> Mon Jan 26 11:01:01 EST 2015 -0500
            # miqtop: start: date time is-> Mon Jan 26 08:57:39 EST 2015 -0500
            str_start = top_line.index('is->')
            miqtop_time = du_parser.parse(top_line[str_start:], fuzzy=True, ignoretz=True)
            # Timezone conversion...
            # Time logged in top is the system's time which is ahead/behind by the timezone offset
            timezone_offset = int(top_line[str_start + 34:str_start + 37])
            miqtop_time = miqtop_time - timedelta(hours=timezone_offset)
        else:
            top_results = miq_top.search(top_line)
            if top_results:
                top_pid = top_results.group(1)
                top_virt = convert_mem_to_mib(top_results.group(2))
                top_res = convert_mem_to_mib(top_results.group(3))
                top_share = convert_mem_to_mib(top_results.group(4))
                top_cpu_per = float(top_results.group(5))
                top_mem_per = float(top_results.group(6))
                for worker in workers:
                    if workers[worker].pid == top_pid:
                        if cur_time > workers[worker].start_ts and \
                                (workers[worker].end_ts == '' or cur_time < workers[worker].end_ts):
                            w_id = workers[worker].worker_id
                            if w_id not in top_workers:
                                top_workers[w_id] = {}
                                top_workers[w_id]['datetimes'] = []
                                top_workers[w_id]['virt'] = []
                                top_workers[w_id]['res'] = []
                                top_workers[w_id]['share'] = []
                                top_workers[w_id]['cpu_per'] = []
                                top_workers[w_id]['mem_per'] = []
                            top_workers[w_id]['datetimes'].append(str(cur_time))
                            top_workers[w_id]['virt'].append(top_virt)
                            top_workers[w_id]['res'].append(top_res)
                            top_workers[w_id]['share'].append(top_share)
                            top_workers[w_id]['cpu_per'].append(top_cpu_per)
                            top_workers[w_id]['mem_per'].append(top_mem_per)
                            break
            else:
                logger.error('Issue with miq_top regex or grepping of top file:{}'.format(top_line))
        if (line_count % 20000) == 0:
            timediff = time() - runningtime
            runningtime = time()
            logger.info('Count {} : Parsed 20000 lines in {}'.format(line_count, timediff))
    return top_workers, len(top_lines)


def perf_process_evm(evm_file, top_file):
    msg_filters = {
        '-hourly': re.compile(r'\"[0-9\-]*T[0-9\:]*Z\",\s\"hourly\"'),
        '-daily': re.compile(r'\"[0-9\-]*T[0-9\:]*Z\",\s\"daily\"'),
        '-EmsRedhat': re.compile(r'\[\[\"EmsRedhat\"\,\s[0-9]*\]\]'),
        '-EmsVmware': re.compile(r'\[\[\"EmsVmware\"\,\s[0-9]*\]\]'),
        '-EmsAmazon': re.compile(r'\[\[\"EmsAmazon\"\,\s[0-9]*\]\]'),
        '-EmsOpenstack': re.compile(r'\[\[\"EmsOpenstack\"\,\s[0-9]*\]\]')
    }

    starttime = time()
    initialtime = starttime

    logger.info('----------- Parsing evm log file for messages -----------')
    messages, msg_cmds, test_start, test_end, msg_lc = evm_to_messages(evm_file, msg_filters)
    timediff = time() - starttime
    logger.info('----------- Completed Parsing evm log file -----------')
    logger.info('Parsed {} lines of evm log file for messages in {}'.format(msg_lc, timediff))
    logger.info('Total # of Messages: {}'.format(len(messages)))
    logger.info('Total # of Commands: {}'.format(len(msg_cmds)))
    logger.info('Start Time: {}'.format(test_start))
    logger.info('End Time: {}'.format(test_end))

    logger.info('----------- Parsing evm log file for workers -----------')
    starttime = time()
    workers, wkr_mem_exc, wkr_upt_exc, wkr_stp, wkr_int, wkr_ext, wkr_lc = evm_to_workers(evm_file)
    timediff = time() - starttime
    logger.info('----------- Completed Parsing evm log for workers -----------')
    logger.info('Parsed {} lines of evm log file for workers in {}'.format(wkr_lc, timediff))
    logger.info('Total # of Workers: {}'.format(len(workers)))
    logger.info('# Workers Memory Exceeded: {}'.format(wkr_mem_exc))
    logger.info('# Workers Uptime Exceeded: {}'.format(wkr_upt_exc))
    logger.info('# Workers Exited: {}'.format(wkr_ext))
    logger.info('# Workers Stopped: {}'.format(wkr_stp))
    logger.info('# Workers Interrupted: {}'.format(wkr_int))

    logger.info('----------- Parsing top_output log file for worker CPU/Mem -----------')
    starttime = time()
    top_workers, tp_lc = top_to_workers(workers, top_file)
    timediff = time() - starttime
    logger.info('----------- Completed Parsing top_output log -----------')
    logger.info('Parsed {} lines of top_output file for workers in {}'.format(tp_lc, timediff))

    charts_dir = log_path.join('charts')
    if not os.path.exists(str(charts_dir)):
        os.mkdir(str(charts_dir))

    logger.info('----------- Generating Raw Data csv files -----------')
    starttime = time()
    generate_raw_data_csv(messages, 'messages-rawdata.csv')
    generate_raw_data_csv(workers, 'workers-rawdata.csv')
    timediff = time() - starttime
    logger.info('Generated Raw Data csv files in: {}'.format(timediff))

    logger.info('----------- Generating Hourly Buckets -----------')
    starttime = time()
    hr_bkt = messages_to_hourly_buckets(messages, test_start, test_end)
    timediff = time() - starttime
    logger.info('Generated Hourly Buckets in: {}'.format(timediff))

    logger.info('----------- Generating Hourly Charts and csvs -----------')
    starttime = time()
    generate_hourly_charts_and_csvs(hr_bkt, charts_dir)
    timediff = time() - starttime
    logger.info('Generated Hourly Charts and csvs in: {}'.format(timediff))

    logger.info('----------- Generating Total Time Charts -----------')
    starttime = time()
    generate_total_time_charts(msg_cmds, charts_dir)
    timediff = time() - starttime
    logger.info('Generated Total Time Charts in: {}'.format(timediff))

    logger.info('----------- Generating Worker Charts -----------')
    starttime = time()
    generate_worker_charts(workers, top_workers, charts_dir)
    timediff = time() - starttime
    logger.info('Generated Worker Charts in: {}'.format(timediff))

    logger.info('----------- Generating Message Statistics -----------')
    starttime = time()
    messages_to_statistics_csv(messages, 'messages-statistics.csv')
    timediff = time() - starttime
    logger.info('Generated Message Statistics in: {}'.format(timediff))

    logger.info('----------- Writing html files for report -----------')
    # Write an index.html file for fast switching between graphs:
    html_index = log_path.join('index.html').open('w', ensure=True)
    cmd = hr_bkt.keys()[0]
    html_index.write(
        '<html>\n'
        '<title>Performance Worker/Message Metrics</title>\n'
        '<frameset cols="17%,83%">\n'
        '   <frame src="msg_menu.html" name="menu"/>\n'
        '   <frame src="charts/{}-{}-dequeue.svg" name="showframe" />\n'
        '</frameset>\n'
        '</html>'.format(cmd, sorted(hr_bkt[cmd].keys())[-1]))
    html_index.close()

    # Write the side bar menu html file
    html_menu = log_path.join('msg_menu.html').open('w', ensure=True)
    html_menu.write('<html>\n')
    html_menu.write('<font size="2">')
    html_menu.write('<a href="worker_menu.html" target="menu">Worker CPU/Memory</a><br>')
    html_menu.write('Parsed {} lines for messages<br>'.format(msg_lc))
    html_menu.write('Start Time: {}<br>'.format(test_start))
    html_menu.write('End Time: {}<br>'.format(test_end))
    html_menu.write('Message Count: {}<br>'.format(len(messages)))
    html_menu.write('Command Count: {}<br>'.format(len(msg_cmds)))
    html_menu.write('Parsed {} lines for workers<br>'.format(wkr_lc, timediff))
    html_menu.write('Total Workers: {}<br>'.format(len(workers)))
    html_menu.write('Workers Memory Exceeded: {}<br>'.format(wkr_mem_exc))
    html_menu.write('Workers Uptime Exceeded: {}<br>'.format(wkr_upt_exc))
    html_menu.write('Workers Exited: {}<br>'.format(wkr_ext))
    html_menu.write('Workers Stopped: {}<br>'.format(wkr_stp))
    html_menu.write('Workers Interrupted: {}<br>'.format(wkr_int))

    html_menu.write('<a href="csv_output/messages-rawdata.csv">messages-rawdata.csv</a><br>')
    html_menu.write('<a href="csv_output/messages-statistics.csv">messages-statistics.csv</a><br>')
    html_menu.write('<a href="csv_output/workers-rawdata.csv">workers-rawdata.csv</a><br><br>')

    # Sorts by the the messages which have the most, descending
    for cmd in sorted(msg_cmds, key=lambda x: len(msg_cmds[x]['total']), reverse=True):
        html_menu.write('<a href="csv_output/hourly_{}.csv"'
            'target="showframe">{}</a><br>'.format(cmd, cmd))
        html_menu.write('<a href="charts/{}-total.svg" target="showframe">'
            'Total Messages: {} </a><br>'.format(cmd, len(msg_cmds[cmd]['total'])))
        for dt in sorted(hr_bkt[cmd].keys()):
            if dt == '':
                html_menu.write('Queued:&nbsp;')
            else:
                html_menu.write('{}:&nbsp;'.format(dt))
            html_menu.write('<a href="charts/{}-{}-cmdcnt.svg" target="showframe">'
                'cnt</a>&nbsp;|&nbsp;'.format(cmd, dt))
            html_menu.write('<a href="charts/{}-{}-dequeue.svg" target="showframe">'
                'deq</a>&nbsp;|&nbsp;'.format(cmd, dt))
            html_menu.write('<a href="charts/{}-{}-deliver.svg" target="showframe">'
                'del</a><br>'.format(cmd, dt))
        html_menu.write('<br>')
    html_menu.write('</font>')
    html_menu.write('</html>')
    html_menu.close()

    html_wkr_menu = log_path.join('worker_menu.html').open('w', ensure=True)
    html_wkr_menu.write('<html>\n')
    html_wkr_menu.write('<font size="2">')
    html_wkr_menu.write('<a href="msg_menu.html" target="menu">Message Latencies</a><br>')
    html_wkr_menu.write('Parsed {} lines for messages<br>'.format(msg_lc))
    html_wkr_menu.write('Start Time: {}<br>'.format(test_start))
    html_wkr_menu.write('End Time: {}<br>'.format(test_end))
    html_wkr_menu.write('Message Count: {}<br>'.format(len(messages)))
    html_wkr_menu.write('Command Count: {}<br>'.format(len(msg_cmds)))

    html_wkr_menu.write('Parsed {} lines for workers<br>'.format(wkr_lc, timediff))
    html_wkr_menu.write('Total Workers: {}<br>'.format(len(workers)))
    html_wkr_menu.write('Workers Memory Exceeded: {}<br>'.format(wkr_mem_exc))
    html_wkr_menu.write('Workers Uptime Exceeded: {}<br>'.format(wkr_upt_exc))
    html_wkr_menu.write('Workers Exited: {}<br>'.format(wkr_ext))
    html_wkr_menu.write('Workers Stopped: {}<br>'.format(wkr_stp))
    html_wkr_menu.write('Workers Interrupted: {}<br>'.format(wkr_int))

    html_wkr_menu.write('<a href="csv_output/messages-rawdata.csv">messages-rawdata.csv</a><br>')
    html_wkr_menu.write('<a href="csv_output/messages-statistics.csv">'
        'messages-statistics.csv</a><br>')
    html_wkr_menu.write('<a href="csv_output/workers-rawdata.csv">workers-rawdata.csv</a><br><br>')

    html_wkr_menu.write('Running Workers:<br>')
    w_type = ''
    for worker_id in sorted(workers, key=lambda x: workers[x].worker_type):
        if workers[worker_id].terminated == '':
            if not w_type == workers[worker_id].worker_type:
                w_type = workers[worker_id].worker_type
                html_wkr_menu.write('{}<br>'.format(w_type))
            worker_name = '{}-{}'.format(worker_id, workers[worker_id].worker_type)
            html_wkr_menu.write('{} - '.format(worker_id))
            html_wkr_menu.write('<a href="charts/{}-CPU.svg" target="showframe">CPU</a>'
                ' | '.format(worker_name))
            html_wkr_menu.write('<a href="charts/{}-Memory.svg" target="showframe">Memory</a><br>'
                ''.format(worker_name))

    html_wkr_menu.write('<br>Terminated Workers:<br>')
    w_type = ''
    for worker_id in sorted(workers, key=lambda x: workers[x].worker_type):
        if not workers[worker_id].terminated == '':
            if not w_type == workers[worker_id].worker_type:
                w_type = workers[worker_id].worker_type
                html_wkr_menu.write('<br>{}<br>'.format(w_type))
            worker_name = '{}-{}'.format(worker_id, workers[worker_id].worker_type)
            html_wkr_menu.write('{} - '.format(worker_id))
            html_wkr_menu.write('<a href="charts/{}-CPU.svg" target="showframe">CPU</a>'
                ' | '.format(worker_name))
            html_wkr_menu.write('<a href="charts/{}-Memory.svg" target="showframe">Memory</a><br>'
                ''.format(worker_name))
            html_wkr_menu.write('{}<br>'.format(workers[worker_id].terminated))
    html_wkr_menu.write('</font>')
    html_wkr_menu.write('</html>')
    html_wkr_menu.close()

    timediff = time() - initialtime
    logger.info('----------- Finished -----------')
    logger.info('Total time processing evm log file and generating report: {}'.format(timediff))


class MiqMsgStat(object):

    def __init__(self):
        self.headers = ['msg_id', 'msg_cmd', 'msg_args', 'pid_put', 'pid_get', 'puttime', 'gettime',
            'deq_time', 'del_time', 'total_time']
        self.msg_id = ''
        self.msg_cmd = ''
        self.msg_args = ''
        self.pid_put = ''
        self.pid_get = ''
        self.puttime = ''
        self.gettime = ''
        self.deq_time = 0.0
        self.del_time = 0.0
        self.total_time = 0.0

    def __iter__(self):
        for header in self.headers:
            yield header, getattr(self, header)

    def __str__(self):
        return self.msg_cmd + ' : ' + self.msg_args + ' : ' + self.pid_put + ' : ' + self.pid_get \
            + ' : ' + self.puttime + ' : ' + self.gettime + ' : ' + str(self.deq_time) + ' : ' + \
            str(self.del_time) + ' : ' + str(self.total_time)


class MiqMsgLists(object):

    def __init__(self):
        self.cmd = ''
        self.puts = 0
        self.gets = 0
        self.dequeuetimes = []
        self.delivertimes = []
        self.totaltimes = []


class MiqMsgBucket(object):
    def __init__(self):
        self.headers = ['date', 'hour', 'total_put', 'total_get', 'sum_deq', 'min_deq', 'max_deq',
            'avg_deq', 'sum_del', 'min_del', 'max_del', 'avg_del']
        self.date = ''
        self.hour = ''
        self.total_put = 0
        self.total_get = 0
        self.sum_deq = 0.0
        self.min_deq = 0.0
        self.max_deq = 0.0
        self.avg_deq = 0.0
        self.sum_del = 0.0
        self.min_del = 0.0
        self.max_del = 0.0
        self.avg_del = 0.0

    def __iter__(self):
        for header in self.headers:
            yield header, getattr(self, header)

    def __str__(self):
        return self.date + ' : ' + self.hour + ' : ' + str(self.total_put) \
            + ' : ' + str(self.total_get) + ' : ' + str(self.sum_deq) + ' : ' + str(self.min_deq) \
            + ' : ' + str(self.max_deq) + ' : ' + str(self.avg_deq) + ' : ' + str(self.sum_del) \
            + ' : ' + str(self.min_del) + ' : ' + str(self.max_del) + ' : ' + str(self.avg_del)


class MiqWorker(object):

    def __init__(self):
        self.headers = ['worker_id', 'worker_type', 'pid', 'start_ts', 'end_ts', 'terminated']
        self.worker_id = 0
        self.worker_type = ''
        self.pid = ''
        self.start_ts = ''
        self.end_ts = ''
        self.terminated = ''

    def __iter__(self):
        for header in self.headers:
            yield header, getattr(self, header)

    def __str__(self):
        return self.worker_id + ' : ' + self.worker_type + ' : ' + self.pid + ' : ' + \
            str(self.start_ts) + ' : ' + str(self.end_ts) + ' : ' + self.terminated

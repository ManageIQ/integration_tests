#! /bin/env python2
import sys
import re
from collections import defaultdict
import json
from datetime import datetime
import pygal


events = defaultdict(dict)


def process(line):
    pww = re.findall('\[(?P<date>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{6}) '
                     '#\d+:[a-f0-9]+]\s+(\w+)\s--\s:\s+MIQ\((?P<thing>.*)\)\s+(?P<msg>.*)', line)
    if pww:
        pww = pww[0]
        if "Message id:" in pww[3]:
            mid = re.findall('Message id:\s+?\[(\d*?)\],*', pww[3])[0]
        if "Target id:" in pww[3]:
            tid = re.findall('Target id:\s+?\[(.*?)\],', pww[3])[0]
            if tid:
                events[mid]['tid'] = tid

        if pww[2] == 'MiqQueue.put':
            events[mid]['start-time'] = datetime.strptime(pww[0], '%Y-%m-%dT%H:%M:%S.%f')
            if "Args:" in pww[3]:
                args = re.findall('Args:\s+(.*)', pww[3])[0]
                args = args.replace(":", "")
                args = args.replace("=>", ":")
                try:
                    p = json.loads(args)
                    events[mid]['args'] = p
                except:
                    pass

            event_type = ""
            if ' :name' in pww[3]:
                event_type = re.findall(' :name=>"(.*?)"', pww[3])[0]
            elif ' "eventType"=>"' in pww[3]:
                event_type = re.findall(' "eventType"=>"(.*?)"', pww[3])[0]
            if event_type:
                events[mid]['event_type'] = event_type

            host_name = ""
            if ' "host"=>{"name"=>"' in pww[3]:
                host_name = re.findall(' "host"=>{"name"=>"(.*?)"', pww[3])[0]
            else:
                host_name = tid
            if host_name:
                events[mid]['host_name'] = host_name

        elif pww[2] == 'MiqQueue.delivered':
            events[mid]['end-time'] = datetime.strptime(pww[0], '%Y-%m-%dT%H:%M:%S.%f')
            try:
                events[mid]['duration'] = events[mid]['end-time'] - events[mid]['start-time']
            except:
                events[mid]['duration'] = None

filename = sys.argv[1]
with open(filename) as f:
    data = f.readlines()
for line in data:
    process(line)

date_list = []
dura_list = []


for event in sorted(events.keys()):
    if 'host_name' in events[event] and 'event_type' in events[event] \
       and 'duration' in events[event]:
        print "{}, {}, {}, {}, {}".format(event, events[event]['start-time'],
            events[event]['host_name'],
            events[event]['event_type'],
            events[event]['duration'].total_seconds())
        date_list.append(events[event]['end-time'])
        dura_list.append(events[event]['duration'].total_seconds())

line_chart = pygal.Line()
line_chart.title = 'Duration of event (in s)'
line_chart.x_labels = map(str, date_list)
line_chart.add('Duration', dura_list)
line_chart.render_to_file('bar_chart.svg')

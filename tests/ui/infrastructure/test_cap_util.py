# -*- coding: utf-8 -*-

import pytest
import psycopg2
import sys
from unittestzero import Assert

@pytest.fixture # IGNORE:E1101
def vm_page(home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()

@pytest.fixture # IGNORE:E1101
def optimize_page(home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu("Optimize").sub_navigation_menu("Utilization").click()

@pytest.mark.nondestructive  # IGNORE:E1101
@pytest.mark.usefixtures("maximized")  # IGNORE:E1101
class TestCapAndUtil:
    _lookup = {'High': 'max', 'Average': 'avg', 'Low': 'min'}
    def test_vm_data(self, mozwebqa, vm_page):
        try:
            db_stat = self.fetch_db_data(resource_id=8, resource_type='VmOrTemplate', interval='daily', table='metric_rollups_06', desired_data=[
                                                                                                                                           ('cpu_usagemhz_rate_average', 'cpu_avg', float),
                                                                                                                                           ('max_cpu_usagemhz_rate_average', 'cpu_max', float),
                                                                                                                                           ('min_cpu_usagemhz_rate_average', 'cpu_min', float),
                                                                                                                                           ('max_cpu_usage_rate_average', 'cpu_usage_max', float),
                                                                                                                                           ('min_cpu_usage_rate_average', 'cpu_usage_min', float),
                                                                                                                                           ('cpu_usage_rate_average', 'cpu_usage_avg', float),
                                                                                                                                           ('max_derived_memory_used', 'mem_max', float),
                                                                                                                                           ('min_derived_memory_used', 'mem_min', float),
                                                                                                                                           ('derived_memory_used', 'mem_avg', float),
                                                                                                                                           ('max_mem_usage_absolute_average', 'mem_usage_max', float),
                                                                                                                                           ('min_mem_usage_absolute_average', 'mem_usage_min', float),
                                                                                                                                           ('mem_usage_absolute_average', 'mem_usage_avg', float),
                                                                                                                                           ])
            ui_stat = {}

            # Now find the same items from the UI
            #vm_pg = home_page_logged_in.header.site_navigation_menu("Services").sub_navigation_menu("Virtual Machines").click()
            vm_pg = vm_page
            Assert.true(vm_pg.is_the_current_page)
            detail = vm_pg.find_vm_page('dgao_cfme_5108_dnd', None, True, True).details.get_section('Normal Operating Ranges (over 30 days)')
    
            def gen_items(item_list):
                for i in item_list:
                    yield i
                
            # TODO: Simplify this; at the time of this creation, the value is not very helpful in identifying the section. Also fetching key
            # could produce a selenium 'The element could not be found' exception.
            # As a result, we have to do it the ghetto way (hardcode)
            hardcode_sections = ['cpu', 'cpu_usage', 'mem', 'mem_usage']
            catagory = gen_items(hardcode_sections)

            for item in detail.items:
                if '\n' in item.value: # data row
                    pieces = item.value.split('\n')
                    section = next(catagory)
                    for stat_line in pieces:
                        k = "%s_%s" % (section, self._lookup[str(stat_line.split(' ')[0])])
                        v = float(stat_line.split(' ')[1].replace('%', ''))
                        ui_stat[k] = v

            # Compare the results
            for k in db_stat.keys():
                Assert.true(self.compare_stat(db_stat[k], ui_stat[k]))

        except:
            raise


    def test_host_data(self, mozwebqa, optimize_page):
        try:
            db_stat = self.fetch_db_data(resource_id=2, resource_type='Host', interval='daily', table='metric_rollups_06', desired_data=[
                                                                                                                                   ('cpu_usagemhz_rate_average', 'cpu_avg', float),
                                                                                                                                   ('mem_usage_absolute_average', 'mem_usage_avg', float),
                                                                                                                                   ])
            ui_stat = {}

            opt_pg = optimize_page
            Assert.true(opt_pg.is_the_current_page)
            report_pg = opt_pg.click_on_node('qeblade28.rhq.lab.eng.bos.redhat.com').click_on_report()
            
            cpu_section = report_pg.details.sections[-2]
            mem_section = report_pg.details.sections[-1]
        
            ui_stat['cpu_avg'] = float(cpu_section.items[2].value.split(' ')[0]) * 1000 # since the reported value is in Ghz
            ui_stat['mem_usage_avg'] = float(mem_section.items[2].value.split(' ')[0])

            # Compare the results
            for k in db_stat.keys():
                Assert.true(self.compare_stat(db_stat[k], ui_stat[k]))

        except: 
            raise

    def test_cluster_data(self, mozwebqa, optimize_page):
        try:
            db_stat = self.fetch_db_data(resource_id=1, resource_type='EmsCluster', interval='daily', table='metric_rollups_06', desired_data=[
                                                                                                                                   ('cpu_usagemhz_rate_average', 'cpu_avg', float),
                                                                                                                                   ('mem_usage_absolute_average', 'mem_usage_avg', float),
                                                                                                                                   ('derived_cpu_available', 'total_cpu', float),
                                                                                                                                   ('derived_memory_available', 'total_mem', float),
                                                                                                                                   ])
            ui_stat = {}

            opt_pg = optimize_page
            Assert.true(opt_pg.is_the_current_page)
            report_pg = opt_pg.click_on_node('test_cluster').click_on_report()
            
            cpu_section = report_pg.details.sections[-2]
            mem_section = report_pg.details.sections[-1]
        
            ui_stat['total_cpu'] = float(cpu_section.items[0].value.split(' ')[0]) * 1000 # since the reported value is in Ghz
            ui_stat['cpu_avg'] = float(cpu_section.items[3].value.split(' ')[0]) * 1000 # since the reported value is in Ghz
            ui_stat['total_mem'] = float(mem_section.items[0].value.split(' ')[0]) * 1000 # since the reported value is in Gb
            ui_stat['mem_usage_avg'] = float(mem_section.items[3].value.split(' ')[0])

            # Compare the results
            for k in db_stat.keys():
                Assert.true(self.compare_stat(db_stat[k], ui_stat[k]))

        except: 
            raise

    # Utility Methods
    def compare_stat(self, x, y):
        diff = x*.3
        print x, y, diff
        return x-diff < y < x+diff        

    def fetch_db_data(self, resource_id, resource_type, interval, table, desired_data):
        try:
            db_stat = {}
            count = {} # used to calculate running averages when necessary

            # make db connections
            conn = psycopg2.connect("dbname='vmdb_production' user='root' host='10.16.120.99' password='smartvm'")
            cur = conn.cursor()
            cur.execute("select * from %s where resource_id=%s and resource_type='%s' and capture_interval_name='%s';" % (table, resource_id, resource_type, interval))
            colnames = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            # extract data
            for row in rows:
                data = dict(zip(colnames, list(row)))

                # further expand data
                for mm_data in data['min_max'].split('\n'):
                    if mm_data.find(':') == 0:
                        mm_data = mm_data[1:]
                    key = mm_data.split(':', 1)[0]
                    val = mm_data.split(':', 1)[-1]
                    if not data.has_key(key):
                        data[key] = val

                intermediate = {}
                for data_key, key, t in desired_data:
                    if not data.has_key(data_key) or data[data_key] == None:
                        continue
                    intermediate[key] = t(data[data_key])

                # do running average
                for k, v in intermediate.items():
                    if not db_stat.has_key(k):
                        db_stat[k] = v
                        count[k] = 1
                    else:
                        # i wonder if there's a better way to calculate the
                        # running average w/o utilizing count array
                        db_stat[k] = (db_stat[k]*count[k] + v) / (count[k]+1)
                        count[k] = count[k]+1
            return db_stat

        except:
            #exc_type, exc_value, exc_traceback = sys.exc_info()
            #print "Unexpected error:", exc_type, exc_value
            #print exc_traceback
            raise
        finally:
            conn.close()

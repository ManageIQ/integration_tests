import re

from cfme.utils.log import logger


def compare_data(table_data, graph_data, legends, tolerance=1):
    """ Compare Utilization graph and table data.
    Args:
        table_data : Data from Utilization table
        graph_data : Data from Utilization graph
        legends : Legends in graph; which will help for comparison
        tolerance : Its error which we have to allow while comparison
    """
    for row in table_data:
        for key, data in graph_data.items():
            if any([re.match(key, item) for item in row['Date/Time'].split()]):
                for leg in legends:
                    table_item = row[leg].replace(',', '').replace('%', '').split()
                    if table_item:
                        table_item = round(float(table_item[0]), 1)
                        graph_item = round(
                            float(data[leg].replace(',', '').replace('%', '').split()[0]), 1)
                        cmp_data = abs(table_item - graph_item) <= tolerance
                        assert cmp_data, "compare graph and table readings with tolerance"
                    else:
                        logger.warning("No {leg} data captured for DateTime: {dt}".format(
                            leg=leg, dt=row['Date/Time']))

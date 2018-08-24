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


def compare_data_with_unit(table_data, graph_data, legends, tolerance=1):
    """ Compare Utilization graph and table data and consider units
    Args:
        table_data : Data from Utilization table
        graph_data : Data from Utilization graph
        legends : Legends in graph; which will help for comparison
        tolerance : Its error which we have to allow while comparison

    Note: Mainly, when we check graph for some tag the unit in table reading missed. The unit
        conversion totally depends on manual observation.
    """
    for row in table_data:
        for key, data in graph_data.items():
            if any([re.match(key, item) for item in row["Date/Time"].split()]):
                for leg in legends:
                    table_item = re.split(" |%", row[leg].replace(",", ""))
                    tb_value, tb_unit = table_item if len(table_item) > 1 else (table_item[0], None)
                    if table_item:
                        graph_item = re.split(" |%", data[leg].replace(",", ""))
                        gp_value, gp_unit = (
                            graph_item if len(graph_item) > 1 else (graph_item[0], None)
                        )

                        if not tb_unit:
                            if gp_unit == "GHz":
                                tb_value = round(float(tb_value) * 10 ** -3, 1)
                                tb_unit = "GHz"
                            elif gp_unit == "GB":
                                tb_value = round(float(tb_value) / 1024, 1)
                                tb_unit = "GB"
                            elif gp_unit in ["MHz", "MB", "B", "KBps"]:
                                tb_unit = gp_unit
                        elif gp_unit == "":
                            gp_unit = tb_unit = "%"
                        elif tb_unit == "Bytes" and gp_unit == "B":
                            tb_unit = gp_unit
                        tb_value = round(float(tb_value), 1)
                        gp_value = round(float(gp_value), 1)

                        if tb_unit == gp_unit:
                            cmp_data = abs(tb_value - gp_value) <= tolerance
                            assert cmp_data, "compare graph and table readings with tolerance"
                        else:
                            logger.warning(
                                "Unit missmatch: {leg}: Table:{tb} {tbu}   Graph:{gp} {gpu}".format(
                                    leg=leg, tb=tb_value, tbu=tb_unit, gp=gp_value, gpu=gp_unit
                                )
                            )
                    else:
                        logger.warning(
                            "No {leg} data captured for DateTime: {dt}".format(
                                leg=leg, dt=row["Date/Time"]
                            )
                        )

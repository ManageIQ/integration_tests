# -*- coding: utf-8 -*-
# pylint: skip-file
"""Manual tests"""
import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.ignore_stream('upstream'),
    pytest.mark.manual,
    test_requirements.right_size
]


@pytest.mark.tier(1)
def test_nor_cpu_values_correct_vsphere6():
    """
    NOR cpu values are correct.
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 6 provider
    Normal Operating Ranges widget displays correct values for CPU and CPU
    Usage max, high, average, and low, if at least one days" worth of
    metrics have been captured:
    The Average reflects the most common value obtained during the past 30
    days" worth of captured metrics.
    The High and Low reflect the range of values obtained ~85% of the time
    within the past 30 days.
    The Max reflects the maximum value obtained within the past 30 days.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(1)
def test_nor_cpu_values_correct_rhv41():
    """
    NOR CPU values are correct.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(1)
def test_rightsize_memory_values_correct_vsphere6():
    """
    Right-size memory values are correct.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(1)
def test_rightsize_memory_values_correct_rhv41():
    """
    Right-size memory values are correct.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_nor_cpu_vsphere6():
    """
    Test Normal Operating Range for CPU usage
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 6 provider
    Normal Operating Ranges widget displays values for CPU and CPU Usage
    max, high, average, and low, if at least one days" worth of metrics
    have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(1)
def test_nor_cpu_rhv41():
    """
    Normal Operating Ranges for CPU display correctly for RHV 4.1 VM.
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    RHV 4.1 provider
    Normal Operating Ranges widget displays values for CPU and CPU Usage
    max, high, average, and low, if at least one days" worth of metrics
    have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_nor_cpu_vsphere55():
    """
    Test Normal Operating Range for CPU usage
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 5.5 provider
    Normal Operating Ranges widget displays values for CPU and CPU Usage
    max, high, average, and low, if at least one days" worth of metrics
    have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(1)
def test_nor_memory_values_correct_vsphere6():
    """
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 6 provider
    Normal Operating Ranges widget displays correct values for Memory and
    Memory Usage max, high, average, and low, if at least one days" worth
    of metrics have been captured:
    The Average reflects the most common value obtained during the past 30
    days" worth of captured metrics.
    The High and Low reflect the range of values obtained ~85% of the time
    within the past 30 days.
    The Max reflects the maximum value obtained within the past 30 days.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(1)
def test_nor_memory_values_correct_rhv41():
    """
    NOR memory values are correct.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_rightsize_cpu_vsphere55():
    """
    Test Right size recommendation for cpu

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_rightsize_cpu_vsphere6():
    """
    Test Right size recommendation for cpu

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(1)
def test_rightsize_cpu_rhv41():
    """
    For a RHV 4.1 provider with C & U metrics collection configured and
    running for >1 day, a VM that has been up and running for >1 day shows
    values in all cells of the tables displayed on the Right-Size
    Recommendations page:
    Compute > Infrastructure > Virtual Machines > click on VM name >
    Configuration > Right-Size Recommendations

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(1)
def test_rightsize_cpu_values_correct_rhv41():
    """
    For a RHV 4.1 provider with C & U metrics collection configured and
    running for >1 day, a VM that has been up and running for >1 day shows
    correct recommended CPU values on the Right-Size Recommendations page:
    Compute > Infrastructure > Virtual Machines > click on VM name >
    Configuration > Right-Size Recommendations
    The correct Max, High, Average, and Low CPU and CPU Usage values in
    the Normal Operating Ranges table should be determined by the maximum,
    ~85th percentile, ~50th percentile, and ~15th percentile CPU (MHz) and
    CPU Usage (%) realtime metric values from the past 30 days for this
    VM.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(1)
def test_rightsize_cpu_values_correct_vsphere6():
    """
    Right-size recommended cpu values are correct.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.tier(1)
def test_rightsize_memory_rhv41():
    """
    For a RHV 4.1 provider with C & U metrics collection configured and
    running for >1 day, a VM that has been up and running for >1 day shows
    values in all cells of the tables displayed on the Right-Size
    Recommendations page:
    Compute > Infrastructure > Virtual Machines > click on VM name >
    Configuration > Right-Size Recommendations

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_rightsize_memory_vsphere55():
    """
    Test Right size recommendation for memory

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_rightsize_memory_vsphere6():
    """
    Test Right size recommendation for memory

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_nor_memory_vsphere55():
    """
    Test Normal Operating Range for memory usage
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 5.5 provider
    Normal Operating Ranges widget displays values for Memory and Memory
    Usage max, high, average, and low, if at least one days" worth of
    metrics have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(1)
def test_nor_memory_rhv41():
    """
    Normal Operating Ranges for memory display correctly for RHV 4.1 VM.
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    RHV 4.1 provider
    Normal Operating Ranges widget displays values for Memory and Memory
    Usage max, high, average, and low, if at least one days" worth of
    metrics have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/6h
    """
    pass


@pytest.mark.tier(2)
def test_nor_memory_vsphere6():
    """
    Test Normal Operating Range for memory usage
    Compute > Infrastructure > Virtual Machines > select a VM running on a
    vSphere 6 provider
    Normal Operating Ranges widget displays values for Memory and Memory
    Usage max, high, average, and low, if at least one days" worth of
    metrics have been captured.

    Polarion:
        assignee: tpapaioa
        casecomponent: CandU
        initialEstimate: 1/6h
    """
    pass

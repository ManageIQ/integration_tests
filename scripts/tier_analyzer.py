#!/usr/bin/env python3
"""This simple script lists all tests generated for the given provider. Then it lists all the tests
marked with given tier marker(s). In the end it simply compares those two list, showing you tests
that are generated for provider but NOT marked with the tier(s)."""
import argparse
import re
import subprocess
import sys


def check_virtualenv():
    """Check if we are in virtualenv and if not, raise an error."""
    if not hasattr(sys, 'real_prefix'):
        raise OSError('You must activate CFME virtualenv in oder to run this script.')


def get_pytest_collect_only_output(args, use_tier_marker=False):
    """
    Get a string that is returned by pytest after invoking it with --collect-only argument.
    If use_tier_marker is set to False (default), all the tests for given provider are collected.
    If use_tier_marker is set to True, only the marked tests are collected.
    """
    print('Getting pytest --collect-only output for provider {} {} tier marker {}.'
        .format(
            args.provider,
            'with' if use_tier_marker else 'without',
            args.tier_marker))
    pytest_args = ['pytest',
        args.test_path,
        '--collect-only',
        '--long-running',
        '--use-provider',
        args.provider,
        '-m']
    if use_tier_marker:
        pytest_args.append(args.tier_marker)
    else:
        pytest_args.append('uses_testgen')

    return subprocess.check_output(pytest_args)


def get_testcases_from_pytest_output(output):
    """Parse raw pytest --collect-only output to get list of parametrized test cases."""
    test_cases = []
    testcase_regex = \
        re.compile(r"\s*<Function '(?P<test_case_name>test_\w+)(?P<parameters>\[.+\])?'>")
    for line in output.splitlines():
        match = re.match(pattern=testcase_regex, string=line)
        if match:
            test_cases.append('{}{}'.format(
                match.group('test_case_name'),
                match.group('parameters') if match.group('parameters') else ''))

    return test_cases


def get_diff_from_lists(all, tiers):
    """Get sorted list of test cases that are not marked with tiers."""
    diff = set(all).difference(set(tiers))
    return sorted(diff)


def print_message(args, diff, all_parsed, all_count, tiers_parsed, tiers_count):
    """Human-readable output."""
    def sep():
        print('*' * 60)

    if args.verbose:
        sep()
        print(f'There are {all_count} test_cases run for {args.provider} provider:\n')
        for test_case in all_parsed:
            print(test_case)
        sep()
        print(f'There are {tiers_count} test_cases marked with "{args.tier_marker}":\n')
        for test_case in tiers_parsed:
            print(test_case)

    sep()
    print('There are {} test cases not marked with "{}":\n'.format(len(diff), args.tier_marker))
    for test_case in diff:
        print(test_case)
    sep()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-p', '--provider', action='store', default='rhv_cfme_integration')
    parser.add_argument('-t', '--test-path', action='store', default='cfme/tests')
    parser.add_argument('-m', '--tier-marker', action='store', default='rhv1 or rhv2 or rhv3')
    args = parser.parse_args()

    check_virtualenv()

    output_with_tiers = get_pytest_collect_only_output(args, use_tier_marker=True)
    output_without_tiers = get_pytest_collect_only_output(args, use_tier_marker=False)
    tiers_parsed = get_testcases_from_pytest_output(output_with_tiers)
    all_parsed = get_testcases_from_pytest_output(output_without_tiers)

    tiers_count = len(tiers_parsed)
    all_count = len(all_parsed)

    final_diff = get_diff_from_lists(all_parsed, tiers_parsed)

    print_message(args, final_diff, all_parsed, all_count, tiers_parsed, tiers_count)

#!/usr/bin/env python

import argparse
import re
import subprocess
import sys


def check_virtualenv():
    """Check if we are in virtualenv and if not, exit."""
    if not hasattr(sys, 'real_prefix'):
        print('You must activate CFME virtualenv in oder to run this script.')
        sys.exit(1)


def get_pytest_output(args, use_tier_marker=False):
    """Get string output of pytest command."""
    print('Getting pytest output {} tier marker.'.format('with' if use_tier_marker else 'without'))
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


def parse_pytest_output(output):
    """Parse raw pytest output to get list of parametrized test cases."""
    test_cases = []
    tc_regex = re.compile(r"\s*<Function '(?P<test_case_name>test_\w+)(?P<parameters>\[.+\])?'>")
    for line in output.splitlines():
        match = re.match(pattern=tc_regex, string=line)
        if match:
            test_cases.append('{}{}'.format(
                match.group('test_case_name'),
                match.group('parameters') if match.group('parameters') else ''))

    return test_cases


def compare_parsed_outputs(all, tiers):
    """Get sorted list of test cases that are not marked with tiers."""
    diff = set(all).difference(set(tiers))
    return sorted(diff)


def print_message(args, diff, all_parsed, all_count, tiers_parsed, tiers_count):
    """Human-readable output."""
    def sep():
        print('*' * 60)

    if args.verbose:
        sep()
        print('There are {} test_cases run for {} provider:\n'.format(all_count, args.provider))
        for test_case in all_parsed:
            print(test_case)
        sep()
        print('There are {} test_cases marked with "{}":\n'.format(tiers_count, args.tier_marker))
        for test_case in tiers_parsed:
            print(test_case)

    sep()
    print('There are {} test cases not marked with "{}":\n'.format(len(diff), args.tier_marker))
    for test_case in diff:
        print(test_case)
    sep()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="""This simple script lists all tests generated
    for the given provider. Then it lists all the tests makred with given tier marker(s).
    In the end it simply compares thhose two list, showing you tests that are generated for provider
    but NOT marked with the tier(s).""")
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-p', '--provider', action='store', default='rhv_cfme_integration')
    parser.add_argument('-t', '--test-path', action='store', default='cfme/tests')
    parser.add_argument('-m', '--tier-marker', action='store', default='rhv1 or rhv2 or rhv3')
    args = parser.parse_args()

    check_virtualenv()

    output_with_tiers = get_pytest_output(args, use_tier_marker=True)
    output_without_tiers = get_pytest_output(args, use_tier_marker=False)
    tiers_parsed = parse_pytest_output(output_with_tiers)
    all_parsed = parse_pytest_output(output_without_tiers)

    tiers_count = len(tiers_parsed)
    all_count = len(all_parsed)

    final_diff = compare_parsed_outputs(all_parsed, tiers_parsed)

    print_message(args, final_diff, all_parsed, all_count, tiers_parsed, tiers_count)

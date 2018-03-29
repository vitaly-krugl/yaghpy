"""
Command-line tool that supports retrieval of the following from a GitHub
organization:

    Top-N repos by number of stars.
    Top-N repos by number of forks.
    Top-N repos by number of Pull Requests (PRs).
    Top-N repos by contribution percentage (PRs/forks).

Command-line examples (--max is optional, defaults to top-5 items)
    ghtoporgrepos stars nodejs --max 10
    ghtoporgrepos forks nodejs --max 10
    ghtoporgrepos pulls nodejs --max 10
    ghtoporgrepos contrib-percent nodejs --max 10

Output format of the "top-N repo" commands:

    Output items are newline-terminated and output to stdout in decreasing order
    by the value of the requested sort field. Each item consists of two items:
    the repo name and value of requested sort field separated by colon. For
    example: `ghtoporgrepos nodejs forks` output might include lines like these:
        node:9833
        node-v8:15
        modules:10

Assumptions:
    Python 2.7.x and 3.4+
    Linux, OS X
    Coding/naming conventions: Assumption: ~ PEP-8
    Queries work on public repositories within an organization in GitHub
        TODO: support authentication for access to an org with private repos and
        increased rate quota.

"""

from __future__ import print_function

import argparse
import functools
import heapq
import logging
import numbers
import sys

from yagpy import yagpy


_LOG = logging.getLogger('__name__')


def top_org_repos(args=None, file=sys.stdout):
    """Console script entry point for the `ghtoporgrepos` command-line tool.
    Perform the requested query against GitHub and output results to the given
    text file object.

    See this package's `setup.py` for console script integration info.

    :param sequence args: command-line args; defaults to `sys.argv`.
    :param file: output text file object exposing a file-oriented API;
        defaults to `sys.stdout`

    """
    GitHubTopOrgReposCommand.get_top_repos(args, file)


class _SizeConstrainedMaxHeap(object):
    """Implements a size-constrained max heap on top of heapq's min heap
    implementation. The size constraint acts to truncate the heap after N
    biggest items.

    """

    def __init__(self, max_items=None):
        """
        :param int | None max_items: Limit on the number of largest items in
            the heap (the following smaller items are automatically deleted);
            None (default) bypasses this limit constraint.
        """
        if not isinstance(max_items, (type(None), numbers.Integral)):
            raise TypeError(
                'Expected int | None max_items but got {!r}'.format(max_items))

        if max_items is not None and max_items < 0:
            raise ValueError(
                'Expected non-negative max_items, but got {!r}'.format(
                    max_items))

        self._max_items = max_items
        self._heap = []

    def __bool__(self):
        """Python 3.x"""
        return bool(self._heap)

    def __nonzero__(self):
        """Python 2.x"""
        return self.__bool__()

    def push(self, item):
        """Push the item onto the heap.

        :param opaque item:
        """
        heapq.heappush(self._heap, self.InvertedComparisonWrapper(item))

        if self._max_items is not None:
            if len(self._heap) > self._max_items:
                del self._heap[self._max_items:]

    def pop(self):
        """Pop and return the largest item from the heap.

        :return: the largest item from the heap
        :raise IndexError: if heap is empty
        """
        return heapq.heappop(self._heap).value

    @functools.total_ordering
    class InvertedComparisonWrapper(object):
        """Container for heap's items that inverts comparisons so that we can
        utilize the builtin min heap as a max heap
        """
        def __init__(self, value):
            self.value = value

        def __eq__(self, other):
            return self.value == other.value

        def __lt__(self, other):
            # Invert the comparison to adapt min heap as max heap
            return self.value > other.value


class GitHubTopOrgReposCommand(object):
    """This module's command-line tool implementation."""

    # Default maximum number of items to return
    _DEFAULT_MAX_RESULT_ITEMS = 5

    @staticmethod
    def _get_top_star_repos(org, max_items, credentials):
        """Create a generator that yields up to `max_items` of top repos by
        stargazers count. Each yielded item is a string concatenation of
        unqualified repo name and its stargazers count value separated by the
        ':' character.

        :param str org:
        :param int max_items:
        :rtype: generator
        """
        heap = _SizeConstrainedMaxHeap(max_items)

        hub = yagpy.GitHub(credentials)
        for repo in hub.org(org).repos().list_all_sources():
            heap.push((repo['stargazers_count'], repo['name']))

        while heap:
            stars, name = heap.pop()
            yield '{}:{}'.format(name, stars)

    @staticmethod
    def _get_top_fork_repos(org, max_items, credentials):
        """Create a generator that yields up to `max_items` of top repos by
        forks count. Each yielded item is a string concatenation of
        unqualified repo name and its forks count value separated by the
        ':' character.

        :param str org:
        :param int max_items:
        :rtype: generator
        """
        heap = _SizeConstrainedMaxHeap(max_items)

        hub = yagpy.GitHub(credentials)
        for repo in hub.org(org).repos().list_all_sources():
            heap.push((repo['forks_count'], repo['name']))

        while heap:
            forks, name = heap.pop()
            yield '{}:{}'.format(name, forks)

    @staticmethod
    def _get_top_pull_request_repos(org, max_items, credentials):
        """Create a generator that yields up to `max_items` of top repos by
        pull request count. Each yielded item is a string concatenation of
        unqualified repo name and its pull request count value separated by the
        ':' character.

        :param str org:
        :param int max_items:
        :rtype: generator
        """
        heap = _SizeConstrainedMaxHeap(max_items)

        hub = yagpy.GitHub(credentials)
        for repo in hub.org(org).repos().list_all_sources():
            num_pulls = sum(
                1 for _ in
                hub.repo(*repo['full_name'].split('/')).pulls().list_all())
            heap.push((num_pulls, repo['name']))

        while heap:
            num_pulls, name = heap.pop()
            yield '{}:{}'.format(name, num_pulls)

    @staticmethod
    def _get_top_contribution_ratio_repos(org, max_items, credentials):
        """Create a generator that yields up to `max_items` of top repos by
        contribution ratio (PRs/forks). Each yielded item is a string
        concatenation of unqualified repo name and its contribution ratio value
        separated by the ':' character.

        :param str org:
        :param int max_items:
        :rtype: generator
        """
        heap = _SizeConstrainedMaxHeap(max_items)

        hub = yagpy.GitHub(credentials)
        for repo in hub.org(org).repos().list_all_sources():
            if repo['forks_count']:
                num_pulls = sum(
                    1 for _ in
                    hub.repo(*repo['full_name'].split('/')).pulls().list_all())
                heap.push((num_pulls / repo['forks_count'], repo['name']))

        while heap:
            ratio, name = heap.pop()
            yield '{}:{}'.format(name, ratio)

    # Supported actions for get_top_repos()
    _TOP_REPOS_ACTIONS = {
        'stars':
            ['_get_top_star_repos', 'Top-N repos by number of stars;'],
        'forks':
            ['_get_top_fork_repos', 'Top-N repos by number of forks;'],
        'pulls':
            ['_get_top_pull_request_repos',
             'Top-N repos by number of Pull Requests (PRs);'],
        'contrib-ratio':
            ['_get_top_contribution_ratio_repos',
             'Top-N repos by contribution ratio (PRs/forks);']
    }

    @classmethod
    def _get_action_help_str(cls):
        """Return the ACTION help string generated from `_TOP_REPOS_ACTIONS`.

        :rtype: str
        """
        lines = []

        for action, (_func, help_str) in sorted(cls._TOP_REPOS_ACTIONS.items()):
            lines.append('{}: {}'.format(action, help_str))

        return ' '.join(lines)

    @classmethod
    def get_top_repos(cls, args=None, file=sys.stdout):
        """Perform the requested query against GitHub and output results to the given
        text file object.

        :param sequence args: command-line args; defaults to `sys.argv`.
        :param file: output text file object exposing a file-oriented API;
            defaults to `sys.stdout`

        """
        if args is None:
            args = sys.argv

        # Parse the command-line
        parser = argparse.ArgumentParser(
            prog=args[0],
            usage=(
                '{} ACTION ORGANIZATION [-h] [--max MAX] '
                '[--basic-auth BASIC_AUTH]'.format(args[0])),
            description=(
                'Get top-N GitHub organization repositories meeting '
                'the given criteria. Basic Authentication credentials may '
                'provided either via the optional arg --basic-auth or '
                'via config file at location referenced by the '
                'environment variable {}, defaulting to {!r}. '
                'Unauthenticated access is subject to severely '
                'reduced GitHub request rate quota limits and increased '
                'command errors.'.format(
                    yagpy.GitHubBasicAuthCredentials.CONFIG_PATH_ENV_VAR,
                    yagpy.GitHubBasicAuthCredentials.DEFAULT_CONFIG_PATH)))

        parser.add_argument('action',
                            metavar='ACTION',
                            choices=tuple(cls._TOP_REPOS_ACTIONS.keys()),
                            help=cls._get_action_help_str())

        parser.add_argument('org',
                            metavar='ORGANIZATION',
                            type=str,
                            help="Name of GitHub organization.")

        parser.add_argument("--basic-auth", type=str,
                            help=('Colon-separated GitHub basic authentication '
                                  'credentials (user:password). NOTE: user '
                                  'containing colon character(s) is not '
                                  'supported.'),
                            default=':')

        parser.add_argument("--max", type=int,
                            help='Maximum results to output [{}].'.format(
                                cls._DEFAULT_MAX_RESULT_ITEMS),
                            default=cls._DEFAULT_MAX_RESULT_ITEMS)

        parsed_args = parser.parse_args(args[1:])

        if not parsed_args.org:
            parser.error('Expected ORGANIZATION name, but got {!r}'.format(
                parsed_args.org))

        if parsed_args.max < 0:
            parser.error('Expected non-negative MAX, but got {!r}'.format(
                parsed_args.max))

        if parsed_args.basic_auth.count(':') < 1:
            parser.error(
                'Expected colon-separated BASIC_AUTH user:password '
                'pair, but got {!r}'.format(parsed_args.basic_auth))

        # Query and output results
        process = getattr(cls, cls._TOP_REPOS_ACTIONS[parsed_args.action][0])

        try:
            colon_pos = parsed_args.basic_auth.find(':')
            credentials = yagpy.GitHubBasicAuthCredentials(
                parsed_args.basic_auth[:colon_pos],
                parsed_args.basic_auth[colon_pos + 1:])

            for item in process(parsed_args.org, parsed_args.max, credentials):
                print(item, file=file)
        except Exception as error:  # pylint: disable=W0703
            _LOG.debug('Request failed.', exc_info=True)
            sys.exit(error)

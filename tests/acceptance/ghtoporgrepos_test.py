"""
Acceptance test for the ghtoporgrepos.py command-line tool.

Assumes that the `yagpy` package has been installed and the `ghtoporgrepos`
console script is in PATH.
"""

import errno
import logging

try:
    # Python 3.x
    from io import StringIO
except ImportError:
    # Python 2.x
    from StringIO import StringIO

import subprocess
import unittest


# pylint: disable=C0111

_LOG = logging.getLogger(__name__)


class ProcessTerminator(object):
    """Context Manager that kills the managed process on exit

    NOTE: borrowed my original implementation from numenta/numenta-apps/nta.utils

    """

    def __init__(self, process):
        """
        :param subprocess.Popen p:
        """
        self._process = process

    def __enter__(self):
        """
        :rtype: subprocess.Popen
        """
        return self._process

    def __exit__(self, *args):
        if self._process.returncode is None:
            try:
                self._process.kill()
            except OSError as error:
                if error.errno == errno.ESRCH:
                    # "no such process" - we must have already killed it
                    pass
                else:
                    raise
            else:
                self._process.wait()

        return False


class GitHubTopOrgReposTest(unittest.TestCase):
    """NOTE: this is work-in-progress meant to demonstrate how one would
    implement acceptance tests for this tool.

    """

    @staticmethod
    def _start_tool_in_subprocess(args):
        """

        :param sequence args: args to pass to the command-line tool
        :return: `process.Popen` instance wrapped in ProcessTerminator
            context manager
        :rtype: ProcessTerminator
        """
        process = subprocess.Popen(
            args=['ghtoporgrepos'] + list(args),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True)

        return ProcessTerminator(process)

    def test_top_repos_help(self):
        with self._start_tool_in_subprocess(['--help']) as process:
            # Wait for it to exit
            stdout_data, stderr_data = process.communicate()  # pylint: disable=E1101

        _LOG.debug('stdout: %s', stdout_data)
        _LOG.debug('stderr: %s', stderr_data)

        self.assertEqual(process.returncode, 0)  # pylint: disable=E1101

        self.assertEqual(stderr_data, b'')

        self.assertIn(b'usage:', stdout_data)
        self.assertIn(b'ghtoporgrepos', stdout_data)
        self.assertIn(b'positional arguments:', stdout_data)
        self.assertIn(b'optional arguments:', stdout_data)

    def test_top_repos_bad_arg(self):
        args = ['stars', 'org', '--foo']
        with self._start_tool_in_subprocess(args) as process:
            # Wait for it to exit
            stdout_data, stderr_data = process.communicate()  # pylint: disable=E1101

        _LOG.debug('stdout: %s', stdout_data)
        _LOG.debug('stderr: %s', stderr_data)

        self.assertNotEqual(process.returncode, 0)  # pylint: disable=E1101

        self.assertEqual(stdout_data, b'')

        self.assertIn(b'usage:', stderr_data)
        self.assertIn(b'error:', stderr_data)
        self.assertIn(b'--foo', stderr_data)

    def test_top_repos_by_number_of_stars(self):
        args = ['stars', 'vitalykrugl', '--max=3']
        with self._start_tool_in_subprocess(args) as process:
            # Wait for it to exit
            stdout_data, stderr_data = process.communicate()  # pylint: disable=E1101

        _LOG.debug('stdout: %s', stdout_data)
        _LOG.debug('stderr: %s', stderr_data)

        self.assertEqual(process.returncode, 0)  # pylint: disable=E1101

        file = StringIO(stdout_data.decode())

        num_lines = 0
        stats = []
        for line in file:
            num_lines += 1

            repo, num_stars = line.split(':')

            # Check for non-empty repo name
            self.assertTrue(repo)
            # Check that num stars is an int
            stats.append(int(num_stars))

        self.assertEqual(num_lines, 3)
        self.assertEqual(stats, list(reversed(sorted(stats))))

    def test_top_repos_by_number_of_forks(self):
        args = ['forks', 'vitalykrugl', '--max=3']
        with self._start_tool_in_subprocess(args) as process:
            # Wait for it to exit
            stdout_data, stderr_data = process.communicate()  # pylint: disable=E1101

        _LOG.debug('stdout: %s', stdout_data)
        _LOG.debug('stderr: %s', stderr_data)

        self.assertEqual(process.returncode, 0)  # pylint: disable=E1101

        file = StringIO(stdout_data.decode())

        num_lines = 0
        stats = []
        for line in file:
            num_lines += 1

            repo, num_forks = line.split(':')

            # Check for non-empty repo name
            self.assertTrue(repo)
            # Check that num forks is an int
            stats.append(int(num_forks))

        self.assertEqual(num_lines, 3)
        self.assertEqual(stats, list(reversed(sorted(stats))))

    def test_top_repos_by_number_of_pulls(self):
        args = ['pulls', 'vitalykrugl', '--max=3']
        with self._start_tool_in_subprocess(args) as process:
            # Wait for it to exit
            stdout_data, stderr_data = process.communicate()  # pylint: disable=E1101

        _LOG.debug('stdout: %s', stdout_data)
        _LOG.debug('stderr: %s', stderr_data)

        self.assertEqual(process.returncode, 0)  # pylint: disable=E1101

        file = StringIO(stdout_data.decode())

        num_lines = 0
        stats = []
        for line in file:
            num_lines += 1

            repo, num_pulls = line.split(':')

            # Check for non-empty repo name
            self.assertTrue(repo)
            # Check that num pulls is an int
            stats.append(int(num_pulls))

        self.assertEqual(num_lines, 3)
        self.assertEqual(stats, list(reversed(sorted(stats))))

    def test_top_repos_by_contrib_ratio(self):
        args = ['contrib-ratio', 'vitalykrugl', '--max=3']
        with self._start_tool_in_subprocess(args) as process:
            # Wait for it to exit
            stdout_data, stderr_data = process.communicate()  # pylint: disable=E1101

        _LOG.debug('stdout: %s', stdout_data)
        _LOG.debug('stderr: %s', stderr_data)

        self.assertEqual(process.returncode, 0)  # pylint: disable=E1101

        file = StringIO(stdout_data.decode())

        num_lines = 0
        stats = []
        for line in file:
            num_lines += 1

            repo, ratio = line.split(':')

            # Check for non-empty repo name
            self.assertTrue(repo)
            # Check that ratio is compatible with float
            stats.append(float(ratio))

        self.assertGreaterEqual(num_lines, 1)
        self.assertLessEqual(num_lines, 3)
        self.assertEqual(stats, list(reversed(sorted(stats))))

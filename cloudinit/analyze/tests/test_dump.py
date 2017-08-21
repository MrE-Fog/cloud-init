# This file is part of cloud-init. See LICENSE file for license information.

from datetime import datetime
from textwrap import dedent

from cloudinit.analyze.dump import (
    dump_events, parse_ci_logline, parse_timestamp)
from cloudinit.util import subp, write_file
from tests.unittests.helpers import CiTestCase


class TestParseTimestamp(CiTestCase):

    def test_parse_timestamp_handles_cloud_init_default_format(self):
        """Logs with cloud-init detailed formats will be properly parsed."""
        trusty_fmt = '%Y-%m-%d %H:%M:%S,%f'
        trusty_stamp = '2016-09-12 14:39:20,839'

        parsed = parse_timestamp(trusty_stamp)

        # convert ourselves
        dt = datetime.strptime(trusty_stamp, trusty_fmt)
        expected = float(dt.strftime('%s.%f'))

        # use date(1)
        out, _err = subp(['date', '+%s.%3N', '-d', trusty_stamp])
        timestamp = out.strip()
        date_ts = float(timestamp)

        self.assertEqual(expected, parsed)
        self.assertEqual(expected, date_ts)
        self.assertEqual(date_ts, parsed)

    def test_parse_timestamp_handles_syslog_adding_year(self):
        """Syslog timestamps lack a year. Add year and properly parse."""
        syslog_fmt = '%b %d %H:%M:%S %Y'
        syslog_stamp = 'Aug 08 15:12:51'

        # convert stamp ourselves by adding the missing year value
        year = datetime.now().year
        dt = datetime.strptime(syslog_stamp + " " + str(year), syslog_fmt)
        expected = float(dt.strftime('%s.%f'))
        parsed = parse_timestamp(syslog_stamp)

        # use date(1)
        out, _ = subp(['date', '+%s.%3N', '-d', syslog_stamp])
        timestamp = out.strip()
        date_ts = float(timestamp)

        self.assertEqual(expected, parsed)
        self.assertEqual(expected, date_ts)
        self.assertEqual(date_ts, parsed)

    def test_parse_timestamp_handles_journalctl_format_adding_year(self):
        """Journalctl precise timestamps lack a year. Add year and parse."""
        journal_fmt = '%b %d %H:%M:%S.%f %Y'
        journal_stamp = 'Aug 08 17:15:50.606811'

        # convert stamp ourselves by adding the missing year value
        year = datetime.now().year
        dt = datetime.strptime(journal_stamp + " " + str(year), journal_fmt)
        expected = float(dt.strftime('%s.%f'))
        parsed = parse_timestamp(journal_stamp)

        # use date(1)
        out, _ = subp(['date', '+%s.%6N', '-d', journal_stamp])
        timestamp = out.strip()
        date_ts = float(timestamp)

        self.assertEqual(expected, parsed)
        self.assertEqual(expected, date_ts)
        self.assertEqual(date_ts, parsed)

    def test_parse_unexpected_timestamp_format_with_date_command(self):
        """Dump sends unexpected timestamp formats to data for processing."""
        new_fmt = '%H:%M %m/%d %Y'
        new_stamp = '17:15 08/08'

        # convert stamp ourselves by adding the missing year value
        year = datetime.now().year
        dt = datetime.strptime(new_stamp + " " + str(year), new_fmt)
        expected = float(dt.strftime('%s.%f'))
        parsed = parse_timestamp(new_stamp)

        # use date(1)
        out, _ = subp(['date', '+%s.%6N', '-d', new_stamp])
        timestamp = out.strip()
        date_ts = float(timestamp)

        self.assertEqual(expected, parsed)
        self.assertEqual(expected, date_ts)
        self.assertEqual(date_ts, parsed)


class TestParseCILogLine(CiTestCase):

    def test_parse_logline_returns_none_without_separators(self):
        """When no separators are found, parse_ci_logline returns None."""
        expected_parse_ignores = [
            '', '-', 'adsf-asdf', '2017-05-22 18:02:01,088', 'CLOUDINIT']
        for parse_ignores in expected_parse_ignores:
            self.assertIsNone(parse_ci_logline(parse_ignores))

    def test_parse_logline_returns_event_for_cloud_init_logs(self):
        """parse_ci_logline returns an event parse from cloud-init format."""
        line = (
            "2017-08-08 20:05:07,147 - util.py[DEBUG]: Cloud-init v. 0.7.9"
            " running 'init-local' at Tue, 08 Aug 2017 20:05:07 +0000. Up"
            " 6.26 seconds.")
        dt = datetime.strptime(
            '2017-08-08 20:05:07,147', '%Y-%m-%d %H:%M:%S,%f')
        timestamp = float(dt.strftime('%s.%f'))
        expected = {
            'description': 'starting search for local datasources',
            'event_type': 'start',
            'name': 'init-local',
            'origin': 'cloudinit',
            'timestamp': timestamp}
        self.assertEqual(expected, parse_ci_logline(line))

    def test_parse_logline_returns_event_for_journalctl_logs(self):
        """parse_ci_logline returns an event parse from journalctl format."""
        line = ("Nov 03 06:51:06.074410 x2 cloud-init[106]: [CLOUDINIT]"
                " util.py[DEBUG]: Cloud-init v. 0.7.8 running 'init-local' at"
                "  Thu, 03 Nov 2016 06:51:06 +0000. Up 1.0 seconds.")
        year = datetime.now().year
        dt = datetime.strptime(
            'Nov 03 06:51:06.074410 %d' % year, '%b %d %H:%M:%S.%f %Y')
        timestamp = float(dt.strftime('%s.%f'))
        expected = {
            'description': 'starting search for local datasources',
            'event_type': 'start',
            'name': 'init-local',
            'origin': 'cloudinit',
            'timestamp': timestamp}
        self.assertEqual(expected, parse_ci_logline(line))

    def test_parse_logline_returns_event_for_finish_events(self):
        """parse_ci_logline returns a finish event for a parsed log line."""
        line = ('2016-08-30 21:53:25.972325+00:00 y1 [CLOUDINIT]'
                ' handlers.py[DEBUG]: finish: modules-final: SUCCESS: running'
                ' modules for final')
        expected = {
            'description': 'running modules for final',
            'event_type': 'finish',
            'name': 'modules-final',
            'origin': 'cloudinit',
            'result': 'SUCCESS',
            'timestamp': 1472594005.972}
        self.assertEqual(expected, parse_ci_logline(line))


SAMPLE_LOGS = dedent("""\
Nov 03 06:51:06.074410 x2 cloud-init[106]: [CLOUDINIT] util.py[DEBUG]:\
 Cloud-init v. 0.7.8 running 'init-local' at Thu, 03 Nov 2016\
 06:51:06 +0000. Up 1.0 seconds.
2016-08-30 21:53:25.972325+00:00 y1 [CLOUDINIT] handlers.py[DEBUG]: finish:\
 modules-final: SUCCESS: running modules for final
""")


class TestDumpEvents(CiTestCase):
    maxDiff = None

    def test_dump_events_with_rawdata(self):
        """Rawdata is split and parsed into a tuple of events and data"""
        events, data = dump_events(rawdata=SAMPLE_LOGS)
        expected_data = SAMPLE_LOGS.splitlines()
        year = datetime.now().year
        dt1 = datetime.strptime(
            'Nov 03 06:51:06.074410 %d' % year, '%b %d %H:%M:%S.%f %Y')
        timestamp1 = float(dt1.strftime('%s.%f'))
        expected_events = [{
            'description': 'starting search for local datasources',
            'event_type': 'start',
            'name': 'init-local',
            'origin': 'cloudinit',
            'timestamp': timestamp1}, {
            'description': 'running modules for final',
            'event_type': 'finish',
            'name': 'modules-final',
            'origin': 'cloudinit',
            'result': 'SUCCESS',
            'timestamp': 1472594005.972}]
        self.assertEqual(expected_events, events)
        self.assertEqual(expected_data, data)

    def test_dump_events_with_cisource(self):
        """Cisource file is read and parsed into a tuple of events and data."""
        tmpfile = self.tmp_path('logfile')
        write_file(tmpfile, SAMPLE_LOGS)
        events, data = dump_events(cisource=open(tmpfile))
        year = datetime.now().year
        dt1 = datetime.strptime(
            'Nov 03 06:51:06.074410 %d' % year, '%b %d %H:%M:%S.%f %Y')
        timestamp1 = float(dt1.strftime('%s.%f'))
        expected_events = [{
            'description': 'starting search for local datasources',
            'event_type': 'start',
            'name': 'init-local',
            'origin': 'cloudinit',
            'timestamp': timestamp1}, {
            'description': 'running modules for final',
            'event_type': 'finish',
            'name': 'modules-final',
            'origin': 'cloudinit',
            'result': 'SUCCESS',
            'timestamp': 1472594005.972}]
        self.assertEqual(expected_events, events)
        self.assertEqual(SAMPLE_LOGS.splitlines(), [d.strip() for d in data])

from falafel.core.plugins import mapper
from falafel.core import LogFileOutput

from datetime import datetime
import re

"""
2016/06/21 14:01:07 +01:00 29079 172.16.41.79: rhnServer/server_certificate.valid('Server id ID-1000014665 not found in database',)
"""


@mapper('rhn_server_xmlrpc.log')
class ServerXMLRPCLog(LogFileOutput):

    LINE_STR = r"^(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} " + \
        r"[+-]?\d{2}:\d{2}) (?P<pid>\d+) (?P<client_ip>\S+): " + \
        r"(?P<module>\w+)/(?P<function>[\w.-]+)" + \
        r"(?:\((?:(?P<client_id>\d+), ?)?(?P<args>.*?),?\))?$"
    LINE_RE = re.compile(LINE_STR)
    GROUPS = ('timestamp', 'pid', 'client_ip', 'module', 'function',
              'client_id', 'args')

    def parse_line(self, line):
        """
            Parse a log line using the XMLRPC regular expression into a dict.
            All data will be in fields, and the raw log line is stored in
            'raw_log'.
        """
        msg_info = dict()
        msg_info['raw_log'] = line

        match = self.LINE_RE.search(line)
        if match:
            for group in self.GROUPS:
                msg_info[group] = match.group(group)
            try:
                stamp = match.group('timestamp')
                # Must remove : from timezone for strptime %z
                msg_info['timestamp'] = datetime.strptime(
                    stamp[0:23] + stamp[24:26], "%Y/%m/%d %H:%M:%S %z")
            except:
                pass

        return msg_info

    def __contains__(self, s):
        """
        Check if the specified string 's' is contained in one line
        """
        return any(s in l for l in self.data)

    def get(self, s):
        """
        Returns all lines that contain 's' and wrap them in a list
        """
        return [self.parse_line(l) for l in self.data if s in l]

    def last(self):
        """
        Returns the last complete log line
        If the last line is not complete, then return the second last line
        """
        msg_info = dict()
        # Only check the last 2 lines, in that order
        for l in reversed(self.data[-2:]):
            msg_info = self.parse_line(l)
            # assume parse is successful if we got an IP address
            if msg_info['client_ip']:
                return msg_info
        # Return the last one even if it didn't parse.
        return msg_info

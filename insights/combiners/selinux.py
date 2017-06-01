"""
SELinux
=======

Combiner for more complex handling of SELinux being disabled by any means available to the
users. It uses results of ``SEStatus``, ``GrubConfig``, and ``SelinuxConfig`` parsers.

It contains a dictionary ``problems`` in which it stores detected problems with keys as follows
and values are parsed lines with detected problem:

* ``sestatus_disabled`` - SELinux is disabled on runtime.
* ``sestatus_not_enforcing`` - SELinux is not in enforcing mode.
* ``grub_disabled`` - SELinux is set in Grub to be disabled.
* ``grub_not_enforcing`` - SELinux is set in Grub to not be in enforcing mode.
* ``selinux_conf_disabled`` - SELinux is set in configuration file to be disabled.
* ``sestatus_not_enforcing`` - SELinux is set in configuration file to not be in enforcing mode.

Examples:
    >>> selinux = shared[SELinux]
    >>> selinux.ok()
    False
    >>> selinux.problems
    {'grub_disabled': ['/vmlinuz-2.6.32-642.el6.x86_64 selinux=0 ro root= ...'],
     'selinux_conf_disabled': 'disabled',
     'sestatus_not_enforcing': 'permissive'}
"""

from ..core.plugins import combiner
from ..parsers.sestatus import SEStatus
from ..parsers.grub_conf import GrubConfig
from ..parsers.selinux_config import SelinuxConfig

GRUB_DISABLED = 'grub_disabled'
GRUB_NOT_ENFORCING = 'grub_not_enforcing'
RUNTIME_DISABLED = 'sestatus_disabled'
RUNTIME_NOT_ENFORCING = 'sestatus_not_enforcing'
BOOT_DISABLED = 'selinux_conf_disabled'
BOOT_NOT_ENFORCING = 'selinux_conf_not_enforcing'


@combiner(requires=[SEStatus, GrubConfig, SelinuxConfig])
class SELinux(object):
    """
    A combiner for detecting that SELinux is enabled and running and also enabled at boot time.
    """
    def __init__(self, local, shared):
        self.problems = {}
        self.sestatus = shared[SEStatus]
        self.selinux_config = shared[SelinuxConfig]
        self.grub_config = shared[GrubConfig]

        self._check_sestatus()
        self._check_boot_config()
        self._check_grub_config()

    def _check_sestatus(self):
        """
        Check runtime SELinux configuration from sestatus output.

        Values of output from sestatus command are always lowercase.
        """
        if self.sestatus.data['selinux_status'] != 'enabled':
            self.problems[RUNTIME_DISABLED] = self.sestatus.data['selinux_status']
        elif self.sestatus.data['current_mode'] != 'enforcing':
            self.problems[RUNTIME_NOT_ENFORCING] = self.sestatus.data['current_mode']

    def _check_boot_config(self):
        """
        Check that SELinux is not disabled in /etc/sysconfig/selinux.

        This file determines the boot configuration for SELinux.
        """
        opt_value = self.selinux_config.data['SELINUX']
        if opt_value == 'disabled':
            self.problems[BOOT_DISABLED] = opt_value
        elif opt_value != 'enforcing':
            self.problems[BOOT_NOT_ENFORCING] = opt_value

    def _check_grub_config(self):
        """
        Check grub and grub 2 for kernel boot options if selinux settings is not overriden.

        Experiments confirmed that only lowercase is accepted in grub configuration.

        grub is in rhel-6 and the boot line looks usually like
            kernel /boot/vmlinuz-2.4.20-selinux-2003040709 ro root=/dev/hda1 nousb selinux=0
        grub 2 is in rhel-7 and the boot line looks usually like
            linux16 /vmlinuz-0-rescue-9f20b35c9faa49aebe171f62a11b236f root=/dev/mapper/rhel-root ro crashkernel=auto rd.lvm.lv=rhel/root rd.lvm.lv=rhel/swap rhgb quiet
        """
        kernel_lines = []

        # grub2 line
        if self.grub_config.get('menuentry'):
            for line in self.grub_config.get('menuentry'):
                for name, options in line:
                    if name.startswith('linux'):
                        kernel_lines.append(options)
        # Fallback to grub1 detection
        elif self.grub_config.get('title'):
            for line in self.grub_config.get('title'):
                for name, options in line:
                    if name.startswith('kernel'):
                        kernel_lines.append(options)

        # Detection of problems
        for line in kernel_lines:
            if 'selinux=0' in line:
                if GRUB_DISABLED not in self.problems:
                    self.problems[GRUB_DISABLED] = []
                self.problems[GRUB_DISABLED].append(line)
            if 'enforcing=0' in line:
                if GRUB_NOT_ENFORCING not in self.problems:
                    self.problems[GRUB_NOT_ENFORCING] = []
                self.problems[GRUB_NOT_ENFORCING].append(line)

    def ok(self):
        """
        Checks if there are any problems with SELinux configuration.

        Returns
            bool: True if SELinux is enabled and functional, false otherwise.
        """
        return not bool(self.problems)
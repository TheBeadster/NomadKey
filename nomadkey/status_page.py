"""Read-only host measurements. No shell, private configuration or control actions."""
from datetime import datetime, timezone
from pathlib import Path
import os
import shutil
import time


class StatusPage:
    def __init__(self, storage):
        self.storage = storage
        self.started = time.monotonic()

    def __call__(self):
        sampled = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        lines = ['PiMonitor | Private status', '', 'Sampled: ' + sampled,
                 'NomadKey process uptime: %d seconds' % (time.monotonic() - self.started)]
        try:
            uptime = float(Path('/proc/uptime').read_text().split()[0])
            lines.append('Host uptime: %.1f days' % (uptime / 86400))
        except (OSError, ValueError, IndexError):
            lines.append('Host uptime: unavailable')
        try:
            lines.append('CPU load (1 / 5 / 15 min): %.2f / %.2f / %.2f' % os.getloadavg())
        except (OSError, AttributeError):
            lines.append('CPU load: unavailable')
        try:
            disk = shutil.disk_usage(self.storage)
            lines.append('Storage free: %.1f GiB of %.1f GiB' % (disk.free / 2**30, disk.total / 2**30))
        except OSError:
            lines.append('Storage: unavailable')
        try:
            memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
            available = int(memory['MemAvailable'].split()[0]) / 1024
            total = int(memory['MemTotal'].split()[0]) / 1024
            lines.append('Memory available: %.0f MiB of %.0f MiB' % (available, total))
        except (OSError, ValueError, KeyError, IndexError):
            lines.append('Memory: unavailable')
        lines += ['', 'Refresh for a new sample. This is a read-only host snapshot,',
                  'not an estate-wide health assessment.', '',
                  'Access ends five minutes after authentication. Refresh never',
                  'extends it. Forget me revokes this connection immediately.']
        return '\n'.join(lines).encode('utf-8')

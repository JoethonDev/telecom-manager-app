"""Read system stats directly from /proc — no DB round-trip.

Used by /monitoring/live.json for the real-time card values on the
monitoring page.  Cached at the OS level by the kernel — safe to call
multiple times per second.
"""
import os
import time

_prev_cpu = None  # (total, idle) from the previous call


def _read_cpu():
    """Return CPU usage percent since the previous call.
    First call returns 0 (no baseline yet)."""
    global _prev_cpu
    try:
        with open("/proc/stat") as f:
            parts = f.readline().split()
        values = [int(x) for x in parts[1:8]]
        idle = values[3] + values[4]
        total = sum(values)
        if _prev_cpu is None:
            _prev_cpu = (total, idle)
            return 0.0
        prev_total, prev_idle = _prev_cpu
        _prev_cpu = (total, idle)
        d_total = total - prev_total
        d_idle = idle - prev_idle
        if d_total <= 0:
            return 0.0
        return max(0.0, min(100.0, (1 - d_idle / d_total) * 100))
    except Exception:
        return 0.0


def _read_mem():
    """Return memory usage percent (MemTotal - MemAvailable) / MemTotal."""
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip()] = v.strip()
        total = int(info.get("MemTotal", "0").split()[0])
        avail = int(info.get("MemAvailable", "0").split()[0])
        if total <= 0:
            return 0.0
        return max(0.0, min(100.0, (total - avail) / total * 100))
    except Exception:
        return 0.0


def _read_disk(path="/"):
    """Return disk usage percent for the filesystem holding `path`."""
    try:
        st = os.statvfs(path)
        if st.f_blocks == 0:
            return 0.0
        used = st.f_blocks - st.f_bfree
        return max(0.0, min(100.0, used / st.f_blocks * 100))
    except Exception:
        return 0.0


def read_all():
    """Return (cpu_pct, mem_pct, disk_pct) using direct /proc reads.
    No state beyond the in-memory CPU baseline is persisted."""
    return {
        "cpu_pct":  round(_read_cpu(), 1),
        "mem_pct":  round(_read_mem(), 1),
        "disk_pct": round(_read_disk(), 1),
        "ts":       int(time.time()),
    }

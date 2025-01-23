import psutil
from psutil._pslinux import svmem

def usage_percent(used, total, round_=None):
    """Calculate percentage usage of 'used' against 'total'."""
    try:
        ret = (float(used) / total) * 100
    except ZeroDivisionError:
        return 0.0
    else:
        if round_ is not None:
            ret = round(ret, round_)
        return ret

def apply_zfs_arcstats(vm_stats):
    """Apply ZFS ARC (Adaptive Replacement Cache) stats to
    input virtual memory call results"""
    mems = {}

    try:
        with open('%s/spl/kstat/zfs/arcstats' % psutil.PROCFS_PATH, 'rb') as f:
            for line in f:
                fields = line.split()
                try:
                    mems[fields[0]] = int(fields[2])
                except ValueError:
                    # Not a key: value line
                    continue

        zfs_min = mems[b'c_min']
        zfs_size = mems[b'size']
    except (KeyError, FileNotFoundError):
        msg = ("ZFS ARC memory is not configured on this device, "
               "no modification made to virtual memory stats")
        warnings.warn(msg, RuntimeWarning, stacklevel=2)
        return vm_stats

    # ZFS ARC memory consumption is not reported by /proc/meminfo.
    # Running this func will include reclaimable ZFS ARC
    # memory in the returned values.
    # See:
    # https://www.reddit.com/r/zfs/comments/ha0p7f/understanding_arcstat_and_free/
    # https://github.com/openzfs/zfs/issues/10255

    shrinkable_size = max(zfs_size - zfs_min, 0)
    print(f"shrinkable_size= {shrinkable_size}")
    used = vm_stats.used + vm_stats.shared - shrinkable_size
    cached = vm_stats.cached - vm_stats.shared + shrinkable_size
    available = vm_stats.available + shrinkable_size
    percent = usage_percent(vm_stats.total - available, vm_stats.total, round_=1)

    return svmem(
        vm_stats.total,
        available,
        percent,
        used,
        vm_stats.free,
        vm_stats.active,
        vm_stats.inactive,
        vm_stats.buffers,
        cached,
        vm_stats.shared,
        vm_stats.slab,
    )


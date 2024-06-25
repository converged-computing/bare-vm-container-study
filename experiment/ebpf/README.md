# Testing eBPF

I want to test using bpftrace and other tools to collect bpf metrics.

```console
sudo bpftrace -e 'kprobe:do_nanosleep { printf("%d sleeping\n", pid); }' -c 'sleep 1'
```

I'm starting with [this table](https://github.com/bpftrace/bpftrace/blob/master/man/adoc/bpftrace.adoc#probes) to explore families of events. Another idea - there might be a difference in kernel calls if we extend to +1 nodes, so we might want to diff those two (but maybe that would be a follow up study).

Here is an example of system calls for lammps:

```console
sudo bpftrace ./singularity.bt -c '/usr/local/bin/mpirun --allow-run-as-root --host container-testing:56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 2000' -f json
```

And here is the program `singularity.bt`

```console
#!/usr/bin/env bpftrace

BEGIN
{
	printf("Tracing system call enters...\n");
}

tracepoint:cgroup:*
{
 @mycount[probe] = count();
}

END
{
	printf("\nStick a fork in me I am done.");
}
```


We could try writing a program that can further time a function (note I didn't wind up using this, used Python instead):

```console
#!/usr/bin/env bpftrace

BEGIN
{
    printf("=== Start of kprobe timing for poll\n");
}

kprobe:poll*
{
	@start[tid] = nsecs;
	$name = (struct qstr *)arg1;
	@fname[tid] = $name->name;
}
 
kretprobe:poll* / @start[tid] /
{
	@times = nsecs - @start[tid];
	printf("%-8d %-6d %-16s M %s\n", @times / 1e6, pid, comm, str(@fname[tid]));
	delete(@start[tid]);
	delete(@fname[tid]);
}
```

See [here](https://github.com/bpftrace/bpftrace/blob/master/man/adoc/bpftrace.adoc#probes-kprobe) for notes on how I wrote this.

## Testing Empirically

Let's try running these and seeing what kprobes we get.

```
sudo bpftrace -e 'kprobe:do_nanosleep { }' -c '/usr/local/bin/mpirun --allow-run-as-root --host container-testing:56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 500' -f json
```

### Categories of Tracepoints (1 Node)

Of all the bpftrace listing, there are 1614 that start with `tracepoint`. When we reduce that set to the top level categories, we get the following. I'm going to run each with a singularity container and write down the ones that get hits!

#### block:*

```bash
sudo bpftrace -e 'tracepoint:block:* { @mycount[probe] = count();}' -c '/usr/local/bin/mpirun --allow-run-as-root --host container-testing:56 singularity exec ../metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 500' -f json
```
```console
{"type": "map", "data": {"@mycount": {"tracepoint:block:block_bio_remap": 13, "tracepoint:block:block_split": 64, "tracepoint:block:block_touch_buffer": 2471, "tracepoint:block:block_dirty_buffer": 4843, "tracepoint:block:block_unplug": 16770, "tracepoint:block:block_rq_insert": 16775, "tracepoint:block:block_plug": 19618, "tracepoint:block:block_bio_queue": 35371, "tracepoint:block:block_rq_complete": 35435, "tracepoint:block:block_io_start": 35435, "tracepoint:block:block_io_done": 35435, "tracepoint:block:block_rq_issue": 35435, "tracepoint:block:block_getrq": 35435}}}
```

### compaction

```bash
sudo bpftrace -e 'tracepoint:compaction:* { @mycount[probe] = count();}' -c '/usr/local/bin/mpirun --allow-run-as-root --host container-testing:56 singularity exec ../metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 500' -f json
```
```console
{"type": "map", "data": {"@mycount": {"tracepoint:compaction:mm_compaction_kcompactd_sleep": 36}}}
```

#### csd

```bash
sudo bpftrace -e 'tracepoint:csd:* { @mycount[probe] = count();}' -c '/usr/local/bin/mpirun --allow-run-as-root --host container-testing:56 singularity exec ../metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 500' -f json
```
```console
{"type": "map", "data": {"@mycount": {"tracepoint:csd:csd_queue_cpu": 168482, "tracepoint:csd:csd_function_entry": 216409, "tracepoint:csd:csd_function_exit": 216600}}}
```

#### exceptions

```console
{"type": "map", "data": {"@mycount": {"tracepoint:exceptions:page_fault_kernel": 10611, "tracepoint:exceptions:page_fault_user": 483420}}}
```

#### ext4

```console
{"type": "map", "data": {"@mycount": {"tracepoint:ext4:ext4_mballoc_prealloc": 1, "tracepoint:ext4:ext4_journal_start_reserved": 1, "tracepoint:ext4:ext4_ext_handle_unwritten_extents": 1, "tracepoint:ext4:ext4_ext_show_extent": 1, "tracepoint:ext4:ext4_es_cache_extent": 1, "tracepoint:ext4:ext4_da_write_pages_extent": 1, "tracepoint:ext4:ext4_da_update_reserve_space": 1, "tracepoint:ext4:ext4_da_write_pages": 1, "tracepoint:ext4:ext4_alloc_da_blocks": 1, "tracepoint:ext4:ext4_da_release_space": 2, "tracepoint:ext4:ext4_writepages": 2, "tracepoint:ext4:ext4_writepages_result": 2, "tracepoint:ext4:ext4_fallocate_exit": 6, "tracepoint:ext4:ext4_fallocate_enter": 6, "tracepoint:ext4:ext4_unlink_enter": 9, "tracepoint:ext4:ext4_unlink_exit": 9, "tracepoint:ext4:ext4_begin_ordered_truncate": 9, "tracepoint:ext4:ext4_discard_preallocations": 30, "tracepoint:ext4:ext4_trim_extent": 39, "tracepoint:ext4:ext4_forget": 63, "tracepoint:ext4:ext4_mballoc_alloc": 69, "tracepoint:ext4:ext4_allocate_blocks": 70, "tracepoint:ext4:ext4_mballoc_free": 70, "tracepoint:ext4:ext4_free_blocks": 70, "tracepoint:ext4:ext4_request_blocks": 70, "tracepoint:ext4:ext4_remove_blocks": 70, "tracepoint:ext4:ext4_es_find_extent_range_exit": 72, "tracepoint:ext4:ext4_es_find_extent_range_enter": 72, "tracepoint:ext4:ext4_drop_inode": 72, "tracepoint:ext4:ext4_evict_inode": 72, "tracepoint:ext4:ext4_request_inode": 72, "tracepoint:ext4:ext4_allocate_inode": 72, "tracepoint:ext4:ext4_journal_start_sb": 72, "tracepoint:ext4:ext4_free_inode": 72, "tracepoint:ext4:ext4_ext_remove_space_done": 78, "tracepoint:ext4:ext4_truncate_exit": 78, "tracepoint:ext4:ext4_ext_remove_space": 78, "tracepoint:ext4:ext4_ext_rm_leaf": 78, "tracepoint:ext4:ext4_truncate_enter": 78, "tracepoint:ext4:ext4_da_reserve_space": 96, "tracepoint:ext4:ext4_es_insert_delayed_block": 96, "tracepoint:ext4:ext4_da_write_begin": 133, "tracepoint:ext4:ext4_da_write_end": 133, "tracepoint:ext4:ext4_es_insert_extent": 143, "tracepoint:ext4:ext4_ext_map_blocks_exit": 143, "tracepoint:ext4:ext4_ext_map_blocks_enter": 143, "tracepoint:ext4:ext4_es_remove_extent": 150, "tracepoint:ext4:ext4_journal_start_inode": 982, "tracepoint:ext4:ext4_mark_inode_dirty": 1751, "tracepoint:ext4:ext4_invalidate_folio": 2139, "tracepoint:ext4:ext4_release_folio": 2139, "tracepoint:ext4:ext4_es_lookup_extent_enter": 5204, "tracepoint:ext4:ext4_es_lookup_extent_exit": 5204}}}
```

#### fib

```console
{"type": "map", "data": {"@mycount": {"tracepoint:fib:fib_table_lookup": 329}}}
```

#### filelock

```console
{"type": "map", "data": {"@mycount": {"tracepoint:fib:fib_table_lookup": 329}}}
```

#### filemap

```console
{"type": "map", "data": {"@mycount": {"tracepoint:filemap:mm_filemap_add_to_page_cache": 523926, "tracepoint:filemap:mm_filemap_delete_from_page_cache": 526628}}}
```

#### huge_memory

```
{"type": "map", "data": {"@mycount": {"tracepoint:huge_memory:mm_khugepaged_scan_pmd": 4}}}
```

#### ipi

```console
{"type": "map", "data": {"@mycount": {"tracepoint:ipi:ipi_send_cpumask": 2691, "tracepoint:ipi:ipi_send_cpu": 23679}}}
```

#### irq

```console
{"type": "map", "data": {"@mycount": {"tracepoint:irq:irq_handler_exit": 1269, "tracepoint:irq:irq_handler_entry": 1269, "tracepoint:irq:softirq_entry": 126676, "tracepoint:irq:softirq_exit": 126918, "tracepoint:irq:softirq_raise": 127359}}}
```

### irq_vectors

```console
{"type": "map", "data": {"@mycount": {"tracepoint:irq_vectors:irq_work_entry": 1, "tracepoint:irq_vectors:reschedule_exit": 1144, "tracepoint:irq_vectors:reschedule_entry": 1144, "tracepoint:irq_vectors:call_function_single_entry": 21657, "tracepoint:irq_vectors:call_function_single_exit": 21657, "tracepoint:irq_vectors:call_function_entry": 62060, "tracepoint:irq_vectors:call_function_exit": 62071, "tracepoint:irq_vectors:local_timer_entry": 427762, "tracepoint:irq_vectors:local_timer_exit": 427817}}}
```

### jbd2

```console
{"type": "map", "data": {"@mycount": {"tracepoint:jbd2:jbd2_handle_start": 759, "tracepoint:jbd2:jbd2_handle_stats": 759}}}
```

### kmem

```console
{"type": "map", "data": {"@mycount": {"tracepoint:kmem:mm_page_alloc_extfrag": 1, "tracepoint:kmem:kmalloc": 305574, "tracepoint:kmem:kfree": 550075, "tracepoint:kmem:mm_page_pcpu_drain": 662635, "tracepoint:kmem:mm_page_alloc_zone_locked": 666309, "tracepoint:kmem:mm_page_free_batched": 755638, "tracepoint:kmem:mm_page_free": 1034329, "tracepoint:kmem:mm_page_alloc": 1035862, "tracepoint:kmem:kmem_cache_alloc": 1246464, "tracepoint:kmem:kmem_cache_free": 1442025, "tracepoint:kmem:rss_stat": 1921766}}}
```

### lock

```console
{"type": "map", "data": {"@mycount": {"tracepoint:lock:contention_end": 5402, "tracepoint:lock:contention_begin": 5436}}}
```

### maple_tree

```console
{"type": "map", "data": {"@mycount": {"tracepoint:maple_tree:ma_op": 23998, "tracepoint:maple_tree:ma_read": 298936, "tracepoint:maple_tree:ma_write": 349310}}}
```

### mmap

```console
{"type": "map", "data": {"@mycount": {"tracepoint:mmap:exit_mmap": 954, "tracepoint:mmap:vm_unmapped_area": 22490}}}
```

### mmap_lock

```console
{"type": "map", "data": {"@mycount": {"tracepoint:mmap_lock:mmap_lock_released": 364512, "tracepoint:mmap_lock:mmap_lock_start_locking": 366226, "tracepoint:mmap_lock:mmap_lock_acquire_returned": 379661}}}
```

### module

```console
{"type": "map", "data": {"@mycount": {"tracepoint:module:module_get": 1177, "tracepoint:module:module_put": 1177}}}
```

### msr

```console
{"type": "map", "data": {"@mycount": {"tracepoint:msr:read_msr": 799, "tracepoint:msr:write_msr": 889867}}}
```

### napi

```console
{"type": "map", "data": {"@mycount": {"tracepoint:napi:napi_poll": 1907}}}
```

### net

```console
{"type": "map", "data": {"@mycount": {"tracepoint:net:napi_gro_frags_entry": 2, "tracepoint:net:napi_gro_frags_exit": 2, "tracepoint:net:napi_gro_receive_entry": 23, "tracepoint:net:napi_gro_receive_exit": 23, "tracepoint:net:netif_rx_entry": 2592, "tracepoint:net:netif_rx_exit": 2592, "tracepoint:net:netif_rx": 2592, "tracepoint:net:net_dev_start_xmit": 2615, "tracepoint:net:net_dev_xmit": 2615, "tracepoint:net:net_dev_queue": 2615, "tracepoint:net:netif_receive_skb": 2616}}}
```

### nvme

```console
{"type": "map", "data": {"@mycount": {"tracepoint:nvme:nvme_sq": 14, "tracepoint:nvme:nvme_complete_rq": 14, "tracepoint:nvme:nvme_setup_cmd": 14}}}
```

### oom

```console
{"type": "map", "data": {"@mycount": {"tracepoint:oom:oom_score_adj_update": 25}}}
```

### pagemap

```console
{"type": "map", "data": {"@mycount": {"tracepoint:pagemap:mm_lru_insertion": 790410}}}
```

### percpu

```console
{"type": "map", "data": {"@mycount": {"tracepoint:percpu:percpu_alloc_percpu": 10716, "tracepoint:percpu:percpu_free_percpu": 10759}}}
```

### power

```console
{"type": "map", "data": {"@mycount": {"tracepoint:power:cpu_idle_miss": 150219, "tracepoint:power:cpu_idle": 1397190}}}
```

### printk

```console
{"type": "map", "data": {"@mycount": {"tracepoint:printk:console": 168}}}
```

### qdisc

```console
{"type": "map", "data": {"@mycount": {"tracepoint:qdisc:qdisc_dequeue": 22}}}
```

### raw_syscalls

```console
{"type": "map", "data": {"@mycount": {"tracepoint:raw_syscalls:sys_enter": 1472591, "tracepoint:raw_syscalls:sys_exit": 1474340}}}
```

### rcu

```console
{"type": "map", "data": {"@mycount": {"tracepoint:rcu:rcu_utilization": 2461203}}}
```

### rseq

```console
{"type": "map", "data": {"@mycount": {"tracepoint:rpm:rpm_idle": 155, "tracepoint:rpm:rpm_suspend": 405, "tracepoint:rpm:rpm_usage": 1311, "tracepoint:rpm:rpm_resume": 1716, "tracepoint:rpm:rpm_return_int": 2276}}}
```

### sched

```console
{"type": "map", "data": {"@mycount": {"tracepoint:sched:sched_move_numa": 1, "tracepoint:sched:sched_wait_task": 1, "tracepoint:sched:sched_process_exec": 449, "tracepoint:sched:sched_process_wait": 876, "tracepoint:sched:sched_process_exit": 2374, "tracepoint:sched:sched_process_free": 2374, "tracepoint:sched:sched_wakeup_new": 2395, "tracepoint:sched:sched_process_fork": 2395, "tracepoint:sched:sched_migrate_task": 10891, "tracepoint:sched:sched_wake_idle_without_ipi": 133361, "tracepoint:sched:sched_wakeup": 632485, "tracepoint:sched:sched_waking": 632533, "tracepoint:sched:sched_stat_runtime": 689826, "tracepoint:sched:sched_switch": 1185712}}}
```

### signal

```console
{"type": "map", "data": {"@mycount": {"tracepoint:signal:signal_generate": 1496, "tracepoint:signal:signal_deliver": 2917}}}
```

### skb

```console
{"type": "map", "data": {"@mycount": {"tracepoint:skb:kfree_skb": 1544, "tracepoint:skb:consume_skb": 13507, "tracepoint:skb:skb_copy_datagram_iovec": 14654}}}
```

### sock

```console
{"type": "map", "data": {"@mycount": {"tracepoint:sock:inet_sk_error_report": 78, "tracepoint:sock:inet_sock_set_state": 752, "tracepoint:sock:sock_send_length": 9133, "tracepoint:sock:sk_data_ready": 12131, "tracepoint:sock:sock_recv_length": 18077}}}
```

### syscalls

Too many!

### task

```console
{"type": "map", "data": {"@mycount": {"tracepoint:task:task_rename": 763, "tracepoint:task:task_newtask": 2449}}}
```

### tcp

```console
{"type": "map", "data": {"@mycount": {"tracepoint:tcp:tcp_receive_reset": 10, "tracepoint:tcp:tcp_cong_state_set": 124, "tracepoint:tcp:tcp_destroy_sock": 1860, "tracepoint:tcp:tcp_probe": 2321, "tracepoint:tcp:tcp_rcv_space_adjust": 2800}}}
```

### timer

```console
{"type": "map", "data": {"@mycount": {"tracepoint:timer:timer_expire_entry": 1813, "tracepoint:timer:timer_expire_exit": 1822, "tracepoint:timer:tick_stop": 18944, "tracepoint:timer:timer_cancel": 35745, "tracepoint:timer:timer_start": 36125, "tracepoint:timer:timer_init": 42747, "tracepoint:timer:hrtimer_init": 424954, "tracepoint:timer:hrtimer_expire_entry": 461976, "tracepoint:timer:hrtimer_expire_exit": 461998, "tracepoint:timer:hrtimer_cancel": 509031, "tracepoint:timer:hrtimer_start": 511529}}}
```

### tlb

```console
{"type": "map", "data": {"@mycount": {"tracepoint:tlb:tlb_flush": 267353}}}
```

### vmalloc

```console
{"type": "map", "data": {"@mycount": {"tracepoint:vmalloc:purge_vmap_area_lazy": 1, "tracepoint:vmalloc:free_vmap_area_noflush": 1406, "tracepoint:vmalloc:alloc_vmap_area": 1448}}}
```

### wbt

```console
{"type": "map", "data": {"@mycount": {"tracepoint:wbt:wbt_step": 2, "tracepoint:wbt:wbt_timer": 6}}}
```

### workqueue

```console
{"type": "map", "data": {"@mycount": {"tracepoint:workqueue:workqueue_activate_work": 55964, "tracepoint:workqueue:workqueue_queue_work": 55998, "tracepoint:workqueue:workqueue_execute_end": 56128, "tracepoint:workqueue:workqueue_execute_start": 56140}}}
```

### writeback

```console
{"type": "map", "data": {"@mycount": {"tracepoint:writeback:sb_clear_inode_writeback": 1, "tracepoint:writeback:sb_mark_inode_writeback": 1, "tracepoint:writeback:writeback_pages_written": 5, "tracepoint:writeback:writeback_queue_io": 5, "tracepoint:writeback:writeback_start": 5, "tracepoint:writeback:writeback_written": 5, "tracepoint:writeback:global_dirty_state": 15, "tracepoint:writeback:writeback_dirty_inode_enqueue": 70, "tracepoint:writeback:writeback_dirty_inode": 1911, "tracepoint:writeback:writeback_dirty_inode_start": 1911, "tracepoint:writeback:writeback_dirty_folio": 2323, "tracepoint:writeback:writeback_mark_inode_dirty": 4234}}}
```

### x86_fpu

```console
{"type": "map", "data": {"@mycount": {"tracepoint:x86_fpu:x86_fpu_dropped": 2367, "tracepoint:x86_fpu:x86_fpu_copy_src": 2384, "tracepoint:x86_fpu:x86_fpu_copy_dst": 2384, "tracepoint:x86_fpu:x86_fpu_regs_activated": 69764, "tracepoint:x86_fpu:x86_fpu_regs_deactivated": 526265}}}
```

Here is the whole set tested.

```
{'tracepoint:alarmtimer',
 'tracepoint:amd_cpu',
 'tracepoint:avc',
 'tracepoint:block',
 'tracepoint:bpf_test_run',
 'tracepoint:bpf_trace',
 'tracepoint:bridge',
 'tracepoint:cgroup',
 'tracepoint:clk',
 'tracepoint:compaction',
 'tracepoint:cpuhp',
 'tracepoint:cros_ec',
 'tracepoint:csd',
 'tracepoint:dev',
 'tracepoint:devfreq',
 'tracepoint:devlink',
 'tracepoint:dma_fence',
 'tracepoint:drm',
 'tracepoint:error_report',
 'tracepoint:exceptions',
 'tracepoint:ext4',
 'tracepoint:fib',
 'tracepoint:fib6',
 'tracepoint:filelock',
 'tracepoint:filemap',
 'tracepoint:fs_dax',
 'tracepoint:gpio',
 'tracepoint:handshake',
 'tracepoint:huge_memory',
 'tracepoint:hwmon',
 'tracepoint:hyperv',
 'tracepoint:i2c',
 'tracepoint:initcall',
 'tracepoint:intel_iommu',
 'tracepoint:interconnect',
 'tracepoint:io_uring',
 'tracepoint:iocost',
 'tracepoint:iomap',
 'tracepoint:iommu',
 'tracepoint:ipi',
 'tracepoint:irq',
 'tracepoint:irq_matrix',
 'tracepoint:irq_vectors',
 'tracepoint:jbd2',
 'tracepoint:kmem',
 'tracepoint:ksm',
 'tracepoint:libata',
 'tracepoint:lock',
 'tracepoint:maple_tree',
 'tracepoint:mce',
 'tracepoint:mctp',
 'tracepoint:mdio',
 'tracepoint:migrate',
 'tracepoint:mmap',
 'tracepoint:mmap_lock',
 'tracepoint:mmc',
 'tracepoint:module',
 'tracepoint:mptcp',
 'tracepoint:msr',
 'tracepoint:napi',
 'tracepoint:neigh',
 'tracepoint:net',
 'tracepoint:netlink',
 'tracepoint:nmi',
 'tracepoint:notifier',
 'tracepoint:nvme',
 'tracepoint:oom',
 'tracepoint:osnoise',
 'tracepoint:page_isolation',
 'tracepoint:page_pool',
 'tracepoint:pagemap',
 'tracepoint:percpu',
 'tracepoint:power',
 'tracepoint:printk',
 'tracepoint:pwm',
 'tracepoint:qdisc',
 'tracepoint:ras',
 'tracepoint:raw_syscalls',
 'tracepoint:rcu',
 'tracepoint:regmap',
 'tracepoint:regulator',
 'tracepoint:resctrl',
 'tracepoint:rpm',
 'tracepoint:rseq',
 'tracepoint:rtc',
 'tracepoint:sched',
 'tracepoint:scsi',
 'tracepoint:sd',
 'tracepoint:signal',
 'tracepoint:skb',
 'tracepoint:smbus',
 'tracepoint:sock',
 'tracepoint:spi',
 'tracepoint:swiotlb',
 'tracepoint:sync_trace',
 'tracepoint:syscalls',
 'tracepoint:task',
 'tracepoint:tcp',
 'tracepoint:thermal',
 'tracepoint:thermal_power_allocator',
 'tracepoint:thp',
 'tracepoint:timer',
 'tracepoint:tlb',
 'tracepoint:udp',
 'tracepoint:vmalloc',
 'tracepoint:vmscan',
 'tracepoint:vsyscall',
 'tracepoint:watchdog',
 'tracepoint:wbt',
 'tracepoint:workqueue',
 'tracepoint:writeback',
 'tracepoint:x86_fpu',
 'tracepoint:xdp',
 'tracepoint:xen',
 'tracepoint:xhci-hcd'}
```

### Categories of Kprobes (1 Node)

These all take the format of:

```bash
sudo bpftrace -e 'tracepoint:${ARG}* { @mycount[probe] = count();}' -c '/usr/local/bin/mpirun --allow-run-as-root --host container-testing:56 singularity exec ../metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 500' -f json
```

And here is a script, `krun.sh`

```bash
sudo bpftrace -e "kprobe:${ARG}* { @mycount[probe] = count();}" -c '/usr/local/bin/mpirun --allow-run-as-root --host container-testing:56 singularity exec ../metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 500' -f json
```

Where ARG refers to the term of the heading.
The full list of prefixes that I tried I'm not including here (almost 56k unique).
I started doing these manually but then did the following:

```bash
for term in $(cat prefix.txt);
  do
   echo $term
   ARG=$term . krun.sh &> krun-out.txt
   cat krun-out.txt | grep map && echo $term >> ./results.out
   cat krun-out.txt | grep BPFTRACE_MAX_BPF_PROGS && echo "Too many kprobes for $term" && echo $term >> ./toomany.txt
 done
```

I started piping the name of the prefixes to flie instead of to the terminal.
And that would print the output (json) and the name of the kprobe if there was a result!

#### poll

```bash
sudo bpftrace -e 'tracepoint:poll* { @mycount[probe] = count();}' -c '/usr/local/bin/mpirun --allow-run-as-root --host container-testing:56 singularity exec ../metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 500' -f json
```
```console
{"type": "map", "data": {"@mycount": {"kprobe:poll_state_synchronize_rcu": 7, "kprobe:poll_select_finish": 432, "kprobe:pollwake": 2130, "kprobe:poll_select_set_timeout": 375700, "kprobe:poll_freewait": 376348}}}
```

#### klp

```console
{"type": "map", "data": {"@mycount": {"kprobe:klp_copy_process": 2405}}}
```

#### zap

```console
{"type": "map", "data": {"@mycount": {"kprobe:zap_page_range_single": 237, "kprobe:zap_other_threads": 617, "kprobe:zap_huge_pmd": 695, "kprobe:zap_pte_range": 145547}}}
```

#### cap

```console
{"type": "map", "data": {"@mycount": {"kprobe:cap_ptrace_access_check": 54, "kprobe:cap_inode_getsecurity": 56, "kprobe:cap_capset": 392, "kprobe:cap_inode_need_killpriv": 400, "kprobe:cap_capget": 448, "kprobe:cap_bprm_creds_from_file": 449, "kprobe:cap_task_setscheduler": 473, "kprobe:cap_validate_magic": 896, "kprobe:capable_wrt_inode_uidgid": 1454, "kprobe:cap_task_prctl": 4175, "kprobe:capable": 20372, "kprobe:cap_capable": 24468, "kprobe:cap_vm_enough_memory": 46556, "kprobe:cap_mmap_file": 49418, "kprobe:cap_mmap_addr": 52180}}}
```

#### load

```console
{"type": "map", "data": {"@mycount": {"kprobe:load_elf_interp.constprop.0": 449, "kprobe:load_elf_binary": 449, "kprobe:load_misc_binary": 617, "kprobe:load_script": 617, "kprobe:load_elf_phdrs": 898, "kprobe:load_balance": 807510}}}
```

#### ilookup

```console
{"type": "map", "data": {"@mycount": {"kprobe:ilookup": 2324, "kprobe:ilookup5": 22512}}}
```

#### bdev

```console
{"type": "map", "data": {"@mycount": {"kprobe:bdev_disk_changed": 112, "kprobe:bdev_set_nr_sectors": 168}}}
```

#### int

```console
{"type": "map", "data": {"@mycount": {"kprobe:internal_create_group": 56, "kprobe:internal_get_user_pages_fast": 2014, "kprobe:integrity_inode_free": 55850}}}
```

#### if

```console
{"type": "map", "data": {"@mycount": {"kprobe:if6_seq_show": 114, "kprobe:if6_seq_start": 114, "kprobe:if6_seq_next": 114, "kprobe:if6_seq_stop": 114}}}
```

#### bvec

```console
{"type": "map", "data": {"@mycount": {"kprobe:bvec_alloc": 531, "kprobe:bvec_split_segs": 1771, "kprobe:bvec_free": 2550, "kprobe:bvec_try_merge_page": 15438}}}
```

#### mprotect

```console
{"type": "map", "data": {"@mycount": {"kprobe:mprotect_fixup": 13443}}}
```

#### mode

```console
{"type": "map", "data": {"@mycount": {"kprobe:mode_strip_sgid": 1307}}}
```

#### count.constprop.0.isra.0

```console
{"type": "map", "data": {"@mycount": {"kprobe:count.constprop.0.isra.0": 898}}}
```

#### trigger

```console
{"type": "map", "data": {"@mycount": {"kprobe:trigger_load_balance": 58522}}}
```

#### locked

```console
{"type": "map", "data": {"@mycount": {"kprobe:locked_inode_to_wb_and_lock_list": 741}}}
```

#### syscall

```console
{"type": "map", "data": {"@mycount": {"kprobe:syscall_trace_enter.constprop.0": 97177}}}
```

#### jit

```console
{"type": "map", "data": {"@mycount": {"kprobe:jit_subprogs": 1}}}
```

#### sysfs

```console
{"type": "map", "data": {"@mycount": {"kprobe:sysfs_format_mac": 1, "kprobe:sysfs_init_fs_context": 56, "kprobe:sysfs_get_tree": 56, "kprobe:sysfs_remove_group": 56, "kprobe:sysfs_create_group": 56, "kprobe:sysfs_fs_context_free": 56, "kprobe:sysfs_add_file_mode_ns": 336, "kprobe:sysfs_kf_bin_read": 532, "kprobe:sysfs_emit_at": 2454, "kprobe:sysfs_emit": 3769, "kprobe:sysfs_kf_seq_show": 4824}}}
```

#### uid

```console
{"type": "map", "data": {"@mycount": {"kprobe:uid_m_show": 392, "kprobe:uid_m_start": 784}}}
```

#### chan

```console
{"type": "map", "data": {"@mycount": {"kprobe:change_page_attr_set_clr": 7, "kprobe:change_pid": 56, "kprobe:change_pte_range": 10439, "kprobe:change_protection_range": 13444, "kprobe:change_protection": 13444, "kprobe:change_mnt_propagation": 13888}}}
```

#### yama

```console
{"type": "map", "data": {"@mycount": {"kprobe:yama_relation_cleanup": 25, "kprobe:yama_dointvec_minmax": 56, "kprobe:yama_ptrace_access_check": 56, "kprobe:yama_ptracer_add": 56, "kprobe:yama_task_free": 2354, "kprobe:yama_ptracer_del": 2354, "kprobe:yama_task_prctl": 3728}}}
```
#### xfrm


```console
{"type": "map", "data": {"@mycount": {"kprobe:xfrm_lookup_with_ifid": 254, "kprobe:xfrm_lookup_route": 254}}}
```

#### propagation

```console
{"type": "map", "data": {"@mycount": {"kprobe:propagation_next": 1960}}}
```

#### filp

```console
{"type": "map", "data": {"@mycount": {"kprobe:filp_close": 53745}}}
```

#### hugetlb

```console
{"type": "map", "data": {"@mycount": {"kprobe:hugetlb_report_meminfo": 57, "kprobe:hugetlb_total_pages": 57, "kprobe:hugetlb_report_usage": 112, "kprobe:hugetlbfs_show_options": 224, "kprobe:hugetlb_report_node_meminfo": 228}}}
```

#### memcg

```console
{"type": "map", "data": {"@mycount": {"kprobe:memcg_destroy_list_lru": 448, "kprobe:memcg_init_list_lru_one": 1008, "kprobe:memcg_alloc_slab_cgroups": 3208, "kprobe:memcg_list_lru_alloc": 142622, "kprobe:memcg_account_kmem": 154475, "kprobe:memcg_check_events": 911008}}}
```

#### mm

```console
{"type": "map", "data": {"@mycount": {"kprobe:mm_access": 57, "kprobe:mm_get_huge_zero_page": 74, "kprobe:mm_alloc": 449, "kprobe:mmap_base.isra.0": 898, "kprobe:mm_init": 984, "kprobe:mm_put_huge_zero_page": 985, "kprobe:mm_pasid_drop": 1012, "kprobe:mmap_address_hint_valid": 1306, "kprobe:mm_trace_rss_stat": 2486, "kprobe:mm_update_next_owner": 2849, "kprobe:mm_release": 2868, "kprobe:mmput": 3204, "kprobe:mm_find_pmd": 3918, "kprobe:mmap_region": 49384}}}
```

#### dev_

```console
{"type": "map", "data": {"@mycount": {"kprobe:dev_show": 1, "kprobe:dev_watchdog": 2, "kprobe:dev_pm_enable_wake_irq_check": 2, "kprobe:dev_pm_disable_wake_irq_check": 2, "kprobe:dev_pm_enable_wake_irq_complete": 2, "kprobe:dev_get_by_index_rcu": 10, "kprobe:dev_gro_receive": 26, "kprobe:dev_uevent_name": 168, "kprobe:dev_ifconf": 228, "kprobe:dev_get_mac_address": 342, "kprobe:dev_uevent_filter": 515, "kprobe:dev_uevent": 515, "kprobe:dev_lstats_read": 560, "kprobe:dev_get_tstats64": 1120, "kprobe:dev_fetch_sw_netstats": 1120, "kprobe:dev_get_iflink": 1680, "kprobe:dev_ethtool": 1792, "kprobe:dev_get_alias": 2240, "kprobe:dev_get_phys_port_name": 2240, "kprobe:dev_get_phys_port_id": 2240, "kprobe:dev_get_port_parent_id": 2240, "kprobe:dev_get_stats": 2240, "kprobe:dev_get_flags": 2582, "kprobe:dev_hard_start_xmit": 2617, "kprobe:dev_ioctl": 3160, "kprobe:dev_load": 3844, "kprobe:dev_attr_show": 4371, "kprobe:dev_xdp_prog_id": 4480, "kprobe:dev_get_by_name_rcu": 4870}}}
```

#### devi

(e.g., device)

```console
{"type": "map", "data": {"@mycount": {"kprobe:device_get_ownership": 56, "kprobe:device_show": 142, "kprobe:device_get_devnode": 521, "kprobe:devinet_ioctl": 684, "kprobe:device_match_devt": 11200}}}
```

#### devl

```console
{"type": "map", "data": {"@mycount": {"kprobe:devlink_compat_switch_id_get": 2240, "kprobe:devlink_compat_phys_port_name_get": 2240}}}
```

#### devk

```console
{"type": "map", "data": {"@mycount": {"kprobe:devkmsg_read": 168, "kprobe:devkmsg_poll": 227}}}
```

#### devp

```console
{"type": "map", "data": {"@mycount": {"kprobe:devpts_release": 56, "kprobe:devpts_mntget": 56, "kprobe:devpts_pty_kill": 56, "kprobe:devpts_get_priv": 56, "kprobe:devpts_new_index": 56, "kprobe:devpts_acquire": 56, "kprobe:devpts_kill_index": 56, "kprobe:devpts_pty_new": 56, "kprobe:devpts_show_options": 225}}}
```

#### ret

```console
{"type": "map", "data": {"@mycount": {"kprobe:retarget_shared_pending.isra.0": 8, "kprobe:ret_from_fork": 2398}}}
```

#### put

```console
{"type": "map", "data": {"@mycount": {"kprobe:put_css_set_locked": 4, "kprobe:put_nsset": 56, "kprobe:put_crypt_info": 72, "kprobe:put_timespec64": 110, "kprobe:put_prev_task_rt": 162, "kprobe:put_ipc_ns": 225, "kprobe:put_fs_context": 280, "kprobe:put_mnt_ns": 449, "kprobe:put_filesystem": 783, "kprobe:put_prev_task_stop": 895, "kprobe:put_cmsg": 981, "kprobe:put_prev_task_balance": 2111, "kprobe:put_task_stack": 2359, "kprobe:put_files_struct": 2405, "kprobe:put_device": 2436, "kprobe:put_pid_ns": 2560, "kprobe:put_user_ifreq": 3844, "kprobe:put_cred_rcu": 4100, "kprobe:put_ucounts": 4430, "kprobe:put_task_struct_rcu_user": 4726, "kprobe:put_cpu_partial": 44831, "kprobe:put_unused_fd": 69269, "kprobe:put_pid": 96214, "kprobe:putname": 183310, "kprobe:put_prev_task_fair": 558103, "kprobe:put_prev_task_idle": 558749, "kprobe:put_prev_entity": 1196555}}}
```

#### handle

```console
{"type": "map", "data": {"@mycount": {"kprobe:handle_signal": 968, "kprobe:handle_irq_event": 1459, "kprobe:handle_edge_irq": 1459, "kprobe:handle_dots": 42011, "kprobe:handle_next_page": 310856, "kprobe:handle_pte_fault": 507097, "kprobe:handle_mm_fault": 510979}}}
```

#### drain

```console
{"type": "map", "data": {"@mycount": {"kprobe:drain_zone_pages": 316, "kprobe:drain_obj_stock": 2309, "kprobe:drain_stock": 3733}}}
```

#### curr

```console
{"type": "map", "data": {"@mycount": {"kprobe:current_is_workqueue_rescuer": 4, "kprobe:current_check_refer_path": 336, "kprobe:current_umask": 1305, "kprobe:current_in_userns": 1347, "kprobe:current_save_fsgs": 2389, "kprobe:current_work": 9023, "kprobe:current_time": 301156}}}
```

#### sigaction

```console
{"type": "map", "data": {"@mycount": {"kprobe:sigaction_compat_abi": 51844}}}
```

#### cdev

```console
{"type": "map", "data": {"@mycount": {"kprobe:cdev_put": 512}}}
```

FAIL TO COMPILE BETWEEN HERE

#### nr

```console
{"type": "map", "data": {"@mycount": {"kprobe:nr_hugepages_show": 10, "kprobe:nr_processes": 56, "kprobe:nr_blockdev_pages": 113, "kprobe:nr_iowait_cpu": 1160067}}}
```

#### kernfs

```console
{"type": "map", "data": {"@mycount": {"kprobe:kernfs_create_dir_ns": 56, "kprobe:kernfs_free_fs_context": 56, "kprobe:kernfs_find_and_get_ns": 56, "kprobe:kernfs_test_super": 56, "kprobe:kernfs_get_tree": 56, "kprobe:kernfs_remove": 56, "kprobe:kernfs_root_to_node": 112, "kprobe:kernfs_get_inode": 112, "kprobe:kernfs_evict_inode": 112, "kprobe:kernfs_path_from_node": 113, "kprobe:kernfs_path_from_node_locked": 113, "kprobe:kernfs_get": 168, "kprobe:kernfs_put": 224, "kprobe:kernfs_sop_show_path": 280, "kprobe:kernfs_remove_by_name_ns": 336, "kprobe:kernfs_sop_show_options": 338, "kprobe:kernfs_activate": 392, "kprobe:kernfs_add_one": 392, "kprobe:kernfs_should_drain_open_files": 392, "kprobe:kernfs_link_sibling": 392, "kprobe:kernfs_unlink_sibling": 392, "kprobe:kernfs_activate_one": 392, "kprobe:kernfs_drain": 392, "kprobe:kernfs_new_node": 392, "kprobe:kernfs_file_read_iter": 532, "kprobe:kernfs_fop_readdir": 812, "kprobe:kernfs_iop_lookup": 840, "kprobe:kernfs_dir_fop_release": 855, "kprobe:kernfs_find_ns": 1232, "kprobe:kernfs_name_hash": 1624, "kprobe:kernfs_seq_show": 4833, "kprobe:kernfs_seq_next": 4833, "kprobe:kernfs_seq_start": 5057, "kprobe:kernfs_seq_stop": 5057, "kprobe:kernfs_root_from_sb": 5132, "kprobe:kernfs_unlink_open_file": 5365, "kprobe:kernfs_fop_release": 5369, "kprobe:kernfs_fop_open": 5369, "kprobe:kernfs_fop_read_iter": 5597, "kprobe:kernfs_iop_getattr": 6092, "kprobe:kernfs_iop_get_link": 7441, "kprobe:kernfs_get_target_path": 7441, "kprobe:kernfs_put_active": 10954, "kprobe:kernfs_get_active": 10966, "kprobe:kernfs_dir_pos": 25444, "kprobe:kernfs_dop_revalidate": 93181, "kprobe:kernfs_refresh_inode": 127108, "kprobe:kernfs_iop_permission": 138233}}}
```

#### dput

```console
{"type": "map", "data": {"@mycount": {"kprobe:dput_to_list": 1681, "kprobe:dput": 727035}}}
```

#### integrity

```console
{"type": "map", "data": {"@mycount": {"kprobe:integrity_inode_free": 55278}}}
```

#### km

```console
{"type": "map", "data": {"@mycount": {"kprobe:kmalloc_large": 10, "kprobe:kmsg_read": 59, "kprobe:kmemdup_nul": 336, "kprobe:kmalloc_node_trace": 1538, "kprobe:kmalloc_size_roundup": 9786, "kprobe:kmalloc_reserve": 14374, "kprobe:kmem_cache_alloc_node": 24371, "kprobe:kmem_cache_alloc_bulk": 102197, "kprobe:kmem_cache_free_bulk": 102889, "kprobe:kmalloc_trace": 135960, "kprobe:kmem_cache_alloc_lru": 143744, "kprobe:kmalloc_slab": 177887, "kprobe:kmem_cache_alloc": 1067750, "kprobe:kmem_cache_free": 1444199}}}
```

#### refresh

```console
{"type": "map", "data": {"@mycount": {"kprobe:refresh_cpu_vm_stats": 2273}}}
```

#### getname

```console
{"type": "map", "data": {"@mycount": {"kprobe:getname_kernel": 2029, "kprobe:getname_flags": 77071, "kprobe:getname": 102604}}}
```

####  jbd2


```console
{"type": "map", "data": {"@mycount": {"kprobe:jbd2_alloc": 1, "kprobe:jbd2_journal_free_transaction": 1, "kprobe:jbd2_freeze_jh_data": 1, "kprobe:jbd2_free": 1, "kprobe:jbd2_journal_write_revoke_records": 1, "kprobe:jbd2_journal_switch_revoke_table": 2, "kprobe:jbd2_journal_wait_updates": 2, "kprobe:jbd2_journal_commit_transaction": 2, "kprobe:jbd2_clear_buffer_revoked_flags": 2, "kprobe:jbd2_journal_get_log_tail": 2, "kprobe:jbd2_log_start_commit": 3, "kprobe:jbd2_journal_try_remove_checkpoint": 3, "kprobe:jbd2_descriptor_block_csum_set": 4, "kprobe:jbd2_journal_get_descriptor_buffer": 6, "kprobe:jbd2_journal_release_jbd_inode": 8, "kprobe:jbd2_journal_init_jbd_inode": 8, "kprobe:jbd2_journal_begin_ordered_truncate": 9, "kprobe:jbd2_journal_start_reserved": 13, "kprobe:jbd2_journal_write_metadata_buffer": 37, "kprobe:jbd2_journal_forget": 63, "kprobe:jbd2_journal_set_features": 63, "kprobe:jbd2_journal_revoke": 63, "kprobe:jbd2_journal_check_used_features": 63, "kprobe:jbd2_journal_get_create_access": 63, "kprobe:jbd2_buffer_frozen_trigger": 67, "kprobe:jbd2_journal_file_buffer": 68, "kprobe:jbd2_journal_bmap": 74, "kprobe:jbd2_journal_next_log_block": 74, "kprobe:jbd2_journal_add_journal_head": 101, "kprobe:jbd2_journal_cancel_revoke": 101, "kprobe:jbd2_journal_blocks_per_page": 113, "kprobe:jbd2_journal_put_journal_head": 444, "kprobe:jbd2__journal_start": 1072, "kprobe:jbd2_journal_stop": 1085, "kprobe:jbd2_journal_try_to_free_buffers": 2139, "kprobe:jbd2_journal_grab_journal_head": 2371, "kprobe:jbd2_journal_get_write_access": 2917, "kprobe:jbd2_write_access_granted": 2917, "kprobe:jbd2_journal_dirty_metadata": 2980}}}
```

#### prb

```console
{"type": "map", "data": {"@mycount": {"kprobe:prb_final_commit": 168, "kprobe:prb_reserve": 168, "kprobe:prb_read_valid_info": 226, "kprobe:prb_read_valid": 1072, "kprobe:prb_read": 1298}}}
```

#### cache

```console
{"type": "map", "data": {"@mycount": {"kprobe:cachemode2protval": 337, "kprobe:cache_finish_page": 13496, "kprobe:cache_first_page": 13496, "kprobe:cache_next_page": 122528}}}
```

#### nl

```console
{"type": "map", "data": {"@mycount": {"kprobe:nlmsg_notify": 2, "kprobe:nldev_get_dumpit": 112, "kprobe:nla_put_ifalias": 2240}}}
```

#### stream

```console
{"type": "map", "data": {"@mycount": {"kprobe:stream_open": 6052}}}
```

#### alloc

```console
{"type": "map", "data": {"@mycount": {"kprobe:alloc_misplaced_dst_folio": 2, "kprobe:alloc_worker": 2, "kprobe:alloc_fdtable": 48, "kprobe:alloc_mnt_ns": 112, "kprobe:alloc_tty_struct": 112, "kprobe:alloc_super": 224, "kprobe:alloc_ucounts": 280, "kprobe:alloc_fs_context": 280, "kprobe:alloc_bprm": 449, "kprobe:alloc_new_pud.constprop.0": 922, "kprobe:alloc_pipe_info": 1293, "kprobe:alloc_file_clone": 1349, "kprobe:alloc_pages_bulk_array_mempolicy": 1793, "kprobe:alloc_vmap_area": 1969, "kprobe:alloc_buffer_head": 2293, "kprobe:alloc_thread_stack_node": 2371, "kprobe:alloc_pid": 2371, "kprobe:alloc_user_cpus_ptr": 2562, "kprobe:allocate_slab": 4379, "kprobe:alloc_vfsmnt": 5096, "kprobe:alloc_skb_with_frags": 6104, "kprobe:alloc_file_pseudo": 6434, "kprobe:alloc_empty_backing_file": 7672, "kprobe:alloc_file": 7777, "kprobe:alloc_inode": 55412, "kprobe:alloc_fd": 110043, "kprobe:alloc_empty_file": 111338, "kprobe:alloc_pages": 750482}}}
```

#### p4

```console
{"type": "map", "data": {"@mycount": {"kprobe:p4d_clear_huge": 1461}}}
```

#### ma

```console
{"type": "map", "data": {"@mycount": {"kprobe:mark_precise_scalar_ids": 1, "kprobe:mark_buffer_async_write_endio": 7, "kprobe:map_lookup_elem": 41, "kprobe:may_open_dev": 56, "kprobe:make_kprojid": 72, "kprobe:machine_check_poll": 139, "kprobe:mark_ptr_not_null_reg": 150, "kprobe:madvise_dontneed_free_valid_vma": 277, "kprobe:mark_ptr_or_null_regs": 304, "kprobe:mark_reg_known_zero": 310, "kprobe:map_vdso": 449, "kprobe:may_setattr": 626, "kprobe:map_pte": 762, "kprobe:madvise_update_vma": 993, "kprobe:mark_reg_unknown": 1112, "kprobe:madvise_walk_vmas": 1151, "kprobe:may_delete": 1250, "kprobe:madvise_vma_behavior": 1270, "kprobe:maybe_emit_mod": 1612, "kprobe:mark_ptr_or_null_reg.constprop.0": 3322, "kprobe:mark_reg_not_init": 3588, "kprobe:mark_buffer_dirty": 4723, "kprobe:match_exception_partial": 5397, "kprobe:maybe_add_creds": 6107, "kprobe:maybe_emit_1mod": 6432, "kprobe:mark_reg_read": 6437, "kprobe:mangle_path": 10821, "kprobe:may_open": 28143, "kprobe:may_expand_vm": 56550, "kprobe:make_kgid": 76558, "kprobe:make_kuid": 80795, "kprobe:map_id_up": 133708, "kprobe:map_id_range_down": 157425, "kprobe:make_vfsgid": 356771, "kprobe:make_vfsuid": 1455823, "kprobe:mark_page_accessed": 1534966}}}
```

#### follow

```console
{"type": "map", "data": {"@mycount": {"kprobe:follow_down": 112, "kprobe:follow_page_pte": 2187, "kprobe:follow_p4d_mask": 2187, "kprobe:follow_pmd_mask.isra.0": 2187, "kprobe:follow_page_mask": 2636}}}
```

#### ext4fs

```console
{"type": "map", "data": {"@mycount": {"kprobe:ext4fs_dirhash": 2151}}}
```

#### housekeeping

```console
{"type": "map", "data": {"@mycount": {"kprobe:housekeeping_test_cpu": 1536, "kprobe:housekeeping_cpumask": 5451}}}
```

#### tr

```console
{"type": "map", "data": {"@mycount": {"kprobe:truncate_inode_partial_folio": 4, "kprobe:truncate_pagecache": 10, "kprobe:try_to_migrate": 16, "kprobe:try_to_unmap_flush": 16, "kprobe:try_to_migrate_one": 36, "kprobe:truncate_inode_pages": 95, "kprobe:transfer_pid": 168, "kprobe:tracefs_show_options": 224, "kprobe:try_check_zero": 298, "kprobe:track_pfn_insert": 337, "kprobe:track_pfn_copy": 533, "kprobe:try_to_unlazy_next": 1229, "kprobe:try_grab_folio": 1998, "kprobe:try_grab_page": 2019, "kprobe:try_to_free_buffers": 2142, "kprobe:truncate_inode_folio": 2791, "kprobe:try_to_grab_pending": 16971, "kprobe:truncate_inode_pages_final": 53032, "kprobe:truncate_inode_pages_range": 53137, "kprobe:try_module_get": 57348, "kprobe:trigger_load_balance": 64839, "kprobe:try_to_unlazy": 95415, "kprobe:truncate_cleanup_folio": 441723, "kprobe:try_to_wake_up": 662113, "kprobe:try_charge_memcg": 903586}}}
```

#### conv

```console
{"type": "map", "data": {"@mycount": {"kprobe:convert_ctx_accesses": 6}}}
```

#### physical

```console
{"type": "map", "data": {"@mycount": {"kprobe:physical_package_id_show": 2, "kprobe:physical_line_partition_show": 194}}}
```

FAILED TO COMPILE after this one

#### delay

```console
{"type": "map", "data": {"@mycount": {"kprobe:delayed_work_timer_fn": 796, "kprobe:delayed_vfree_work": 991, "kprobe:delayacct_add_tsk": 2093, "kprobe:delayed_put_pid": 2373, "kprobe:delayed_put_task_struct": 2373, "kprobe:delayed_free_vfsmnt": 5096}}}
```

#### calculate

```console
{"type": "map", "data": {"@mycount": {"kprobe:calculate_sigpending": 2364}}}
```

#### synchronize

```console
{"type": "map", "data": {"@mycount": {"kprobe:synchronize_rcu_tasks_rude": 4, "kprobe:synchronize_rcu_tasks_generic": 5, "kprobe:synchronize_rcu": 10, "kprobe:synchronize_srcu": 133, "kprobe:synchronize_rcu_expedited_wait": 142, "kprobe:synchronize_rcu_expedited": 280}}}
```

#### igrab

```console
{"type": "map", "data": {"@mycount": {"kprobe:igrab": 282}}}
```

#### idle

```console
{"type": "map", "data": {"@mycount": {"kprobe:idle_worker_timeout": 51, "kprobe:idle_cull_fn": 54, "kprobe:idle_cpu": 63214944}}}
```

#### mangle

```console
{"type": "map", "data": {"@mycount": {"kprobe:mangle_path": 10821}}}
```

#### pop

```console
{"type": "map", "data": {"@mycount": {"kprobe:pop_stack": 3, "kprobe:populate_seccomp_data": 96836}}}
```

#### em

```console
{"type": "map", "data": {"@mycount": {"kprobe:empty_dir_lookup": 56, "kprobe:emit_ldx": 84, "kprobe:emit_prologue": 100, "kprobe:emit_return": 104, "kprobe:emit_mov_imm64": 184, "kprobe:emit_insn_suffix": 240, "kprobe:emit_mov_reg": 288, "kprobe:emit_stx": 324, "kprobe:emit_mov_imm32": 348}}}
```

#### ptm

```console
{"type": "map", "data": {"@mycount": {"kprobe:ptmx_open": 56, "kprobe:ptm_open_peer": 56}}}
```

#### mnt

```console
{"type": "map", "data": {"@mycount": {"kprobe:mntns_get": 56, "kprobe:mntns_install": 56, "kprobe:mntns_put": 56, "kprobe:mnt_cursor_del": 169, "kprobe:mnt_set_mountpoint": 224, "kprobe:mnt_warn_timestamp_expiry": 616, "kprobe:mnt_may_suid": 898, "kprobe:mnt_release_group_id": 1848, "kprobe:mnt_drop_write": 3685, "kprobe:mnt_want_write": 3686, "kprobe:mnt_idmap_get": 4872, "kprobe:mnt_idmap_put": 5095, "kprobe:mnt_get_writers": 5096, "kprobe:mnt_get_count": 6328, "kprobe:mntget": 93209, "kprobe:mntput_no_expire": 253506, "kprobe:mntput": 323752}}}
```

#### legitimize

```console
{"type": "map", "data": {"@mycount": {"kprobe:legitimize_links": 96498}}}
```

#### poll

```console
{"type": "map", "data": {"@mycount": {"kprobe:poll_state_synchronize_rcu": 7, "kprobe:poll_select_finish": 227, "kprobe:pollwake": 1787, "kprobe:poll_select_set_timeout": 348686, "kprobe:poll_freewait": 349113}}}
```

#### vfsgid

```console
{"type": "map", "data": {"@mycount": {"kprobe:vfsgid_in_group_p": 1758}}}
```

#### rand

```console
{"type": "map", "data": {"@mycount": {"kprobe:randomize_page": 449, "kprobe:randomize_stack_top": 449}}}
```

#### setfl

```console
{"type": "map", "data": {"@mycount": {"kprobe:setfl": 4763}}}
```

#### crng

```console
{"type": "map", "data": {"@mycount": {"kprobe:crng_make_state": 1775, "kprobe:crng_fast_key_erasure": 1776}}}
```

#### fsnotify

```console
{"type": "map", "data": {"@mycount": {"kprobe:fsnotify_mark_destroy_workfn": 58, "kprobe:fsnotify_connector_destroy_workfn": 60, "kprobe:fsnotify_put_group": 168, "kprobe:fsnotify_add_mark_locked": 168, "kprobe:fsnotify_detach_connector_from_object": 168, "kprobe:fsnotify_destroy_mark": 168, "kprobe:fsnotify_init_mark": 168, "kprobe:fsnotify_detach_mark": 168, "kprobe:fsnotify_free_mark": 168, "kprobe:fsnotify_get_group": 168, "kprobe:fsnotify_put_sb_connectors": 168, "kprobe:fsnotify_sb_delete": 168, "kprobe:fsnotify_drop_object": 168, "kprobe:fsnotify_add_mark_list.constprop.0": 168, "kprobe:fsnotify_compare_groups": 174, "kprobe:fsnotify_handle_inode_event.isra.0": 194, "kprobe:fsnotify_get_cookie": 336, "kprobe:fsnotify_destroy_event": 345, "kprobe:fsnotify_insert_event": 364, "kprobe:fsnotify_remove_first_event": 372, "kprobe:fsnotify_get_mark": 672, "kprobe:fsnotify_put_mark": 840, "kprobe:fsnotify_peek_first_event": 907, "kprobe:fsnotify_find_mark": 2607, "kprobe:fsnotify": 24981, "kprobe:fsnotify_destroy_marks": 61857, "kprobe:fsnotify_grab_connector": 64800}}}
```

#### pid

```console
{"type": "map", "data": {"@mycount": {"kprobe:pid_maps_open": 1, "kprobe:pid_update_inode": 112, "kprobe:pid_nr_ns": 112, "kprobe:pidfd_prepare": 280, "kprobe:pidfd_release": 280, "kprobe:pidfd_poll": 560, "kprobe:pids_release": 2355, "kprobe:pids_can_fork": 2387, "kprobe:pid_vnr": 4552, "kprobe:pid_delete_dentry": 11207, "kprobe:pid_revalidate": 11724, "kprobe:pid_task": 13855}}}
```

#### msg

```console
{"type": "map", "data": {"@mycount": {"kprobe:msg_add_ext_text": 168, "kprobe:msg_add_dict_text": 336}}}
```

#### kmalloc

```console
{"type": "map", "data": {"@mycount": {"kprobe:kmalloc_large": 1, "kprobe:kmalloc_node_trace": 1471, "kprobe:kmalloc_size_roundup": 9687, "kprobe:kmalloc_reserve": 14375, "kprobe:kmalloc_trace": 135807, "kprobe:kmalloc_slab": 177379}}}
```

#### cachemode2protval

```console
{"type": "map", "data": {"@mycount": {"kprobe:cachemode2protval": 337}}}
```

#### ramfs

```console
{"type": "map", "data": {"@mycount": {"kprobe:ramfs_show_options": 112}}}
```

#### vmem

```console
{"type": "map", "data": {"@mycount": {"kprobe:vmemdup_user": 43}}}
```

#### open

```console
{"type": "map", "data": {"@mycount": {"kprobe:open_exec": 617, "kprobe:open_last_lookups": 40976}}}
```

#### clockevents

```console
{"type": "map", "data": {"@mycount": {"kprobe:clockevents_program_min_delta": 2, "kprobe:clockevents_program_event": 894645}}}
```

#### graft

```console
{"type": "map", "data": {"@mycount": {"kprobe:graft_tree": 952}}}
```

#### kmem

```console
{"type": "map", "data": {"@mycount": {"kprobe:kmemdup_nul": 336, "kprobe:kmem_cache_alloc_node": 24231, "kprobe:kmem_cache_alloc_bulk": 102205, "kprobe:kmem_cache_free_bulk": 102785, "kprobe:kmem_cache_alloc_lru": 142994, "kprobe:kmem_cache_alloc": 1067302, "kprobe:kmem_cache_free": 1443625}}}
```

#### dequeue

```console
{"type": "map", "data": {"@mycount": {"kprobe:dequeue_task_rt": 158, "kprobe:dequeue_top_rt_rq": 316, "kprobe:dequeue_rt_stack": 320, "kprobe:dequeue_task_stop": 681, "kprobe:dequeue_signal": 1031, "kprobe:dequeue_task_fair": 665782, "kprobe:dequeue_entity": 1204619}}}
```

#### state

```console
{"type": "map", "data": {"@mycount": {"kprobe:states_equal": 4}}}
```

#### rwb

```console
{"type": "map", "data": {"@mycount": {"kprobe:rwb_trace_step": 4, "kprobe:rwb_arm_timer": 14}}}
```

#### vdso

```console
{"type": "map", "data": {"@mycount": {"kprobe:vdso_fault": 617}}}
```

#### trans

```console
{"type": "map", "data": {"@mycount": {"kprobe:transfer_pid": 168}}}
```

#### parse

```console
{"type": "map", "data": {"@mycount": {"kprobe:parse_monolithic_mount_data": 280}}}
```

#### syslog

```console
{"type": "map", "data": {"@mycount": {"kprobe:syslog_print": 60}}}
```

#### sha1

```console
{"type": "map", "data": {"@mycount": {"kprobe:sha1_init": 10, "kprobe:sha1_transform": 68}}}
```

#### console

```console
{"type": "map", "data": {"@mycount": {"kprobe:console_unlock": 168, "kprobe:console_trylock_spinning": 168, "kprobe:console_flush_all": 168, "kprobe:console_trylock": 168, "kprobe:console_emit_next_record": 336}}}
```

#### pt

```console
{"type": "map", "data": {"@mycount": {"kprobe:pty_write": 47, "kprobe:pts_unix98_lookup": 56, "kprobe:pty_set_termios": 56, "kprobe:pty_set_lock": 56, "kprobe:pty_unix98_remove": 56, "kprobe:pty_common_install": 56, "kprobe:ptmx_open": 56, "kprobe:pty_flush_buffer": 56, "kprobe:pty_unix98_install": 56, "kprobe:ptm_open_peer": 56, "kprobe:pty_open": 112, "kprobe:pty_close": 112, "kprobe:pty_cleanup": 112, "kprobe:pty_unix98_ioctl": 168, "kprobe:ptrace_may_access": 3696, "kprobe:pty_write_room": 18922, "kprobe:pte_alloc_one": 21009, "kprobe:ptep_set_access_flags": 33572, "kprobe:ptep_clear_flush": 85055, "kprobe:pte_offset_map_nolock": 514383}}}
```

#### shmctl

```console
{"type": "map", "data": {"@mycount": {"kprobe:shmctl_stat": 57, "kprobe:shmctl_down": 57}}}
```

#### redirected

```console
{"type": "map", "data": {"@mycount": {"kprobe:redirected_tty_write": 57}}}
```

#### devkmsg

```console
{"type": "map", "data": {"@mycount": {"kprobe:devkmsg_read": 168, "kprobe:devkmsg_poll": 228}}}
```

#### mp

```console
{"type": "map", "data": {"@mycount": {"kprobe:mpol_misplaced": 2, "kprobe:mpage_map_and_submit_buffers": 9, "kprobe:mpage_map_and_submit_extent": 9, "kprobe:mpage_prepare_extent_to_map": 19, "kprobe:mpage_release_unused_pages": 19, "kprobe:mpol_new": 56, "kprobe:mpage_process_folio": 65, "kprobe:mpage_submit_folio": 455, "kprobe:mpage_process_page_bufs": 463, "kprobe:mpol_free_shared_policy": 788, "kprobe:mpol_shared_policy_init": 1292, "kprobe:mpol_put_task_policy": 2402, "kprobe:mpage_readahead": 2538, "kprobe:mpage_read_end_io": 2538, "kprobe:mpol_shared_policy_lookup": 2799, "kprobe:mprotect_fixup": 13460}}}
```

#### scale

```console
{"type": "map", "data": {"@mycount": {"kprobe:scale_up": 3}}}
```

#### rt

```console
{"type": "map", "data": {"@mycount": {"kprobe:rtnl_notify": 2, "kprobe:rtnl_calcit.isra.0": 560, "kprobe:rtnetlink_rcv_msg": 1120, "kprobe:rtnetlink_rcv": 1120, "kprobe:rtnl_link_fill": 1120, "kprobe:rtnl_dump_ifinfo": 1680, "kprobe:rtnl_dump_all": 1680, "kprobe:rtnl_xdp_prog_skb": 2240, "kprobe:rtnl_fill_vf": 2240, "kprobe:rtnl_fill_ifinfo": 2240, "kprobe:rtnl_fill_stats": 2240, "kprobe:rtnl_xdp_fill": 2240, "kprobe:rtnl_port_fill": 2240, "kprobe:rtnl_unlock": 2704, "kprobe:rtnl_lock": 2704, "kprobe:rtnl_is_locked": 4592}}}
```

#### ib

```console
{"type": "map", "data": {"@mycount": {"kprobe:ib_enum_all_devs": 112}}}
```

#### journal

```console
{"type": "map", "data": {"@mycount": {"kprobe:journal_end_buffer_io_sync": 33, "kprobe:journal_get_superblock": 63}}}
```

#### propagate

```console
{"type": "map", "data": {"@mycount": {"kprobe:propagate_liveness": 2, "kprobe:propagate_precision": 6, "kprobe:propagate_mount_unlock": 56, "kprobe:propagate_umount": 56, "kprobe:propagate_mnt": 224, "kprobe:propagate_protected_usage": 552458}}}
```

#### account

```console
{"type": "map", "data": {"@mycount": {"kprobe:account_system_index_time": 4149, "kprobe:account_system_time": 4150, "kprobe:account_idle_ticks": 6053, "kprobe:account_user_time": 6911, "kprobe:account_process_tick": 57433}}}
```

#### our 

```console
{"type": "map", "data": {"@mycount": {"kprobe:our_mnt": 898}}}
```

#### fasync

```console
{"type": "map", "data": {"@mycount": {"kprobe:fasync_remove_entry": 112, "kprobe:fasync_helper": 112}}}
```

#### decay

```console
{"type": "map", "data": {"@mycount": {"kprobe:decay_load": 186228}}}
```

#### trace

```console
{"type": "map", "data": {"@mycount": {"kprobe:tracefs_show_options": 224}}}
```


#### core

```console
{"type": "map", "data": {"@mycount": {"kprobe:core_id_show": 96, "kprobe:core_cpus_read": 192, "kprobe:core_sys_select": 227}}}
```

#### psi

```console
{"type": "map", "data": {"@mycount": {"kprobe:psi_memstall_enter": 2, "kprobe:psi_memstall_leave": 2, "kprobe:psi_avgs_work": 78, "kprobe:psi_task_change": 636009, "kprobe:psi_task_switch": 1185289, "kprobe:psi_flags_change": 1949133, "kprobe:psi_group_change": 6547330}}}
```

#### delayacct

```console
{"type": "map", "data": {"@mycount": {"kprobe:delayacct_add_tsk": 2098}}}
```

#### serial8250

```console
{"type": "map", "data": {"@mycount": {"kprobe:serial8250_start_tx": 398, "kprobe:serial8250_tx_chars": 1227, "kprobe:serial8250_interrupt": 1227, "kprobe:serial8250_modem_status": 1227, "kprobe:serial8250_handle_irq": 2454, "kprobe:serial8250_default_handle_irq": 2454}}}
```

#### inet6

```console
{"type": "map", "data": {"@mycount": {"kprobe:inet6_ioctl": 560, "kprobe:inet6_create": 560, "kprobe:inet6_cleanup_sock": 560, "kprobe:inet6_release": 560, "kprobe:inet6_sock_destruct": 560, "kprobe:inet6_dump_ifaddr": 1120, "kprobe:inet6_fill_ifaddr": 1120, "kprobe:inet6_dump_addr": 1120, "kprobe:inet6_fill_link_af": 1680, "kprobe:inet6_fill_ifla6_attrs": 1680}}}
```

#### rm

```console
{"type": "map", "data": {"@mycount": {"kprobe:rmap_walk": 21, "kprobe:rmap_walk_file": 42, "kprobe:rmqueue_bulk": 11363}}}
```

#### pollwake

```console
{"type": "map", "data": {"@mycount": {"kprobe:pollwake": 1800}}}
```

#### ns

```console
{"type": "map", "data": {"@mycount": {"kprobe:nsfs_show_path": 56, "kprobe:ns_capable_setid": 56, "kprobe:ns_to_kernel_old_timeval": 281, "kprobe:nsfs_evict": 765, "kprobe:ns_prune_dentry": 765, "kprobe:nsec_to_clock_t": 1044, "kprobe:ns_capable": 2744, "kprobe:ns_get_path": 3192, "kprobe:ns_to_timespec64": 3790, "kprobe:nsecs_to_jiffies": 11391}}}
```

#### cmd

```console
{"type": "map", "data": {"@mycount": {"kprobe:cmdline_proc_show": 336}}}
```

#### fl6

```console
{"type": "map", "data": {"@mycount": {"kprobe:fl6_free_socklist": 560}}}
```

#### need

```console
{"type": "map", "data": {"@mycount": {"kprobe:need_update": 13798, "kprobe:need_active_balance": 47903}}}
```

#### phy

```console
{"type": "map", "data": {"@mycount": {"kprobe:physical_package_id_show": 2, "kprobe:physical_line_partition_show": 194}}}
```

#### cpuinfo

```console
{"type": "map", "data": {"@mycount": {"kprobe:cpuinfo_open": 58}}}
```

#### detach

```console
{"type": "map", "data": {"@mycount": {"kprobe:detach_entity_load_avg": 731, "kprobe:detach_pid": 3881, "kprobe:detach_tasks": 28521, "kprobe:detach_if_pending": 68857}}}
```

#### for

```console
{"type": "map", "data": {"@mycount": {"kprobe:force_qs_rnp": 381, "kprobe:force_page_cache_ra": 2034, "kprobe:forget_original_parent": 2371}}}
```

#### worker

```console
{"type": "map", "data": {"@mycount": {"kprobe:worker_thread": 2, "kprobe:worker_attach_to_pool": 2, "kprobe:worker_detach_from_pool": 2, "kprobe:worker_enter_idle": 54452}}}
```

#### clock

```console
{"type": "map", "data": {"@mycount": {"kprobe:clockevents_program_min_delta": 11, "kprobe:clockevents_program_event": 852746}}}
```

#### sch

```console
{"type": "map", "data": {"@mycount": {"kprobe:schedule_page_work_fn": 1, "kprobe:sched_setnuma": 1, "kprobe:sched_setscheduler_nocheck": 2, "kprobe:schedule_timeout_idle": 5, "kprobe:schedule_on_each_cpu": 10, "kprobe:sched_rt_period_timer": 10, "kprobe:sched_exec": 449, "kprobe:sched_mm_cid_after_execve": 449, "kprobe:sched_setaffinity": 473, "kprobe:sched_autogroup_fork": 506, "kprobe:sched_autogroup_exit": 539, "kprobe:sched_getaffinity": 612, "kprobe:schedule_preempt_disabled": 1808, "kprobe:sched_mm_cid_fork": 2363, "kprobe:sched_post_fork": 2365, "kprobe:sched_core_fork": 2365, "kprobe:sched_fork": 2365, "kprobe:sched_cgroup_fork": 2365, "kprobe:schedule_tail": 2365, "kprobe:sched_core_free": 2392, "kprobe:sched_move_task": 2393, "kprobe:sched_autogroup_exit_task": 2399, "kprobe:sched_mm_cid_exit_signals": 2399, "kprobe:sched_slice": 2407, "kprobe:sched_mm_cid_before_execve": 2848, "kprobe:schedule_delayed_monitor_work": 5681, "kprobe:sched_mm_cid_migrate_to": 11768, "kprobe:schedule_hrtimeout_range_clock": 19449, "kprobe:schedule_hrtimeout_range": 19452, "kprobe:schedule_timeout": 33673, "kprobe:scheduler_tick": 60071, "kprobe:sched_mm_cid_remote_clear": 106738, "kprobe:sched_ttwu_pending": 147250, "kprobe:schedule_idle": 519188, "kprobe:schedule": 627970, "kprobe:sched_idle_set_state": 1548483}}}
```

#### untrack

```console
{"type": "map", "data": {"@mycount": {"kprobe:untrack_pfn": 954}}}
```

#### bt

```console
{"type": "map", "data": {"@mycount": {"kprobe:btf_alloc_id": 3, "kprobe:btf_check_all_metas": 10, "kprobe:btf_check_all_types": 11, "kprobe:btf_check_func_arg_match": 13, "kprobe:btf_check_subprog_arg_match": 16, "kprobe:btf_check_type_tags": 19, "kprobe:btf_datasec_check_meta": 21, "kprobe:btf_datasec_resolve": 23, "kprobe:btf_array_check_meta": 30, "kprobe:btf_array_resolve": 42, "kprobe:btf_get_by_fd": 63, "kprobe:btf_get_prog_ctx_type": 68, "kprobe:btf_is_kernel": 75, "kprobe:btf_name_by_offset": 86, "kprobe:btf_new_fd": 88, "kprobe:btf_parse": 91, "kprobe:btf_parse_hdr": 94, "kprobe:btf_parse_str_sec": 97, "kprobe:btf_parse_struct_metas.constprop.0": 98, "kprobe:btf_release": 112, "kprobe:btf_free_rcu": 115, "kprobe:btf_sec_info_cmp": 116, "kprobe:btf_free_kfunc_set_tab": 116, "kprobe:btf_free": 117, "kprobe:btf_put": 169, "kprobe:btf_record_find": 216, "kprobe:btf_find_by_name_kind": 246, "kprobe:btf_type_skip_modifiers": 292, "kprobe:btf_int_check_meta": 360, "kprobe:btf_struct_check_meta": 378, "kprobe:btf_struct_resolve": 387, "kprobe:btf_type_by_id": 399, "kprobe:btf_var_check_meta": 450, "kprobe:btf_var_resolve": 456, "kprobe:btf_verifier_log_vsi": 468, "kprobe:btf_add_type.isra.0": 734, "kprobe:btf_ptr_resolve": 927, "kprobe:btf_ref_type_check_meta": 990, "kprobe:btf_ptr_check_member": 1020, "kprobe:btf_verifier_log_member": 1550, "kprobe:btf_type_id_resolve": 1608, "kprobe:btf_type_int_is_regular": 1644, "kprobe:btf_func_check_meta": 9180, "kprobe:btf_func_proto_check": 9350, "kprobe:btf_func_proto_check_meta": 9520, "kprobe:btf_func_resolve": 9860, "kprobe:btf_resolve": 21696, "kprobe:btf_resolve_valid": 22080, "kprobe:btf_type_id_size": 50355, "kprobe:btf_type_needs_resolve.isra.0": 99820}}}
```

#### on

```console
{"type": "map", "data": {"@mycount": {"kprobe:ondemand_readahead": 13730, "kprobe:on_each_cpu_cond_mask": 46815}}}
```

#### remove

```console
{"type": "map", "data": {"@mycount": {"kprobe:remove_migration_pte": 18, "kprobe:remove_files": 56, "kprobe:remove_arg_zero": 168, "kprobe:remove_vm_area": 1521, "kprobe:remove_entity_load_avg": 12851, "kprobe:remove_wait_queue": 27549, "kprobe:remove_vma": 143094}}}
```

#### ll

```console
{"type": "map", "data": {"@mycount": {"kprobe:ll_back_merge_fn": 3}}}
```

#### strndup

```console
{"type": "map", "data": {"@mycount": {"kprobe:strndup_user": 3079}}}
```

#### commit

```console
{"type": "map", "data": {"@mycount": {"kprobe:commit_tree": 1176, "kprobe:commit_creds": 3305}}}
```

#### watchdog

```console
{"type": "map", "data": {"@mycount": {"kprobe:watchdog_timer_fn": 192}}}
```

#### subsystem

```console
{"type": "map", "data": {"@mycount": {"kprobe:subsystem_vendor_show": 142, "kprobe:subsystem_device_show": 142}}}
```

#### unregister

```console
{"type": "map", "data": {"@mycount": {"kprobe:unregister_shrinker": 224, "kprobe:unregister_hw_breakpoint": 11480}}}
```

#### apic

```console
{"type": "map", "data": {"@mycount": {"kprobe:apic_ack_edge": 1271}}}
```

#### change

```console
{"type": "map", "data": {"@mycount": {"kprobe:change_page_attr_set_clr": 6, "kprobe:change_pid": 56, "kprobe:change_pte_range": 10424, "kprobe:change_protection_range": 13446, "kprobe:change_protection": 13446, "kprobe:change_mnt_propagation": 13888}}}
```

#### stat

```console
{"type": "map", "data": {"@mycount": {"kprobe:states_equal": 8, "kprobe:statfs_by_dentry": 841}}}
```

#### dax

```console
{"type": "map", "data": {"@mycount": {"kprobe:dax_layout_busy_page": 10, "kprobe:dax_layout_busy_page_range": 10}}}
```

#### isolate

```console
{"type": "map", "data": {"@mycount": {"kprobe:isolate_lru_page": 6}}}
```

#### devcgroup

```console
{"type": "map", "data": {"@mycount": {"kprobe:devcgroup_check_permission": 5209}}
```

#### transfer

```console
{"type": "map", "data": {"@mycount": {"kprobe:transfer_pid": 168}}}
```

#### squashfs

```console
{"type": "map", "data": {"@mycount": {"kprobe:squashfs_read_inode_lookup_table": 56, "kprobe:squashfs_max_decompressors": 56, "kprobe:squashfs_decompressor_setup": 56, "kprobe:squashfs_statfs": 56, "kprobe:squashfs_decompressor_create": 56, "kprobe:squashfs_init_fs_context": 56, "kprobe:squashfs_fill_super": 56, "kprobe:squashfs_get_tree": 56, "kprobe:squashfs_lookup_decompressor": 56, "kprobe:squashfs_read_id_index_table": 56, "kprobe:squashfs_decompressor_destroy": 56, "kprobe:squashfs_read_fragment_index_table": 56, "kprobe:squashfs_free_fs_context": 56, "kprobe:squashfs_put_super": 56, "kprobe:squashfs_read_xattr_id_table": 56, "kprobe:squashfs_parse_param": 56, "kprobe:squashfs_cache_delete": 168, "kprobe:squashfs_cache_init": 168, "kprobe:squashfs_readpage_block": 224, "kprobe:squashfs_read_folio": 336, "kprobe:squashfs_read_table": 336, "kprobe:squashfs_show_options": 504, "kprobe:squashfs_readdir": 560, "kprobe:squashfs_page_actor_init": 1008, "kprobe:squashfs_symlink_read_folio": 1624, "kprobe:squashfs_get_fragment": 5040, "kprobe:squashfs_page_actor_init_special": 10640, "kprobe:squashfs_readahead": 12208, "kprobe:squashfs_frag_lookup": 15344, "kprobe:squashfs_xattr_get": 18536, "kprobe:squashfs_xattr_handler_get": 18536, "kprobe:squashfs_iget": 20216, "kprobe:squashfs_free_inode": 20272, "kprobe:squashfs_read_inode": 20272, "kprobe:squashfs_alloc_inode": 20272, "kprobe:squashfs_decompress": 22960, "kprobe:squashfs_read_data": 24136, "kprobe:squashfs_lookup": 26880, "kprobe:squashfs_bio_read": 32536, "kprobe:squashfs_get_id": 40544, "kprobe:squashfs_fill_page": 48272, "kprobe:squashfs_read_metadata": 5223904, "kprobe:squashfs_cache_get": 5239416, "kprobe:squashfs_cache_put": 5239416, "kprobe:squashfs_copy_data": 5282648}}}
squashfs
```

#### nv

```console
{"type": "map", "data": {"@mycount": {"kprobe:nvme_queue_rqs": 6, "kprobe:nvme_pci_setup_prps": 9, "kprobe:nvme_setup_discard": 41, "kprobe:nvme_queue_rq": 44, "kprobe:nvme_setup_cmd": 52, "kprobe:nvme_unmap_data": 52, "kprobe:nvme_pci_complete_batch": 69, "kprobe:nvme_irq": 80, "kprobe:nvme_map_data": 90, "kprobe:nvme_complete_batch_req": 365}}}
```

#### privileged

```console
{"type": "map", "data": {"@mycount": {"kprobe:privileged_wrt_inode_uidgid": 1439}}}
```

#### inflate

```console
{"type": "map", "data": {"@mycount": {"kprobe:inflate_fast": 734272}}}
```

#### convert

```console
{"type": "map", "data": {"@mycount": {"kprobe:convert_ctx_accesses": 3}}}
```

#### smp

```console
{"type": "map", "data": {"@mycount": {"kprobe:smp_call_function_single_async": 1018, "kprobe:smp_call_function_single": 3299, "kprobe:smp_call_function_many_cond": 44162}}}
```

#### mpol

```console
{"type": "map", "data": {"@mycount": {"kprobe:mpol_misplaced": 44, "kprobe:mpol_new": 56, "kprobe:mpol_free_shared_policy": 786, "kprobe:mpol_shared_policy_init": 1290, "kprobe:mpol_put_task_policy": 2374, "kprobe:mpol_shared_policy_lookup": 2799}}}
```

#### notify

```console
{"type": "map", "data": {"@mycount": {"kprobe:notify_change": 628}}}
```

#### delayed

```console
{"type": "map", "data": {"@mycount": {"kprobe:delayed_work_timer_fn": 790, "kprobe:delayed_vfree_work": 1018, "kprobe:delayed_put_task_struct": 2379, "kprobe:delayed_put_pid": 2379, "kprobe:delayed_free_vfsmnt": 5095}}}
```

#### dl

```console
{"type": "map", "data": {"@mycount": {"kprobe:dl_task_check_affinity": 473}}}
```

#### vunmap

```console
{"type": "map", "data": {"@mycount": {"kprobe:vunmap_p4d_range": 1456}}}
```

#### part

```console
{"type": "map", "data": {"@mycount": {"kprobe:part_size_show": 1}}}
```

#### serial

```console
{"type": "map", "data": {"@mycount": {"kprobe:serial_port_runtime_resume": 1, "kprobe:serial8250_start_tx": 396, "kprobe:serial8250_interrupt": 1223, "kprobe:serial8250_tx_chars": 1223, "kprobe:serial8250_modem_status": 1223, "kprobe:serial8250_default_handle_irq": 2446, "kprobe:serial8250_handle_irq": 2446}}}
```

#### always

```console
{"type": "map", "data": {"@mycount": {"kprobe:always_delete_dentry": 3406}}}
```

#### direct

```console
{"type": "map", "data": {"@mycount": {"kprobe:direct_first_page": 10640, "kprobe:direct_finish_page": 10640, "kprobe:direct_next_page": 300216}}}
```

#### invoke

```console
{"type": "map", "data": {"@mycount": {"kprobe:invoke_rcu_core": 47569}}}
```

#### child

```console
{"type": "map", "data": {"@mycount": {"kprobe:child_wait_callback": 129}}}
```

#### bit

```console
{"type": "map", "data": {"@mycount": {"kprobe:bit_wait_io": 3, "kprobe:bit_waitqueue": 55610}}}
```

#### crypt

```console
{"type": "map", "data": {"@mycount": {"kprobe:crypto_shash_update": 13572}}}
```

#### create

```console
{"type": "map", "data": {"@mycount": {"kprobe:create_worker": 11, "kprobe:create_empty_buffers": 14, "kprobe:create_files": 56, "kprobe:create_new_namespaces": 168, "kprobe:create_elf_tables": 449, "kprobe:create_pipe_files": 1270}}}
```

#### simple

```console
{"type": "map", "data": {"@mycount": {"kprobe:simple_statfs": 56, "kprobe:simple_read_from_buffer": 56, "kprobe:simple_empty": 336, "kprobe:simple_xattr_get": 1176, "kprobe:simple_acl_create": 1233, "kprobe:simple_xattrs_init": 1962, "kprobe:simple_xattrs_free": 1962, "kprobe:simple_lookup": 4696, "kprobe:simple_copy_to_iter": 14483}}}
```

#### vprintk

```console
{"type": "map", "data": {"@mycount": {"kprobe:vprintk_store": 168, "kprobe:vprintk": 168, "kprobe:vprintk_default": 168, "kprobe:vprintk_emit": 168}}}
```

#### printk

```console
{"type": "map", "data": {"@mycount": {"kprobe:printk_sprint": 168, "kprobe:printk_parse_prefix": 336, "kprobe:printk_get_next_message": 504}}}
```

#### pw

```console
{"type": "map", "data": {"@mycount": {"kprobe:pwq_dec_nr_in_flight": 57040}}}
```

#### blk

```console
{"type": "map", "data": {"@mycount": {"kprobe:blkdev_read_folio": 1, "kprobe:blk_bio_list_merge": 19, "kprobe:blk_stat_timer_fn": 24, "kprobe:blk_next_bio": 41, "kprobe:blkdev_issue_discard": 41, "kprobe:blk_account_io_merge_bio": 51, "kprobe:blk_mq_timeout_work": 54, "kprobe:blk_mq_queue_tag_busy_iter": 55, "kprobe:blk_mq_run_hw_queues": 56, "kprobe:blk_queue_usage_counter_release": 56, "kprobe:blk_mq_unfreeze_queue": 56, "kprobe:blkdev_get_by_path": 56, "kprobe:blk_freeze_queue_start": 56, "kprobe:blk_queue_flag_set": 56, "kprobe:blk_mq_freeze_queue_wait": 56, "kprobe:blk_mq_freeze_queue": 56, "kprobe:blk_rq_timed_out_timer": 58, "kprobe:blk_queue_physical_block_size": 112, "kprobe:blk_queue_logical_block_size": 112, "kprobe:blk_queue_io_min": 112, "kprobe:blk_queue_max_discard_sectors": 112, "kprobe:blk_queue_max_write_zeroes_sectors": 112, "kprobe:blkdev_flush_mapping": 168, "kprobe:blk_mq_put_tags": 518, "kprobe:blk_mq_end_request_batch": 518, "kprobe:blk_mq_sched_bio_merge": 594, "kprobe:blk_rq_merge_ok": 613, "kprobe:blk_attempt_plug_merge": 645, "kprobe:blk_integrity_merge_bio": 692, "kprobe:blkcg_iostat_update": 750, "kprobe:blkdev_common_ioctl": 2044, "kprobe:blkdev_release": 2268, "kprobe:blkdev_get_by_dev": 2268, "kprobe:blkdev_open": 2268, "kprobe:blkdev_put": 2324, "kprobe:blkdev_get_no_open": 2324, "kprobe:blkdev_get_whole": 2324, "kprobe:blkdev_ioctl": 2324, "kprobe:blkdev_put_whole": 2324, "kprobe:blkcg_exit": 2387, "kprobe:blkdev_llseek": 2520, "kprobe:blk_mq_request_issue_directly": 2604, "kprobe:blk_mq_plug_issue_direct": 2604, "kprobe:blkdev_readahead": 2604, "kprobe:blkdev_get_block": 2608, "kprobe:blkdev_read_iter": 2632, "kprobe:blkcg_rstat_flush": 5040, "kprobe:blk_mq_try_issue_directly": 15799, "kprobe:blk_start_plug": 16129, "kprobe:blk_finish_plug": 16149, "kprobe:blk_mq_flush_busy_ctxs": 17013, "kprobe:blk_mq_dispatch_rq_list": 17013, "kprobe:blk_mq_run_work_fn": 17013, "kprobe:blk_mq_sched_dispatch_requests": 17013, "kprobe:blk_mq_hctx_mark_pending": 17018, "kprobe:blk_mq_insert_requests": 17018, "kprobe:blk_mq_dispatch_plug_list": 17018, "kprobe:blk_mq_delay_run_hw_queue": 17018, "kprobe:blk_mq_hctx_has_pending": 17074, "kprobe:blk_mq_run_hw_queue": 17074, "kprobe:blk_mq_get_budget_and_tag": 18403, "kprobe:blk_add_rq_to_plug": 19940, "kprobe:blk_complete_reqs": 34057, "kprobe:blk_done_softirq": 34057, "kprobe:blk_mq_complete_request": 35144, "kprobe:blk_mq_put_tag": 35144, "kprobe:blk_mq_free_request": 35144, "kprobe:blk_mq_end_request": 35144, "kprobe:blk_update_request": 35144, "kprobe:blk_status_to_errno": 35181, "kprobe:blkcg_set_ioprio": 35214, "kprobe:blk_queue_exit": 35309, "kprobe:blk_stat_add": 35671, "kprobe:blk_add_timer": 35739, "kprobe:blk_mq_start_request": 35739, "kprobe:blk_mq_complete_request_remote": 35739, "kprobe:blk_mq_get_tag": 35739, "kprobe:blk_mq_rq_ctx_init.isra.0": 35739, "kprobe:blk_cgroup_bio_start": 35790, "kprobe:blk_mq_submit_bio": 35790, "kprobe:blk_mq_attempt_bio_merge": 35790, "kprobe:blk_mq_flush_plug_list": 50173, "kprobe:blk_cgroup_congested": 295969, "kprobe:blkcg_maybe_throttle_current": 629007}}}
```

#### expand

```console
{"type": "map", "data": {"@mycount": {"kprobe:expand_stack_locked": 449, "kprobe:expand_downwards": 617, "kprobe:expand_files": 110994}}}
```

#### search

```console
{"type": "map", "data": {"@mycount": {"kprobe:search_binary_handler": 617, "kprobe:search_exception_tables": 1428}}}
```

#### would

```console
{"type": "map", "data": {"@mycount": {"kprobe:would_dump": 898}}}
```

#### dec

```console
{"type": "map", "data": {"@mycount": {"kprobe:dec_ucount": 280, "kprobe:dec_rlimit_put_ucounts": 1062, "kprobe:dec_rlimit_ucounts": 2375, "kprobe:decay_load": 185942}}}
```

#### sys

```console
{"type": "map", "data": {"@mycount": {"kprobe:sysfs_format_mac": 1, "kprobe:sysfs_get_tree": 56, "kprobe:sysfs_create_group": 56, "kprobe:sysfs_init_fs_context": 56, "kprobe:sysfs_remove_group": 56, "kprobe:sysfs_fs_context_free": 56, "kprobe:syslog_print": 60, "kprobe:sysfs_add_file_mode_ns": 336, "kprobe:sys_dmi_field_show": 354, "kprobe:sysctl_perm": 392, "kprobe:sysfs_kf_bin_read": 532, "kprobe:sysfs_emit_at": 2484, "kprobe:sysfs_emit": 3769, "kprobe:sysfs_kf_seq_show": 4830, "kprobe:syscall_trace_enter.constprop.0": 97643}}}
```

#### call

```console
{"type": "map", "data": {"@mycount": {"kprobe:call_rcu_tasks_rude": 18, "kprobe:call_rcu_tasks_iw_wakeup": 19, "kprobe:call_rcu_tasks_generic": 20, "kprobe:call_filldir": 1745, "kprobe:call_timer_fn": 2333, "kprobe:call_function_single_prep_ipi": 158542, "kprobe:call_rcu": 501596, "kprobe:call_cpuidle": 671857}}}
```

#### real

```console
{"type": "map", "data": {"@mycount": {"kprobe:realloc_array": 2}}}
```

#### ktime

```console
{"type": "map", "data": {"@mycount": {"kprobe:ktime_mono_to_any": 280, "kprobe:ktime_get_real_seconds": 883, "kprobe:ktime_get_seconds": 2629, "kprobe:ktime_get_with_offset": 5145, "kprobe:ktime_add_safe": 5832, "kprobe:ktime_get_ts64": 20938, "kprobe:ktime_get_coarse_real_ts64": 276708, "kprobe:ktime_get_update_offsets_now": 452427, "kprobe:ktime_get": 2757931}}}
```

#### pids

```console
{"type": "map", "data": {"@mycount": {"kprobe:pids_release": 2384, "kprobe:pids_can_fork": 2385}}}
```

FAILED TO COMPILE

#### inc

```console
{"type": "map", "data": {"@mycount": {"kprobe:inc_diskseq": 112, "kprobe:inc_ucount": 280, "kprobe:inc_rlimit_get_ucounts": 902, "kprobe:inc_nlink": 1351, "kprobe:inc_rlimit_ucounts": 2378}}}
```

#### queue

```console
{"type": "map", "data": {"@mycount": {"kprobe:queue_attr_show": 1, "kprobe:queue_logical_block_size_show": 1, "kprobe:queue_rcu_work": 3, "kprobe:queue_io": 15, "kprobe:queued_read_lock_slowpath": 258, "kprobe:queue_delayed_work_on": 1439, "kprobe:queued_write_lock_slowpath": 3036, "kprobe:queue_work_on": 40398}}}
```

#### pfn

```console
{"type": "map", "data": {"@mycount": {"kprobe:pfn_range_is_mapped": 4, "kprobe:pfn_modify_allowed": 337}}}
```

#### wrap

```console
{"type": "map", "data": {"@mycount": {"kprobe:wrap_directory_iterator": 560}}}
```

#### nonseekable

```console
{"type": "map", "data": {"@mycount": {"kprobe:nonseekable_open": 112}}}
```

#### cancel

```console
{"type": "map", "data": {"@mycount": {"kprobe:cancel_work_sync": 224}}}
```

#### bd

```console
{"type": "map", "data": {"@mycount": {"kprobe:bdi_dev_name": 5, "kprobe:bdi_put": 56, "kprobe:bd_abort_claiming": 97, "kprobe:bdev_disk_changed": 112, "kprobe:bdev_set_nr_sectors": 168, "kprobe:bd_prepare_to_claim": 1876, "kprobe:bd_may_claim": 1932}}}
```

#### urandom

```console
{"type": "map", "data": {"@mycount": {"kprobe:urandom_read_iter": 1}}}
```

#### filldir

```console
{"type": "map", "data": {"@mycount": {"kprobe:filldir64": 160337}}}
```

#### vmf

```console
{"type": "map", "data": {"@mycount": {"kprobe:vmf_insert_pfn": 337, "kprobe:vmf_insert_pfn_prot": 337}}}
```

#### filename

```console
{"type": "map", "data": {"@mycount": {"kprobe:filename_create": 1248, "kprobe:filename_lookup": 76849}}}
```

#### timespec64

```console
{"type": "map", "data": {"@mycount": {"kprobe:timespec64_add_safe": 10534}}}
```

#### hugepage

```console
{"type": "map", "data": {"@mycount": {"kprobe:hugepage_madvise": 954, "kprobe:hugepage_vma_check": 65448}}}
```

#### srcu

```console
{"type": "map", "data": {"@mycount": {"kprobe:srcu_delay_timer": 3, "kprobe:srcu_gp_start_if_needed": 120, "kprobe:srcu_funnel_gp_start": 120, "kprobe:srcu_advance_state": 120, "kprobe:srcu_invoke_callbacks": 120, "kprobe:srcu_gp_end": 120, "kprobe:srcu_gp_start": 120, "kprobe:srcu_reschedule": 121, "kprobe:srcu_get_delay.isra.0": 479}}}
```

#### sanitize

```bash
{"type": "map", "data": {"@mycount": {"kprobe:sanitize_ptr_alu": 18}}}
```

#### inat

```bash
{"type": "map", "data": {"@mycount": {"kprobe:inat_get_escape_attribute": 4, "kprobe:inat_get_opcode_attribute": 20}}}
```

#### profile

```console
{"type": "map", "data": {"@mycount": {"kprobe:profile_transition": 449, "kprobe:profile_signal_perm": 1776, "kprobe:profile_tick": 57254}}}
```
#### unhash

```console
{"type": "map", "data": {"@mycount": {"kprobe:unhash_mnt": 4928}}}
```

#### visit

```console
{"type": "map", "data": {"@mycount": {"kprobe:visit_insn": 84}}}
```

#### str2hashbuf

```console
{"type": "map", "data": {"@mycount": {"kprobe:str2hashbuf_signed": 2843}}}
```

#### thread

```console
{"type": "map", "data": {"@mycount": {"kprobe:thread_group_exited": 560, "kprobe:thread_group_cputime": 673, "kprobe:thread_group_cputime_adjusted": 673, "kprobe:thread_stack_free_rcu": 1488}}}
```

#### mark

```console
{"type": "map", "data": {"@mycount": {"kprobe:mark_precise_scalar_ids": 1, "kprobe:mark_ptr_not_null_reg": 14, "kprobe:mark_ptr_or_null_regs": 32, "kprobe:mark_reg_known_zero": 38, "kprobe:mark_reg_unknown": 160, "kprobe:mark_ptr_or_null_reg.constprop.0": 330, "kprobe:mark_reg_not_init": 460, "kprobe:mark_reg_read": 861, "kprobe:mark_buffer_dirty": 4731, "kprobe:mark_page_accessed": 1513026}}}
```

#### sg

```console
{"type": "map", "data": {"@mycount": {"kprobe:sget_fc": 280}}}
```

#### mo

```console
{"type": "map", "data": {"@mycount": {"kprobe:mod_find": 1, "kprobe:move_to_new_folio": 2, "kprobe:module_kallsyms_on_each_symbol": 3, "kprobe:move_expired_inodes": 10, "kprobe:move_vma": 10, "kprobe:module_alloc": 35, "kprobe:mounts_open": 57, "kprobe:module_memfree": 89, "kprobe:mountinfo_open": 112, "kprobe:mounts_poll": 112, "kprobe:mounts_open_common": 169, "kprobe:mounts_release": 169, "kprobe:mount_too_revealing": 224, "kprobe:mount_capable": 280, "kprobe:move_page_tables": 449, "kprobe:move_ptes.constprop.0": 459, "kprobe:move_queued_task": 530, "kprobe:mode_strip_sgid": 1305, "kprobe:move_addr_to_kernel": 4374, "kprobe:mod_timer": 4467, "kprobe:mod_zone_page_state": 5440, "kprobe:move_addr_to_user": 5882, "kprobe:mod_node_page_state": 9335, "kprobe:mod_delayed_work_on": 17029, "kprobe:module_put": 74926, "kprobe:mod_objcg_state": 1471044}}}
```

#### vfs

```console
{"type": "map", "data": {"@mycount": {"kprobe:vfs_mknod": 1, "kprobe:vfs_fallocate": 6, "kprobe:vfs_path_lookup": 56, "kprobe:vfs_getxattr_alloc": 56, "kprobe:vfs_rmdir": 62, "kprobe:vfs_getattr": 112, "kprobe:vfs_get_super": 168, "kprobe:vfs_parse_monolithic_sep": 224, "kprobe:vfs_create_mount": 224, "kprobe:vfs_parse_fs_param_source": 224, "kprobe:vfs_statfs": 224, "kprobe:vfs_get_tree": 280, "kprobe:vfs_parse_fs_string": 336, "kprobe:vfs_rename": 336, "kprobe:vfs_parse_fs_param": 336, "kprobe:vfs_fstat": 392, "kprobe:vfs_utimes": 392, "kprobe:vfs_symlink": 504, "kprobe:vfs_unlink": 514, "kprobe:vfs_mkdir": 678, "kprobe:vfs_readlink": 920, "kprobe:vfs_writev": 1288, "kprobe:vfsgid_in_group_p": 1750, "kprobe:vfs_get_link": 9016, "kprobe:vfs_write": 12897, "kprobe:vfs_getxattr": 19320, "kprobe:vfs_open": 33892, "kprobe:vfs_read": 62777, "kprobe:vfs_statx": 63943, "kprobe:vfs_fstatat": 63948, "kprobe:vfs_getattr_nosec": 81283, "kprobe:vfs_iter_read": 246145}}}
```

#### disassociate

```console
{"type": "map", "data": {"@mycount": {"kprobe:disassociate_ctty": 507}}}
```

#### key

```console
{"type": "map", "data": {"@mycount": {"kprobe:key_fsgid_changed": 112, "kprobe:key_put": 20082}}}
```

#### fscrypt

```console
{"type": "map", "data": {"@mycount": {"kprobe:fscrypt_free_inode": 71, "kprobe:fscrypt_prepare_new_inode": 71, "kprobe:fscrypt_policy_to_inherit": 71, "kprobe:fscrypt_put_encryption_info": 71, "kprobe:fscrypt_set_bio_crypt_ctx": 84, "kprobe:fscrypt_set_bio_crypt_ctx_bh": 89, "kprobe:fscrypt_setup_filename": 142, "kprobe:fscrypt_destroy_keyring": 168, "kprobe:fscrypt_fname_free_buffer": 418, "kprobe:fscrypt_mergeable_bio": 586, "kprobe:fscrypt_mergeable_bio_bh": 586, "kprobe:fscrypt_show_test_dummy_encryption": 785, "kprobe:fscrypt_free_bounce_page": 1274, "kprobe:fscrypt_file_open": 4017, "kprobe:fscrypt_match_name": 4415}}}
```

#### devinet

```console
{"type": "map", "data": {"@mycount": {"kprobe:devinet_ioctl": 684}}}
```

#### unmap

```console
{"type": "map", "data": {"@mycount": {"kprobe:unmap_mapping_range": 22, "kprobe:unmap_region": 37180, "kprobe:unmap_vmas": 38134, "kprobe:unmap_page_range": 143322, "kprobe:unmap_single_vma": 143322}}}
```

#### netlink

```console
{"type": "map", "data": {"@mycount": {"kprobe:netlink_attachskb": 137, "kprobe:netlink_broadcast": 504, "kprobe:netlink_autobind.isra.0": 591, "kprobe:netlink_insert": 703, "kprobe:netlink_getname": 703, "kprobe:netlink_create": 703, "kprobe:netlink_bind": 703, "kprobe:netlink_sock_destruct": 707, "kprobe:netlink_release": 709, "kprobe:netlink_table_ungrab": 709, "kprobe:netlink_dump_done": 1232, "kprobe:netlink_rcv_skb": 1288, "kprobe:netlink_unicast": 1537, "kprobe:netlink_sendmsg": 1537, "kprobe:netlink_trim": 2041, "kprobe:netlink_has_listeners": 2422, "kprobe:netlink_dump": 3472, "kprobe:netlink_recvmsg": 4617, "kprobe:netlink_compare_arg_init": 5635, "kprobe:netlink_skb_destructor": 5849, "kprobe:netlink_skb_set_owner_r": 5849}}}
```

#### loopback

```console
{"type": "map", "data": {"@mycount": {"kprobe:loopback_get_stats64": 560, "kprobe:loopback_xmit": 2592}}}
```

#### readahead

```console
{"type": "map", "data": {"@mycount": {"kprobe:readahead_expand": 12208}}}
```

#### datagram

```console
{"type": "map", "data": {"@mycount": {"kprobe:datagram_poll": 1965}}}
```

#### process

```console
{"type": "map", "data": {"@mycount": {"kprobe:process_srcu": 132, "kprobe:process_echoes": 163, "kprobe:process_output_block": 215, "kprobe:process_timeout": 417, "kprobe:process_backlog": 1864, "kprobe:process_measurement": 43972, "kprobe:process_one_work": 61046}}}
```

#### package

```console
{"type": "map", "data": {"@mycount": {"kprobe:package_cpus_read": 2}}}
```

#### get

```console
{"type": "map", "data": {"@mycount": {"kprobe:get_gate_vma": 1, "kprobe:get_device": 1, "kprobe:get_burstcount": 6, "kprobe:get_task_policy": 49, "kprobe:get_tree_bdev": 56, "kprobe:get_task_exe_file": 56, "kprobe:get_avenrun": 56, "kprobe:get_nodes": 56, "kprobe:get_proc_task_net": 57, "kprobe:get_orlov_stats": 62, "kprobe:get_close_on_exec": 66, "kprobe:get_rsvd": 71, "kprobe:get_nr_inodes": 73, "kprobe:get_nr_dirty_inodes": 73, "kprobe:get_super": 112, "kprobe:getrusage": 116, "kprobe:get_unique_tuple": 132, "kprobe:get_random_u8": 136, "kprobe:get_tree_nodev": 168, "kprobe:get_next_lpos": 168, "kprobe:get_anon_bdev": 168, "kprobe:get_fs_type": 280, "kprobe:get_task_mm": 337, "kprobe:get_sigframe_size": 449, "kprobe:get_vfs_caps_from_disk": 449, "kprobe:get_itimerspec64": 467, "kprobe:get_user_cpu_mask": 473, "kprobe:get_data": 504, "kprobe:get_filesystem": 504, "kprobe:get_random_bytes": 505, "kprobe:get_random_bytes_user": 565, "kprobe:get_mm_exe_file": 592, "kprobe:get_inode_acl": 878, "kprobe:get_old_pud": 900, "kprobe:get_sigframe": 985, "kprobe:get_random_u16": 1020, "kprobe:get_task_cred": 1098, "kprobe:get_max_files": 1165, "kprobe:get_mountpoint": 1960, "kprobe:get_user_pages_remote": 2019, "kprobe:get_arg_page": 2019, "kprobe:getname_kernel": 2030, "kprobe:get_user_pages_fast": 2045, "kprobe:get_cached_acl": 2352, "kprobe:get_seccomp_filter": 2409, "kprobe:get_l4proto": 2600, "kprobe:get_signal": 2797, "kprobe:get_dominating_id": 2856, "kprobe:get_user_ifreq": 3844, "kprobe:get_ucounts": 4066, "kprobe:get_random_u64": 4654, "kprobe:get_zeroed_page": 5104, "kprobe:get_any_partial": 5151, "kprobe:get_random_u32": 7133, "kprobe:get_task_pid": 9321, "kprobe:get_next_ino": 11735, "kprobe:get_pid_task": 12342, "kprobe:get_mmap_base": 22499, "kprobe:get_align_mask": 24546, "kprobe:get_recent_times": 26111, "kprobe:get_dir_index_using_name": 26880, "kprobe:get_unmapped_area": 52147, "kprobe:get_cached_acl_rcu": 58032, "kprobe:getname_flags": 77427, "kprobe:getname": 102939, "kprobe:get_futex_key": 107498, "kprobe:get_unused_fd_flags": 110975, "kprobe:get_timespec64": 419055, "kprobe:get_nohz_timer_target": 465475, "kprobe:get_mem_cgroup_from_mm": 792382, "kprobe:get_next_timer_interrupt": 853835, "kprobe:get_page_from_freelist": 1026584, "kprobe:get_cpu_device": 1132420}}}
```

#### user

```console
{"type": "map", "data": {"@mycount": {"kprobe:user_termios_to_kernel_termios_1": 56, "kprobe:userfaultfd_remove": 238, "kprobe:user_statfs": 1009, "kprobe:user_disable_single_step": 2394, "kprobe:userns_put": 3440, "kprobe:userns_get": 3440, "kprobe:user_path_at_empty": 11654, "kprobe:userfaultfd_set_vm_flags": 57279, "kprobe:userfaultfd_unmap_prep": 58590, "kprobe:userfaultfd_unmap_complete": 65812}}}
```

#### shared

```console
{"type": "map", "data": {"@mycount": {"kprobe:shared_ovl_iterate": 560, "kprobe:shared_cpu_map_show": 768}}}
```

#### timer

```console
{"type": "map", "data": {"@mycount": {"kprobe:timerfd_read": 2, "kprobe:timerfd_tmrproc": 2, "kprobe:timer_delete_sync": 59, "kprobe:timerfd_release": 280, "kprobe:timerfd_poll": 284, "kprobe:timer_delete": 22914, "kprobe:timer_reduce": 35027, "kprobe:timer_clear_idle": 749921}}}
```

#### lru

```console
{"type": "map", "data": {"@mycount": {"kprobe:lru_add_drain_all": 1, "kprobe:lru_add_drain_per_cpu": 20, "kprobe:lru_gen_migrate_mm": 64, "kprobe:lru_gen_del_mm": 954, "kprobe:lru_gen_add_mm": 976, "kprobe:lru_add_drain": 60070, "kprobe:lru_add_drain_cpu": 68838, "kprobe:lru_cache_add_inactive_or_unevictable": 77419, "kprobe:lru_add_fn": 795090}}}
```

#### queued

```console
{"type": "map", "data": {"@mycount": {"kprobe:queued_read_lock_slowpath": 245, "kprobe:queued_write_lock_slowpath": 3123}}}
```

#### namespace

```console
{"type": "map", "data": {"@mycount": {"kprobe:namespace_unlock": 1624}}}
```

#### fat
 
```console
{"type": "map", "data": {"@mycount": {"kprobe:fat_show_options": 112}}}
```

#### yield

```console
{"type": "map", "data": {"@mycount": {"kprobe:yield_task_fair": 2451}}}
```

#### sp

```console
{"type": "map", "data": {"@mycount": {"kprobe:special_mapping_name": 2, "kprobe:spin_lock_irqsave_ssp_contention": 128, "kprobe:spin_lock_irqsave_sdp_contention": 129, "kprobe:space_used": 168, "kprobe:special_mapping_fault": 981, "kprobe:special_mapping_close": 1962, "kprobe:split_vma": 15977}}}
```

#### lookup

```console
{"type": "map", "data": {"@mycount": {"kprobe:lookup_bdev": 56, "kprobe:lookup_address_in_pgd": 64, "kprobe:lookup_mountpoint": 279, "kprobe:lookup_memtype": 337, "kprobe:lookup_constant": 672, "kprobe:lookup_mnt": 1893, "kprobe:lookup_one_qstr_excl": 2832, "kprobe:lookup_bh_lru": 3074, "kprobe:lookup_open.isra.0": 9731, "kprobe:lookup_one_unlocked": 28280, "kprobe:lookup_one_common": 28280, "kprobe:lookup_dcache": 31112, "kprobe:lookup_fast": 549122}}}
```

#### auxv

```console
{"type": "map", "data": {"@mycount": {"kprobe:auxv_open": 56, "kprobe:auxv_read": 56}}}
```

#### unix

```console
{"type": "map", "data": {"@mycount": {"kprobe:unix_stream_data_wait": 112, "kprobe:unix_socketpair": 112, "kprobe:unix_peer_get": 168, "kprobe:unix_dgram_sendmsg": 168, "kprobe:unix_dgram_recvmsg": 320, "kprobe:unix_dgram_poll": 321, "kprobe:unix_getname": 448, "kprobe:unix_mkname_bsd": 460, "kprobe:unix_find_other": 470, "kprobe:unix_stream_connect": 470, "kprobe:unix_create": 694, "kprobe:unix_close": 694, "kprobe:unix_release": 694, "kprobe:unix_sock_destructor": 1164, "kprobe:unix_release_sock": 1164, "kprobe:unix_create1": 1164, "kprobe:unix_copy_addr": 3293, "kprobe:unix_stream_sendmsg": 5936, "kprobe:unix_scm_to_skb": 5936, "kprobe:unix_destruct_scm": 6104, "kprobe:unix_write_space": 6574, "kprobe:unix_stream_read_actor": 7045, "kprobe:unix_poll": 9760, "kprobe:unix_stream_recvmsg": 10246, "kprobe:unix_stream_read_generic": 10246}}}
```

#### use

```console
{"type": "map", "data": {"@mycount": {"kprobe:user_termios_to_kernel_termios_1": 56, "kprobe:userfaultfd_remove": 257, "kprobe:user_statfs": 1009, "kprobe:user_disable_single_step": 2384, "kprobe:userns_put": 3886, "kprobe:userns_get": 3886, "kprobe:user_path_at_empty": 11673, "kprobe:userfaultfd_set_vm_flags": 55254, "kprobe:userfaultfd_unmap_prep": 58572, "kprobe:userfaultfd_unmap_complete": 65864}}}
```

#### mod

```console
{"type": "map", "data": {"@mycount": {"kprobe:module_kallsyms_on_each_symbol": 2, "kprobe:module_memfree": 16, "kprobe:module_alloc": 33, "kprobe:mode_strip_sgid": 1306, "kprobe:mod_zone_page_state": 2143, "kprobe:mod_timer": 4466, "kprobe:mod_node_page_state": 8404, "kprobe:mod_delayed_work_on": 16764, "kprobe:module_put": 74615, "kprobe:mod_objcg_state": 1478547}}}
```

#### freezer

```console
{"type": "map", "data": {"@mycount": {"kprobe:freezer_fork": 2375}}}
```

#### collect

```console
{"type": "map", "data": {"@mycount": {"kprobe:collect_mm_slot": 2, "kprobe:collect_percpu_times": 60, "kprobe:collect_sigign_sigcatch.constprop.0": 112, "kprobe:collect_signal": 1029}}}
```

#### blkdev

```console
{"type": "map", "data": {"@mycount": {"kprobe:blkdev_read_folio": 3, "kprobe:blkdev_issue_discard": 25, "kprobe:blkdev_get_by_path": 56, "kprobe:blkdev_flush_mapping": 168, "kprobe:blkdev_common_ioctl": 2044, "kprobe:blkdev_get_by_dev": 2268, "kprobe:blkdev_release": 2268, "kprobe:blkdev_open": 2268, "kprobe:blkdev_put_whole": 2324, "kprobe:blkdev_get_no_open": 2324, "kprobe:blkdev_ioctl": 2324, "kprobe:blkdev_put": 2324, "kprobe:blkdev_get_whole": 2324, "kprobe:blkdev_llseek": 2520, "kprobe:blkdev_read_iter": 2632, "kprobe:blkdev_readahead": 2637, "kprobe:blkdev_get_block": 2649}}}
```

#### generic

```console
{"type": "map", "data": {"@mycount": {"kprobe:generic_set_encrypted_ci_d_ops": 73, "kprobe:generic_parse_monolithic": 112, "kprobe:generic_write_end": 135, "kprobe:generic_shutdown_super": 224, "kprobe:generic_fadvise": 280, "kprobe:generic_file_llseek": 282, "kprobe:generic_file_write_iter": 336, "kprobe:generic_write_checks": 460, "kprobe:generic_perform_write": 460, "kprobe:generic_write_check_limits": 460, "kprobe:generic_update_time": 845, "kprobe:generic_file_llseek_size": 3208, "kprobe:generic_exec_single": 3834, "kprobe:generic_file_open": 7941, "kprobe:generic_file_readonly_mmap": 24752, "kprobe:generic_fill_statx_attr": 28448, "kprobe:generic_delete_inode": 29616, "kprobe:generic_fillattr": 52932, "kprobe:generic_smp_call_function_single_interrupt": 114733, "kprobe:generic_file_read_iter": 227325, "kprobe:generic_permission": 880290}}}
```

#### mntput

```console
{"type": "map", "data": {"@mycount": {"kprobe:mntput_no_expire": 254139, "kprobe:mntput": 324938}}}
```

#### tt

```console
{"type": "map", "data": {"@mycount": {"kprobe:tty_get_pgrp": 1, "kprobe:tty_buffer_free": 7, "kprobe:tty_ldisc_receive_buf": 36, "kprobe:tty_port_default_receive_buf": 36, "kprobe:tty_write": 47, "kprobe:tty_insert_flip_string_and_push_buffer": 47, "kprobe:tty_insert_flip_string_fixed_flag": 47, "kprobe:tty_alloc_file": 56, "kprobe:tty_vhangup": 56, "kprobe:tty_buffer_set_lock_subclass": 56, "kprobe:tty_open": 56, "kprobe:tty_signal_session_leader": 56, "kprobe:tty_ldisc_release": 56, "kprobe:tty_init_dev": 56, "kprobe:tty_reopen": 56, "kprobe:tty_release_struct": 56, "kprobe:tty_ldisc_hangup": 56, "kprobe:tty_check_change": 56, "kprobe:tty_lock_interruptible": 56, "kprobe:tty_ldisc_setup": 56, "kprobe:tty_set_termios": 56, "kprobe:tty_buffer_flush": 56, "kprobe:tty_save_termios": 56, "kprobe:tty_add_file": 56, "kprobe:tty_set_lock_subclass": 56, "kprobe:tty_driver_flush_buffer": 56, "kprobe:tty_lookup_driver": 56, "kprobe:tty_audit_add_data": 72, "kprobe:tty_read": 82, "kprobe:tty_ldisc_ref": 92, "kprobe:tty_ldisc_open": 112, "kprobe:tty_ldisc_unlock": 112, "kprobe:tty_lock_slave": 112, "kprobe:tty_ldisc_put": 112, "kprobe:tty_port_init": 112, "kprobe:tty_release_checks": 112, "kprobe:tty_unthrottle": 112, "kprobe:tty_buffer_set_limit": 112, "kprobe:tty_ldisc_deinit": 112, "kprobe:tty_ldisc_close": 112, "kprobe:tty_unlock_slave": 112, "kprobe:tty_buffer_init": 112, "kprobe:tty_release": 112, "kprobe:tty_port_destructor": 112, "kprobe:tty_ldisc_init": 112, "kprobe:tty_ldisc_lock": 112, "kprobe:tty_termios_baud_rate": 112, "kprobe:tty_termios_input_baud_rate": 112, "kprobe:tty_buffer_free_all": 112, "kprobe:tty_port_put": 112, "kprobe:tty_update_time": 133, "kprobe:tty_buffer_cancel_work": 224, "kprobe:tty_lock": 280, "kprobe:tty_unlock": 280, "kprobe:tty_mode_ioctl": 340, "kprobe:tty_jobctrl_ioctl": 509, "kprobe:tty_audit_fork": 533, "kprobe:tty_audit_exit": 534, "kprobe:tty_ioctl": 565, "kprobe:tty_port_default_wakeup": 953, "kprobe:tty_port_tty_wakeup": 953, "kprobe:tty_port_tty_get": 953, "kprobe:tty_wakeup": 979, "kprobe:tty_kref_put": 1823, "kprobe:tty_chars_in_buffer": 17388, "kprobe:tty_poll": 17388, "kprobe:tty_buffer_flush_work": 17418, "kprobe:tty_buffer_space_avail": 17435, "kprobe:tty_hung_up_p": 17495, "kprobe:tty_write_room": 17771, "kprobe:tty_ldisc_ref_wait": 17973, "kprobe:tty_ldisc_deref": 18065, "kprobe:ttwu_do_activate": 677860, "kprobe:ttwu_queue_wakelist": 677865}}}
```

#### cpufreq

```console
{"type": "map", "data": {"@mycount": {"kprobe:cpufreq_quick_get": 11250, "kprobe:cpufreq_cpu_get": 11250}}}
```

#### ilookup5

```console
{"type": "map", "data": {"@mycount": {"kprobe:ilookup5": 22512}}}
```

Stopped manually recording here - will save results to file (and write down some of interest)

#### proc

This one was large!

```console
{"type": "map", "data": {"@mycount": {"kprobe:proc_cgroup_show": 1, "kprobe:proc_map_release": 1, "kprobe:proc_cpuset_show": 1, "kprobe:proc_lookup": 2, "kprobe:proc_sys_poll": 54, "kprobe:proc_dointvec": 54, "kprobe:proc_reg_poll": 55, "kprobe:proc_exe_link": 56, "kprobe:proc_dointvec_minmax": 56, "kprobe:proc_root_getattr": 56, "kprobe:proc_tgid_net_lookup": 57, "kprobe:proc_task_instantiate": 57, "kprobe:proc_get_inode": 57, "kprobe:proc_mem_open": 57, "kprobe:proc_lookup_de": 59, "kprobe:proc_lookupfd": 86, "kprobe:proc_sys_delete": 109, "kprobe:proc_sys_read": 110, "kprobe:proc_put_long": 110, "kprobe:proc_sys_open": 110, "kprobe:proc_sys_call_handler": 110, "kprobe:proc_task_name": 112, "kprobe:proc_pid_status": 112, "kprobe:proc_ns_file": 112, "kprobe:proc_free_inum": 112, "kprobe:proc_ns_instantiate": 112, "kprobe:proc_alloc_inum": 112, "kprobe:proc_id_connector": 112, "kprobe:proc_pid_readlink": 112, "kprobe:proc_ns_dir_lookup": 112, "kprobe:proc_single_open": 113, "kprobe:proc_single_show": 113, "kprobe:proc_reg_llseek": 114, "kprobe:proc_get_link": 114, "kprobe:proc_put_link": 114, "kprobe:process_srcu": 148, "kprobe:process_echoes": 164, "kprobe:proc_sys_compare": 168, "kprobe:proc_fd_getattr": 168, "kprobe:proc_readfd_count": 168, "kprobe:proc_reg_read": 175, "kprobe:process_output_block": 215, "kprobe:proc_pid_instantiate": 256, "kprobe:proc_pid_lookup": 257, "kprobe:proc_root_lookup": 257, "kprobe:proc_sys_revalidate": 280, "kprobe:proc_comm_connector": 280, "kprobe:proc_show_options": 281, "kprobe:proc_pid_make_base_inode.constprop.0": 313, "kprobe:proc_reg_unlocked_ioctl": 336, "kprobe:proc_task_getattr": 339, "kprobe:proc_match": 349, "kprobe:proc_id_map_release": 390, "kprobe:proc_uid_map_open": 390, "kprobe:proc_id_map_open": 390, "kprobe:proc_sys_permission": 392, "kprobe:proc_pid_get_link": 393, "kprobe:proc_readfd_common": 448, "kprobe:proc_readfd": 448, "kprobe:proc_fd_link": 448, "kprobe:proc_exec_connector": 449, "kprobe:proc_task_readdir": 452, "kprobe:proc_misc_d_delete": 543, "kprobe:proc_reg_release": 564, "kprobe:proc_reg_open": 564, "kprobe:process_timeout": 604, "kprobe:proc_fd_permission": 618, "kprobe:proc_tgid_base_lookup": 795, "kprobe:proc_pident_instantiate": 795, "kprobe:proc_pident_lookup": 795, "kprobe:proc_misc_d_revalidate": 1465, "kprobe:process_backlog": 1868, "kprobe:proc_fork_connector": 2403, "kprobe:proc_invalidate_siblings_dcache": 2476, "kprobe:proc_flush_pid": 2476, "kprobe:proc_exit_connector": 2476, "kprobe:proc_self_get_link": 4552, "kprobe:proc_pid_permission": 5004, "kprobe:proc_fd_instantiate": 5672, "kprobe:proc_ns_get_link": 6216, "kprobe:proc_fill_cache": 6707, "kprobe:proc_pid_make_inode": 6892, "kprobe:proc_alloc_inode": 6949, "kprobe:proc_pid_evict_inode": 7302, "kprobe:proc_free_inode": 7359, "kprobe:proc_evict_inode": 7379, "kprobe:proc_reg_read_iter": 17311, "kprobe:process_measurement": 44295, "kprobe:process_one_work": 61273}}}
```
Stopped writing them down here (see text files with final listings).

## Grouping Kprobes

Now we want to put them into groups that can get close to 1000, so each run we maximally run as many programs as we can. I did this work manually to group the prefixes into sets that would not exceed 1K.

```
pattern="^(aa|abort|account|acct|activate|active|add).*$"
sudo -E python3 time-calls.py --pattern "$pattern" /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 200
```

I made [kprobe-groups.txt](kprobes/kprobe-groups.txt) from this, and then we can test across a "strong scaled" single node experiment (meaning we give it fewer to more processes). Let's first time that (without ebpf)

```bash
# 7 seconds
time sudo -E /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000

# 11 seconds
time sudo -E /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):28 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000

# 21 seconds
time sudo -E /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):14 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000
```

This is just a test run - understandably this will take too long.

```bash
results=./results/bare-metal
mkdir -p ${results}
counter=0
for pattern in $(cat kprobe-groups.txt)
  do
    for proc in 56 28 14
      do
       time sudo -E python3 time-before-calls.py --pattern "$pattern" /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ./results/bare-metal/${counter}-${proc}.out
    done
    counter=$((counter+1))
done

results=./results/singularity
mkdir -p ${results}
counter=0
for pattern in $(cat kprobe-groups.txt)
  do
    for proc in 56 28 14
      do
       time sudo -E python3 time-before-calls.py --pattern "$pattern" /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc singularity exec ../metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee $results/${counter}-${proc}.out
    done
    counter=$((counter+1))
done
```

And note I only did this once to see that there wasn't difference in running LAMMPS.

```console
results=./results/no-ebpf-singularity
mkdir -p ${results}
counter=0
for pattern in $(cat kprobe-groups.txt)
  do
    for proc in 56 28 14
      do
       time sudo -E /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc singularity exec ../metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee $results/${counter}-${proc}.out
    done
    counter=$((counter+1))
done

results=./results/no-ebpf
mkdir -p ${results}
counter=0
for pattern in $(cat kprobe-groups.txt)
  do
    for proc in 56 28 14
      do
       time sudo -E /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee $results/${counter}-${proc}.out
    done
    counter=$((counter+1))
done
```

## Cannot assign requested address

I'm seeing this message:

```console
cannot attach kprobe, Cannot assign requested address
```

And it might be because we are using [symbols instead of addresses](https://github.com/cilium/pwru/issues/284#issuecomment-1788875518). We arguably want to remove these. Next I am going to use the same krun.sh to test each of my functions.
I want to remove those that don't attach (suggesting that the symbol is wrong).

```bash
# note this is img/ebpf-functions.txt
for term in $(cat functions.txt)
  do
   echo $term
   ARG=$term . krun.sh &> krun-out.txt
   cat krun-out.txt | grep map && echo $term >> ./has-probes.txt
   cat krun-out.txt | grep "cannot attach"  
done
```

I think this is just because some functions are wrong, and when we run against the set we get data for we won't see this.

## First Prototype Run

We now have [img/ebpf-functions.json](img/ebpf-functions.json) and this is everything running when LAMMPS is running. Since we are going to create distributions and look for significant differences, I think we can be OK with background stuff (it should not be significantly different between cases). I want to first do a test run with the new script.

Let's write a wrapper to test exec and see if the pid is maintained.

```bash
#!/bin/bash

echo $$
sleep 10
exec /bin/bash -c "echo $$"
```

That seems to work? Let's try with our run. With the smaller group, each of these runs takes about 30 seconds, as we are just profiling the pid.

```bash
results=./results/test-1/bare-metal
sresults=./results/test-1/singularity
mkdir -p ${results} ${sresults}
counter=0
for iter in $(seq 1 32); do
  for index in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14
    do
      # Just do one size to start, it is fastest too
      for proc in 56
        do
       if [[ ! -f "${results}/${index}-${counter}-${proc}.out" ]]; then
       time sudo -E python3 time-wrapped.py --index $index /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee $results/${index}-${counter}-${proc}.out
       fi
       if [[ ! -f "${sresults}/${index}-${counter}-${proc}.out" ]]; then
         time sudo -E -E python3 time-wrapped.py --index $index /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc singularity exec ../metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${sresults}/${index}-${counter}-${proc}.out
      fi
      done
      counter=$((counter+1))
  done
done
```

Now let's do the smaller sizes, which take a tiny bit longer (which is OK).

```bash
results=./results/test-1/bare-metal
sresults=./results/test-1/singularity
mkdir -p ${results} ${sresults}
for iter in $(seq 1 32); do
  for index in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14
    do
      # Just do one size to start, it is fastest too
      for proc in 28 14
        do
       if [[ ! -f "${results}/${index}-${iter}-${proc}.out" ]]; then
       time sudo -E python3 time-wrapped.py --index $index /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee $results/${index}-${iter}-${proc}.out
       fi
       if [[ ! -f "${sresults}/${index}-${iter}-${proc}.out" ]]; then
         time sudo -E -E python3 time-wrapped.py --index $index /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):$proc singularity exec ../metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 10000 |& tee ${sresults}/${index}-${iter}-${proc}.out
      fi
      done
  done
done
```

## Categories of KProbes

I had first started looking them up, but knew this would take too long.

- kprobe:FSE : HP File System Extender 
- kprobe:FUA_show [Forced Unit Access](https://infohub.delltechnologies.com/en-us/l/performance-best-practices-3/sql-server-2019-forced-unit-access/#:~:text=FUA%20is%20a%20bit%20that,impact%20storage%20I%2FO%20performance.)
 - kprobe:HIST_* (histogram))
 - kprobe:HUF_* [Huffman Codec](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/lib/zstd/common/huf.h#L143) 
 - [kprobe:IO_APIC_get_PCI_irq_vector](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/arch/x86/kernel/apic/io_apic.c#L1146)
 - [kprobe:I_BDEV](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/block/bdev.c#L51) block device?
 - kprobe:KSTK_ESP: [user program counter / stack pointer](https://github.com/davet321/rpi-linux/commit/32effd19f64908551f8eff87e7975435edd16624) macro.
 - kprobe:LZ4_decompress_* [LZ4 decompression](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/include/linux/lz4.h#L253-L270)
 - kprobe:PageHuge I think [called](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/include/linux/page-flags.h#L885) if application looking for HugePage usage?
 - kprobe:PageMovable [Determine if a page moveable?](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/mm/compaction.c#L135)
 - kprobe:SEQ_printf: print to [/proc/timer_list and the console](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/kernel/time/timer_list.c#L26)
 - kprobe:SetPageHWPoisonTakenOff [related to this](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/mm/memory-failure.c#L1367-L1370) and recovery from [memory failure](https://www.kernel.org/doc/html/v5.0/vm/hwpoison.html)
 - kprobe:TSS_authhmac [calculate auth info fields](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/security/keys/trusted-keys/trusted_tpm1.c#L115) to send to [TPM](https://wiki.archlinux.org/title/Trusted_Platform_Module#:~:text=Trusted%20Platform%20Module%20(TPM)%20is,integrating%20cryptographic%20keys%20into%20devices.), "Trusted Platform Module"
 - kprobe:ZSTD_* is a compresion algorithm
 - kprobe:aafs_ maybe [automatic application features](https://doc.windev.com/en-US/?1000022109&verdisp=250)?
 - kprobe:aat2870_ [LED channels](https://media.digikey.com/pdf/Data%20Sheets/Skyworks%20PDFs/AAT2870.pdf)?
 - kprobe:abort Likely [abort](https://man7.org/linux/man-pages/man3/abort.3.html)
 - kprobe:ac6_* Maybe get the [next ip v6 address](https://github.com/spotify/linux/blob/6eb782fc88d11b9f40f3d1d714531f22c57b39f9/net/ipv6/anycast.c#L451)?
 - kprobe:aca_put also [related to that](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/net/ipv6/anycast.c#L253)
 - kprobe:accel_core_* [Might be related to device management (GPU)](https://github.com/torvalds/linux/blob/50736169ecc8387247fe6a00932852ce7b057083/drivers/accel/drm_accel.c#L288)
 - kprobe:accept_all part of a hook in [netfilter.c](https://github.com/torvalds/linux/blob/35bb670d65fc0f80c62383ab4f2544cec85ac57a/net/netfilter/core.c#L91)
 - kprobe:accept_memory seems to be part of firmware drivers for EFI [here](https://github.com/torvalds/linux/blob/35bb670d65fc0f80c62383ab4f2544cec85ac57a/drivers/firmware/efi/libstub/unaccepted_memory.c#L180) - I think this is where boot stuff is [stored](https://en.wikipedia.org/wiki/EFI_system_partition)
 - kprobe:access_process_vm
 - kprobe:access_remote_vm
 

## AMG

```bash
time singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-c2d
time singularity pull docker://ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu
```

Since this container requires sourcing spack, we need to write a bash script to run on the host.

```bash
#!/bin/bash
# run_amg.sh
. /etc/profile.d/z10_spack_environment.sh
amg -P 2 4 7 -n 64 128 128
```

And now the runs! These are just tests.

```console
# Bare metal: 33.866 seconds
time /opt/view/bin/mpirun --host $(hostname):56 /opt/view/bin/amg -P 2 4 7 -n 64 128 128 &
procid=$?
sudo python /home/vanessa/time-calls.py -p $procid do_sys*
```
```console
FUNC                                    COUNT     TIME (nsecs)
do_sys_openat2                            659           765935
do_sys_poll                             28906      44605582051
```

```console
# Singularity "my computer" : 37.091 seconds (from outside the container) - it seems like the delay is in the startup
time mpirun --host $(hostname):56 singularity exec metric-amg2023_spack-slim-cpu.sif /bin/bash ./run_amg.sh

# Singularity "c2d": 36.89 seconds
time mpirun --host $(hostname):56 singularity exec metric-amg2023_spack-c2d.sif /bin/bash ./run_amg.sh &
procid=$?
sudo python /home/vanessa/time-calls.py -p $procid do_sys*
```

```console
# Singularity "c2d" inside container: 34.506
singularity shell metric-amg2023_spack-c2d.sif
time /opt/view/bin/mpirun --host $(hostname):56 /bin/bash ./run_amg.sh

# Singularity "my computer" inside container: 34.574
singularity shell metric-amg2023_spack-slim-cpu.sif
time /opt/view/bin/mpirun --host $(hostname):56 /bin/bash ./run_amg.sh

# docker "my computer": 33.93 seconds
docker run -it ghcr.io/converged-computing/metric-amg2023:spack-slim-cpu
time /opt/view/bin/mpirun --allow-run-as-root --host $(hostname):56 /opt/view/bin/amg -P 2 4 7 -n 64 128 128

# docker "c2d": 34.410 seconds
docker run -it ghcr.io/converged-computing/metric-amg2023:spack-c2d
time /opt/view/bin/mpirun --allow-run-as-root --host $(hostname):56 /opt/view/bin/amg -P 2 4 7 -n 64 128 128
```

## LAMMPS

I'll quickly test lammps since we don't need mpirun (for a run in docker)

```bash
time singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu
time singularity pull docker://ghcr.io/converged-computing/metric-lammps-cpu:c2d

# pull the data
oras pull ghcr.io/converged-computing/metric-lammps-cpu:libfabric-data
```

And time! We are going to consider total wrapped time AND wall time. Each has two runs.

```console
cd ./common

# Bare metal with mpirun: 
# wrapped: 30.46, 30.527 seconds
# wall time: 28, 28 seconds
time /usr/local/bin/mpirun --host $(hostname):56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# Testing with ebpf
sudo -E python3 time-calls.py /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

sudo -E python3 time-calls.py /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# and with singularity
sudo -E python3 ../../time-calls.py /usr/local/bin/mpirun --allow-run-as-root --host $(hostname):56 singularity exec --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# "My computer" singularity: 
# wrapped: 32.55, 32.989 seconds
# wall times: 29, 28 seconds (tie breaker 28 seconds)
time /usr/local/bin/mpirun --host $(hostname):56 singularity exec --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-lammps-cpu_latest.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# "My computer" singularity, in shell: 
# wrapped: 31.631, 30.785 seconds
# wall times: 29, 29  seconds
singularity shell --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-lammps-cpu_latest.sif
time mpirun --host $(hostname):56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# "c2d" singularity, in shell: 
# wrapped: 31.632, 31.165  seconds
# wall times: 29, 29 seconds
singularity shell --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-lammps-cpu_c2d.sif
time mpirun --host $(hostname):56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# "c2d" singularity
# wrapped: 33.124, 32.627 seconds
# wall times: 28, 29 seconds
time /usr/local/bin/mpirun --host $(hostname):56 singularity exec --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-lammps-cpu_c2d.sif lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# docker "my computer": 
# wrapped: 30.806, 30.892 seconds
# wall time: 29, 29 seconds, 
docker run -it ghcr.io/converged-computing/metric-lammps-cpu
time mpirun --allow-run-as-root --host $(hostname):56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000

# docker "c2d":
# wrapped: 31.337, 31.150
# wall time: 29, 29 seconds
docker run -it ghcr.io/converged-computing/metric-lammps-cpu:c2d
time mpirun --allow-run-as-root --host $(hostname):56 lmp -in in.snap.test -var snapdir 2J8_W.SNAP -v x 228 -v y 228 -v z 228 -var nsteps 20000
```

My conclusions - the wall times are (mostly) the same! Since the granularity is by the second it's hard to tell if 28 vs. 29 is significantly different. But if not, the application doesn't "see" anything different, at least in this tiny set of runs.
But there is some overhead to starting things up I think. It would be fun to profile just that.

I would also like a consistent way to always get a time for a run, or other metrics.


## Kripke

```bash
time singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu
time singularity pull docker://ghcr.io/converged-computing/metric-kripke-cpu:c2d
```

And time! We are going to consider total wrapped time AND wall time. Each has two runs.

```console
# Bare metal with mpirun: 
time /usr/local/bin/mpirun --host $(hostname):56 kripke --layout GDZ --dset 8 --zones 56,56,56 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 2,4,7
```
```console
TIMER_NAMES:Generate,LPlusTimes,LTimes,Population,Scattering,Solve,Source,SweepSolver,SweepSubdomain
TIMER_DATA:0.040797,3.802591,7.491424,0.060380,87.039040,108.981689,0.005787,8.194255,0.261393

Figures of Merit
================

  Throughput:         8.250505e+06 [unknowns/(second/iteration)]
  Grind time :        1.212047e-07 [(seconds/iteration)/unknowns]
  Sweep efficiency :  3.18995 [100.0 * SweepSubdomain time / SweepSolver time]
  Number of unknowns: 89915392

END

real	1m51.126s
user	101m33.193s
sys	0m39.193s
```

And "My computer" singularity: 

```console
time /usr/local/bin/mpirun --host $(hostname):56 singularity exec --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-kripke-cpu_latest.sif kripke --layout GDZ --dset 8 --zones 56,56,56 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 2,4,7
```
```console
Figures of Merit
================

  Throughput:         8.254216e+06 [unknowns/(second/iteration)]
  Grind time :        1.211502e-07 [(seconds/iteration)/unknowns]
  Sweep efficiency :  3.71224 [100.0 * SweepSubdomain time / SweepSolver time]
  Number of unknowns: 89915392

END

real	1m53.323s
user	101m34.642s
sys	0m45.859s
```

And  "c2d" singularity

```console
time /usr/local/bin/mpirun --host $(hostname):56 singularity exec --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-kripke-cpu_c2d.sif kripke --layout GDZ --dset 8 --zones 56,56,56 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 2,4,7
```
```console
TIMER_NAMES:Generate,LPlusTimes,LTimes,Population,Scattering,Solve,Source,SweepSolver,SweepSubdomain
TIMER_DATA:0.169121,2.694554,8.321639,0.058425,92.294044,108.623195,0.005598,2.720175,0.254447

Figures of Merit
================

  Throughput:         8.277734e+06 [unknowns/(second/iteration)]
  Grind time :        1.208060e-07 [(seconds/iteration)/unknowns]
  Sweep efficiency :  9.35405 [100.0 * SweepSubdomain time / SweepSolver time]
  Number of unknowns: 89915392

END

real	1m53.195s
user	101m23.758s
sys	0m45.484s
```

"c2d" in the container

```console
singularity shell --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-kripke-cpu_c2d.sif
time /usr/local/bin/mpirun --host $(hostname):56  kripke --layout GDZ --dset 8 --zones 56,56,56 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 2,4,7
```
```console
TIMER_NAMES:Generate,LPlusTimes,LTimes,Population,Scattering,Solve,Source,SweepSolver,SweepSubdomain
TIMER_DATA:0.536636,3.626879,7.508796,0.061674,87.406531,107.333871,0.005738,6.178350,0.256155

Figures of Merit
================

  Throughput:         8.377168e+06 [unknowns/(second/iteration)]
  Grind time :        1.193721e-07 [(seconds/iteration)/unknowns]
  Sweep efficiency :  4.14600 [100.0 * SweepSubdomain time / SweepSolver time]
  Number of unknowns: 89915392

END

real	1m50.232s
user	100m25.407s
sys	0m42.877s
```

And "my computer" from in the container:

```console
singularity shell --pwd /home/vanessa/containers/common /home/vanessa/containers/metric-kripke-cpu_latest.sif
time /usr/local/bin/mpirun --host $(hostname):56  kripke --layout GDZ --dset 8 --zones 56,56,56 --gset 16 --groups 64 --niter 10 --legendre 9 --quad 8 --procs 2,4,7
```
```console
TIMER_NAMES:Generate,LPlusTimes,LTimes,Population,Scattering,Solve,Source,SweepSolver,SweepSubdomain
TIMER_DATA:0.164594,2.725723,3.567298,0.060416,63.193214,107.615859,0.005174,36.541976,0.265569

Figures of Merit
================

  Throughput:         8.355218e+06 [unknowns/(second/iteration)]
  Grind time :        1.196857e-07 [(seconds/iteration)/unknowns]
  Sweep efficiency :  0.72675 [100.0 * SweepSubdomain time / SweepSolver time]
  Number of unknowns: 89915392

END

real	1m50.088s
user	100m21.574s
sys	0m41.107s
```

**To be prototyped**

I'm going to write a better script for automation than the above.

## Laghos

## Linpack / HPL

## MiniFE

## Mixbench

## Gemm

## Nekrs

## OSU

## Pennant

## Quicksilver

## Stream

That was very satisfying - I think we can learn a lot without spending too much.

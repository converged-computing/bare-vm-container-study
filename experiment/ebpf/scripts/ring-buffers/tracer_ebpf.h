#ifndef TRACER_EBPF_PRELOAD_H
#define TRACER_EBPF_PRELOAD_H
__attribute__((visibility("default"))) extern int tracer_get_pid();

__attribute__((visibility("default"))) extern int tracer_remove_pid();

extern void __attribute__((constructor)) tracer_ebpf_init(void);

extern void __attribute__((destructor)) tracer_ebpf_fini(void);

#endif // TRACER_EBPF_PRELOAD_H

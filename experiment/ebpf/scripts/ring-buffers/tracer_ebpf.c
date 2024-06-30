#include "tracer_ebpf.h"
__attribute__((visibility("default"))) int tracer_get_pid() {
  return getpid();
}
__attribute__((visibility("default"))) int tracer_remove_pid() {
  return getpid();
}

void tracer_ebpf_init(void) {
  printf("Constructor Loaded\n");
  tracer_get_pid();
}

void tracer_ebpf_fini(void) {
  printf("Desctructor Loaded\n");
  tracer_remove_pid();
}

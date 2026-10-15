/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 Mason. Permission is granted to use, copy, modify,
 * distribute, sublicense and/or sell this software, provided this notice is
 * retained. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
 */
#include <mach/mach.h>
#include <mach/i386/thread_status.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>
#include <dlfcn.h>
static _Atomic int stopping;
__attribute__((noinline)) static void *hot_worker(void *arg){
 (void)arg;volatile uint64_t x=1;
 while(!atomic_load(&stopping))x=x*6364136223846793005ULL+1;
 return NULL;
}
int main(void){
 pthread_t t;if(pthread_create(&t,NULL,hot_worker,NULL))return 1;
 usleep(10000);
 thread_t port=pthread_mach_thread_np(t);
 for(int i=0;i<5;i++){
  x86_thread_state64_t state={0};mach_msg_type_number_t count=x86_THREAD_STATE64_COUNT;
  kern_return_t suspend=thread_suspend(port),rc=KERN_FAILURE,resume=KERN_FAILURE;
  if(suspend==KERN_SUCCESS){rc=thread_get_state(port,x86_THREAD_STATE64,(thread_state_t)&state,&count);resume=thread_resume(port);}
  Dl_info d={0};if(rc==KERN_SUCCESS)dladdr((void *)(uintptr_t)state.__rip,&d);
  printf("suspend=%d get=%d resume=%d pc=0x%llx name=%s\n",suspend,rc,resume,(unsigned long long)state.__rip,d.dli_sname?d.dli_sname:"UNKNOWN");
  if(suspend==KERN_SUCCESS&&resume!=KERN_SUCCESS)return 3;
  usleep(10000);
 }
 atomic_store(&stopping,1);if(pthread_join(t,NULL))return 2;return 0;
}

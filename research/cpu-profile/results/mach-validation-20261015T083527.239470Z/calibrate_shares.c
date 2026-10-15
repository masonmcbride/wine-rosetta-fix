/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 Mason. Permission is granted to use, copy, modify,
 * distribute, sublicense and/or sell this software, provided this notice is
 * retained. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
 */
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <errno.h>
#include <mach/mach.h>
static double deadline;
struct result { int cool; double cpu; double clock_cpu; uint64_t checksum; uint64_t tid; int error; };
static double seconds(clockid_t clock) { struct timespec t; if(clock_gettime(clock,&t))return -1; return t.tv_sec+t.tv_nsec/1e9; }
static double thread_seconds(void) {
 thread_basic_info_data_t info;mach_msg_type_number_t count=THREAD_BASIC_INFO_COUNT;
 thread_t thread=mach_thread_self();kern_return_t rc=thread_info(thread,THREAD_BASIC_INFO,(thread_info_t)&info,&count);
 mach_port_deallocate(mach_task_self(),thread);if(rc!=KERN_SUCCESS)return -1;
 return info.user_time.seconds+info.system_time.seconds+(info.user_time.microseconds+info.system_time.microseconds)/1e6;
}
__attribute__((noinline)) static uint64_t hot_leaf(uint64_t x) {
 for(unsigned i=0;i<20000;i++) { x=x*6364136223846793005ULL+1442695040888963407ULL; __asm__ volatile("" : "+r"(x)); } return x;
}
__attribute__((noinline)) static uint64_t cool_leaf(uint64_t x) {
 for(unsigned i=0;i<20000;i++) { x=x*2862933555777941757ULL+3037000493ULL; __asm__ volatile("" : "+r"(x)); } return x;
}
static void *worker(void *arg) {
 struct result *r=arg;double start=thread_seconds(),clock_start=seconds(CLOCK_THREAD_CPUTIME_ID);uint64_t x=1;
 if(pthread_threadid_np(NULL,&r->tid)){r->error=1;return NULL;}
 if(start<0){r->error=1;return NULL;}
 while(seconds(CLOCK_MONOTONIC)<deadline){
  if(!r->cool)x=hot_leaf(x);
  else {
   double until=seconds(CLOCK_MONOTONIC)+0.001;
   do{x=cool_leaf(x);}while(seconds(CLOCK_MONOTONIC)<until);
   struct timespec wait={0,3000000};while(nanosleep(&wait,&wait)&&errno==EINTR){}
  }
 }
 double end=thread_seconds();r->cpu=end-start;r->clock_cpu=seconds(CLOCK_THREAD_CPUTIME_ID)-clock_start;r->checksum=x;r->error=end<0;
 return NULL;
}
int main(void){
 pthread_t a,b;struct result hot={0},cool={.cool=1};double now=seconds(CLOCK_MONOTONIC);
 if(now<0)return 1;deadline=now+3;
 if(pthread_create(&a,NULL,worker,&hot))return 2;
 if(pthread_create(&b,NULL,worker,&cool))return 3;
 if(pthread_join(a,NULL)||pthread_join(b,NULL)||hot.error||cool.error)return 4;
 printf("PASS hot_cpu=%.9f cool_cpu=%.9f clock_hot=%.9f clock_cool=%.9f hot_checksum=%llu cool_checksum=%llu hot_tid=%llu cool_tid=%llu\n",hot.cpu,cool.cpu,hot.clock_cpu,cool.clock_cpu,(unsigned long long)hot.checksum,(unsigned long long)cool.checksum,(unsigned long long)hot.tid,(unsigned long long)cool.tid);
 return hot.cpu>0 && cool.cpu>0?0:5;
}

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
int main(void) {
 double wall=seconds(CLOCK_MONOTONIC),hot=0,cool=0;uint64_t x=1,tid;
 if(wall<0||pthread_threadid_np(NULL,&tid))return 1;
 while(seconds(CLOCK_MONOTONIC)-wall<3.0){
  double start=thread_seconds(),end=start;if(start<0)return 2;
  do {for(unsigned i=0;i<16;i++)x=hot_leaf(x);end=thread_seconds();if(end<0)return 3;}while(end-start<0.020);
  hot+=end-start;start=end;
  do {for(unsigned i=0;i<16;i++)x=cool_leaf(x);end=thread_seconds();if(end<0)return 4;}while(end-start<0.005);
  cool+=end-start;
 }
 printf("PASS hot_cpu=%.9f cool_cpu=%.9f tid=%llu checksum=%llu\n",hot,cool,(unsigned long long)tid,(unsigned long long)x);return 0;
}

/* SPDX-License-Identifier: MIT
 * Experimental in-process Mach thread sampler. Never suspends across symbol lookup.
 * Copyright (c) 2026 Mason. Permission is granted to use, copy, modify,
 * distribute, sublicense and/or sell this software, provided this notice is
 * retained. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
 */
#include <mach/mach.h>
#include <mach/mach_vm.h>
#if defined(__x86_64__)
#include <mach/i386/thread_status.h>
#else
#include <mach/arm/thread_status.h>
#endif
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <dlfcn.h>
#include <errno.h>
#include <sys/resource.h>
#define MAX_SAMPLES 65536
#define MAX_THREADS 1024
struct sample { uintptr_t pc; uint64_t tid, user_us, system_us; double time; };
struct tracked { uint64_t tid, first_user,first_system,last_user,last_system; unsigned seen,running,samples; };
static struct sample samples[MAX_SAMPLES];
static struct tracked tracked[MAX_THREADS];
static unsigned used,nthreads,skipped,failures,overflow;
static _Atomic int stopping;
static pthread_t collector;
static int initialized;
static long interval_us=5000;
static double delay_seconds,window_seconds;
static const char *output;
static double window_user,window_system;
static uint64_t collector_cpu_us;
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static void wait_seconds(double value){struct timespec t={(time_t)value,(long)((value-(time_t)value)*1e9)};while(nanosleep(&t,&t)&&errno==EINTR){if(atomic_load(&stopping))break;}}
static uint64_t us(time_value_t value){return (uint64_t)value.seconds*1000000+value.microseconds;}
static struct tracked *track(uint64_t tid,uint64_t u,uint64_t s){
 for(unsigned i=0;i<nthreads;i++)if(tracked[i].tid==tid)return &tracked[i];
 if(nthreads==MAX_THREADS)return NULL;
 struct tracked *t=&tracked[nthreads++];t->tid=tid;t->first_user=u;t->first_system=s;return t;
}
static void poll_threads(mach_port_t self,double start,uint32_t order){
 thread_act_array_t threads=NULL;mach_msg_type_number_t count=0;
 if(task_threads(mach_task_self(),&threads,&count)!=KERN_SUCCESS){failures++;return;}
 for(unsigned k=0;k<count;k++){
  unsigned i=(k+order%count)%count;
  thread_t thread=threads[i];
  if(thread!=self){
   thread_basic_info_data_t info;mach_msg_type_number_t size=THREAD_BASIC_INFO_COUNT;
   thread_identifier_info_data_t id;mach_msg_type_number_t idsize=THREAD_IDENTIFIER_INFO_COUNT;
   if(thread_info(thread,THREAD_BASIC_INFO,(thread_info_t)&info,&size)==KERN_SUCCESS &&
      thread_info(thread,THREAD_IDENTIFIER_INFO,(thread_info_t)&id,&idsize)==KERN_SUCCESS){
    uint64_t user=us(info.user_time),system=us(info.system_time);
    struct tracked *t=track(id.thread_id,user,system);
    if(t){t->seen++;t->last_user=user;t->last_system=system;}
    if(info.run_state==TH_STATE_RUNNING && info.suspend_count==0){
     if(t)t->running++;
     uintptr_t pc=0;kern_return_t rc=KERN_FAILURE;
     if(thread_suspend(thread)==KERN_SUCCESS){
#if defined(__x86_64__)
      x86_thread_state64_t state={0};mach_msg_type_number_t n=x86_THREAD_STATE64_COUNT;
      rc=thread_get_state(thread,x86_THREAD_STATE64,(thread_state_t)&state,&n);pc=(uintptr_t)state.__rip;
#else
      arm_thread_state64_t state={0};mach_msg_type_number_t n=ARM_THREAD_STATE64_COUNT;
      rc=thread_get_state(thread,ARM_THREAD_STATE64,(thread_state_t)&state,&n);pc=(uintptr_t)arm_thread_state64_get_pc(state);
#endif
      kern_return_t resumed=thread_resume(thread);
      if(resumed!=KERN_SUCCESS){/* Never continue with a thread knowingly suspended by us. */
       rc=KERN_FAILURE;failures++;
      }
     }
     if(rc==KERN_SUCCESS && pc){
      if(used<MAX_SAMPLES){samples[used++]=(struct sample){pc,id.thread_id,user,system,now()-start};if(t)t->samples++;}
      else overflow++;
     }else failures++;
    }else skipped++;
   }else failures++;
  }
  mach_port_deallocate(mach_task_self(),thread);
 }
 mach_vm_deallocate(mach_task_self(),(mach_vm_address_t)threads,count*sizeof(thread_t));
}
static void dump(double wall){
 FILE *f=fopen(output,"w");if(!f)return;
 fprintf(f,"pc,base,module,tid,time,user_us,system_us\n");
 for(unsigned i=0;i<used;i++){
  Dl_info d={0};dladdr((void *)samples[i].pc,&d);
  fprintf(f,"0x%llx,0x%llx,%s,%llu,%.9f,%llu,%llu\n",(unsigned long long)samples[i].pc,(unsigned long long)(uintptr_t)d.dli_fbase,d.dli_fname?d.dli_fname:"UNKNOWN",(unsigned long long)samples[i].tid,samples[i].time,(unsigned long long)samples[i].user_us,(unsigned long long)samples[i].system_us);
 }
 fclose(f);char path[4096];snprintf(path,sizeof(path),"%s.stats.json",output);f=fopen(path,"w");if(!f)return;
 fprintf(f,"{\"wall_seconds\":%.9f,\"window_user_seconds\":%.9f,\"window_system_seconds\":%.9f,\"collector_cpu_us\":%llu,\"interval_us\":%ld,\"samples\":%u,\"skipped_not_running\":%u,\"failures\":%u,\"overflow\":%u,\"threads\":[",wall,window_user,window_system,(unsigned long long)collector_cpu_us,interval_us,used,skipped,failures,overflow);
 for(unsigned i=0;i<nthreads;i++){struct tracked *t=&tracked[i];fprintf(f,"%s{\"tid\":%llu,\"cpu_us\":%llu,\"first_user_us\":%llu,\"first_system_us\":%llu,\"last_user_us\":%llu,\"last_system_us\":%llu,\"seen\":%u,\"running\":%u,\"samples\":%u}",i?",":"",(unsigned long long)t->tid,(unsigned long long)(t->last_user-t->first_user+t->last_system-t->first_system),(unsigned long long)t->first_user,(unsigned long long)t->first_system,(unsigned long long)t->last_user,(unsigned long long)t->last_system,t->seen,t->running,t->samples);}
 fprintf(f,"]}\n");fclose(f);
}
static void *run(void *unused){
 (void)unused;mach_port_t self=mach_thread_self();uint32_t random=0x7f4a7c15;
 wait_seconds(delay_seconds);double start=now();
 struct rusage before,after;getrusage(RUSAGE_SELF,&before);
 thread_basic_info_data_t self_before={0},self_after={0};mach_msg_type_number_t n=THREAD_BASIC_INFO_COUNT;
 thread_info(self,THREAD_BASIC_INFO,(thread_info_t)&self_before,&n);
 while(!atomic_load(&stopping) && (!window_seconds || now()-start<window_seconds)){
  random^=random<<13;random^=random>>17;random^=random<<5;poll_threads(self,start,random);
  wait_seconds(interval_us/1e6*(0.8+(random%4001)/10000.0));
 }
 double wall=now()-start;getrusage(RUSAGE_SELF,&after);n=THREAD_BASIC_INFO_COUNT;
 thread_info(self,THREAD_BASIC_INFO,(thread_info_t)&self_after,&n);
 collector_cpu_us=us(self_after.user_time)+us(self_after.system_time)-us(self_before.user_time)-us(self_before.system_time);
 window_user=after.ru_utime.tv_sec-before.ru_utime.tv_sec+(after.ru_utime.tv_usec-before.ru_utime.tv_usec)/1e6;
 window_system=after.ru_stime.tv_sec-before.ru_stime.tv_sec+(after.ru_stime.tv_usec-before.ru_stime.tv_usec)/1e6;
 mach_port_deallocate(mach_task_self(),self);dump(wall);return NULL;
}
__attribute__((constructor)) static void initialize(void){
 output=getenv("MACH_SAMPLE_OUTPUT");if(!output)return;
 const char *parent=getenv("MACH_SAMPLE_PARENT_PID");if(parent && strtol(parent,NULL,10)!=getppid())return;
 const char *rate=getenv("MACH_SAMPLE_INTERVAL_US");if(rate){char *end;interval_us=strtol(rate,&end,10);if(*end||interval_us<1000||interval_us>50000)return;}
 const char *delay=getenv("MACH_SAMPLE_DELAY");if(delay)delay_seconds=strtod(delay,NULL);
 const char *window=getenv("MACH_SAMPLE_SECONDS");if(window)window_seconds=strtod(window,NULL);
 if(delay_seconds<0||delay_seconds>30||window_seconds<0||window_seconds>60)return;
 if(!pthread_create(&collector,NULL,run,NULL))initialized=1;
}
__attribute__((destructor)) static void finish(void){if(initialized){atomic_store(&stopping,1);pthread_join(collector,NULL);}}

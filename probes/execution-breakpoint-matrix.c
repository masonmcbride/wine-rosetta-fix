/* Generic execution-breakpoint matrix, independent of applications. */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
static BYTE *code;static int action,multi,initial;static LONG hits,bad;static ULONG_PTR first_pc;
#ifdef _WIN64
#define PC(c) ((c)->Rip)
#else
#define PC(c) ((c)->Eip)
#endif
static LONG CALLBACK handler(EXCEPTION_POINTERS *p){CONTEXT *c=p->ContextRecord;
 printf("handler code=%08lx pc=%p dr6=%llx dr7=%llx flags=%lx\n",p->ExceptionRecord->ExceptionCode,(void *)(ULONG_PTR)PC(c),(unsigned long long)c->Dr6,(unsigned long long)c->Dr7,c->EFlags);fflush(stdout);
 if(p->ExceptionRecord->ExceptionCode!=EXCEPTION_SINGLE_STEP)return EXCEPTION_CONTINUE_SEARCH;
 if(++hits>8)ExitProcess(4);
 if(PC(c)!=first_pc || (c->Dr6&15)!=(multi?3:1))bad++;
 if(action==0||action==1)c->Dr7=0;
 if(action==1)PC(c)=(ULONG_PTR)(code+16);
 if(action==3)c->EFlags|=0x10000;
 return EXCEPTION_CONTINUE_EXECUTION;
}
static DWORD WINAPI worker(void *arg){return ((LPTHREAD_START_ROUTINE)code)(arg);}
int main(int argc,char **argv){CONTEXT c={0},got={0};HANDLE t;DWORD wait,result;int rf;
 initial=atoi(argv[1]);action=atoi(argv[2]);multi=atoi(argv[3]);rf=atoi(argv[4]);
 code=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);if(!code)return 2;memset(code,0x90,4096);code[2]=0xb8;code[3]=1;code[4]=code[5]=code[6]=0;
#ifdef _WIN64
 code[7]=0xc3;
#else
 code[7]=0xc2;code[8]=4;code[9]=0;
#endif
 memcpy(code+16,code+2,8);code[17]=2;if(initial==2){code[0]=0xeb;code[1]=0xfe;}FlushInstructionCache(GetCurrentProcess(),code,4096);if(!AddVectoredExceptionHandler(1,handler))return 2;
 t=CreateThread(NULL,0,initial==1?(LPTHREAD_START_ROUTINE)code:worker,NULL,CREATE_SUSPENDED,NULL);if(!t)return 2;if(initial==2){ResumeThread(t);Sleep(30);if(SuspendThread(t)==~0u)return 2;}c.ContextFlags=CONTEXT_CONTROL|CONTEXT_DEBUG_REGISTERS;if(!GetThreadContext(t,&c))return 2;
 if(initial==2)PC(&c)=(ULONG_PTR)(code+2);
 first_pc=c.Dr0=initial==2?PC(&c):(ULONG_PTR)(code+(initial==0?2:0));c.Dr1=multi?c.Dr0:0;c.Dr2=c.Dr3=c.Dr6=0;c.Dr7=multi?5:1;c.EFlags&=~(0x100|0x10000);if(rf)c.EFlags|=0x10000;if(!SetThreadContext(t,&c))return 2;
 got.ContextFlags=CONTEXT_CONTROL|CONTEXT_DEBUG_REGISTERS;if(!GetThreadContext(t,&got))return 2;printf("setup bits=%u initial=%d action=%d multi=%d RF=%d DR0=%p DR7=%llx flags=%lx\n",(unsigned)(8*sizeof(void*)),initial,action,multi,rf,(void *)(ULONG_PTR)got.Dr0,(unsigned long long)got.Dr7,got.EFlags);fflush(stdout);
 if(ResumeThread(t)==~0u)return 2;wait=WaitForSingleObject(t,5000);if(wait!=WAIT_OBJECT_0){printf("timeout wait=%lx\n",wait);fflush(stdout);ExitProcess(124);}GetExitCodeThread(t,&result);CloseHandle(t);printf("result hits=%ld bad=%ld worker=%lu\n",hits,bad,result);
 return rf&&initial==2?(hits!=0||result!=1):(hits!=1||bad||result!=(action==1?2:1));
}

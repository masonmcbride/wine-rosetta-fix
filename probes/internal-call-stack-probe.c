/* Generic internal-stepping CALL/RET stack regression probe. */
#include <windows.h>
#include <stdio.h>
static volatile ULONG_PTR before,callee,after;
__attribute__((noinline)) static void unused_target(void){}
int main(void){CONTEXT c={0};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;c.Dr0=(ULONG_PTR)unused_target;c.Dr7=1;if(!SetThreadContext(GetCurrentThread(),&c)){printf("enable SetThreadContext failed %lu\n",GetLastError());return 2;}
#ifdef _WIN64
 __asm__ volatile("mov %%rsp,%0\n\tcall 1f\n\tjmp 2f\n1:\tmov %%rsp,%1\n\tret\n2:\tmov %%rsp,%2\n\tmov %0,%%rsp":"=m"(before),"=m"(callee),"=m"(after)::"memory","cc");
#else
 __asm__ volatile("mov %%esp,%0\n\tcall 1f\n\tjmp 2f\n1:\tmov %%esp,%1\n\tret\n2:\tmov %%esp,%2\n\tmov %0,%%esp":"=m"(before),"=m"(callee),"=m"(after)::"memory","cc");
#endif
 ZeroMemory(&c,sizeof(c));c.ContextFlags=CONTEXT_DEBUG_REGISTERS;if(!SetThreadContext(GetCurrentThread(),&c)){printf("clear SetThreadContext failed %lu\n",GetLastError());return 2;}
 printf("bits=%u before=%p callee=%p after=%p actual_delta=%lld expected=%u\n",(unsigned)(8*sizeof(void*)),(void*)before,(void*)callee,(void*)after,(long long)(before-callee),(unsigned)sizeof(void*));return before-callee!=sizeof(void*)||after!=before;
}

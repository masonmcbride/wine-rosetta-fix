/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Does a TF exception after a direct CALL report the correct stack width? */
#include <windows.h>
#include <stdio.h>
static volatile ULONG_PTR before, reported, return_word, resumed;
static volatile LONG hits;
static LONG CALLBACK handler(EXCEPTION_POINTERS *p)
{
    if (p->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP)
        return EXCEPTION_CONTINUE_SEARCH;
    hits++;
    if (hits == 2)
    {
#ifdef _WIN64
        resumed = p->ContextRecord->Rsp;
#else
        resumed = p->ContextRecord->Esp;
#endif
        p->ContextRecord->EFlags &= ~0x100;
        return EXCEPTION_CONTINUE_EXECUTION;
    }
#ifdef _WIN64
    reported = p->ContextRecord->Rsp;
#else
    reported = p->ContextRecord->Esp;
#endif
    return_word = *(ULONG_PTR *)reported;
    p->ContextRecord->EFlags |= 0x100;
    return EXCEPTION_CONTINUE_EXECUTION;
}
int main(void)
{
    PVOID registration = AddVectoredExceptionHandler(1, handler);
    if (!registration) return 2;
#ifdef _WIN64
    __asm__ volatile("mov %%rsp,%0\n\tpushfq\n\torl $0x100,(%%rsp)\n\tpopfq\n\tcall 1f\n\tjmp 2f\n1:\tret\n2:\tmov %0,%%rsp"
                     : "=m"(before) : : "memory", "cc");
#else
    __asm__ volatile("mov %%esp,%0\n\tpushfl\n\torl $0x100,(%%esp)\n\tpopfl\n\tcall 1f\n\tjmp 2f\n1:\tret\n2:\tmov %0,%%esp"
                     : "=m"(before) : : "memory", "cc");
#endif
    RemoveVectoredExceptionHandler(registration);
    printf("bits=%u hits=%ld before=%p reported=%p call_stack_delta=%lld expected=%u return=%p\n",
           (unsigned)(8*sizeof(void*)), hits, (void*)before, (void*)reported,
           (long long)(before-reported), (unsigned)sizeof(void*), (void*)return_word);
    printf("after RET=%p expected=%p\n", (void*)resumed, (void*)before);
    return hits != 2 || before-reported != sizeof(void*) || resumed != before;
}

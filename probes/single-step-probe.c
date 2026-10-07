/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Test instruction stepping independently of hardware debug registers. */
#include <windows.h>
#include <stdio.h>

static volatile LONG hits;
static LONG CALLBACK handler(EXCEPTION_POINTERS *exception)
{
    if (exception->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP)
        return EXCEPTION_CONTINUE_SEARCH;
    hits++;
    exception->ContextRecord->EFlags &= ~0x100;
    return EXCEPTION_CONTINUE_EXECUTION;
}

int main(void)
{
    PVOID registration = AddVectoredExceptionHandler(1, handler);
    if (!registration) return 2;
#ifdef _WIN64
    __asm__ volatile("pushfq\n\torl $0x100, (%%rsp)\n\tpopfq\n\tnop\n\tnop" ::: "memory", "cc");
#else
    __asm__ volatile("pushfl\n\torl $0x100, (%%esp)\n\tpopfl\n\tnop\n\tnop" ::: "memory", "cc");
#endif
    RemoveVectoredExceptionHandler(registration);
    printf("Pointer size: %u; single-step exceptions: %ld\n", (unsigned)sizeof(void *), hits);
    return hits != 1;
}

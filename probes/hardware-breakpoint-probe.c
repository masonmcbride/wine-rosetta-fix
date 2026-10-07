/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Distinguish debug-register readback from actual execution-breakpoint delivery. */
#include <windows.h>
#include <stdio.h>
static volatile LONG hits;
static volatile LONG ran;
static LONG CALLBACK handler(EXCEPTION_POINTERS *exception)
{
    if (exception->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP) return EXCEPTION_CONTINUE_SEARCH;
    hits++;
    exception->ContextRecord->Dr7 = 0;
    exception->ContextRecord->EFlags |= 0x10000; /* resume without immediately retriggering */
    return EXCEPTION_CONTINUE_EXECUTION;
}
__attribute__((noinline)) static void target(void) { ran++; }
int main(void)
{
    CONTEXT ctx = {0}, got = {0};
    PVOID registration = AddVectoredExceptionHandler(1, handler);
    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    ctx.Dr0 = (ULONG_PTR)target;
    ctx.Dr7 = 1;
    if (!registration || !SetThreadContext(GetCurrentThread(), &ctx)) return 2;
    got.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (!GetThreadContext(GetCurrentThread(), &got)) return 2;
    printf("Pointer size: %u; readback=%s\n", (unsigned)sizeof(void *),
           got.Dr0 == ctx.Dr0 && got.Dr7 == 1 ? "matches" : "differs");

    target();
    ZeroMemory(&ctx, sizeof(ctx));
    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (!SetThreadContext(GetCurrentThread(), &ctx)) return 2;
    RemoveVectoredExceptionHandler(registration);
    printf("Execution count: %ld; breakpoint delivery count: %ld\n", ran, hits);
    printf("RESULT: %s\n", hits == 1 && ran == 1 ? "breakpoint delivered" : "breakpoint NOT delivered");
    return hits != 1 || ran != 1;
}

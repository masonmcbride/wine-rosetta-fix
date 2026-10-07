/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Check handler redirection and rearming, independently of any game. */
#include <windows.h>
#include <stdio.h>
static volatile LONG hits, original_ran, redirect_ran, secondary_ran;
__attribute__((noinline)) static void secondary(void) { secondary_ran++; }
__attribute__((noinline)) static void redirect(void) { redirect_ran++; secondary(); }
__attribute__((noinline)) static void original(void) { original_ran++; }
static LONG CALLBACK handler(EXCEPTION_POINTERS *p)
{
    if (p->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP)
        return EXCEPTION_CONTINUE_SEARCH;
    hits++;
    if (hits == 1)
    {
        p->ContextRecord->Dr0 = (ULONG_PTR)secondary;
#ifdef _WIN64
        p->ContextRecord->Rip = (ULONG_PTR)redirect;
#else
        p->ContextRecord->Eip = (ULONG_PTR)redirect;
#endif
    }
    else p->ContextRecord->Dr7 = 0;
    return EXCEPTION_CONTINUE_EXECUTION;
}
int main(void)
{
    CONTEXT ctx = {0};
    PVOID registration = AddVectoredExceptionHandler(1, handler);
    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    ctx.Dr0 = (ULONG_PTR)original;
    ctx.Dr7 = 1;
    if (!registration || !SetThreadContext(GetCurrentThread(), &ctx)) return 2;
    original();
    ZeroMemory(&ctx, sizeof(ctx));
    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (!SetThreadContext(GetCurrentThread(), &ctx)) return 2;
    RemoveVectoredExceptionHandler(registration);
    printf("bits=%u exceptions=%ld original=%ld redirected=%ld secondary=%ld\n",
           (unsigned)(8*sizeof(void*)), hits, original_ran, redirect_ran, secondary_ran);
    return hits != 2 || original_ran != 0 || redirect_ran != 1 || secondary_ran != 1;
}

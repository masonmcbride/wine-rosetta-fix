/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 Mason. Permission is granted to use, copy, modify,
 * distribute, sublicense and/or sell this software, provided this notice is
 * retained. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
static HANDLE ready, reply;
static volatile LONG stopping;
static ULONGLONG worker_roundtrips;
static DWORD WINAPI worker(void *unused)
{
    (void)unused;
    for (;;) {
        if (WaitForSingleObject(ready, INFINITE) != WAIT_OBJECT_0) return 1;
        if (InterlockedCompareExchange(&stopping, 0, 0)) return 0;
        ++worker_roundtrips;
        if (!SetEvent(reply)) return 2;
    }
}
int main(int argc, char **argv)
{
    char *end = NULL;
    unsigned long requested = argc > 1 ? strtoul(argv[1], &end, 10) : 45;
    DWORD seconds;
    ULONGLONG start, count = 0;
    HANDLE thread;
    DWORD code;
    FILETIME created, exited, kernel, user;
    if (argc > 2 || (argc > 1 && (!argv[1][0] || *end)) || requested < 1 || requested > 300) return 10;
    seconds = (DWORD)requested;
    ready = CreateEventW(NULL, FALSE, FALSE, NULL);
    reply = CreateEventW(NULL, FALSE, FALSE, NULL);
    if (!ready || !reply) return 11;
    thread = CreateThread(NULL, 0, worker, NULL, 0, NULL);
    if (!thread) return 12;
    printf("READY pid=%lu seconds=%lu\n", GetCurrentProcessId(), seconds);
    fflush(stdout);
    start = GetTickCount64();
    do {
        if (!SetEvent(ready)) return 13;
        if (WaitForSingleObject(reply, 10000) != WAIT_OBJECT_0) return 14;
        ++count;
    } while (GetTickCount64() - start < seconds * 1000ULL);
    InterlockedExchange(&stopping, 1);
    if (!SetEvent(ready) || WaitForSingleObject(thread, 10000) != WAIT_OBJECT_0) return 15;
    if (!GetExitCodeThread(thread, &code) || code) return 16;
    if (worker_roundtrips != count) return 18;
    if (!GetProcessTimes(GetCurrentProcess(), &created, &exited, &kernel, &user)) return 17;
    printf("PASS roundtrips=%llu elapsed_ms=%llu kernel_100ns=%llu user_100ns=%llu\n",
           count, GetTickCount64()-start,
           ((ULONGLONG)kernel.dwHighDateTime<<32)|kernel.dwLowDateTime,
           ((ULONGLONG)user.dwHighDateTime<<32)|user.dwLowDateTime);
    CloseHandle(thread); CloseHandle(ready); CloseHandle(reply);
    return 0;
}

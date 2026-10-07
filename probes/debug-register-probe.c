/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Generic Windows debug-register state probe; no game addresses or patches. */
#include <windows.h>
#include <stdio.h>
#include <string.h>

static int failures;

static DWORD WINAPI worker(void *unused)
{
    CONTEXT got = {0}, clear = {0};
    (void)unused;
    got.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (!GetThreadContext(GetCurrentThread(), &got) || got.Dr0 != 0x12340000 ||
        got.Dr1 != 0x12340001 || got.Dr2 != 0x12340002 || got.Dr3 != 0x12340003 ||
        (got.Dr6 & 0xf00f) || (got.Dr7 & ~0xdc00) != 0x155)
    {
        printf("FAIL resumed worker state DR0=%llx DR7=%llx\n",
               (unsigned long long)got.Dr0, (unsigned long long)got.Dr7);
        failures++;
    }
    else printf("PASS resumed worker state\n");
    clear.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (!SetThreadContext(GetCurrentThread(), &clear)) failures++;
    return 0;
}

static void roundtrip(HANDLE thread, const char *name, int clear)
{
    CONTEXT set = {0}, got = {0};
    set.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    set.Dr0 = 0x12340000;
    set.Dr1 = 0x12340001;
    set.Dr2 = 0x12340002;
    set.Dr3 = 0x12340003;
    set.Dr6 = 0;
    set.Dr7 = 0x155;
    if (!SetThreadContext(thread, &set))
    {
        printf("FAIL %s SetThreadContext error=%lu\n", name, GetLastError());
        failures++;
        return;
    }
    got.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (!GetThreadContext(thread, &got))
    {
        printf("FAIL %s GetThreadContext error=%lu\n", name, GetLastError());
        failures++;
        return;
    }
    printf("%s DR0=%llx DR1=%llx DR2=%llx DR3=%llx DR6=%llx DR7=%llx\n",
           name, (unsigned long long)got.Dr0, (unsigned long long)got.Dr1,
           (unsigned long long)got.Dr2, (unsigned long long)got.Dr3,
           (unsigned long long)got.Dr6, (unsigned long long)got.Dr7);
    if (got.Dr0 != set.Dr0 || got.Dr1 != set.Dr1 || got.Dr2 != set.Dr2 ||
        got.Dr3 != set.Dr3 || (got.Dr6 & 0xf00f) != set.Dr6 ||
        (got.Dr7 & ~0xdc00) != set.Dr7)
    {
        printf("FAIL %s roundtrip\n", name);
        failures++;
    }
    if (!clear) return;
    ZeroMemory(&set, sizeof(set));
    set.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (!SetThreadContext(thread, &set)) failures++;
    ZeroMemory(&got, sizeof(got));
    got.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (!GetThreadContext(thread, &got) || got.Dr0 || got.Dr1 || got.Dr2 ||
        got.Dr3 || (got.Dr6 & 0xf00f) || (got.Dr7 & ~0xdc00)) failures++;
}

static int child_check(const char *go_name, const char *ready_name)
{
    HANDLE go = OpenEventA(SYNCHRONIZE, FALSE, go_name);
    HANDLE ready = OpenEventA(EVENT_MODIFY_STATE, FALSE, ready_name);
    CONTEXT got = {0};
    if (!go || !ready) return 2;
    SetEvent(ready);
    if (WaitForSingleObject(go, 15000) != WAIT_OBJECT_0) return 2;
    got.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (!GetThreadContext(GetCurrentThread(), &got) || got.Dr0 != 0x56780000 ||
        got.Dr1 != 0x56780001 || got.Dr2 != 0x56780002 || got.Dr3 != 0x56780003 ||
        (got.Dr7 & ~0xdc00) != 0x101) return 1;
    return 0;
}

#ifdef _WIN64
static void cross_architecture(void)
{
    char path[MAX_PATH], command[MAX_PATH * 3], go_name[80], ready_name[80], *suffix;
    PROCESS_INFORMATION pi = {0};
    STARTUPINFOA si = {0};
    CONTEXT native = {0};
    WOW64_CONTEXT wow = {0};
    HANDLE go, ready;
    DWORD code;
    si.cb = sizeof(si);
    GetModuleFileNameA(NULL, path, sizeof(path));
    suffix = strstr(path, "probe64.exe");
    if (!suffix) { failures++; return; }
    memcpy(suffix, "probe32.exe", sizeof("probe32.exe"));
    sprintf(go_name, "Local\\WineDRGo%lu", GetCurrentProcessId());
    sprintf(ready_name, "Local\\WineDRReady%lu", GetCurrentProcessId());
    go = CreateEventA(NULL, TRUE, FALSE, go_name);
    ready = CreateEventA(NULL, TRUE, FALSE, ready_name);
    snprintf(command, sizeof(command), "\"%s\" --child %s %s", path, go_name, ready_name);
    if (!go || !ready || !CreateProcessA(NULL, command, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi))
    { failures++; return; }
    if (WaitForSingleObject(ready, 10000) != WAIT_OBJECT_0)
    { failures++; goto done; }
    if (SuspendThread(pi.hThread) == (DWORD)-1) { failures++; goto done; }
    native.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    native.Dr0 = 0x12340000; native.Dr1 = 0x12340001;
    native.Dr2 = 0x12340002; native.Dr3 = 0x12340003; native.Dr7 = 0x155;
    wow.ContextFlags = WOW64_CONTEXT_DEBUG_REGISTERS;
    if (!SetThreadContext(pi.hThread, &native) || !Wow64GetThreadContext(pi.hThread, &wow) ||
        wow.Dr0 != native.Dr0 || wow.Dr1 != native.Dr1 || wow.Dr2 != native.Dr2 ||
        wow.Dr3 != native.Dr3 || (wow.Dr7 & ~0xdc00) != native.Dr7)
    { printf("FAIL native to WOW64 view\n"); failures++; }
    else printf("PASS native to WOW64 view\n");
    wow.Dr0 = 0x56780000; wow.Dr1 = 0x56780001;
    wow.Dr2 = 0x56780002; wow.Dr3 = 0x56780003; wow.Dr6 = 0; wow.Dr7 = 0x101;
    ZeroMemory(&native, sizeof(native));
    native.ContextFlags = CONTEXT_DEBUG_REGISTERS;
    if (!Wow64SetThreadContext(pi.hThread, &wow) || !GetThreadContext(pi.hThread, &native) ||
        native.Dr0 != wow.Dr0 || native.Dr1 != wow.Dr1 || native.Dr2 != wow.Dr2 ||
        native.Dr3 != wow.Dr3 || (native.Dr7 & ~0xdc00) != wow.Dr7)
    { printf("FAIL WOW64 to native view\n"); failures++; }
    else printf("PASS WOW64 to native view\n");
    ResumeThread(pi.hThread);
    SetEvent(go);
    if (WaitForSingleObject(pi.hProcess, 10000) != WAIT_OBJECT_0 ||
        !GetExitCodeProcess(pi.hProcess, &code) || code)
    { printf("FAIL WOW64 child state after resume\n"); failures++; }
    else printf("PASS WOW64 child state after resume\n");
done:
    if (GetExitCodeProcess(pi.hProcess, &code) && code == STILL_ACTIVE) TerminateProcess(pi.hProcess, 2);
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    CloseHandle(go); CloseHandle(ready);
}
#endif

int main(int argc, char **argv)
{
    HANDLE thread;
    if (argc == 4 && !strcmp(argv[1], "--child")) return child_check(argv[2], argv[3]);
    printf("Pointer size: %u\n", (unsigned)sizeof(void *));
    roundtrip(GetCurrentThread(), "self", 1);
    thread = CreateThread(NULL, 0, worker, NULL, CREATE_SUSPENDED, NULL);
    if (!thread) return 2;
    roundtrip(thread, "suspended worker", 0);
    ResumeThread(thread);
    WaitForSingleObject(thread, 10000);
    CloseHandle(thread);
#ifdef _WIN64
    cross_architecture();
#endif
    printf("RESULT: %d failures\n", failures);
    return failures != 0;
}

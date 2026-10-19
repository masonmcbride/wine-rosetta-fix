// SPDX-License-Identifier: MIT
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
extern "C" int exception_correctness();
extern "C" void guarded_work(unsigned, int);
extern "C" unsigned work_checksum();
DWORD WINAPI worker(LPVOID) { return (DWORD)exception_correctness(); }
int main(int argc, char **argv) {
  const int result = exception_correctness();
  if (result) { printf("{\"correctness\":false,\"failure\":%d}\n", result); return result; }
  HANDLE thread = CreateThread(0, 0, worker, 0, 0, 0);
  if (!thread) return 24;
  if (WaitForSingleObject(thread, 10000) != WAIT_OBJECT_0) return 25;
  DWORD worker_result = 0;
  if (!GetExitCodeThread(thread, &worker_result)) return 26;
  CloseHandle(thread);
  if (worker_result) return 27;
  const unsigned iterations = argc > 1 ? strtoul(argv[1], 0, 10) : 1000000;
  if (!iterations || iterations > 100000000) return 20;
  LARGE_INTEGER frequency, begin, end;
  if (!QueryPerformanceFrequency(&frequency) || frequency.QuadPart <= 0) return 21;
  // Warm up translation before the measured loop; exceptions are tested above.
  for (unsigned i = 0; i < 10000; ++i) guarded_work(i, 0);
  const unsigned before_checksum = work_checksum();
  if (!QueryPerformanceCounter(&begin)) return 22;
  for (unsigned i = 0; i < iterations; ++i) guarded_work(i, 0);
  if (!QueryPerformanceCounter(&end)) return 23;
  const unsigned expected = before_checksum +
      (unsigned)(((unsigned long long)iterations * (iterations - 1)) / 2);
  if (work_checksum() != expected) return 28;
  printf("{\"correctness\":true,\"iterations\":%u,\"ticks\":%lld,"
         "\"frequency\":%lld,\"checksum\":%u}\n", iterations,
         (long long)(end.QuadPart - begin.QuadPart),
         (long long)frequency.QuadPart, work_checksum());
}

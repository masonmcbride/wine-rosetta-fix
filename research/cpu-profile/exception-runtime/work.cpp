// SPDX-License-Identifier: MIT
// No standard C++ library dependency: compare coherent exception runtimes.
namespace {
volatile int live = 0;
volatile int destroyed = 0;
volatile unsigned checksum = 0;
struct Guard {
  Guard() noexcept { live = live + 1; }
  ~Guard() noexcept { destroyed = destroyed + 1; live = live - 1; }
};
struct Failure { int code; };
struct DerivedFailure : Failure { int detail; };
struct ConstructorFailure {
  Guard member;
  ConstructorFailure() { throw Failure{23}; }
};
}

extern "C" __attribute__((noinline)) void exception_leaf(unsigned value, int fail) {
  Guard guard;
  checksum = checksum + value;
  if (fail) throw Failure{17};
}

extern "C" __attribute__((noinline)) void guarded_work(unsigned value, int fail) {
  Guard guard;
  exception_leaf(value, fail);
}

// Return a distinct failure code, never rely on NDEBUG-sensitive assert().
extern "C" int exception_correctness() {
  int before = destroyed;
  guarded_work(1, 0);
  if (live != 0 || destroyed != before + 2) return 1;
  before = destroyed;
  try { guarded_work(2, 1); return 2; }
  catch (const Failure &e) { if (e.code != 17) return 3; }
  catch (...) { return 4; }
  if (live != 0 || destroyed != before + 2) return 5;
  before = destroyed;
  try {
    Guard outer;
    try { Guard inner; throw Failure{29}; }
    catch (const Failure &) { if (live != 1) return 6; throw; }
  } catch (const Failure &e) { if (e.code != 29) return 7; }
  if (live != 0 || destroyed != before + 2) return 8;
  try { throw DerivedFailure{{31}, 41}; }
  catch (const Failure &e) { if (e.code != 31) return 9; }
  catch (...) { return 10; }
  before = destroyed;
  try { ConstructorFailure failure; return 11; }
  catch (const Failure &e) { if (e.code != 23) return 12; }
  if (live != 0 || destroyed != before + 1) return 13;
  for (int i = 0; i < 1000; ++i) {
    try { guarded_work(3, 1); return 14; }
    catch (const Failure &e) { if (e.code != 17) return 15; }
  }
  if (live != 0) return 16;
  return 0;
}
extern "C" unsigned work_checksum() { return checksum; }

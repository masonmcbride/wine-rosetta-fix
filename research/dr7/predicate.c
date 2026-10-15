/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Baseline derived from Wine signal_x86_64.c, rosetta_exec_breakpoints.
 * Only the pure DR7 predicate is extracted; feature/platform gates stay outside.
 */
#include <stdint.h>

__attribute__((noinline)) unsigned baseline(uint64_t d)
{
    for (unsigned i = 0; i < 4; ++i)
        if (((d >> (2 * i)) & 3) && !((d >> (16 + 4 * i)) & 15))
            return 1;
    return 0;
}

__attribute__((noinline)) unsigned candidate(uint64_t d)
{
    /* Evaluate all four independent slots without short-circuit OR. */
    return (!!(d & 3) & !(d & UINT64_C(0x000f0000))) |
           (!!(d & 12) & !(d & UINT64_C(0x00f00000))) |
           (!!(d & 48) & !(d & UINT64_C(0x0f000000))) |
           (!!(d & 192) & !(d & UINT64_C(0xf0000000)));
}

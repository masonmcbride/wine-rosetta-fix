/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Sampling workload only. Never use its timing as benchmark evidence.
 */
#include <stdint.h>
#include <stdio.h>
unsigned baseline(uint64_t);
int main(void)
{
    uint64_t d = UINT64_C(0x6a09e667f3bcc909), sum = 0;
    for (uint64_t i = 0; i < UINT64_C(2000000000); ++i)
    {
        d ^= d << 13; d ^= d >> 7; d ^= d << 17;
        sum += baseline(d);
    }
    printf("%llu\n", (unsigned long long)sum);
}

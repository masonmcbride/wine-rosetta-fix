/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <inttypes.h>

unsigned baseline(uint64_t);
unsigned candidate(uint64_t);
static uint64_t rng = UINT64_C(0x6a09e667f3bcc909);
static uint64_t next(void)
{
    rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17;
    return rng;
}
static uint64_t ns(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000 + t.tv_nsec;
}
static void check(uint64_t d)
{
    if (baseline(d) != candidate(d))
    { fprintf(stderr, "mismatch: %016" PRIx64 "\n", d); exit(1); }
}
int main(int argc, char **argv)
{
    if (argc == 1)
    {
        /* Exhaust every relevant input bit: enable bits 0..7, type/len 16..31. */
        for (uint64_t i = 0; i < (UINT64_C(1) << 24); ++i)
            check((i & 255) | ((i >> 8) << 16));
        for (unsigned i = 0; i < 1000000; ++i) check(next());
        puts("PASS: 16777216 relevant-bit assignments + 1000000 full-width random words");
        return 0;
    }
    unsigned (*fn)(uint64_t) = argv[1][0] == 'b' ? baseline : candidate;
    unsigned mode = argc > 2 ? (unsigned)atoi(argv[2]) : 0;
    uint64_t words[4096], sum = 0;
    for (unsigned i = 0; i < 4096; ++i)
    {
        uint64_t d = next();
        switch (mode)
        {
        case 0: d = 1; break; /* fixed enabled slot 0 */
        case 1: d = 64; break; /* fixed enabled slot 3 */
        case 2: d = 0; break; /* disabled */
        case 3: break; /* uniform full-width synthetic */
        default: return 2;
        }
        words[i] = d;
    }
    for (unsigned i = 0; i < 1000000; ++i) sum += fn(words[i & 4095]);
    uint64_t start = ns();
    for (unsigned i = 0; i < 20000000; ++i) sum += fn(words[i & 4095]);
    printf("%s,%u,%.6f,%" PRIu64 "\n", argv[1], mode,
           (double)(ns() - start) / 20000000, sum);
    return 0;
}

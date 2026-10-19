// SPDX-License-Identifier: MIT
// Code-generation experiment only; not linked into Wine or a game.
struct Guard { Guard(); ~Guard(); };
extern void encode_work();
__attribute__((noinline)) void encode_chunk() {
  Guard guard;
  encode_work();
}

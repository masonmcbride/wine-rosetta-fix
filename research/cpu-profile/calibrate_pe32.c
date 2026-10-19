/* SPDX-License-Identifier: MIT
 * Local source-available original-PC/PE assembly calibration; never a game patch.
 */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
__declspec(dllexport) __attribute__((noinline)) uint32_t hot_leaf(uint32_t x){
 for(unsigned i=0;i<100000;i++){x=x*1664525u+1013904223u;x^=x>>13;}
 return x;
}
int main(void){
 printf("READY bits=%u base=%p hot=%p\n",(unsigned)(sizeof(void*)*8),(void*)GetModuleHandleA(NULL),(void*)hot_leaf);fflush(stdout);
 ULONGLONG end=GetTickCount64()+12000;uint32_t x=7;unsigned blocks=0;
 while(GetTickCount64()<end){x=hot_leaf(x);blocks++;}
 printf("PASS blocks=%u checksum=%u\n",blocks,x);return blocks?0:1;
}

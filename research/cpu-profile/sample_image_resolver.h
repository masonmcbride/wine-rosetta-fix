/* SPDX-License-Identifier: MIT
 * Post-window identity lookup only; never runs while a sampled thread is suspended.
 * PE lookup is bounded to 64 MB behind a sampled 32-bit PC in 64 KB steps.
 */
#include <libproc.h>
#include <mach-o/loader.h>
struct resolved_image {uintptr_t base;uint32_t size,cpu;char kind[16],path[4096];};
static struct resolved_image pe_images[128];
static unsigned pe_image_count;
static int self_read(uintptr_t address,void *dst,size_t bytes){
 mach_vm_size_t got=0;return mach_vm_read_overwrite(mach_task_self(),address,bytes,(mach_vm_address_t)dst,&got)==KERN_SUCCESS&&got==bytes;
}
static uint16_t u16(const unsigned char *p){uint16_t v;memcpy(&v,p,2);return v;}
static uint32_t u32(const unsigned char *p){uint32_t v;memcpy(&v,p,4);return v;}
static struct resolved_image resolve_image(uintptr_t pc){
 struct resolved_image r={0};
 for(unsigned i=0;i<pe_image_count;i++)if(pc>=pe_images[i].base&&pc-pe_images[i].base<pe_images[i].size)return pe_images[i];
 if(pc<=UINT32_MAX){
  uintptr_t page=pc&~(uintptr_t)65535;
  for(unsigned i=0;i<1024&&page>=i*(uintptr_t)65536;i++){
   uintptr_t base=page-i*(uintptr_t)65536;unsigned char dos[64],nt[264];
   if(!base||!self_read(base,dos,sizeof(dos))||u16(dos)!=0x5a4d)continue;
   uint32_t off=u32(dos+60);if(off<64||off>4096||!self_read(base+off,nt,sizeof(nt)))continue;
   if(u32(nt)!=0x4550||u16(nt+4)!=0x14c||u16(nt+24)!=0x10b)continue;
   uint32_t size=u32(nt+80);unsigned sections=u16(nt+6),optsize=u16(nt+20);
   if(!size||size>0x40000000||pc<base||pc-base>=size||!sections||sections>96||optsize<96||optsize>240)continue;
   int executable=0;
   for(unsigned s=0;s<sections;s++){
    unsigned char section[40];if(!self_read(base+off+24+optsize+s*40,section,sizeof(section)))break;
    uint32_t va=u32(section+12),vs=u32(section+8);
    if((u32(section+36)&0x20000000)&&pc-base>=va&&pc-base-va<vs){executable=1;break;}
   }
   if(!executable)continue;
   r.base=base;r.size=size;r.cpu=0x14c;strcpy(r.kind,"PE32");
   if(proc_regionfilename(getpid(),base,r.path,sizeof(r.path))<=0)strcpy(r.path,"UNKNOWN");
   if(pe_image_count<128)pe_images[pe_image_count++]=r;
   return r;
  }
 }
 Dl_info d={0};
 if(dladdr((void*)pc,&d)&&d.dli_fbase&&pc>=(uintptr_t)d.dli_fbase){
  struct mach_header_64 mh;uintptr_t base=(uintptr_t)d.dli_fbase;
  if(self_read(base,&mh,sizeof(mh))&&mh.magic==MH_MAGIC_64&&mh.ncmds<4096&&mh.sizeofcmds<1048576){
   uintptr_t command=base+sizeof(mh);int executable=0;
   for(unsigned i=0;i<mh.ncmds;i++){
    struct load_command lc;if(!self_read(command,&lc,sizeof(lc))||lc.cmdsize<8||command+lc.cmdsize>base+sizeof(mh)+mh.sizeofcmds)break;
    if(lc.cmd==LC_SEGMENT_64){
     struct segment_command_64 seg;if(!self_read(command,&seg,sizeof(seg)))break;
     /* __TEXT begins at the Mach header for the supported dylibs/executables. */
     if(!strcmp(seg.segname,"__TEXT")&&(seg.initprot&VM_PROT_EXECUTE)&&pc-base<seg.vmsize){executable=1;break;}
    }
    command+=lc.cmdsize;
   }
   if(executable){r.base=base;r.cpu=mh.cputype;strcpy(r.kind,"MachO64");snprintf(r.path,sizeof(r.path),"%s",d.dli_fname?d.dli_fname:"UNKNOWN");return r;}
  }
 }
 strcpy(r.kind,"UNKNOWN");strcpy(r.path,"UNKNOWN");return r;
}
static void csv_path(FILE *f,const char *s){fputc('"',f);for(;*s;s++){if(*s=='"')fputc('"',f);fputc(*s,f);}fputc('"',f);}
static void write_identity_sample(FILE *f,const struct sample *s){
 struct resolved_image r=resolve_image(s->pc);unsigned char bytes[16];char hex[33]={0};
 if(self_read(s->pc,bytes,sizeof(bytes)))for(unsigned i=0;i<sizeof(bytes);i++)snprintf(hex+i*2,3,"%02x",bytes[i]);
 fprintf(f,"0x%llx,0x%llx,",(unsigned long long)s->pc,(unsigned long long)r.base);csv_path(f,r.path);
 fprintf(f,",%llu,%.9f,%llu,%llu,%s,0x%x,%s\n",(unsigned long long)s->tid,s->time,(unsigned long long)s->user_us,(unsigned long long)s->system_us,r.kind,r.cpu,hex);
}

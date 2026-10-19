/* SPDX-License-Identifier: MIT
 * Disposable Metal presentation fixture; no Wine/game code is loaded.
 * Timing is a collector validation signal, not a game-performance benchmark.
 */
#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <QuartzCore/CAMetalLayer.h>
#include <time.h>
#include <stdlib.h>
@interface Frames : NSObject
@property(strong) CAMetalLayer *layer;
@property(strong) id<MTLCommandQueue> queue;
@property unsigned count;
@property double deadline;
@end
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
@implementation Frames
-(void)tick:(NSTimer *)timer {
 if(now()>self.deadline){[timer invalidate];printf("PASS frames=%u\n",self.count);fflush(stdout);[NSApp terminate:nil];return;}
 @autoreleasepool {
  id<CAMetalDrawable> drawable=[self.layer nextDrawable];if(!drawable)return;
  MTLRenderPassDescriptor *pass=[MTLRenderPassDescriptor renderPassDescriptor];
  pass.colorAttachments[0].texture=drawable.texture;
  pass.colorAttachments[0].loadAction=MTLLoadActionClear;
  pass.colorAttachments[0].storeAction=MTLStoreActionStore;
  pass.colorAttachments[0].clearColor=MTLClearColorMake(.08,.12,.18,1);
  id<MTLCommandBuffer> buffer=[self.queue commandBuffer];
  id<MTLRenderCommandEncoder> encoder=[buffer renderCommandEncoderWithDescriptor:pass];[encoder endEncoding];
  [buffer presentDrawable:drawable];[buffer commit];self.count++;
 }
}
@end
int main(void){@autoreleasepool {
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
 NSWindow *window=[[NSWindow alloc] initWithContentRect:NSMakeRect(40,40,320,200) styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO];
 [window setTitle:@"Disposable profiling fixture"];
 Frames *frames=[Frames new];frames.layer=[CAMetalLayer layer];frames.layer.device=MTLCreateSystemDefaultDevice();
 if(!frames.layer.device)return 2;
 frames.layer.pixelFormat=MTLPixelFormatBGRA8Unorm;frames.layer.drawableSize=CGSizeMake(320,200);frames.queue=[frames.layer.device newCommandQueue];
 window.contentView.wantsLayer=YES;window.contentView.layer=frames.layer;[window orderBack:nil];
 const char *duration=getenv("PACING_FIXTURE_SECONDS");double seconds=duration?strtod(duration,NULL):60;
 if(seconds<1||seconds>120)return 4;
 frames.deadline=now()+seconds;
 [NSTimer scheduledTimerWithTimeInterval:1.0/60 target:frames selector:@selector(tick:) userInfo:nil repeats:YES];
 [NSApp run];printf("PASS frames=%u\n",frames.count);
 return frames.count?0:3;
}}

	.section	__TEXT,__text,regular,pure_instructions
	.build_version macos, 15, 0	sdk_version 15, 5
	.globl	_baseline                       ; -- Begin function baseline
	.p2align	2
_baseline:                              ; @baseline
	.cfi_startproc
; %bb.0:
	tst	x0, #0x3
	b.eq	LBB0_3
; %bb.1:
	and	x8, x0, #0xf0000
	cbnz	x8, LBB0_3
; %bb.2:
	mov	w0, #1                          ; =0x1
	ret
LBB0_3:
	tst	x0, #0xc
	b.eq	LBB0_6
; %bb.4:
	and	x8, x0, #0xf00000
	cbnz	x8, LBB0_6
; %bb.5:
	mov	w0, #1                          ; =0x1
	ret
LBB0_6:
	tst	x0, #0x30
	b.eq	LBB0_9
; %bb.7:
	and	x8, x0, #0xf000000
	cbnz	x8, LBB0_9
; %bb.8:
	mov	w0, #1                          ; =0x1
	ret
LBB0_9:
	tst	x0, #0xc0
	cset	w8, ne
	tst	x0, #0xf0000000
	csel	w0, wzr, w8, ne
	ret
	.cfi_endproc
                                        ; -- End function
	.section	__TEXT,__literal16,16byte_literals
	.p2align	4, 0x0                          ; -- Begin function candidate
lCPI1_0:
	.quad	3                               ; 0x3
	.quad	12                              ; 0xc
lCPI1_1:
	.quad	48                              ; 0x30
	.quad	192                             ; 0xc0
lCPI1_2:
	.quad	983040                          ; 0xf0000
	.quad	15728640                        ; 0xf00000
lCPI1_3:
	.quad	251658240                       ; 0xf000000
	.quad	4026531840                      ; 0xf0000000
	.section	__TEXT,__text,regular,pure_instructions
	.globl	_candidate
	.p2align	2
_candidate:                             ; @candidate
	.cfi_startproc
; %bb.0:
	dup.2d	v0, x0
Lloh0:
	adrp	x8, lCPI1_0@PAGE
Lloh1:
	ldr	q1, [x8, lCPI1_0@PAGEOFF]
	and.16b	v1, v0, v1
Lloh2:
	adrp	x8, lCPI1_1@PAGE
Lloh3:
	ldr	q2, [x8, lCPI1_1@PAGEOFF]
	and.16b	v2, v0, v2
Lloh4:
	adrp	x8, lCPI1_2@PAGE
Lloh5:
	ldr	q3, [x8, lCPI1_2@PAGEOFF]
	and.16b	v3, v0, v3
Lloh6:
	adrp	x8, lCPI1_3@PAGE
Lloh7:
	ldr	q4, [x8, lCPI1_3@PAGEOFF]
	and.16b	v0, v0, v4
	cmeq.2d	v2, v2, #0
	cmeq.2d	v1, v1, #0
	uzp1.4s	v1, v1, v2
	cmeq.2d	v0, v0, #0
	cmeq.2d	v2, v3, #0
	uzp1.4s	v0, v2, v0
	bic.16b	v0, v0, v1
	xtn.4h	v0, v0
	umaxv.4h	h0, v0
	fmov	w8, s0
	and	w0, w8, #0x1
	ret
	.loh AdrpLdr	Lloh6, Lloh7
	.loh AdrpAdrp	Lloh4, Lloh6
	.loh AdrpLdr	Lloh4, Lloh5
	.loh AdrpAdrp	Lloh2, Lloh4
	.loh AdrpLdr	Lloh2, Lloh3
	.loh AdrpAdrp	Lloh0, Lloh2
	.loh AdrpLdr	Lloh0, Lloh1
	.cfi_endproc
                                        ; -- End function
.subsections_via_symbols

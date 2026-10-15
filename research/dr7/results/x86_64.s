	.section	__TEXT,__text,regular,pure_instructions
	.build_version macos, 15, 0	sdk_version 15, 5
	.globl	_baseline                       ## -- Begin function baseline
	.p2align	4, 0x90
_baseline:                              ## @baseline
	.cfi_startproc
## %bb.0:
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	testb	$3, %dil
	setne	%cl
	testl	$983040, %edi                   ## imm = 0xF0000
	sete	%dl
	movl	$1, %eax
	testb	%dl, %cl
	jne	LBB0_4
## %bb.1:
	testb	$12, %dil
	setne	%cl
	testl	$15728640, %edi                 ## imm = 0xF00000
	sete	%dl
	testb	%dl, %cl
	jne	LBB0_4
## %bb.2:
	testb	$48, %dil
	setne	%cl
	testl	$251658240, %edi                ## imm = 0xF000000
	sete	%dl
	testb	%dl, %cl
	jne	LBB0_4
## %bb.3:
	testb	$-64, %dil
	setne	%al
	testl	$-268435456, %edi               ## imm = 0xF0000000
	sete	%cl
	andb	%al, %cl
	movzbl	%cl, %eax
LBB0_4:
	popq	%rbp
	retq
	.cfi_endproc
                                        ## -- End function
	.globl	_candidate                      ## -- Begin function candidate
	.p2align	4, 0x90
_candidate:                             ## @candidate
	.cfi_startproc
## %bb.0:
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset %rbp, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register %rbp
	testb	$3, %dil
	setne	%al
	testl	$983040, %edi                   ## imm = 0xF0000
	sete	%cl
	andb	%al, %cl
	testb	$12, %dil
	setne	%al
	testl	$15728640, %edi                 ## imm = 0xF00000
	sete	%dl
	andb	%al, %dl
	orb	%cl, %dl
	testb	$48, %dil
	setne	%al
	testl	$251658240, %edi                ## imm = 0xF000000
	sete	%cl
	andb	%al, %cl
	testb	$-64, %dil
	setne	%al
	testl	$-268435456, %edi               ## imm = 0xF0000000
	sete	%sil
	andb	%al, %sil
	orb	%cl, %sil
	orb	%dl, %sil
	movzbl	%sil, %eax
	popq	%rbp
	retq
	.cfi_endproc
                                        ## -- End function
.subsections_via_symbols

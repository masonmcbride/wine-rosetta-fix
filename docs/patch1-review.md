# Patch 1: upstream submission eligibility issue

Wine's official Clean Room Guidelines, retrieved on 2026-10-08, explicitly
prohibit using an LLM to generate code:
https://gitlab.winehq.org/wine/wine/-/wikis/Clean-Room-Guidelines

These patches were developed with substantial AI-generated code. They must
not be represented as compliant submissions or have that provenance concealed.
Passing tests, changing the author name, or manually approving the generated
patch does not establish an exception to the policy. Ask maintainers for
clarification before proposing any submission route. No submission was made.

The generic reproduction and measurement records remain useful technical
evidence; the playable private build remains unchanged. The isolated review
branch is retained as a local reference, not a merge-ready branch.

The fresh verification build was stopped after discovering this policy; no
new runtime test results were obtained. Its temporary files were removed.
Live upstream HEAD matched the existing base when checked.

---

The following preparation notes are historical and do not override the
eligibility issue above.

# Historical review preparation

## Local submission branch

`rosetta-debug-state-review` points to
`b81e0922706f9cc23602fecc014043901c059e88`, exactly one commit above
`63f62f7cd6964f544b08ae191d6a3d08fc8e5925`. It excludes execution delivery,
TF stepping, RF handling and the CALL workaround. The working two-commit branch
and playable engine are unchanged.

Only the upstream remote is currently configured. Add your WineHQ GitLab fork
as a separate remote before pushing; do not push this branch to the upstream
origin. No push or merge request was performed during preparation.

## Suggested merge request title

server: Preserve x86 debug register state under Rosetta.

## Suggested merge request description

Under Rosetta, the Mach thread-state API cannot retrieve or install translated
x86 debug registers. The existing server path returns zero state on reads and
STATUS_UNSUCCESSFUL on writes, preventing debug-register context round trips.

Preserve the requested debug state on the server thread, tracking validity with
SERVER_CTX_DEBUG_REGISTERS. Reads return the stored state when valid and zero
state otherwise. Add a generic ntdll test which sets debug registers on a
suspended thread and checks their values after the thread resumes.

This change preserves Windows-visible context state. Execution-breakpoint
delivery is not implemented by this change.

Validation: the retained isolated Rosetta exception-test logs report 43 i386
and 72 x86_64/WOW64 assertions, zero failures, zero skipped. These are historical
logs; they do not independently establish a fresh run of the final committed
revision. The full exception suite and Windows reference execution have not
been run. Whitespace checks pass for the submitted commit.

## Code review notes

- The server context path operates on the native AMD64 representation on this
  macOS build; WOW64 context translation happens around that path. The whole
  debug union copy preserves that representation. Unlike ptrace's supported
  i386 and AMD64 paths, this does not install physical registers.
- `debug_regs` is initialized with the thread object. `system_regs` marks
  validity; reads return zero when the bit is absent. New-thread creation
  inherits `system_regs` but leaves the new shadow values zero-initialized;
  no parent's breakpoint values are copied by this patch.
- Storage uses a macOS-only field derived from the protocol union via `typeof`.
  This is a potential style discussion; an explicit native register structure
  may be preferable if reviewers want to avoid deriving member types this way.
- The worker receives a static const expected CONTEXT, so its argument remains
  valid even after the parent wait times out. The local setter context is a
  copy. ResumeThread and the actual wait result are checked.
- The implementation's failure-to-success change is intentional even though
  hardware breakpoint delivery remains unsupported. Reviewers may question
  whether preserving readback alone is the desired intermediate behavior.

## Before pressing Submit

Verify the final Patch 1 revision with an isolated state-only test run and
retain the exact exit statuses. Check the current upstream branch for changes
and rebase this isolated branch if necessary. The current master was not fetched
as part of this preparation.

Official submission guidance retrieved from the WineHQ wiki on 2026-10-08:
https://gitlab.winehq.org/wine/wine/-/wikis/Submitting-Patches

It requires a real author name matching the WineHQ GitLab profile, a verified
account and personal fork. Commit subjects end with a period and prose is
wrapped at 72 characters. The existing author is a username, so submission
metadata needs correction on the isolated review branch. The tested working
branch will remain unchanged.

The live upstream HEAD check returned
63f62f7cd6964f544b08ae191d6a3d08fc8e5925, exactly the current Patch 1 base.
No rebase was required against that observed revision.

Do not certify author declarations or sign-off statements automatically. Review
those requirements yourself. Development here used AI assistance; represent
that provenance accurately and verify Wine's current contribution policy.

The branch is prepared for local review, not represented as already submitted,
accepted, or fully validated on the current upstream revision.

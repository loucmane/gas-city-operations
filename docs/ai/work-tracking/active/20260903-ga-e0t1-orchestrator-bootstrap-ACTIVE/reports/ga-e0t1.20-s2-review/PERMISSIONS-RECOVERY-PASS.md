# Scoped permissions recovery PASS

Completed 2026-09-28 at 21:58:47 CEST. Same original goal, still incomplete.

## Exact delivery and actual execution

- Signed candidate 7801c4a9c1d0e25a3a63520c8073494c4d2068aa, verified GPG
  FD5585922F5335BC378AD8D42ECF4432C7E7982D.
- Two independent Astra SOURCE_PASS verdicts each independently ran 61 tests.
  Request SHA256 1ef1b03c2c949a50bb4540d8fd01c9a211d9bd5d048d2f2f0b2f5457d17d6aaa.
  Native reviewer IDs 01a0e993-0c81-76c1-aece-f0f8305e7343 and
  01a0e993-356a-7133-8ccd-069f9ff90a84. Create-only exports in
  /tmp/ga-e0t1-permissions-review-r3 are filed through the supported runner.
- Wrapper SHA256 f00eb313f340d03c26ef37ae72e0e9ea68ecce793ada0e215948aff6058c9ce5.
- Fresh job ga-e0t1-20-permissions-r2 admitted once, started 21:58:33 CEST,
  exited 0 and became inactive at 21:58:47. No job was replayed.
- Final job record SHA256
  283edaf02ff50b841d39995c76d42acce9b7fb747199bb10cca80989e1848588.
- Consumed evidence root /var/tmp/ga-e0t1.20-codex-permissions-20260928-r2.
  result.json SHA256 baae65a63de589bc354a11d8ea673bded479be63aa004170256430073c44c862.
  postimage.json SHA256 709e74b448d50a0f4fc5a3fcaa7fc1728b5b364cfe8a76082ffe90cbd7e03010
  matches commit-intent and fresh actual readback of all six objects.

## Proven outcome

The five exact shared Codex rules/session directories are 0700 with private
owner-only default ACLs. Only rules/default.rules becomes 0600, retaining bytes
SHA256 3d80d7351c83161cadea1a7bbb3271a567c43fe4bc9c6074dd53f684cc576516.
No historical transcript was changed. Fresh inventory comparison preserves all
675 session entries and two rules entries except the authorized targets.

All 30 kernel creation cases pass on retained disposable mirrors using the
actual installed ACLs. New year/month/day directories and requested 0666/0600
files are private under umasks 0002, 0022 and 0077. The unchanged strict rules
reader passes. No rollback, failure, ambiguous or commit-interrupted evidence
exists. Honest ctime changes are recorded, not reset.

Host-before and host-after are byte-identical SHA256
74f669bf9612b6b23f0a5cab9839b953b71cbabee13a483e2ffeb968d8f4659a.
Actual cache and both protected trees retain full snapshot SHA256
2628baea760e6632ee241822befe15e70c30da14d96d85ecd4576eb045e05eaa.
Only the exact approved historical timestamp comparison was applied; no cache
write or other metadata exception occurred.

Core PID2800348 epoch229642910742, broker PID2940285 epoch123477220085,
signer PID2310 epoch39660502 and runner PID2812303 epoch301336188076 remain
stable with zero restarts. City and all four rigs remain suspended, zero agents
and native sessions. All six owned diagnostic child phases exited zero, reaped
their direct child and proved their process group gone without survivor or signal.

## Preserved failures and next boundary

The failed r1 evidence root and job are unchanged. Its prior latch is preserved
as state/HALTED.ga-e0t1-20-permissions-r1.before-permissions-r2 with original
SHA256 4801647950d1bb37e180e6beda459a8bf461e13b0e3f5d72135b8089efb00d69.
The runner is now held at the successful r2 terminal latch. Keep all evidence.

No product worker retry or implementation happened. This closes only the scoped
permissions prerequisite, not ga-e0t1.20, useful execution, C1 or provider parity.
Next is preparation and independent review of a fresh worker-window successor
binding the accepted actual permission postimages and preserved claim history.
Never replay R7 or modify its historical rejected transcript. Keep the worker
held until the separate window contract and applicable authorization are satisfied.

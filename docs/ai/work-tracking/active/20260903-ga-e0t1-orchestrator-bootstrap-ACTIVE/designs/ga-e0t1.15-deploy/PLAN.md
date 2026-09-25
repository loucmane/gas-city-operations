# ga-e0t1.15: deploy the silent-start fixes

Operator approval (2026-09-25, about 17:25 CEST): "i approve and i want it prepared asap". It
answered the request to prepare the reviewed deployment of both silent-start fixes. It covers
preparing this package and applying it through the reviewed path. Any new privilege or scope
found while preparing is reported before the live apply.

## What changes live

| Fix | Merged source | Live effect |
| --- | --- | --- |
| ga-odny: nudge-on-route accepts the supervisor API `{bead}` payload | Core PR 47, merge `b6843d3f` | routed workers are nudged without a coordinator KICK |
| ga-nibd: typed routing cycle detection | Core PR 46, merge `728b9687` | valid parent-waits-child graphs route; real cycles still refused |
| gct-jkgf: `--add-dir` grants before the role prompt | Template PR 71, merge `cfd353f3` | the role prompt reaches the signing and candidate workers |

Scope check:
- The live Core `gc` `69d00186` was built from `796d9a7a`, whose tree `f2c120a5` equals the tree of
  `e6366b9e`.
- `git diff 796d9a7a b6843d3f` touches exactly `internal/sling/cycle.go`, the core pack
  `nudge-on-route.sh`, `.gitignore` and their tests. Nothing else in Core changes.
- On the Template side, e6195b10..cfd353f3 is PR 71 only.

## Stages

Each stage has its own reviewed commit and live evidence, and needs the one before it.

### S1: offline custody build (done, offline)

`build.py` makes two independent no-hardlink clones of the locally signed build-source `9faeabc2`.
Its tree `c9f19d21` is byte-identical to the GitHub merge `b6843d3f`; the GitHub web-flow signature
cannot be verified locally, and the custody audit requires `verify-commit`. The build uses the
sequence 13 custody profile.

Result `/var/tmp/ga-e0t1.15-build-20260925`:
- Artifact `b2760ea407d8a5853fb7fbb3c184870ad4b6e9ccd763241a8ec59a8c3201d489`, 134052980 bytes, 0755.
- Reproducible across both clones.
- 7120 audited inputs, 1541 of them Git-bound; the input set is identical before and after the builds.
- result.json sha `ef023196`.

`verify.py` runs the byte-identical production validator `validateMetadataCustodyBuild` (`87e6855e`,
unchanged in the new source):
- it accepts the live `69d00186` and both new artifacts;
- it refuses the preserved incompatible `83d098fc`.

S1 supplements (r2, answering the S1 reviews of `5416651f`: A SOURCE_PASS, B HOLD):

- `scope-evidence.txt` (sha `fc0524e5`) records:
  - `git ls-remote origin refs/heads/main` = `b6843d3f`;
  - the trees of `796d9a7a`, `e6366b9e` (both `f2c120a5`), `b6843d3f` and `9faeabc2` (both `c9f19d21`);
  - the six-file `git diff --name-status 796d9a7a b6843d3f`;
  - the absence of `go.work` on every build path.
- Build-source provenance:
  - Created by `git commit-tree -S -F <message> -p 728b9687 -p ea78ca2e c9f19d21` in the rig
    repository, the same parents as the merge. The message is retained as `build-source-message.txt`.
  - Kept reachable by the local branch `codex/ga-e0t1.15-build-source`.
  - Signed by FD5585922F5335BC378AD8D42ECF4432C7E7982D, the same operator key that signed `796d9a7a`.
  - The rig's `origin/main` was advanced only by `git fetch`, a read-only remote observation.
  - The binary stamps `main.commit=9faeabc2`. Every S2/S3 receipt and envelope records the mapping
    `9faeabc2` → tree `c9f19d21` = merge `b6843d3f`.
- Known S1 deviations, recorded rather than rerun:
  - The input audit's git calls used the ambient operator environment, as in the retained function,
    rather than the pinned build ENV.
  - **Correction (r3): the `version --json` probe caused live city drift.** It ran the unadopted
    binary with the operator HOME and GC_HOME unset. Its config load ran `EnsureBuiltinRuntimeAssets`
    against the registered live city and, at 17:28:57 CEST, rewrote
    `/home/loucmane/gascity/city/.gc/scripts/gc-beads-bd.sh` to exec
    `~/.gc/cache/repos/69fe9a2e…`. The new sha was `bc0b3e88`; review B of r2 found it. The r2 claim
    "not city state" was false.
    - `~/.gc/cache/repos/69fe9a2e` itself was created at 16:34 by Core test runs with the default HOME.
    - The operator chose restoration. `restore_shim.py` (`55180381`, two SOURCE_PASS) wrote back the
      live supervisor's bytes `2e0a1f74` (GC_HOME `/home/loucmane/gascity/home`, key `a21cc0a2`) with
      mode 755 and a readback. Evidence is in `/var/tmp/ga-e0t1.15-shim-restore-20260925`, and the
      restore is recorded on ga-e0t1.
    - The bd script bytes are identical at both targets, so behaviour did not change while drifted.
    - From now on, every executor that runs gc, a gc-invoking test or a Core test suite uses an
      isolated HOME and GC_HOME, plus `DO_NOT_TRACK=1` and `GC_DISABLE_USAGE_METRICS=1`.
  - The input-audit deviation changes no asserted fact (HEAD, tree, clean status, signature, blob hashes).

### S1b: synthetic pack-cache expectation (done, offline)

The core pack is embedded in `gc`, and the cache key of a bundled source at its canonical pin
includes the binary's embedded content hash (`RepoCacheKey`, `SyntheticCacheKeyComponent`). The new
Core therefore materializes new synthetic cache directories on its first config load.

`cache_expect.py` runs `cache_expect_test.go.txt` in fresh clones of the live source `796d9a7a` and
the new source `9faeabc2`, offline, with an isolated HOME. Root `/var/tmp/ga-e0t1.15-cache-expect-20260925`;
the first attempt is preserved as `.attempt1`.
- **Method check.** The live run reproduces today's cache exactly:
  - content hash `171fe7bb`;
  - `a21cc0a2…` for pin `f895c0ff` (core, bd);
  - `c5f076a22…` for pin `3b3b89f2` (public gascity).
  The pin `33d3a430` (public gastown) is not imported by this city and has no directory.
- **Expectation.** Content hash `81f8a5b283c895cfbd1322606cce8a1df81df9409af0869cb6418fcd6356d979`.
  - **Required at startup:** `69fe9a2e6239743677a6e13188096df34d6eb6d41fad171af58671ef288fdd3f`, for pin `f895c0ff`.
    `requiredBuiltinSources` (cmd/gc/embed_builtin_packs.go) covers only core, bd and dolt, all at
    `f895c0ff`. The public gascity pack is never required, and this city imports the
    `loucmane/gascity-packs` fork instead.
  - **Allowed if present, never required:** `9c8c14fc1968fe278e18cf0a3721760b544fec231bb65779ce83cf59cabb7e47`,
    for pin `3b3b89f2`. The code path that created today's `c5f076a22` is not identified, so it is
    admitted only with the exact manifest. S3 and S4 inventories also allow it to appear late,
    under the same exact-manifest rule.
- **Contents.** 713 entries in each directory. Against the matching live directory for the same pin,
  the materialized content differs only in two places:
  - the marker, where the content hash changes and the commit stays the same;
  - `internal/bootstrap/packs/core/assets/scripts/nudge-on-route.sh`.
  The marker bytes depend on the key. The postflight derives each marker from
  `marker_commit_by_key` plus the content hash; it never uses the manifest digest of the `f895c0ff`
  materialization for `9c8c14fc`.
- **Shim.** The new supervisor rewrites the city shim `.gc/scripts/gc-beads-bd.sh` at startup
  (`ensureGcBeadsBdShim`), from `2e0a1f74` (key `a21cc0a2`) to exactly `a7bcaa7c…`, 312 bytes, mode 755.
  The new bytes exec `/home/loucmane/gascity/home/cache/repos/69fe9a2e…/examples/bd/assets/scripts/gc-beads-bd.sh`.
  The template is unchanged between the two sources.
- **Cache root.** The supervisor's GC_HOME is `/home/loucmane/gascity/home`, read from
  `/proc/<MainPID>/environ`. S2 watches `/home/loucmane/gascity/home/cache/repos` and proves that
  binding at preflight and at both postflights. `~/.gc/cache/repos`, the default-HOME root used by
  tests, is outside the city image and is not a delivery path.
- **Record.** `expectation.json` sha `62c5bb84` records the full manifest.
- **Delivery path.** Because the city imports core at the canonical pin through `packs.lock`, the
  script is served from the synthetic cache of the running binary. Adopting the binary is therefore
  what delivers ga-odny.

### S2: Core binary adoption, broker sequence 14 (live)

The successor of the sequence 13 custody adoption (staging
`ga-mutg-20260920/ga-mutg-custody-adoption-20260920`):
- the fixed broker operation `replace-gas-city-control-plane.v1`;
- Bead `ga-ecwh`;
- `69d00186` → `b2760ea4`;
- source `9faeabc2` / tree `c9f19d21`, with merge `b6843d3f` recorded;
- the same capture, recheck and submit mechanism and the same postflight pair.

Changes from sequence 13:
1. **Chain sources.** The reviewed chain sources (r8 → r4 → r3 → base) are restored byte-for-byte
   from their retained staging copies to the original `/tmp` paths. Each is proven by the digest its
   successor already checks, so no reviewed byte changes.
2. **Accepted predecessor.** A fresh, independently reviewed read-only closure of the current accepted
   image, the successor of R7 `observe.py`: two stable observations at least 5 s apart, bound to the
   ga-nibd TERMINAL result (`full_native_integrity` true) and the current platform and worker
   receipts. R7 `second.json` predates M5, P6 and the worker windows, so it cannot be reused.
3. **Cache and city transition.** The postflight admits exactly the S1b transition:
   - the required directory `69fe9a2e`, whose complete manifest must equal `expectation.json` and
     whose marker must be derived for its key;
   - `9c8c14fc`, only if present, under the same exact rule;
   - the cache root's own mtime, ctime and nlink change caused by the new entries;
   - `.packman-cache.lock`, whose bytes must be unchanged;
   - the city shim moving from exactly `2e0a1f74` to exactly `a7bcaa7c`;
   - the live-key repoint (r4, extended to every rig root in r5). Two materializers repoint links that
     embed the running binary's cache key, both at city start and on reload, with no suspension
     check (`prepareCityForSupervisor`):
     - stage-1 skill materialization (`runStage1SkillMaterialization`), using tmp then rename;
     - formula resolution (`ResolveFormulas`, for the city and every rig in `cfg.Rigs`), using
       remove then symlink, which is not atomic. The initialization wait therefore covers the
       `resolving_formulas` step, and a snapshot that sees a missing formula link refuses closed.

     The roots are the city and its four rigs: `gas-city-native`, `rigs/gascity`, `dev/blog` and
     `dev/hpfetcher-gc-main`, the set that restore-r9-routes-r3.py records. `live_key_inventory.py`
     (read-only) writes the inventory, `live-key-links.tsv` and `live-key-manifests.tsv`:
     - 143 symlinks whose target lies inside `cache/repos/a21cc0a2…`: 30 each in the city,
       `gas-city-native`, `dev/blog` and `dev/hpfetcher-gc-main`, and 23 in `rigs/gascity`;
     - 9 `.gc-skill-ownership.json` files that embed the key, all byte-identical today at `77390929`.
     The inventory also proves that every key-bearing manifest entry names an existing link with the
     same target, so a manifest has no stale key entry that `Run` would leave unsubstituted.

     S2 preflight re-proves the inventory exactly: same items, same targets, same manifest digests.
     Per item, the postflight admits exactly one of two states:
     - (a) unchanged;
     - (b) repointed. For a link, the target becomes the same string with `a21cc0a2…` replaced by
       `69fe9a2e…`, the link may get a new inode, and its parent directory's mtime, ctime and nlink
       may change. For a manifest, the bytes become exactly that key substitution: 1348 bytes,
       sha `f51ef649`.
     A manifest in state (b) requires all of its sink's links to be in state (b). The reverse is
     expected and admitted: links in (b) while their manifest is still in (a), because the manifest
     is saved after the links and a failed save is only a warning. Any other target, a new or removed
     link, a leftover `.<name>.tmp.<hex>` file, or a change to any other manifest or file under these
     roots refuses.
   - key-dependent runtime values that belong to the restart class sequence 13 already admits:
     the config revision (it hashes source paths, including cache paths) in reload events and in the
     trace.
     - Unaffected by construction: the sinks with no `a21cc0a2` targets (`.codex/skills`,
       `rigs/gascity/.codex/skills`, `.gc/agents/*/.claude/skills`, the `.claude.corrupt-*` archive).
       Hook and MCP projections copy embedded content, which is unchanged apart from
       `nudge-on-route.sh`.
     - S3 and S4 bind whichever state S2 observed. Their inventories admit a later (a)→(b) move under
       the same rule.
   Every other cache entry and city file must stay exact, with atime as the policy allows. Any
   other change refuses.
4. **Initialization wait.** The postflight waits, bounded, for city initialization before its exact
   comparison, the sequence 13 lesson. The corrected singleton cgroup-member transition from the
   sequence 13 recovery is carried forward.

**Order** (sequence 13 steps 1 to 7):
1. Recheck the bindings.
2. Pause the reconcile timer and prove it drained.
3. `prepare` with the fixed 900 s same-boot window.
4. Prepare the envelope and bind it once.
5. Independent full-envelope review.
6. `recheck`, then `submit` (one broker call).
7. Check the receipt, then postflight 1 and postflight 2, at least 5 s apart.
8. Independent live readback review.
9. Restore the timer.

It runs from a real terminal under `systemd-run --user -p UMask=0022`.

The city itself and all rigs stay suspended from S2 preflight through S3's end. City suspension is
required, not only rig suspension. The changed content, `nudge-on-route.sh`, is a city-scoped order
that fires on `bead.updated`, and order dispatch is skipped only when the city is suspended. An
unsuspended city could therefore let the new script write
`.gc/runtime/packs/core/nudge-on-route-state.json` and queue or wake a session, which would blur the
S4 acceptance evidence. S4 is the first stage that resumes the city, inside its own reviewed window.

### S3: metadata and receipt refresh (live)

A successor of M5 and P6, in this order within one reviewed window:
1. **Bind S2.** The metadata successor binds the S2 outputs:
   - the new Core image `b2760ea4`;
   - the S2 postflight Core epoch;
   - the sequence 14 receipt;
   - the S2 postflight closure, including the two new cache directories.
2. **Template.** Fast-forward the canonical Template checkout `e6195b10` → `cfd353f3` (PR 71 only).
   The receipt generator reads the checkout, so this comes before the receipt.
3. **Metadata release.** The Template authority moves to `cfd353f3`.
4. **Receipt refresh.** Re-pin the worker provisioning receipt:
   - `template_commit` and `member_heads[template]` to `cfd353f3`;
   - `provider.version`, which is the new `dependency_version` of the changed boundary;
   - the Core `gc` pin to `b2760ea4`, with the source recorded as `9faeabc2` / `c9f19d21`.
   Every other receipt leaf is checked unchanged, including any Core `member_heads` entry. If a
   Core member head exists, it moves to `9faeabc2` in this same step.
5. **Candidate lane.** The candidate lane receipt is re-pinned the same way before its first window.

If the window is interrupted after step 2 and before step 4 completes, stop. The Template checkout
is then ahead of the receipt, and every signing launch refuses on the version mismatch, which fails
closed. The recovery is to complete step 4 or fast-forward back through a reviewed recovery. Never
launch a worker in between.

### S4: acceptance

One worker window, a new successor package re-pinned to `b2760ea4`, the new cache directories and
the S3 receipts:
- no KICK;
- the worker claims from the routed nudge;
- the role prompt arrives as the first message.
Evidence goes on ga-e0t1.15. The committed ga-nibd packages (s1, s2, s2 r2), pinned to `69d00186`
and KICK, are superseded after S2 and must never run again.

## Consumers of the Core digest and epoch

Each consumer is re-pinned in the stage shown.

| Consumer | Pin | Stage |
| --- | --- | --- |
| Platform and worker provisioning receipts | gc sha, provider version, template commit | S3 |
| Candidate lane receipt (ga-6utp) | same | S3, before its first window |
| Window packages (observe-integrity `GC_SHA`, window-base pins, cache inventories) | gc sha, cache dirs | S4 successor |
| R7 or observe closures | full closure | S2 fresh predecessor |
| aegis-obsidian-reconcile timer | pauses and restores around S2 and S3; reads live state | S2, S3 |
| City shim `.gc/scripts/gc-beads-bd.sh` | embeds the bd cache key, which follows the embedded pack content | S2 (supervisor rewrite, admitted exactly) |
| 53 skill and formula symlinks and 3 skill ownership manifests (`live-key-*.tsv`) | embed the cache key | S2 (repoint admitted per item, unchanged or exact) |

## Stop conditions

These carry over from sequence 13:
- any drift from a reviewed digest;
- an ambiguous broker result;
- a postflight refusal: preserve and inspect, with no retry or rollback without review;
- new privilege;
- an interactive signing prompt;
- expiry of the fixed 900 s same-boot window or of the cache renewal horizon;
- a missing independent full-envelope review before submit, or a missing live readback review after it;
- the city or any rig not suspended at any check, from S2 preflight through the end of S3.

A pre-submit failure restores only the timer, after proving no broker call occurred. A post-submit
failure means inspecting the authoritative receipt and host. An ambiguous mutation is a stop, not
authority to retry or roll back. No sequence number, envelope or window root is ever reused.

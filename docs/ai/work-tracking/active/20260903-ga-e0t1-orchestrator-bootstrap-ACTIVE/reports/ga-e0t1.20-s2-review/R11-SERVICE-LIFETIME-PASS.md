# R11 synthetic service lifetime — PASS

2026-09-29 at 03:49 CEST. Both independent Astra reviewers returned SOURCE_PASS
for exact signed candidate `e07eafd06e6962bf37f38c10f2c3c4ad3f96d43d`, after the
preserved first-round HOLD. Fixture source SHA-256
`59b65f4e2069c5461dca547c69eded6f55d5bbcc0899b6be18c0d746df1aae13`
was rechecked along with exact clean HEAD and absence of the proposed evidence
root and JUnit file before the only execution.

Both actual user-unit tests passed in 2.13 seconds. In the negative case, normal
oneshot teardown removed the detached helper before it delivered. In the positive
case, keeping the parent alive allowed acknowledgement and then normal teardown
removed the helper. Both exact process and service cgroup were absent afterward.
A subsequent supported user-unit listing found no `ga-release-fixture-*` units.

- JUnit `/tmp/ga-e0t1-r11-lifetime-proof-20260929.xml`, SHA-256
  `d557ef0bd3314915da32fdf9ddad2e2757ec86a7b260a4dd1c6403f0b1e7d282`.
- Negative proof under `test_real_user_oneshot_owns_de0/proof.json`, SHA-256
  `fc3ced4914a42ecf08d6a227682417a8947127ff785f2c458b968fd97c2f4f2c`.
- Positive proof under `test_real_user_oneshot_owns_de1/proof.json`, SHA-256
  `9f69efdb97bb215b6e12be9e93146b4d2a0d8f008323ccdba64152dd473d3e60`.
- Both fixture directories remain under `/tmp/ga-e0t1-r11-lifetime-proof-20260929`;
  no cleanup or retry.
- Review A native transcript
  `/mnt/c/Users/smoki/.codex/sessions/2026/09/29/rollout-2026-09-29T02-26-09-01a0ea8d-ff5b-7833-abc6-8215a5f4066c.jsonl`,
  checkpoint hash `5f8881330f42ff4735d7dff09a5f0b5c4d6d7d19c81e18f30b242168c3c69a55`.
- Review B native transcript
  `/mnt/c/Users/smoki/.codex/sessions/2026/09/29/rollout-2026-09-29T02-26-19-01a0ea8e-2458-7580-a55b-97a3ee5e37ef.jsonl`,
  checkpoint hash `c6f4dd4a6ccec59967ae1456231abb44f2032e73589d4867e10d70e7073a0553`.

No Gas City command, worker, provider or production-service transition was part
of the fixture. No Fable/Claude inference occurred. This proves the service
lifetime correction's mechanism, not the fresh native release or product task.
The full R11 window still needs assembly, exact review admission, fresh preflight,
fresh startup and its live acknowledgement proof. Preserve the R10 pending
message, failed attempt and complete restoration evidence. Original goal remains
active, with useful source execution and bidirectional handover still incomplete.

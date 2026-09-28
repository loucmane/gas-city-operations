# R6 close correction — final candidate bindings

See R6-CLOSE-CORRECTION.md for the preserved independent HOLDs and RED/GREEN.
Both HOLD verdicts on 76f5de0b are filed and remain authoritative for that commit.

Final assembly SHA-256
6633e62384132e27c025ef7d64bb91a060fb3e7643d116877e64affb14f9ba39.
Exact observed cache directory mtime/ctime pair: 1790604770227789531.
This replaces only the previous observed pair under the existing authorization;
all cache contents, owners, modes and worker write protection remain checked.

Final generated contract SHA-256
c666e28453d9848ee17591e91c2341ed5c14249299ae29d547f4df740905de70.
Final generated close SHA-256
6bcc5636e6d43989d64e18f43ec745980fb5b9d742883b2eae0c47805e3148f2.
Generator SHA-256
4190998e0012e962a4efa698ee3611f5efb1a0c260f365cc4cd9e2cc79620a17.
Generated close regression SHA-256
912641c5a582672b6e339aa3dd299bcba78fdfda97cd60617d118c376dc8a971.

All 655 generator cases passed. The final materialized corpus was rerun after
the timestamp-only rebinding: 42 passed, zero failures or skips, XML
/tmp/ga-e0t1-20-r6-close-final-tests-20260928.xml SHA-256
d72815cbf946c2e49d9558a30284ddaf5dfb6a3ea1aa95d8b8de795a192d3a46.
The 697 total counts distinct final cases, not repeated focused runs.

Workflow verification passed all six checks at 16:17:53 CEST. A final signed
candidate and two independent PASS reviews remain required before execution.
The prepared prompt and probe are unchanged. No live operation or worker ran.
The runner remains halted after successful R6 preparation. No goal completion,
useful provider execution or handover acceptance is claimed.

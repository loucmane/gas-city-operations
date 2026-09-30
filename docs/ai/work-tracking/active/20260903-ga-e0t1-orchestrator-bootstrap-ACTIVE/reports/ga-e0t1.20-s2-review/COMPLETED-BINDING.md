# Preserve completed BIND across an operational successor

Both one-shot native Astra reviews of signed
96160355321144a7bc3626962aa13bcd727c12b4 returned HOLD on the same deterministic
ROUTE refusal. Their complete envelopes are filed and retained under
/tmp/ga-e0t1-20-s2-reviews-20260928-r5. No successor job has run.

The original BIND completed under signed 3c9931721fc8cdd204c8d7debd0c47c739064ccd.
Its executor is 9fd6c49adecf7fb991f9b8cd2c6279c25fcf73455bfa0911609a2079928495e7.
The generator incorrectly treated that consumed receipt identity as a mutable
dependency on the newly generated BIND executor. The successor keeps those
identities separate and additionally hashes all three original receipt files:

- binding-intent.json: 0f85dbaa6de8c174c3bc4950955777bb23621cb3bc8bd55ce9546c5e029e4b37
- result.json: 0e8003f3fa54558537cd93dcd2863ab5bcd0aef8be8af1ec11c198472ad022d2
- task-after.json: e58d90d46f6422aeb6d65a135daf41389fb5d1b9e0115f1019f6b2027abf7dcb

All remain at /var/tmp/ga-e0t1.20-bind-20260927-r1. No replay, rewrite or
receipt fabrication is authorized. BIND stays excluded from the new requests.

Read-only live comparison found every own child field unchanged. Only embedded
parent notes and updated_at had advanced, through the already-recorded supported
coordinator audit. The inherited whole-JSON comparison would reject that next.
The new continued_task check retains the exact key sets and all own fields;
every parent field except notes and updated_at remains exact. Parent notes must
preserve the entire old prefix, and parent audit time must be timezone-aware
and nondecreasing. The established contract still checks the one exact
nonblocking parent edge. Full snapshots and the same-call mutation comparisons
remain unchanged. This is not an exemption for child metadata or assignment.

The preserved RED run executes the old generated receipt block against the
actual completed receipt and fails its executor comparison, exactly as reported:
/tmp/ga-e0t1-20-bind-red-20260928-r1.xml. The first GREEN run passes 20 focused
cases, including all three receipt byte drifts, seven own-field changes, six
non-audit parent changes and audit erasure. Three further negative cases cover
backward, naive and malformed parent audit timestamps. Tests never run package
main, a provider, gc, a job, or any lifecycle operation.

No product repair, worker, staging, routing, resume or service transition has
occurred. Failed OBSERVE r1 and its HALTED latch remain preserved. This is still
the same understood corrected successor, not another live retry. Fresh exact
candidate reviews and immediate admission checks are mandatory. On a further
live mechanism failure, reassess rather than extending the retry chain.

All eight focused modules passed 206 tests with zero failures or skips:
/tmp/ga-e0t1-20-bind-full-20260928-r1.xml. Supported logging and parent-Bead
readback completed, followed by all six workflow checks at 02:10:48 CEST.
Final read-only baseline r6 records no provider or unexplained host/protected
differences and the same 8015-entry workspace. Its only non-access-time delta
is the cache directory timestamp pair 1790554248061328174, explicitly rebound
under the standing corrected-package grant. Observation SHA-256 is
071d34df5a8ddef27c5494e6639df22575c4311c5225159876f74463fbf1ea67.
The exact final assembly rerun is named in each frozen review request.

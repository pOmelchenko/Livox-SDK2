# MID-360S information-query hardware procedure

This is a test procedure for [issue #54](https://github.com/pOmelchenko/Livox-SDK2/issues/54),
not a completed hardware qualification. The reported physical comparison used
MID-360S firmware `35.1.1.11` with a consumer based on upstream
`68ae1e1dc77f61f03c95d7c2809831e198d0aedd`: a broad query containing
`kKeySetImuRange` (`0x002B`) returned `0x20`, and omitting that key succeeded.
The downstream base inspected for this change is
`17f2a7c18e8c5c91d0d794d64e46b7d625065771`. Reproduction on that exact base
and physical validation of the candidate remain pending.

## Candidate scope

The candidate removes only `0x002B` from the standard MID-360S information
query. It leaves explicit IMU-range control, state parsing, other model lists,
command ports, response codes, API/ABI and packaging unchanged. The standard
query consequently returns fewer optional fields. No firmware detection,
capability probing or retry mechanism is introduced. This conservative choice
avoids making ordinary reads depend on an optional firmware-sensitive field;
capability-aware queries would need a separate specified and tested lifecycle.

This is project-owned downstream work prepared by OpenAI Codex under maintainer
direction, preserving Livox's MIT notices. Maintainer pOmelchenko owns device
qualification and any later publication decision. Revisit an upstream
submission after exact-candidate platform checks and the affected-firmware test
below pass. Consumer pin changes, release publication and support for other
firmware are separate decisions.

## Preparation

1. Record the full base and candidate commit SHAs, clean working-tree status,
   OS/architecture, compiler, CMake version, linked library form and consumer
   revision. Build each revision in a separate clean directory; do not mix
   headers and libraries. Record hashes of the actual test binaries.
2. Confirm the physical model and firmware `35.1.1.11` independently, including
   the firmware value returned by `QueryLivoxLidarFirmwareVer`. Record device
   identity privately. Keep the same device, configuration and network for both
   runs, and use one SDK client at a time.
3. Use a small consumer harness that initializes the SDK with the known working
   configuration, discovers the device, and calls
   `QueryLivoxLidarInternalInfo` once from the application control thread.
   Keep callback context alive through SDK shutdown. Record the initiating
   return status, callback count, monotonic elapsed time, callback status,
   response presence, `ret_code`, `param_num` and decoded returned key IDs.
   Check status and response before accessing fields; do not keep the response
   pointer after the callback returns.
4. Capture outgoing/incoming command packets locally or instrument the final
   transport boundary. Distinguish broad command `0x0101` from the single-key
   firmware queries using its key count/list. The command observer alone does
   not record outbound packets. Correlate ACKs by device, command ID and sequence.
   Keep captures, addresses and serial numbers out of Git and public reports.
5. Disable application retries for the explicit-query checks. Use a five-second
   observation window per call and an overall finite harness deadline. A missing
   completion is a failure, not permission to wait or retry indefinitely.

## Same-device comparison

| Check | Base expectation to verify | Candidate acceptance |
| --- | --- | --- |
| Broad query wire payload | 33 keys including `0x002B` | 32 keys; exactly the same list except `0x002B` |
| Ordinary read | Reported failure `ret_code=0x20`; exact-base reproduction still pending | One callback, SDK status success and `ret_code=0`; required information/settings present |
| IMU streaming configuration | Record existing value | `kKeyImuDataEn` and IMU host configuration remain queried; optional range absence is accepted |
| Repeatability | Record results for each attempt | Ten sequential explicit calls, each completed before the next, all with one successful callback |
| Fresh view session | Record whether setup completes | One information-change notification after configuration ACK; no repeated setup after success |

Record any departure from the base expectation rather than assuming reproduction.
Compare packet ports and all retained keys. A candidate pass applies only to the
recorded model, firmware and exact revision; the synthetic test's short reply
does not establish which fields a real firmware will return.

## Error and timeout checks

- After discovery, suppress the response to one explicit broad query at the
  test network/harness boundary while allowing SDK timer processing to continue.
  Record one timeout callback, a null response, and no automatic retransmission
  of that public query. The source default timeout is 1000 ms; timer scheduling
  adds latency, so record actual elapsed time. Require completion within the
  five-second observation window.
- Restore responses and issue a new explicit query. It must succeed. If the
  harness can safely inject a delayed/duplicate captured ACK for the original
  sequence, it must not cause a second completion. Otherwise report that case
  as covered only by deterministic tests, not hardware.
- On a supported test setup, issue a single explicit IMU-range operation only
  with values whose meaning and restorability have been verified for that
  firmware. Record the actual device result, including `0x20` and its error key
  if rejected. Do not count transport success as device acceptance, assume the
  setter is supported, or change sensor settings merely to obtain a passing
  test. If a safe explicit-control test is unavailable, leave it pending.
- Distinguish explicit queries from automatic view discovery: a later discovery
  response can trigger another information read while setup is incomplete.
  The patch does not change that existing behavior or promise a global retry
  limit across discovery events. Verify no immediate recursive retry and no
  repeated setup after successful configuration.

## Evidence record

Report `PASS`, `FAIL` or `NOT RUN` separately for the base reproduction,
candidate ordinary read, repeatability, view setup, timeout, late/duplicate ACK,
and optional explicit-control check. Include exact source and binary identities,
environment, firmware, per-call counts/status/codes/elapsed times, retained-key
comparison and a redacted summary. Keep raw evidence privately with its hash,
owner and retention location. Do not infer macOS, Windows, ARM, other firmware,
other devices or consumer qualification from a Linux unit-test pass.

If the candidate fails, retain the evidence and stop adoption. The removal can
be reverted as a new reviewed change, or a consumer can remain on its previous
immutable pin; published history must not be rewritten.

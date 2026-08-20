# POC-AUDIO-PERF-2026-001 evidence index

Status: `TEST PACKET PREPARED — PI EVIDENCE PENDING`

This index will retain the reviewed, sanitized result of the VAD-label-bounded
small-Q8 investigation. Raw derived WAVs, VAD labels, worker logs and JSON
reports remain in the external controlled evidence location and are identified
here only by checksum.

Required closure fields:

- branch and full tested implementation SHA;
- source/model/binary/build-report identities;
- frozen VAD-label, source-fixture and derived-input-manifest checksums;
- generic/native build flags and one-variable comparison;
- one/two/four-thread screening with task/core/frequency/thermal observations;
- two complete 50-fixture hot cycles for the selected four-thread profile;
- quality, controller/native/CPU time, input/speech duration, RTF and RSS;
- offline, no-capture/no-playback and cleanup proof;
- retained historical Q8 comparison and reviewed recommendation.

No result is claimed until the external evidence is complete and reviewed.

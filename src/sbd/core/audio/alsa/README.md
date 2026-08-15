# M3 Audio Option A

This backend is the selected P4 baseline recorded by
`DELIVERY-AUDIO-POC-M3-P4-ACK-004`:

- `pyalsaaudio==0.11.0`, PSF-2.0, direct `hw:` devices only;
- `samplerate==0.2.4`, MIT, stateful `sinc_best` at 1:3;
- capture: 48 kHz stereo S32_LE, channel 0, signed 24-bit MSB-aligned data;
- output: 16 kHz mono S16_LE, exactly 320 samples / 640 bytes / 20 ms;
- ALSA period/buffer: 960 frames × 4 with one bounded blocking worker per
  capture or playback owner.

Use [requirements/rpi-audio-option-a.txt](../../../../../requirements/rpi-audio-option-a.txt)
on the Pi clean-build flow.  Its source hashes identify the selected sdists;
retain the P4-required PSF-2.0, MIT, BSD-3-Clause, and BSD-2-Clause notices in
the Pi evidence packet.  Do not commit Pi wheels, binaries, raw PCM, or local
device configuration.

The host test exercises the actual `sinc_best` anti-alias path.  RPi cards
remain authoritative for direct device negotiation, audible playback, xrun,
latency, thermals, cancellation and resource ownership.

# SSD1351 native adapter

`driver.py` is the Core wrapper for the accepted Display ABI v1.  It owns the
Python back buffer and invokes one `display_present_rgb565()` per `show()`;
`clear()` and `write_pixels()` never access hardware.  The native artifact is
target-local and must never be added to this repository.

## Target Pi procedure

1. Obtain the accepted POC source at exact SHA
   `5c2b6ba532a2661d5db79e27736e79890931515f`.  Verify its manifest, public
   `display.h`, license/NOTICE, and source identity before building.
2. On the Pi 5 only, run the accepted clean build from its source tree:

   ```bash
   cd src/sbd/core/display/native/waveshare_ssd1351
   make clean
   make
   sha256sum libdisplay.so
   ldd -r libdisplay.so
   ```

   `ldd -r` must have no unresolved symbols.  The produced `.so` remains
   outside Core Git; record its SHA-256 and custody path in the evidence card.
3. Put the artifact path and checksum only in the sanitized Pi-local config.
   The selected fixture is `/dev/spidev0.0`, mode 0, 4 MHz, CE0, DC BCM24,
   RST BCM25, `gpio_chip_index` resolved by the operator, 128x128 RGB565
   MSB-first, and rotation 0.  CE0 is kernel-managed; the adapter maps it to
   ABI `pins.cs = -1` and never claims it as GPIO.
4. Run the six `M3-DSPI-*` cards on the exact Core delivery SHA.  Their Pi
   evidence—not host stubs—decides start/present/stop/reopen, fallback,
   orientation/color/flicker, and latency acceptance.

The host test builds a temporary ABI stub solely to verify ctypes layout and
status handling.  It is not a display artifact or hardware evidence.

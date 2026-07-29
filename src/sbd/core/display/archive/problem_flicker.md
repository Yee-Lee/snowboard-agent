# Display flicker investigation

## Scope

- Platform: Raspberry Pi 5 with Raspberry Pi OS.
- Observed hardware: Waveshare 1.5-inch RGB OLED (SSD1351, 128 x 128, SPI).
- Reproduction: `src/sbd/core/display/driver/waveshare_oled_1in5_rgb/test_fade.py`.
- Observation method: 60 FPS phone video.  The fade animation shows flicker.

The 2-inch ST7789 LCD variants remain relevant to the shared architecture, but LCD backlight PWM and TE synchronization are not the primary suspects for the currently reported OLED result.

## Current data path

```text
Pillow Image (RGB888)
  -> Python bytes
  -> ctypes push_frame()
  -> C RGB888-to-RGB565 conversion
  -> SSD1351 GRAM full-frame SPI write
```

`test_fade.py` requests 60 FPS.  The driver sends `128 * 128 * 2 = 32,768` bytes per frame through an SPI interface configured for 20 MHz.  The ideal wire time alone is approximately 13.1 ms per frame; conversion, eight SPI writes, Python rendering, and scheduling consume the remaining part of the 16.7 ms frame budget.  A stable 60 FPS is therefore not guaranteed.  The 120 FPS star-field tests are infeasible on this path.

## Likely OLED causes to separate experimentally

1. **Unstable application frame pacing**: full-frame transfers occasionally miss their intended 16.7 ms deadline.
2. **Unsynchronised GRAM writes**: a new frame may be written while the controller scans the previous frame, producing visible temporal artifacts in video.
3. **OLED controller timing/current settings**: display clock, phase length, precharge, and contrast are hard-coded in `OLED_1in5_rgb.c`; they need controlled A/B testing against the SSD1351/module specification.
4. **RGB565 fade quantisation**: linear RGB888 blending followed by RGB565 truncation produces conspicuous low-luminance steps, which can be perceived as flicker.
5. **Power integrity**: OLED current changes strongly during full-screen fade; a weak 3.3 V/5 V supply, long jumper wires, or insufficient local decoupling can cause global brightness variation.

## Improvements: native driver

1. Add monotonic timing and instrumentation around every `push_frame`: report p50/p95/p99 conversion time, SPI-write time, and end-to-end frame interval.
2. Keep an RGB565 framebuffer in persistent memory; avoid allocating a full conversion buffer on each call.
3. Add a rectangle API such as `push_rect_rgb565(x, y, width, height, buffer)`, using SSD1351 column/row address commands.  Do not write anything for an unchanged frame.
4. Keep full-frame updates for full-screen fade, but initially cap them at a measured stable 30 FPS; evaluate 45 FPS only after timing data confirms adequate margin.
5. Add a native RGB565 entry point so the application can avoid an RGB888-to-RGB565 conversion at every frame boundary.
6. Test controller clock, phase/precharge, contrast, and current settings one variable at a time.  Do not copy LCD backlight/TE remedies to this OLED.

## Improvements: Python rendering and scheduling

1. Use `time.monotonic_ns()` and absolute deadlines rather than repeated relative `time.sleep()` calls.  When late, drop obsolete frames and render/send only the newest state.
2. Set the fade test to 30 FPS first.  Animation state may still be calculated from continuous elapsed time, so lowering output FPS does not slow the overall three-second fade.
3. Apply gamma-correct blending before RGB565 quantisation; optionally apply temporal/spatial dithering only after timing stability is established.
4. Reuse canvases/layers.  For text, cursor, and small animated objects, calculate a dirty bounding box and call the rectangle API.
5. Explicitly define ctypes signatures for `init_display`, `push_frame`, and `close_display`.

## Luma evaluation

The Luma Python libraries are an alternative Python device layer, not a replacement for the SSD1351 controller or its physical SPI constraints.  A Luma SSD1351 device normally communicates through Python SPI/GPIO backends rather than this repository's `libdisplay.so`; adopting it would generally replace the current ctypes/C wrapper, not use it underneath.

Luma may simplify Pillow integration and driver selection, but it will not by itself provide panel scan synchronization, eliminate RGB565 bandwidth, fix OLED timing registers, or solve power ripple.  If it performs full-frame Python-level writes, it may have less timing headroom than the current C transfer path.  It should therefore be evaluated as a small A/B prototype with the same 30 FPS fade and timing measurements, not adopted as the primary flicker fix.

## Verification sequence

1. Film a static black, grey, and white frame at 60 FPS.  If brightness still varies, investigate controller settings and power before animation code.
2. Run the existing fade at measured 30 FPS, then at 45 and 60 FPS; log actual frame intervals.
3. Repeat with controller settings changed one group at a time.
4. Compare the current native driver and a minimal Luma prototype under the same scene, SPI rate, output FPS, and power wiring.
5. Consider the change successful only if the camera recording and visual inspection both show no periodic brightness variation and the p99 frame interval stays within the selected frame period.

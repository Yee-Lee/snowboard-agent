# M7D1 static sketches

Draft design artifacts only; no Pi/OLED verification or Core integration claim.

- Hierarchy: Style → Theme → Scene.
- STYLE-01: text-only StatusBar; STYLE-02: icon + text StatusBar.
- THM-baseline, name `baseline`: Core baseline colors, fonts and sizes; provisional procedural icons for STYLE-02.
- USER reviewed this sheet without requested changes and assigned the theme name `baseline`; both Style candidates remain available. This is workstation design feedback, not physical-panel assessment or Core acceptance.
- Eight native 128×128 PNGs: both styles × idle, tool, speak and error.
- Second batch: 14 additional native 128×128 PNGs covering boot, wake, perception (empty/text), think, accepted interrupt and shutdown in both styles.
- [Comparison sheet](comparison.png): nearest-neighbor 2× enlargement; gray surround and labels are review framing, not product pixels.
- [Second comparison sheet](comparison_remaining.png): the same framing for the remaining six scenes. Both boot/shutdown styles are identically black.
- All example text is synthetic; tool name and error wording are fixtures, not adopted registry/error-owner values.

## Method and limits

Workstation raster sketches use Pillow 12.3.0 with Noto Sans TC 2.004 Regular/Medium.
Font bytes were compared with Core baseline `80d79d6c74ff93a40a018a03529c275287f2693e`
at this deliberate sketch boundary. Font licensing/source metadata remain in that baseline's
`docs/display_spec.md` §2.3; no font binaries are copied into this directory.

Canvas, safe rectangles, divider and theme values follow the D1 document. Text wraps by measured glyph width
within 120 px, with 20 px Main line height and a five-line limit. These short fixtures do not exercise
overflow, missing glyphs, privacy, stale filtering or failure behavior. Typeface positioning and
antialiasing are workstation sketch choices, not a claim of pixel equivalence with Core's renderer.

The Speak fixture shows punctuation at the beginning of a line under simple width wrapping. Whether to
recommend punctuation-aware wrapping is an open design question requiring Core baseline review and evidence.
No extra wrapping rule is adopted by these sketches.

Icons are provisional small geometric shapes. Physical readability, theme fit, SPI cost and burn-in
protection remain unmeasured. Runtime switching is not implemented. The drawing helper was disposable
workstation tooling; these images are documentation, not delivery-intended runtime code or retained product assets.

Second-batch state fixtures use the exact baseline labels. Think retains the preceding valid Perception
fixture; wake shows a case with empty backing Main. Interrupt shows an accepted interruption while state is
still ACTION, not a new state or a promise that this combination always occurs. Perception bars are static
geometric marks, not a live waveform. Boot/shutdown native images were checked to contain only black pixels.

After this batch, USER selected an animated hourglass beside「思考中」in the StatusBar. The STYLE-02 SCN-05
three-dot image is an earlier draft superseded by that decision; it has not yet been redrawn. Hourglass
appearance/cycle are still under discussion; these static PNGs contain no animation.

The theme ID is now `THM-baseline`; native filenames use this ID. Existing comparison-sheet headers still
show the earlier `THEME-01` label. Image bytes are unchanged; both labels refer to the same baseline theme.
Animation ANI-001 identifies thinking hourglass across themes. THM-baseline gives it a flip-only design;
another theme may give the same ANI-001 different appearance/motion. Details are described in D1.

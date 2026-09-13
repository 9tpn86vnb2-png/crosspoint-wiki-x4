from pathlib import Path
import hashlib

path = Path('freeink-sdk/libs/hardware/BatteryMonitor/src/BatteryMonitor.cpp')
text = path.read_text()
start_marker = '// Standard 1S Li-ion / LiPo (4.20 V) rest-voltage discharge curve'
start = text.find(start_marker)
if start < 0:
    raise SystemExit('BatteryMonitor curve marker not found')
fn = text.find('uint16_t BatteryMonitor::percentageFromMillivolts(uint16_t millivolts) {', start)
if fn < 0:
    raise SystemExit('BatteryMonitor percentage function not found')
fn2 = text.find('uint16_t BatteryMonitor::percentageFromMillivolts(uint16_t millivolts, uint16_t previousPercent) {', fn)
if fn2 < 0:
    raise SystemExit('BatteryMonitor hysteresis function not found')
# This exact SDK revision ends with the overload. Find its balanced closing brace.
def function_end(source, pos):
    brace = source.find('{', pos)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == '{': depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return i + 1
    raise SystemExit('unterminated BatteryMonitor function')
end = function_end(text, fn2)
replacement = r'''// 4.4.0 X4 battery display curve. Keep the proven Li-ion anchor points, but
// interpolate between them instead of quantizing the UI into 10% notches.
// The original X4 is an ADC/divider board, so this gives the user the resolution
// the hardware is already measuring without pretending that an ADC reading is a
// fuel-gauge coulomb count.
//
// A small full-charge hold band absorbs the normal voltage relaxation/load sag
// immediately after unplugging. 4.17 V still represents a near-full 1S cell;
// below that point the display follows the measured curve one percent at a time.
constexpr uint16_t LIION_CURVE_MV[11] = {
    3450,  //   0%
    3680,  //  10%
    3740,  //  20%
    3770,  //  30%
    3790,  //  40%
    3820,  //  50%
    3870,  //  60%
    3920,  //  70%
    3980,  //  80%
    4060,  //  90%
    4170,  // 100% display anchor under normal reader load
};

constexpr uint16_t PERCENT_HYSTERESIS_MV = 4;

uint16_t BatteryMonitor::percentageFromMillivolts(uint16_t millivolts) {
  if (millivolts <= LIION_CURVE_MV[0]) return 0;
  if (millivolts >= LIION_CURVE_MV[10]) return 100;
  for (uint8_t i = 1; i <= 10; ++i) {
    if (millivolts > LIION_CURVE_MV[i]) continue;
    const uint16_t low = LIION_CURVE_MV[i - 1];
    const uint16_t high = LIION_CURVE_MV[i];
    const uint16_t span = high - low;
    const uint16_t within = millivolts - low;
    const uint16_t tenths = static_cast<uint16_t>((uint32_t(within) * 10u + span / 2u) / span);
    return static_cast<uint16_t>(std::min<unsigned>(100u, unsigned(i - 1) * 10u + tenths));
  }
  return 100;
}

uint16_t BatteryMonitor::percentageFromMillivolts(uint16_t millivolts, uint16_t previousPercent) {
  const uint16_t current = percentageFromMillivolts(millivolts);
  if (previousPercent > 100 || current == previousPercent) return current;

  // Apply the deadband in voltage space, but keep the full 1% resolution. This
  // prevents a value sitting on a percent boundary from flickering on refreshes.
  const int32_t bias = current > previousPercent ? -PERCENT_HYSTERESIS_MV : PERCENT_HYSTERESIS_MV;
  const int32_t guardedMv = std::clamp<int32_t>(static_cast<int32_t>(millivolts) + bias, 0, UINT16_MAX);
  const uint16_t guarded = percentageFromMillivolts(static_cast<uint16_t>(guardedMv));
  if (current > previousPercent && guarded <= previousPercent) return previousPercent;
  if (current < previousPercent && guarded >= previousPercent) return previousPercent;
  return current;
}'''
new_text = text[:start] + replacement + text[end:]
path.write_text(new_text)
print('Patched', path)
print('SHA256', hashlib.sha256(new_text.encode()).hexdigest())

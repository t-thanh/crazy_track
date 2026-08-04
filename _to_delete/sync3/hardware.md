# 2026-08-04 — First hardware flights: three circle tests (Crazyflie 2.1 brushless + Lighthouse)

Raw logs and a re-runnable analysis are now in the repo:
`data/flights/2026-08-03/*.csv`, `scripts/analyze_flight_logs.py`
(figures regenerate into `data/flights/2026-08-03/analysis/`).

## What was flown
Same reference in all three runs: circle **r = 0.500 m, T = 4.0 s**
(|v| = 0.79 m/s), logged at 50 Hz, telemetry age 6–18 ms. Only the centre and
altitude differ (0.50 / 0.80 / 0.76 m). All three ran a **43-dimensional DATT
observation**; the layout was verified against the logged state
(obs[0:3] = ref−pos, [3:6] = vel, [6:10] = quat xyzw, [40:43] = L1 estimate;
max deviation 0.0000).

| | 15:09 | 15:13 | 15:21 |
|---|---|---|---|
| airborne | 4.5 s | 8.0 s | 14.7 s |
| RMSE_3D | 0.82 m | **0.44 m** | 0.86 m |
| median error | 0.80 | 0.31 | 0.70 |
| actual radius (cmd 0.50) | 0.94 ± 0.33 | 0.58 ± 0.13 | 0.80 ± 0.37 |
| altitude vs command | −0.17 m | −0.28 m | −0.11 m |
| laps | 1.1 | 2.0 | 3.7 |

**Tracking error is the same order as the circle radius.** Only 15:13
resembles a circle.

## Mechanism: the actuator is saturated, not regulating
- **Attitude.** The policy requests mean |roll| of 79° / 53° / 72°, pinned at
  exactly ±90° for 37–76 % of samples; the vehicle is hard-clipped to **±15°**.
  Roll or pitch sits *at* that clip for **92 / 84 / 97 %** of airborne samples,
  switching between the rails.
- **Thrust.** At one of its two rails for **86 / 96 / 88 %** of samples, at
  maximum for 57–89 %, while the vehicle still hangs 11–28 cm below its
  commanded altitude. Commanded PWM never exceeds 59–67 % of full scale.

## Two candidate root causes (for the next bench session, not yet tested)
1. **The reference starts far from the vehicle.** Position error at takeoff is
   already 0.51 / 0.82 / 0.81 m — the circle runs from t = 0 while the vehicle
   is on the ground, so the policy's first observation is 10–20× outside its
   training distribution and it rails immediately. Starting the reference at
   the current position, or ramping it in over ~1 s, is the cheapest test.
2. **The ±15° attitude clip contradicts the training envelope** (~40° in sim).
   A 0.5 m / 4 s circle needs more lateral acceleration than 15° of tilt
   provides, so even a well-behaved policy could not close the loop.

## Data-quality defect in the logger
The 15:09 and 15:13 files have a **truncated header**: 45 column names
(obs_0..obs_12) against 75 fields per data row (obs_0..obs_42), the same
physical layout as the complete 15:21 header. Parsing them by their own header
silently shifts every column after obs_12 — the actuator and command columns
would read observation values. The analysis script uses the 15:21 header as
canonical for all three and asserts the row width; worth fixing at the source.

## Relation to the paper
Nothing here enters paper 1: the manuscript's hardware section is
pre-registered around a wind-tunnel campaign with three falsification targets,
and these are pre-campaign bring-up flights whose limiting factor is a command
clip, not a controller property. They are recorded because they establish the
logging pipeline and because the saturation finding changes what the campaign
must configure before it can measure anything.

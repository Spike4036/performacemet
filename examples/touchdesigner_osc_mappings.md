# TouchDesigner OSC Mappings

Target host: `127.0.0.1`

Target port: `7000`

Primary addresses:

- `/engagement` -> particle brightness
- `/stress` -> volumetric glow turbulence or noise strength
- `/interest` -> attention field density
- `/relaxation` -> image stabilization or particle damping
- `/excitement` -> particle speed or bloom intensity

Aggregate packet:

- `/cognitive_state`
- Payload order: `timestamp, engagement, stress, interest, relaxation, excitement, attention`

Suggested TouchDesigner setup:

1. Add an `OSC In CHOP` listening on port `7000`.
2. Route scalar channels directly from `/engagement`, `/stress`, `/interest`, `/relaxation`, `/excitement`.
3. Use `Math CHOP` for per-channel remapping into TD-friendly ranges.
4. Use `Lag CHOP` or `Filter CHOP` if you want softer temporal smoothing for visuals.

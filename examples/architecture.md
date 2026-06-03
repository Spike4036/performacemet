# Bridge Architecture

## Data flow

`Insight 5 -> Cortex API websocket -> bridge.py -> parser -> CSV / OSC / future diffusion mappings`

## Runtime responsibilities

- `bridge.py`
  - Owns websocket lifecycle, `authorize()`, `createSession()`, headset discovery, subscription, reconnect loop.
- `emotiv_bridge/metrics_parser.py`
  - Converts `met/dev/eq` samples into a normalized cognitive state object.
- `emotiv_bridge/csv_logger.py`
  - Appends reusable CSV rows in the required format.
- `emotiv_bridge/osc_sender.py`
  - Emits low-latency OSC packets for TouchDesigner.
- `emotiv_bridge/diffusion_mapping.py`
  - Holds future StreamDiffusion / Stable Diffusion mapping placeholders.

## Streams

- Required runtime streams: `met`, `dev`
- Optional quality stream: `eq`

## Cognitive state schema

```python
{
    "timestamp": 1759225262.5052,
    "engagement": 0.72,
    "stress": 0.31,
    "interest": 0.58,
    "relaxation": 0.66,
    "excitement": 0.41,
    "long_term_excitement": 0.37,
    "attention": 0.63,
    "battery_percent": 0.94,
    "signal": 1.0,
    "overall_contact": 0.86,
    "headset_on": True,
    "sample_rate_quality": 0.99,
}
```

# EMOTIV Cognitive Streaming Bridge

This bridge streams real-time cognitive parameters from an EMOTIV Insight 5 headset through the Cortex websocket API into OSC and CSV outputs.

Current stream architecture:

- `met` for slower cognitive state
- `pow` for faster band-power modulation
- `dev` and `eq` for signal health gating

If you want high-resolution `met` (about 2 Hz), the Cortex session must be created as `active`, and your app/license must include the `pm` scope. Otherwise Cortex falls back to low-resolution `met` at about `0.1 Hz`.

If Cortex returns `-32019 Session limit has been reached`, set `EMOTIV_AUTHORIZE_DEBIT=1` (or higher) in `.env`. Cortex uses this debit value to increase the local session quota for activated sessions.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create your local env file:

```bash
cp .env.example .env
```

3. Edit `.env` and set:

- `EMOTIV_CLIENT_ID`
- `EMOTIV_CLIENT_SECRET`
- `EMOTIV_ID` (optional metadata; not required by the current token flow)

4. Start the bridge:

```bash
python3 bridge.py
```

## Run In VS Code

1. Open `/Users/sy/Emotiv headst` in VS Code.
2. Make sure the Python extension is installed.
3. Keep your credentials in `.env`.
4. Open `Run and Debug`.
5. Select `Run EMOTIV Bridge`.
6. Press `F5`.

You can also run it in the VS Code terminal:

```bash
python3 bridge.py
```

## Clear Previous Data

If you want to clear the existing CSV before a new run:

```bash
python3 clear_metrics.py
```

## Current OSC outputs

- `/engagement`
- `/stress`
- `/interest`
- `/relaxation`
- `/excitement`
- `/pow/theta`
- `/pow/alpha`
- `/pow/beta`
- `/pow/gamma`
- `/cognitive_state`

## Notes

- The current implementation uses Cortex websocket auth with `client_id` and `client_secret`.
- `EMOTIV_ID` is stored for operator identity and future extensions, but Cortex `authorize` in this bridge does not require the username directly.

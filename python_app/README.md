# gdigi Python App (Windows-friendly)

This folder contains a standalone Python MIDI UI app.

It is separate from the legacy C/GTK Linux app and does **not** require compiling gdigi.

## Requirements

- Python 3.9+
- MIDI packages:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
python app.py
```

## What it does

- Select a MIDI output port
- Build DigiTech SysEx messages
- Optionally apply gdigi-compatible 7-bit payload packing
- Send the message to the selected MIDI output

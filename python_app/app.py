#!/usr/bin/env python3
"""Simple Windows-friendly UI for sending DigiTech SysEx messages over MIDI."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

try:
    import mido
except ImportError:  # pragma: no cover
    mido = None


def parse_hex_byte(value: str, field_name: str) -> int:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} is required")

    if value.lower().startswith("0x"):
        value = value[2:]

    parsed = int(value, 16)
    if not 0 <= parsed <= 0xFF:
        raise ValueError(f"{field_name} must be a byte (00-FF)")
    return parsed


def parse_hex_payload(payload: str) -> list[int]:
    payload = payload.strip()
    if not payload:
        return []

    parsed = []
    for token in payload.replace(",", " ").split():
        parsed.append(parse_hex_byte(token, "Payload byte"))
    return parsed


def pack_data(data: list[int]) -> list[int]:
    packed: list[int] = []
    status = 0
    status_pos = 0

    for i, byte in enumerate(data):
        if (i % 7) == 0:
            if packed:
                packed[status_pos] = status
            status = 0
            status_pos = len(packed)
            packed.append(0)

        packed.append(byte & 0x7F)
        status |= (byte & 0x80) >> ((i % 7) + 1)

    if packed:
        packed[status_pos] = status
    return packed


def checksum(data: list[int]) -> int:
    result = 0
    for byte in data:
        result ^= byte
    return result & 0xFF


def build_message(
    device_id: int,
    family_id: int,
    product_id: int,
    procedure: int,
    payload: list[int],
    should_pack: bool,
) -> list[int]:
    body = [0x00, 0x00, 0x10, device_id, family_id, product_id, procedure]
    body.extend(pack_data(payload) if should_pack else payload)
    body.append(checksum(body))
    return [0xF0, *body, 0xF7]


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("gdigi Windows MIDI Sender")
        self.root.resizable(False, False)

        frm = ttk.Frame(root, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="MIDI Output Port").grid(row=0, column=0, sticky="w")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(frm, textvariable=self.port_var, width=48, state="readonly")
        self.port_combo.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(2, 8))

        ttk.Button(frm, text="Refresh Ports", command=self.refresh_ports).grid(row=1, column=4, padx=(8, 0))

        self.device_var = tk.StringVar(value="7F")
        self.family_var = tk.StringVar(value="7F")
        self.product_var = tk.StringVar(value="7F")
        self.procedure_var = tk.StringVar(value="01")

        ttk.Label(frm, text="Device ID").grid(row=2, column=0, sticky="w")
        ttk.Label(frm, text="Family ID").grid(row=2, column=1, sticky="w")
        ttk.Label(frm, text="Product ID").grid(row=2, column=2, sticky="w")
        ttk.Label(frm, text="Procedure").grid(row=2, column=3, sticky="w")

        ttk.Entry(frm, textvariable=self.device_var, width=10).grid(row=3, column=0, sticky="ew")
        ttk.Entry(frm, textvariable=self.family_var, width=10).grid(row=3, column=1, sticky="ew")
        ttk.Entry(frm, textvariable=self.product_var, width=10).grid(row=3, column=2, sticky="ew")
        ttk.Entry(frm, textvariable=self.procedure_var, width=10).grid(row=3, column=3, sticky="ew")

        ttk.Label(frm, text="Payload bytes (hex, space/comma separated)").grid(
            row=4, column=0, columnspan=5, sticky="w", pady=(10, 0)
        )
        self.payload_text = tk.Text(frm, width=64, height=6, wrap="char")
        self.payload_text.grid(row=5, column=0, columnspan=5, pady=(2, 8), sticky="ew")

        self.pack_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frm,
            text="Pack payload like gdigi C sender (7-bit packing)",
            variable=self.pack_var,
        ).grid(row=6, column=0, columnspan=5, sticky="w")

        ttk.Button(frm, text="Send SysEx", command=self.send_message).grid(row=7, column=0, columnspan=5, pady=(10, 0))

        self.last_message_var = tk.StringVar(value="Last message: (none)")
        ttk.Label(frm, textvariable=self.last_message_var, wraplength=520).grid(
            row=8, column=0, columnspan=5, sticky="w", pady=(10, 0)
        )

        for col in range(5):
            frm.columnconfigure(col, weight=1)

        self.refresh_ports()

    def refresh_ports(self) -> None:
        ports = mido.get_output_names()
        self.port_combo["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0])

    def send_message(self) -> None:
        port_name = self.port_var.get().strip()
        if not port_name:
            messagebox.showerror("Missing port", "Select a MIDI output port first.")
            return

        try:
            payload = parse_hex_payload(self.payload_text.get("1.0", "end"))
            message_bytes = build_message(
                device_id=parse_hex_byte(self.device_var.get(), "Device ID"),
                family_id=parse_hex_byte(self.family_var.get(), "Family ID"),
                product_id=parse_hex_byte(self.product_var.get(), "Product ID"),
                procedure=parse_hex_byte(self.procedure_var.get(), "Procedure"),
                payload=payload,
                should_pack=self.pack_var.get(),
            )
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        try:
            with mido.open_output(port_name) as out_port:
                out_port.send(mido.Message.from_bytes(message_bytes))
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Send failed", str(exc))
            return

        rendered = " ".join(f"{b:02X}" for b in message_bytes)
        self.last_message_var.set(f"Last message: {rendered}")
        messagebox.showinfo("Sent", f"Sent SysEx to {port_name}.")


def main() -> None:
    if mido is None:
        raise SystemExit("Missing dependency: install with `pip install -r requirements.txt`")

    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

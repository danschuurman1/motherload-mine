import json
import tkinter as tk
from tkinter import ttk, colorchooser
from pathlib import Path
from typing import Callable, Dict

COLORS_FILE = Path(__file__).parent.parent / "config" / "colors.json"

class ColorProfile:
    def __init__(self, r=0, g=0, b=0, tolerance=20, enabled=True):
        self.r = r
        self.g = g
        self.b = b
        self.tolerance = tolerance
        self.enabled = enabled

    def to_dict(self):
        return {"r": self.r, "g": self.g, "b": self.b, "tolerance": self.tolerance, "enabled": self.enabled}

    @staticmethod
    def from_dict(d):
        return ColorProfile(d.get("r", 0), d.get("g", 0), d.get("b", 0), d.get("tolerance", 20), d.get("enabled", True))

def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"

class ColorSlot(ttk.LabelFrame):
    def __init__(self, parent, label: str, profile: ColorProfile, on_change: Callable[[], None]) -> None:
        super().__init__(parent, text=label)
        self._profile = profile
        self._on_change = on_change
        self._updating = False
        self._build()
        self._refresh_swatch()

    def _build(self) -> None:
        self._enabled_var = tk.BooleanVar(value=self._profile.enabled)
        ttk.Checkbutton(self, text="Enabled", variable=self._enabled_var, command=self._commit).grid(row=0, column=0, columnspan=4, sticky="w", padx=4)

        self._swatch = tk.Label(self, width=4, height=2, relief="solid")
        self._swatch.grid(row=1, column=0, padx=4, pady=4)

        ttk.Button(self, text="Pick", command=self._pick_color).grid(row=1, column=1, padx=2)

        ttk.Label(self, text="Hex:").grid(row=1, column=2, sticky="e", padx=2)
        self._hex_var = tk.StringVar(value=_rgb_to_hex(self._profile.r, self._profile.g, self._profile.b))
        self._hex_entry = ttk.Entry(self, textvariable=self._hex_var, width=8)
        self._hex_entry.grid(row=1, column=3, padx=2)
        self._hex_entry.bind("<Return>", lambda _: self._apply_hex())

        self._r_var = tk.IntVar(value=self._profile.r)
        self._g_var = tk.IntVar(value=self._profile.g)
        self._b_var = tk.IntVar(value=self._profile.b)

        for i, (ch, var) in enumerate([("R", self._r_var), ("G", self._g_var), ("B", self._b_var)]):
            ttk.Label(self, text=ch).grid(row=2, column=i, sticky="e", padx=2)
            sb = ttk.Spinbox(self, from_=0, to=255, textvariable=var, width=5, command=self._commit)
            sb.grid(row=3, column=i, padx=2)
            var.trace_add("write", lambda *_: self._commit())

        ttk.Label(self, text="Tol:").grid(row=2, column=3, padx=2)
        self._tol_var = tk.IntVar(value=self._profile.tolerance)
        self._tol_scale = ttk.Scale(self, from_=0, to=50, variable=self._tol_var, orient="horizontal", length=80, command=lambda _: self._commit())
        self._tol_scale.grid(row=3, column=3, padx=2)

    def _apply_hex(self) -> None:
        raw = self._hex_var.get().strip().lstrip("#")
        if len(raw) != 6: return
        try:
            r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
            self._updating = True
            self._r_var.set(r); self._g_var.set(g); self._b_var.set(b)
            self._updating = False
            self._commit()
        except ValueError: pass

    def _pick_color(self) -> None:
        init = _rgb_to_hex(self._profile.r, self._profile.g, self._profile.b)
        result = colorchooser.askcolor(color=init, title="Pick color")
        if result and result[0]:
            r, g, b = (int(x) for x in result[0])
            self._updating = True
            self._r_var.set(r); self._g_var.set(g); self._b_var.set(b)
            self._updating = False
            self._commit()

    def _commit(self) -> None:
        if self._updating: return
        try:
            self._profile.r = self._r_var.get()
            self._profile.g = self._g_var.get()
            self._profile.b = self._b_var.get()
            self._profile.tolerance = self._tol_var.get()
            self._profile.enabled = self._enabled_var.get()
            self._refresh_swatch()
            self._on_change()
        except (tk.TclError, ValueError): pass

    def _refresh_swatch(self) -> None:
        hex_val = _rgb_to_hex(self._profile.r, self._profile.g, self._profile.b)
        self._swatch.configure(bg=hex_val)
        if not self._updating: self._hex_var.set(hex_val)

class TickerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Motherlode Mine Bot")
        self.root.geometry("400x600")
        self.colors = self._load_colors()
        self._build_ui()

    def _load_colors(self) -> Dict[str, ColorProfile]:
        if COLORS_FILE.exists():
            with open(COLORS_FILE, "r") as f:
                data = json.load(f)
                return {k: ColorProfile.from_dict(v) for k, v in data.items()}
        return {}

    def _save_colors(self):
        data = {k: v.to_dict() for k, v in self.colors.items()}
        with open(COLORS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True)

        # Colors Tab
        colors_tab = ttk.Frame(nb)
        nb.add(colors_tab, text="Colors")
        
        # Sub-notebook for color categories
        sub_nb = ttk.Notebook(colors_tab)
        sub_nb.pack(fill="both", expand=True, padx=5, pady=5)

        # Bank
        f_bank = ttk.Frame(sub_nb)
        sub_nb.add(f_bank, text="Bank")
        ColorSlot(f_bank, "Bank Chest", self.colors["bank_chest_color"], self._save_colors).pack(fill="x", padx=5, pady=5)

        # Ore
        f_ore = ttk.Frame(sub_nb)
        sub_nb.add(f_ore, text="Ore")
        ColorSlot(f_ore, "Active Ore", self.colors["ore_active_color"], self._save_colors).pack(fill="x", padx=5, pady=5)
        ColorSlot(f_ore, "Depleted Ore", self.colors["ore_depleted_color"], self._save_colors).pack(fill="x", padx=5, pady=5)

        # Infrastructure
        f_infra = ttk.Frame(sub_nb)
        sub_nb.add(f_infra, text="Infra")
        ColorSlot(f_infra, "Hopper", self.colors["hopper_color"], self._save_colors).pack(fill="x", padx=5, pady=5)
        ColorSlot(f_infra, "Ladder Ascend", self.colors["ladder_ascend_color"], self._save_colors).pack(fill="x", padx=5, pady=5)
        ColorSlot(f_infra, "Ladder Descend", self.colors["ladder_descend_color"], self._save_colors).pack(fill="x", padx=5, pady=5)

        # Collection
        f_coll = ttk.Frame(sub_nb)
        sub_nb.add(f_coll, text="Collection")
        ColorSlot(f_coll, "Sack", self.colors["sack_color"], self._save_colors).pack(fill="x", padx=5, pady=5)

        # Control Tab (Placeholder)
        control_tab = ttk.Frame(nb)
        nb.add(control_tab, text="Control")
        ttk.Label(control_tab, text="Motherlode Mine Bot Control").pack(pady=20)
        self.start_btn = ttk.Button(control_tab, text="Start Bot", command=self.toggle_bot)
        self.start_btn.pack()
        self.running = False

    def toggle_bot(self):
        self.running = not self.running
        self.start_btn.config(text="Stop Bot" if self.running else "Start Bot")

if __name__ == "__main__":
    root = tk.Tk()
    app = TickerGUI(root)
    root.mainloop()

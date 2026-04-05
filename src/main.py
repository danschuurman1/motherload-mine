import threading
import time
import subprocess
import tkinter as tk
from gui.ticker import TickerGUI
from logic.mining_behavior import MiningBot

class MotherlodeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.gui = TickerGUI(self.root)
        self.bot = MiningBot(self.gui.colors)
        
        self.bot_thread = None
        self.gui.toggle_bot = self.on_bot_toggle

    def get_runelite_window(self):
        """Query RuneLite window position and size on macOS."""
        try:
            cmd = 'tell application "System Events" to tell process "RuneLite" to get {position, size} of window 1'
            proc = subprocess.run(['osascript', '-e', cmd], capture_output=True, text=True)
            if proc.returncode == 0:
                parts = [v.strip() for v in proc.stdout.strip().split(',')]
                left, top, width, height = map(int, parts)
                # Adjust for title bar if necessary (OSRS fixed is 765x503)
                # Standard macOS title bar is ~22-25px
                title_bar_height = height - 503 if height > 503 else 0
                return left, top + title_bar_height, width, 503
        except Exception as e:
            print(f"Window detection error: {e}")
        return 0, 0, 800, 600 # Fallback

    def on_bot_toggle(self):
        if not self.gui.running:
            print("Stopping Bot...")
            self.gui.running = False
            self.gui.start_btn.config(text="Start Bot")
            self.bot.running = False
        else:
            print("Starting Bot...")
            self.gui.running = True
            self.gui.start_btn.config(text="Stop Bot")
            self.bot.running = True
            self.bot_thread = threading.Thread(target=self.bot_loop, daemon=True)
            self.bot_thread.start()

    def bot_loop(self):
        """Main state machine loop with dynamic window scaling."""
        while self.gui.running:
            # Update window context every iteration to handle movement/resize
            left, top, width, height = self.get_runelite_window()
            self.bot.set_window(left, top, width, height)
            
            if not self.bot.check_level():
                print("Waiting for upper level...")
                time.sleep(2)
                continue
            
            # Execute refined mining state
            success = self.bot.mine_ore()
            if not success:
                time.sleep(1)
        
        print("Bot loop terminated.")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MotherlodeApp()
    app.run()

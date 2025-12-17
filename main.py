import customtkinter as ctk
from PIL import ImageGrab
from pynput import mouse
import threading
import pyperclip

import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ColorPickerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Modern Color Picker")
        self.geometry("400x550")
        self.resizable(False, False)
        
        # Set icon
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        self.iconbitmap(icon_path)


        # Variables
        self.always_on_top = ctk.BooleanVar(value=False)
        self.current_hex = "Press Pick"
        self.current_rgb = "(0, 0, 0)"
        self.history = []  # List of hex codes
        self.listener = None

        # --- UI Layout ---
        self.create_widgets()

    def create_widgets(self):
        # 1. Header (Always on Top Switch)
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.top_switch = ctk.CTkSwitch(
            self.header_frame, 
            text="Always on Top", 
            command=self.toggle_topmost,
            variable=self.always_on_top,
            font=("Roboto Medium", 12)
        )
        self.top_switch.pack(side="right")

        # 2. Color Preview Area
        self.preview_frame = ctk.CTkFrame(self, fg_color="#333333", width=200, height=150, corner_radius=15)
        self.preview_frame.pack(pady=10)
        self.preview_frame.pack_propagate(False) # Don't shrink to fit children

        # 3. Color Info (Hex & RGB)
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(pady=10)

        self.hex_label = ctk.CTkButton(
            self.info_frame, 
            text="HEX: #-------", 
            font=("Roboto", 24, "bold"),
            fg_color="transparent",
            hover_color="#444444",
            command=lambda: self.copy_to_clipboard(self.current_hex)
        )
        self.hex_label.pack(pady=5)

        self.rgb_label = ctk.CTkButton(
            self.info_frame, 
            text="RGB: (---, ---, ---)", 
            font=("Roboto", 16),
            fg_color="transparent",
            hover_color="#444444",
            text_color="gray",
            command=lambda: self.copy_to_clipboard(self.current_rgb)
        )
        self.rgb_label.pack(pady=5)
        
        self.status_label = ctk.CTkLabel(self.info_frame, text="", text_color="#2CC985", font=("Roboto", 12))
        self.status_label.pack(pady=(0,5))

        # 4. Pick Button
        self.pick_btn = ctk.CTkButton(
            self, 
            text="PICK COLOR", 
            font=("Roboto", 16, "bold"),
            height=50,
            corner_radius=25,
            command=self.start_picking
        )
        self.pick_btn.pack(fill="x", padx=40, pady=20)

        # 5. History
        self.history_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.history_frame.pack(pady=10)
        self.history_label = ctk.CTkLabel(self.history_frame, text="History", font=("Roboto", 12))
        self.history_label.pack(pady=(0, 5))
        
        self.history_buttons_frame = ctk.CTkFrame(self.history_frame, fg_color="transparent")
        self.history_buttons_frame.pack()
        
        self.history_buttons = []
        for _ in range(5):
            btn = ctk.CTkButton(
                self.history_buttons_frame,
                text="",
                width=40,
                height=40,
                corner_radius=10,
                fg_color="#333333",
                state="disabled"
            )
            btn.pack(side="left", padx=5)
            self.history_buttons.append(btn)

    def toggle_topmost(self):
        self.attributes("-topmost", self.always_on_top.get())

    def start_picking(self):
        self.pick_btn.configure(text="Click anywhere...", state="disabled", fg_color="#555555")
        # Start mouse listener in a separate thread so it doesn't block GUI? 
        # Actually pynput listener is already threaded.
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.start()

    def on_click(self, x, y, button, pressed):
        if pressed and button == mouse.Button.left:
            # Color picking relies on taking a screenshot of the pixel
            # We must do this before stopping the listener or immediately after
            try:
                # Capture just the 1x1 pixel at x, y
                # Note: ImageGrab needs integer coordinates
                image = ImageGrab.grab(bbox=(x, y, x+1, y+1))
                color = image.getpixel((0, 0)) # Returns (r, g, b)
                
                # Update UI must be done on main thread usually, 
                # but tkinter is forgiving in simple cases, or we use after()
                self.after(0, self.update_color, color)
            except Exception as e:
                print(f"Error picking color: {e}")
            finally:
                self.listener.stop()
                self.after(0, self.reset_pick_button)

    def reset_pick_button(self):
        self.pick_btn.configure(text="PICK COLOR", state="normal", fg_color=("#3B8ED0", "#1F6AA5")) # Default theme colors

    def update_color(self, color):
        # color is (r, g, b)
        hex_code = '#{:02x}{:02x}{:02x}'.format(*color)
        rgb_str = str(color)

        self.current_hex = hex_code
        self.current_rgb = rgb_str

        # Update Preview
        self.preview_frame.configure(fg_color=hex_code)

        # Update Labels
        self.hex_label.configure(text=f"HEX: {hex_code.upper()}")
        self.rgb_label.configure(text=f"RGB: {rgb_str}")

        # Add to history
        self.add_to_history(hex_code, color)

    def add_to_history(self, hex_code, rgb_tuple):
        # Avoid duplicate consecutive entries if desired, but simple FIFO is requested
        if hex_code in self.history:
             self.history.remove(hex_code)
        
        self.history.insert(0, hex_code)
        if len(self.history) > 5:
            self.history.pop()
            
        self.refresh_history_ui()

    def refresh_history_ui(self):
        for i, btn in enumerate(self.history_buttons):
            if i < len(self.history):
                color = self.history[i]
                btn.configure(
                    fg_color=color, 
                    state="normal", 
                    command=lambda c=color: self.restore_from_history(c)
                )
            else:
                btn.configure(fg_color="#333333", state="disabled", command=None)

    def restore_from_history(self, hex_code):
        # Convert hex back to rgb for consistency
        h = hex_code.lstrip('#')
        rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        self.update_color(rgb)

    def copy_to_clipboard(self, text):
        if text and "---" not in text:
            pyperclip.copy(text)
            self.status_label.configure(text="Copied!")
            self.after(2000, lambda: self.status_label.configure(text=""))

if __name__ == "__main__":
    app = ColorPickerApp()
    app.mainloop()

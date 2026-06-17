import os
import sys

# Enable DPI awareness on Windows to prevent blurry text before importing tkinter
if sys.platform.startswith('win'):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 1 = System DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import subprocess
import threading
import queue
import re
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog
import traceback

class YtdlpDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("yt-dlp Downloader & Inspector")
        self.root.geometry("760x750")
        self.root.minsize(650, 600)
        
        # Determine directory of the application
        if getattr(sys, 'frozen', False):
            self.script_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.ytdlp_path = os.path.join(self.script_dir, "yt-dlp.exe")
        self.ffmpeg_dir = self.script_dir
        
        # Application state variables
        self.current_process = None
        self.log_queue = queue.Queue()
        self.last_line_was_cr = False
        
        # Set up GUI Layout & Styling
        self.setup_ui()
        
        # Start queue reader loop for thread-safe GUI updates
        self.process_queue_loop()
        
        # Proactively check for dependencies
        self.check_dependencies()

    def setup_ui(self):
        # Configure colors (Dark Catppuccin-inspired palette)
        self.bg_color = "#1e1e2e"       # Dark base
        self.bg_surface = "#313244"     # Dark slate
        self.bg_hover_surf = "#45475a"  # Lighter slate
        self.fg_color = "#cdd6f4"       # Light gray
        self.fg_dim = "#a6adc8"         # Dim gray
        self.fg_disabled = "#7f849c"    # Disabled text gray
        
        # Accent colors
        self.accent_blue = "#89b4fa"    # Soft blue
        self.accent_blue_hover = "#b4befe"
        self.accent_green = "#a6e3a1"   # Soft green
        self.accent_green_hover = "#b8f2b3"
        self.accent_purple = "#cba6f7"  # Soft purple
        self.accent_red = "#f38ba8"     # Soft red
        self.accent_red_hover = "#f5a9b8"
        self.terminal_bg = "#11111b"    # Dark terminal base

        self.root.configure(bg=self.bg_color)
        
        # Main Container Frame
        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # --- 1. Header Section ---
        header_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        header_frame.pack(fill="x", pady=(0, 15))
        
        title_lbl = tk.Label(
            header_frame, 
            text="yt-dlp Video Downloader", 
            font=("Segoe UI", 16, "bold"), 
            bg=self.bg_color, 
            fg=self.accent_blue
        )
        title_lbl.pack(anchor="w")
        
        desc_lbl = tk.Label(
            header_frame, 
            text="Download full videos, extract custom clips, or inspect formats using local binaries.", 
            font=("Segoe UI", 9), 
            bg=self.bg_color, 
            fg=self.fg_dim
        )
        desc_lbl.pack(anchor="w", pady=(2, 0))
        
        # --- 2. Input Link Section ---
        link_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        link_frame.pack(fill="x", pady=(0, 10))
        
        url_lbl = tk.Label(
            link_frame, 
            text="Video URL / Link:", 
            font=("Segoe UI", 10, "bold"), 
            bg=self.bg_color, 
            fg=self.fg_color,
            width=14,
            anchor="w"
        )
        url_lbl.pack(side="left")
        
        self.url_entry = tk.Entry(
            link_frame, 
            bg=self.bg_surface, 
            fg=self.fg_color, 
            insertbackground=self.fg_color, 
            relief="flat", 
            bd=5, 
            font=("Segoe UI", 10)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.focus_set()
        
        paste_btn = tk.Button(
            link_frame, 
            text="Paste URL", 
            command=self.paste_link, 
            bg=self.accent_green, 
            fg=self.terminal_bg, 
            activebackground=self.accent_green_hover, 
            activeforeground=self.terminal_bg, 
            relief="flat", 
            bd=0, 
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=3
        )
        paste_btn.pack(side="right")
        self.add_hover(paste_btn, self.accent_green, self.accent_green_hover)
        
        # --- 3. Save Folder Section ---
        save_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        save_frame.pack(fill="x", pady=(0, 15))
        
        save_lbl = tk.Label(
            save_frame, 
            text="Save Folder:", 
            font=("Segoe UI", 10, "bold"), 
            bg=self.bg_color, 
            fg=self.fg_color,
            width=14,
            anchor="w"
        )
        save_lbl.pack(side="left")
        
        self.save_entry = tk.Entry(
            save_frame, 
            bg=self.bg_surface, 
            fg=self.fg_color, 
            insertbackground=self.fg_color, 
            relief="flat", 
            bd=5, 
            font=("Segoe UI", 10)
        )
        self.save_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        # Set default save folder to the user's Downloads directory (fallback to script folder)
        default_save_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        if not os.path.exists(default_save_dir):
            default_save_dir = self.script_dir
        self.save_entry.insert(0, os.path.normpath(default_save_dir))
        
        browse_btn = tk.Button(
            save_frame, 
            text="Browse...", 
            command=self.browse_save_dir, 
            bg=self.bg_surface, 
            fg=self.fg_color, 
            activebackground=self.bg_hover_surf, 
            activeforeground=self.fg_color, 
            relief="flat", 
            bd=0, 
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=3
        )
        browse_btn.pack(side="right")
        self.add_hover(browse_btn, self.bg_surface, self.bg_hover_surf)
        
        # --- 4. Options Section ---
        options_frame = tk.LabelFrame(
            self.main_frame, 
            text=" Operations & Settings ", 
            font=("Segoe UI", 10, "bold"), 
            bg=self.bg_color, 
            fg=self.accent_purple, 
            bd=1, 
            relief="solid",
            padx=15,
            pady=10
        )
        options_frame.pack(fill="x", pady=(0, 15))
        
        self.mode_var = tk.StringVar(value="video")
        
        video_rb = tk.Radiobutton(
            options_frame, 
            text="Download Whole Video (MP4 up to 1080p)", 
            variable=self.mode_var, 
            value="video",
            command=self.on_mode_change,
            bg=self.bg_color, 
            fg=self.fg_color, 
            selectcolor=self.bg_surface, 
            activebackground=self.bg_color, 
            activeforeground=self.fg_color,
            font=("Segoe UI", 9)
        )
        video_rb.pack(anchor="w", pady=2)
        
        clip_rb = tk.Radiobutton(
            options_frame, 
            text="Download Video Clip (Extract custom timeframe)", 
            variable=self.mode_var, 
            value="clip",
            command=self.on_mode_change,
            bg=self.bg_color, 
            fg=self.fg_color, 
            selectcolor=self.bg_surface, 
            activebackground=self.bg_color, 
            activeforeground=self.fg_color,
            font=("Segoe UI", 9)
        )
        clip_rb.pack(anchor="w", pady=2)
        
        # Sub-frame for Clip Inputs (aligned under clip option)
        self.clip_frame = tk.Frame(options_frame, bg=self.bg_color)
        self.clip_frame.pack(fill="x", padx=20, pady=(4, 6))
        
        start_lbl = tk.Label(self.clip_frame, text="Start Time:", bg=self.bg_color, fg=self.fg_dim, font=("Segoe UI", 9))
        start_lbl.grid(row=0, column=0, sticky="w", padx=(0, 5))
        
        self.start_entry = tk.Entry(
            self.clip_frame, 
            bg=self.bg_color, 
            fg="#585b70", 
            disabledbackground=self.bg_color, 
            disabledforeground="#585b70",
            state="disabled",
            relief="flat", 
            bd=3, 
            font=("Segoe UI", 9),
            width=12
        )
        self.start_entry.insert(0, "00:12:30")
        self.start_entry.grid(row=0, column=1, padx=(0, 15))
        
        end_lbl = tk.Label(self.clip_frame, text="End Time:", bg=self.bg_color, fg=self.fg_dim, font=("Segoe UI", 9))
        end_lbl.grid(row=0, column=2, sticky="w", padx=(0, 5))
        
        self.end_entry = tk.Entry(
            self.clip_frame, 
            bg=self.bg_color, 
            fg="#585b70", 
            disabledbackground=self.bg_color, 
            disabledforeground="#585b70",
            state="disabled",
            relief="flat", 
            bd=3, 
            font=("Segoe UI", 9),
            width=12
        )
        self.end_entry.insert(0, "00:13:15")
        self.end_entry.grid(row=0, column=3)
        
        help_lbl = tk.Label(
            self.clip_frame, 
            text="Format: HH:MM:SS or MM:SS (e.g. 00:05:30)", 
            bg=self.bg_color, 
            fg=self.fg_dim, 
            font=("Segoe UI", 8, "italic")
        )
        help_lbl.grid(row=0, column=4, padx=(15, 0), sticky="w")
        
        # --- NEW: Custom Format Code Input Section ---
        format_frame = tk.Frame(options_frame, bg=self.bg_color)
        format_frame.pack(fill="x", padx=5, pady=(8, 4))
        
        format_lbl = tk.Label(
            format_frame, 
            text="Format Code (Optional):", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.bg_color, 
            fg=self.fg_color
        )
        format_lbl.pack(side="left", padx=(0, 10))
        
        self.format_entry = tk.Entry(
            format_frame, 
            bg=self.bg_surface, 
            fg=self.fg_color, 
            insertbackground=self.fg_color, 
            relief="flat", 
            bd=4, 
            font=("Segoe UI", 9),
            width=15
        )
        self.format_entry.pack(side="left", padx=(0, 10))
        
        clear_fmt_btn = tk.Button(
            format_frame, 
            text="Clear Format", 
            command=lambda: (self.format_entry.delete(0, tk.END), self.status_lbl.config(text="Status: Format Cleared", fg=self.accent_purple)), 
            bg=self.bg_surface, 
            fg=self.fg_color, 
            activebackground=self.bg_hover_surf, 
            activeforeground=self.fg_color, 
            relief="flat", 
            bd=0, 
            font=("Segoe UI", 8),
            padx=8,
            pady=1
        )
        clear_fmt_btn.pack(side="left")
        self.add_hover(clear_fmt_btn, self.bg_surface, self.bg_hover_surf)
        
        fmt_help_lbl = tk.Label(
            options_frame, 
            text="💡 Tip: Run 'Inspect Formats' first, then click any row in the console logs to auto-fill this code (e.g. 137+140).", 
            font=("Segoe UI", 8, "italic"), 
            bg=self.bg_color, 
            fg=self.accent_purple
        )
        fmt_help_lbl.pack(anchor="w", padx=5, pady=(2, 0))
        
        # --- 5. Actions Section (Separate Download & Inspect buttons) ---
        actions_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        actions_frame.pack(fill="x", pady=(0, 15))
        
        self.start_btn = tk.Button(
            actions_frame, 
            text="Download Video", 
            command=self.start_download, 
            bg=self.accent_green, 
            fg=self.terminal_bg, 
            activebackground=self.accent_green_hover, 
            activeforeground=self.terminal_bg, 
            relief="flat", 
            bd=0, 
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=6
        )
        self.start_btn.pack(side="left", padx=(0, 10))
        self.add_hover(self.start_btn, self.accent_green, self.accent_green_hover)
        
        self.inspect_btn = tk.Button(
            actions_frame, 
            text="Inspect Formats", 
            command=self.start_inspect, 
            bg=self.accent_blue, 
            fg=self.terminal_bg, 
            activebackground=self.accent_blue_hover, 
            activeforeground=self.terminal_bg, 
            relief="flat", 
            bd=0, 
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=6
        )
        self.inspect_btn.pack(side="left", padx=(0, 10))
        self.add_hover(self.inspect_btn, self.accent_blue, self.accent_blue_hover)
        
        self.stop_btn = tk.Button(
            actions_frame, 
            text="Cancel / Stop", 
            command=self.stop_action, 
            bg=self.fg_disabled, 
            fg=self.fg_color, 
            activebackground=self.accent_red_hover, 
            activeforeground=self.terminal_bg, 
            state="disabled",
            relief="flat", 
            bd=0, 
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=6
        )
        self.stop_btn.pack(side="left")
        self.add_hover(self.stop_btn, self.accent_red, self.accent_red_hover)
        
        clear_btn = tk.Button(
            actions_frame, 
            text="Clear Console Logs", 
            command=self.clear_logs, 
            bg=self.bg_surface, 
            fg=self.fg_color, 
            activebackground=self.bg_hover_surf, 
            activeforeground=self.fg_color, 
            relief="flat", 
            bd=0, 
            font=("Segoe UI", 9),
            padx=15,
            pady=5
        )
        clear_btn.pack(side="right")
        self.add_hover(clear_btn, self.bg_surface, self.bg_hover_surf)
        
        # --- 6. Progress Section ---
        status_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        status_frame.pack(fill="x", pady=(0, 4))
        
        self.status_lbl = tk.Label(
            status_frame, 
            text="Status: Ready", 
            bg=self.bg_color, 
            fg=self.accent_green, 
            font=("Segoe UI", 9, "bold")
        )
        self.status_lbl.pack(side="left")
        
        self.speed_lbl = tk.Label(
            status_frame, 
            text="", 
            bg=self.bg_color, 
            fg=self.fg_dim, 
            font=("Segoe UI", 9)
        )
        self.speed_lbl.pack(side="right")
        
        # Style the custom progressbar using ttk
        self.progress_var = tk.DoubleVar()
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure(
            "Custom.Horizontal.TProgressbar", 
            thickness=12, 
            troughcolor=self.bg_surface, 
            background=self.accent_blue, 
            bordercolor=self.bg_color, 
            lightcolor=self.accent_blue, 
            darkcolor=self.accent_blue
        )
        
        self.progress_bar = ttk.Progressbar(
            self.main_frame, 
            orient="horizontal", 
            variable=self.progress_var, 
            maximum=100,
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x", pady=(0, 15))
        
        # --- 7. Terminal Console Section ---
        console_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        console_frame.pack(fill="both", expand=True)
        
        console_lbl = tk.Label(
            console_frame, 
            text="Console Logs (Click on any format row below to select format):", 
            bg=self.bg_color, 
            fg=self.fg_color, 
            font=("Segoe UI", 9, "bold")
        )
        console_lbl.pack(anchor="w", pady=(0, 3))
        
        self.log_text = scrolledtext.ScrolledText(
            console_frame, 
            bg=self.terminal_bg, 
            fg=self.fg_color, 
            insertbackground=self.fg_color, 
            relief="flat", 
            font=("Consolas", 10)
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state="disabled")

        # Bind mouse clicks on terminal logs to auto-fill custom format code
        self.log_text.bind("<ButtonRelease-1>", self.on_console_click)

        # Configure Log Text Tags for live syntax highlighting
        self.log_text.tag_config("header", foreground="#89b4fa", font=("Consolas", 10, "bold"))  # Blue bold
        self.log_text.tag_config("audio", foreground="#f9e2af")                                  # Yellow
        self.log_text.tag_config("video", foreground="#89dceb")                                  # Sky/Cyan
        self.log_text.tag_config("warning", foreground="#fab387")                                # Orange/Peach
        self.log_text.tag_config("error", foreground="#f38ba8")                                  # Red
        self.log_text.tag_config("download", foreground="#a6e3a1")                               # Green
        self.log_text.tag_config("info", foreground="#cba6f7")                                   # Lavender

    def add_hover(self, widget, normal_bg, hover_bg):
        """Attaches dynamic visual highlights when mouse enters/leaves normal buttons."""
        def on_enter(e):
            if str(widget['state']) != 'disabled':
                widget.config(bg=hover_bg)
        def on_leave(e):
            if str(widget['state']) != 'disabled':
                widget.config(bg=normal_bg)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def set_buttons_running(self):
        """Disables action triggers and activates cancel buttons during processes."""
        self.start_btn.config(state="disabled", bg=self.fg_disabled, fg=self.fg_color)
        self.inspect_btn.config(state="disabled", bg=self.fg_disabled, fg=self.fg_color)
        self.stop_btn.config(state="normal", bg=self.accent_red, fg=self.terminal_bg)

    def set_buttons_idle(self):
        """Enables operational triggers and dims cancel buttons when idle."""
        self.start_btn.config(state="normal", bg=self.accent_green, fg=self.terminal_bg)
        self.inspect_btn.config(state="normal", bg=self.accent_blue, fg=self.terminal_bg)
        self.stop_btn.config(state="disabled", bg=self.fg_disabled, fg=self.fg_color)

    def check_dependencies(self):
        """Verifies if yt-dlp.exe is present in the workspace directory."""
        if not os.path.exists(self.ytdlp_path):
            self.write_log(f"⚠️ Dependency Error: yt-dlp.exe was not found in: {self.script_dir}\n", False)
            self.status_lbl.config(text="Status: yt-dlp missing!", fg=self.accent_red)
            messagebox.showerror(
                "Dependency Missing",
                f"Could not locate 'yt-dlp.exe' in the folder:\n{self.script_dir}\n\nPlease place the executable in the directory and reload."
            )
            self.start_btn.config(state="disabled", bg=self.fg_disabled, fg=self.fg_color)
            self.inspect_btn.config(state="disabled", bg=self.fg_disabled, fg=self.fg_color)

    def paste_link(self):
        """Pastes URL from the clipboard."""
        try:
            clipboard = self.root.clipboard_get()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard.strip())
        except Exception:
            pass  # Clipboard might be empty or invalid

    def browse_save_dir(self):
        """Opens a directory dialog box to change save destination."""
        current_dir = self.save_entry.get().strip()
        if not os.path.exists(current_dir):
            current_dir = self.script_dir
        selected_dir = filedialog.askdirectory(initialdir=current_dir, title="Select Download Directory")
        if selected_dir:
            selected_dir = os.path.normpath(selected_dir)
            self.save_entry.delete(0, tk.END)
            self.save_entry.insert(0, selected_dir)

    def on_mode_change(self):
        """Enables/disables clip parameters when switching operational modes."""
        mode = self.mode_var.get()
        if mode == "clip":
            self.start_entry.config(state="normal", bg=self.bg_surface, fg=self.fg_color)
            self.end_entry.config(state="normal", bg=self.bg_surface, fg=self.fg_color)
        else:
            self.start_entry.config(state="disabled", bg=self.bg_color, fg="#585b70")
            self.end_entry.config(state="disabled", bg=self.bg_color, fg="#585b70")

    def validate_time(self, time_str):
        """Validates if time string matches HH:MM:SS or MM:SS formats."""
        time_str = time_str.strip()
        if re.match(r"^[\d:.]+$", time_str):
            return True
        return False

    def clear_logs(self):
        """Clears the terminal window."""
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")
        self.last_line_was_cr = False

    def on_console_click(self, event):
        """Extracts format IDs from clicked lines in the console logs and populates the Format Code entry box."""
        try:
            # If the user is currently selecting/highlighting text to copy, ignore click callback
            try:
                if self.log_text.tag_ranges("sel"):
                    return
            except Exception:
                pass
                
            # Get index position of the mouse click
            index = self.log_text.index(f"@{event.x},{event.y}")
            # Retrieve the complete line text
            line = self.log_text.get(f"{index} linestart", f"{index} lineend").strip()
            
            if not line:
                return
                
            tokens = line.split()
            if not tokens:
                return
                
            # Format ID is always the first token of a standard format list row in yt-dlp
            format_id = tokens[0]
            
            # Avoid picking up header titles or system log tokens
            if format_id.lower() in (
                "id", "ext", "resolution", "fps", "ch", "filesize", "tbr", 
                "proto", "vcodec", "acodec", "info", "executing", "running", 
                "status", "command", "[info]", "[download]", "[ffmpeg]", "warning:", 
                "error:", "executing", "selected", "command:"
            ) or format_id.startswith("[") or format_id.startswith("="):
                return
                
            # Clean off trailing punctuation from the extracted ID
            format_id = format_id.rstrip(":,.-")
            
            # Auto-fill the Format Code entry field
            current = self.format_entry.get().strip()
            if not current:
                self.format_entry.delete(0, tk.END)
                self.format_entry.insert(0, format_id)
                self.status_lbl.config(text=f"Status: Selected Format {format_id}", fg=self.accent_green)
            else:
                parts = current.split('+')
                if format_id not in parts:
                    # Append format using "+" (e.g. video+audio)
                    new_format = f"{current}+{format_id}"
                    self.format_entry.delete(0, tk.END)
                    self.format_entry.insert(0, new_format)
                    self.status_lbl.config(text=f"Status: Combined Formats {new_format}", fg=self.accent_green)
                else:
                    # Toggle selection off if user clicks an already selected format ID
                    parts.remove(format_id)
                    new_format = "+".join(parts) if parts else ""
                    self.format_entry.delete(0, tk.END)
                    self.format_entry.insert(0, new_format)
                    self.status_lbl.config(text=f"Status: Deselected Format {format_id}", fg=self.accent_green)
        except Exception:
            pass

    def write_log(self, text, is_cr):
        """Appends logs to the text widget, applying live color tags and replacing lines for carriage returns."""
        clean_text = text.replace('\r', '').replace('\n', '')
        if not clean_text and not text.endswith('\n'):
            return
            
        self.log_text.config(state="normal")
        
        # If the last action was a carriage return, wipe the last line before printing the new update
        if self.last_line_was_cr:
            last_line_idx = self.log_text.index("end-2c linestart")
            if float(last_line_idx) >= 1.0:
                self.log_text.delete("end-2c linestart", "end-1c")
                
        # Classify the log string to apply syntax highlights
        tags = []
        lower_text = clean_text.lower()
        if clean_text.startswith('[info]') or "id  ext  resolution" in lower_text or clean_text.startswith('=' * 10):
            tags.append("header")
        elif "audio only" in lower_text:
            tags.append("audio")
        elif "video only" in lower_text:
            tags.append("video")
        elif "warning:" in lower_text or "⚠️" in lower_text:
            tags.append("warning")
        elif "error:" in lower_text or "failed" in lower_text:
            tags.append("error")
        elif clean_text.startswith('[download]'):
            tags.append("download")
        elif clean_text.startswith('[') and ']' in clean_text:
            tags.append("info")
            
        # Insert the text content with parsed tags
        self.log_text.insert("end-1c", clean_text, tuple(tags))
        
        # If this is NOT a carriage return, add a trailing newline so future prints start on the next line
        if not is_cr:
            self.log_text.insert("end-1c", "\n")
            
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.last_line_was_cr = is_cr

    def start_download(self):
        """Begins video/clip downloading process."""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Validation Error", "Please enter a valid video URL.")
            return
            
        save_dir = self.save_entry.get().strip()
        if not save_dir:
            messagebox.showerror("Validation Error", "Please specify a download folder.")
            return
            
        # Create directories if they do not exist
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Save Folder Error", f"Could not create destination directory:\n{str(e)}")
                return
                
        mode = self.mode_var.get()
        custom_format = self.format_entry.get().strip()
        
        # Determine format configurations
        if custom_format:
            format_arg = custom_format
        else:
            if mode == "video":
                format_arg = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]"
            else:
                format_arg = "mp4"

        # Build command based on selection
        if mode == "video":
            cmd = [
                self.ytdlp_path,
                "-P", save_dir,
                "-f", format_arg,
                "--ffmpeg-location", self.ffmpeg_dir,
                url
            ]
        elif mode == "clip":
            start = self.start_entry.get().strip()
            end = self.end_entry.get().strip()
            
            if not start or not end:
                messagebox.showerror("Validation Error", "Please specify both Start and End times.")
                return
            if not self.validate_time(start) or not self.validate_time(end):
                messagebox.showerror("Validation Error", "Time arguments must be formatted as HH:MM:SS or MM:SS.")
                return
                
            cmd = [
                self.ytdlp_path,
                "-P", save_dir,
                "--download-sections", f"*{start}-{end}",
                "-f", format_arg,
                "--ffmpeg-location", self.ffmpeg_dir,
                url
            ]
        else:
            return

        # Prepare GUI buttons and properties
        self.set_buttons_running()
        self.progress_var.set(0.0)
        self.speed_lbl.config(text="")
        self.status_lbl.config(text="Status: Initializing Download...", fg=self.accent_purple)
        
        # Start worker thread
        threading.Thread(target=self.run_command_thread, args=(cmd,), daemon=True).start()

    def start_inspect(self):
        """Asynchronously executes the yt-dlp inspect command (-F) to show stream qualities."""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Validation Error", "Please enter a valid video URL.")
            return
            
        cmd = [
            self.ytdlp_path,
            "-F",
            url
        ]

        # Prepare GUI buttons and properties
        self.set_buttons_running()
        self.progress_var.set(0.0)
        self.speed_lbl.config(text="")
        self.status_lbl.config(text="Status: Inspecting formats...", fg=self.accent_purple)
        
        # Start worker thread
        threading.Thread(target=self.run_command_thread, args=(cmd,), daemon=True).start()

    def run_command_thread(self, cmd):
        """Asynchronously executes the yt-dlp command and streams outputs to the queue."""
        try:
            # Check for FFmpeg when performing merging or clip cutting operations
            if "--ffmpeg-location" in cmd:
                ffmpeg_path = os.path.join(self.ffmpeg_dir, "ffmpeg.exe")
                if not os.path.exists(ffmpeg_path):
                    self.log_queue.put(('log', ("⚠️ WARNING: 'ffmpeg.exe' was not found in the application folder.\n"
                                              "Merging audio/video streams and clip extractions will likely fail without FFmpeg.\n\n", False)))

            # Print command run representation
            self.log_queue.put(('log', (f"Executing Command: {' '.join(cmd)}\n\n", False)))
            self.log_queue.put(('status', "Running..."))
            
            # Spawn process hiding console window
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                cwd=self.script_dir
            )
            
            # Read stdout byte-by-byte to catch carriage returns (\r) in real time
            buffer = bytearray()
            while self.current_process:
                char = self.current_process.stdout.read(1)
                if not char:
                    if buffer:
                        line = buffer.decode('utf-8', errors='replace')
                        self.parse_and_log_line(line, False)
                    break
                    
                buffer.extend(char)
                if char == b'\n':
                    line = buffer.decode('utf-8', errors='replace')
                    self.parse_and_log_line(line, False)
                    buffer.clear()
                elif char == b'\r':
                    line = buffer.decode('utf-8', errors='replace')
                    self.parse_and_log_line(line, True)
                    buffer.clear()
                    
            if self.current_process:
                exit_code = self.current_process.wait()
                self.log_queue.put(('finished', exit_code))
            else:
                self.log_queue.put(('finished', -1))
                
        except Exception as e:
            self.log_queue.put(('log', (f"An error occurred during execution:\n{traceback.format_exc()}\n", False)))
            self.log_queue.put(('finished', -1))

    def parse_and_log_line(self, line, is_cr):
        """Parses operational details (progress, speed, ETA) and forwards lines to log queue."""
        self.log_queue.put(('log', (line, is_cr)))
        
        # Match download progress percentages e.g., "[download]  35.4% of ~10.45MiB"
        pct_match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
        if pct_match:
            pct = float(pct_match.group(1))
            self.log_queue.put(('progress', pct))
            
        # Match speeds and ETA estimates e.g., "at 3.12MiB/s ETA 00:15"
        speed_eta_match = re.search(r"at\s+(\S+)\s+ETA\s+(\S+)", line)
        if speed_eta_match:
            speed = speed_eta_match.group(1)
            eta = speed_eta_match.group(2)
            self.log_queue.put(('speed_eta', (speed, eta)))

    def stop_action(self):
        """Kills the active subprocess tree (yt-dlp + child ffmpeg instances)."""
        if self.current_process:
            try:
                # Tree-kill the process to ensure child subprocesses like ffmpeg are terminated on Windows
                pid = self.current_process.pid
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)], 
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    capture_output=True
                )
                self.current_process = None
                self.log_queue.put(('log', ("\n⚠️ Action aborted by user.\n", False)))
                self.log_queue.put(('status', "Aborted"))
            except Exception as e:
                self.log_queue.put(('log', (f"Error aborting execution: {str(e)}\n", False)))

    def process_queue_loop(self):
        """Main loop draining thread queue tasks into Tkinter GUI widgets."""
        try:
            while True:
                item_type, data = self.log_queue.get_nowait()
                
                if item_type == 'log':
                    text, is_cr = data
                    self.write_log(text, is_cr)
                elif item_type == 'progress':
                    self.progress_var.set(data)
                    self.status_lbl.config(text=f"Status: Downloading ({data:.1f}%)")
                elif item_type == 'speed_eta':
                    speed, eta = data
                    self.speed_lbl.config(text=f"Speed: {speed} | ETA: {eta}")
                elif item_type == 'status':
                    self.status_lbl.config(text=f"Status: {data}")
                elif item_type == 'finished':
                    self.on_process_finished(data)
                    
                self.log_queue.task_done()
        except queue.Empty:
            pass
            
        # Poll again in 50ms
        self.root.after(50, self.process_queue_loop)

    def on_process_finished(self, exit_code):
        """Handles post-execution cleanup and user reporting."""
        self.current_process = None
        
        # Reset buttons to normal state
        self.set_buttons_idle()
        self.speed_lbl.config(text="")
        
        if exit_code == 0:
            self.status_lbl.config(text="Status: Completed Successfully!", fg=self.accent_green)
            self.progress_var.set(100.0)
            messagebox.showinfo("Success", "The operation completed successfully!")
        elif exit_code == -1 or exit_code == 128:  # taskkill often leaves exit code 128 or -1
            self.status_lbl.config(text="Status: Cancelled / Aborted", fg="#f9e2af")
            self.progress_var.set(0.0)
            messagebox.showwarning("Cancelled", "The operation was cancelled.")
        else:
            self.status_lbl.config(text=f"Status: Failed (Code: {exit_code})", fg=self.accent_red)
            self.progress_var.set(0.0)
            messagebox.showerror("Execution Error", f"Operation failed with exit code: {exit_code}.\nPlease inspect console logs.")

if __name__ == "__main__":
    root = tk.Tk()
    app = YtdlpDownloaderApp(root)
    root.mainloop()

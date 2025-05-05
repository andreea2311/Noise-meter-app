import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
import threading
import time
from matplotlib import rcParams
import numpy as np

class NoiseMeterApp:
    def __init__(self, processor):
        self.is_dark_theme = False
        self.fullscreen = False
        self.original_font_sizes = {}
        self.themes = {
            'light': {
                'bg': '#ffffff',
                'fg': '#000000',
                'plot_bg': '#f8f8f8',
                'axes_bg': '#ffffff',
                'grid': '#dddddd'
            },
            'dark': {
                'bg': '#2d2d2d',
                'fg': '#ffffff',
                'plot_bg': '#1e1e1e',
                'axes_bg': '#2d2d2d',
                'grid': '#404040'
            }
        }

        self.processor = processor
        self.root = tk.Tk()
        self.root.title("Real-Time Noise Meter")
        self.root.geometry("1000x800")
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)
        
        # Configure main window grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Create and store all frames
        self.control_frame = tk.Frame(self.root)
        self.control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.button_frame = tk.Frame(self.control_frame)
        self.button_frame.pack(side=tk.LEFT, padx=10)
        
        # Noise Level Display
        self.noise_label = tk.Label(
            self.control_frame, 
            text="Noise Level: -- dB", 
            font=("Helvetica", 16),
            width=20
        )
        self.noise_label.pack(side=tk.LEFT, padx=10)
        
        # Progress Bar
        self.progress = ttk.Progressbar(
            self.control_frame,
            orient="horizontal",
            length=300,
            mode="determinate",
            maximum=120
        )
        self.progress.pack(side=tk.LEFT, padx=10)
        
        # Buttons
        self.start_button = tk.Button(
            self.button_frame,
            text="Start",
            command=self.start_measurement,
            bg="green",
            fg="white",
            width=10
        )
        self.start_button.pack(side=tk.LEFT)
        
        self.stop_button = tk.Button(
            self.button_frame,
            text="Stop",
            command=self.stop_measurement,
            bg="red",
            fg="white",
            state=tk.DISABLED,
            width=10
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.export_button = tk.Button(
            self.button_frame,
            text="Export CSV",
            command=self.export_to_csv,
            state=tk.DISABLED,
            width=10
        )
        self.export_button.pack(side=tk.LEFT, padx=5)
        
        self.close_button = tk.Button(
            self.button_frame,
            text="Close",
            command=self.close_app,
            bg="gray",
            fg="white",
            width=10
        )
        self.close_button.pack(side=tk.LEFT)
        
        self.new_session_button = tk.Button(
            self.button_frame,
            text="New Session",
            command=self.new_session,
            bg="blue",
            fg="white",
            width=10
        )
        self.new_session_button.pack(side=tk.LEFT, padx=5)

        self.theme_button = tk.Button(
            self.button_frame,
            text="☀️",
            command=self.toggle_theme,
            width=3
        )
        self.theme_button.pack(side=tk.LEFT, padx=5)

        self.fullscreen_button = tk.Button(
            self.button_frame,
            text="⛶",
            command=self.toggle_fullscreen,
            width=3
        )
        self.fullscreen_button.pack(side=tk.LEFT, padx=5)

        self.root.bind("<F11>", lambda event: self.toggle_fullscreen())
        self.store_original_font_sizes()
        
        # Threshold Legend
        self.threshold_frame = tk.Frame(self.control_frame)
        self.threshold_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Label(self.threshold_frame, text="Thresholds:", font=("Helvetica", 10)).pack()
        tk.Label(self.threshold_frame, text="Silence: <30 dB", fg="green").pack(anchor="w")
        tk.Label(self.threshold_frame, text="Normal: 30-60 dB", fg="orange").pack(anchor="w")
        tk.Label(self.threshold_frame, text="Noisy: >60 dB", fg="red").pack(anchor="w")
        
        # Visualization Frame
        self.vis_frame = tk.Frame(self.root)
        self.vis_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Matplotlib Figure Setup
        self.figure, self.ax = plt.subplots(figsize=(10, 6))
        self.figure.set_facecolor('#f0f0f0')
        self.ax.set_facecolor('#f8f8f8')
        self.line, = self.ax.plot([], [], 'b-', linewidth=2, label='Noise Level')
        self.ax.set_ylim(0, 120)
        self.ax.set_xlim(0, 60)
        self.ax.set_title("Real-Time Noise Levels", fontsize=12, pad=20)
        self.ax.set_xlabel("Time (seconds)", fontsize=10)
        self.ax.set_ylabel("Decibels (dB)", fontsize=10)
        self.ax.grid(True, linestyle='--', alpha=0.6)
        self.ax.legend(loc='upper right')
        self.ax.axhline(30, color='green', linestyle=':', alpha=0.5)
        self.ax.axhline(60, color='red', linestyle=':', alpha=0.5)
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.vis_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.configure_styles()
        self.running = False
        self.thread = None
        self.max_data_points = 600


    def store_original_font_sizes(self):
        self.original_font_sizes = {
            'noise_label': self.noise_label.cget('font'),
            'button_font': self.start_button.cget('font')
        }

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        theme = self.themes['dark'] if self.is_dark_theme else self.themes['light']
        
        # Update UI colors
        self.root.config(bg=theme['bg'])
        self.control_frame.config(bg=theme['bg'])
        self.vis_frame.config(bg=theme['bg'])
        self.button_frame.config(bg=theme['bg'])
        self.threshold_frame.config(bg=theme['bg'])
        
        # Update plot colors
        self.figure.set_facecolor(theme['axes_bg'])
        self.ax.set_facecolor(theme['plot_bg'])
        self.ax.spines['bottom'].set_color(theme['fg'])
        self.ax.spines['top'].set_color(theme['fg']) 
        self.ax.spines['right'].set_color(theme['fg'])
        self.ax.spines['left'].set_color(theme['fg'])
        self.ax.xaxis.label.set_color(theme['fg'])
        self.ax.yaxis.label.set_color(theme['fg'])
        self.ax.title.set_color(theme['fg'])
        self.ax.tick_params(axis='x', colors=theme['fg'])
        self.ax.tick_params(axis='y', colors=theme['fg'])
        self.ax.grid(color=theme['grid'])
        
        # Update widget colors - only for labels
        for widget in self.threshold_frame.winfo_children():
            if isinstance(widget, tk.Label):
                widget.config(bg=theme['bg'], fg=theme['fg'])
        
        self.noise_label.config(bg=theme['bg'], fg=theme['fg'])
        
        self.theme_button.config(text="🌙" if self.is_dark_theme else "☀️")
        self.canvas.draw()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        
        if self.fullscreen:
            # Enlarge elements
            self.control_frame.grid_configure(pady=20)
            self.noise_label.config(font=("Helvetica", 24))
            self.progress.config(length=800)
            self.button_frame.pack_configure(padx=30)
            
            # Increase font sizes
            for button in [self.start_button, self.stop_button, 
                        self.export_button, self.close_button, 
                        self.new_session_button]:
                current_font = button.cget('font')
                if current_font == "TkDefaultFont":
                    button.config(font=("Helvetica", 12))
                else:
                    size = int(current_font.split(" ")[-1])
                    button.config(font=f"Helvetica {size + 4}")
        else:
            # Restore original sizes
            self.control_frame.grid_configure(pady=10)
            self.noise_label.config(font=self.original_font_sizes['noise_label'])
            self.progress.config(length=300)
            self.button_frame.pack_configure(padx=10)
            
            # Restore original fonts
            for button in [self.start_button, self.stop_button,
                        self.export_button, self.close_button,
                        self.new_session_button]:
                button.config(font=self.original_font_sizes['button_font'])
        
        self.root.update_idletasks()

    def configure_styles(self):
        style = ttk.Style()
        style.configure("TProgressbar",
            thickness=20,
            troughcolor='#e0e0e0',
            background='blue',
            troughrelief='flat'
        )
        style.map("TProgressbar",
            background=[('active', 'green'), ('!active', 'blue')]
        )

    def start_measurement(self):
        if self.running:
            return
            
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.export_button.config(state=tk.NORMAL)
        
        # Clear previous data
        with self.processor.data_lock:
            self.processor.data_history = []
            self.processor.timestamps = []
        
        try:
            self.processor.start()
            self.thread = threading.Thread(
                target=self.processor.capture_audio,
                args=(self.update_visuals,),
                daemon=True
            )
            self.thread.start()
            self.update_graph()
        except Exception as e:
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            messagebox.showerror("Error", f"Failed to start audio: {str(e)}")


    def stop_measurement(self):
        if not self.running:
            return
            
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.processor.stop()

    def new_session(self):
        self.stop_measurement()
        with self.processor.data_lock:
            self.processor.data_history = []
            self.processor.timestamps = []
        
        self.ax.clear()
        self.ax.set_ylim(0, 120)
        self.ax.set_xlim(0, 60)
        self.ax.set_title("Real-Time Noise Levels", fontsize=12, pad=20)
        self.ax.set_xlabel("Time (seconds)", fontsize=10)
        self.ax.set_ylabel("Decibels (dB)", fontsize=10)
        self.ax.grid(True, linestyle='--', alpha=0.6)
        self.ax.legend(loc='upper right')
        self.ax.axhline(30, color='green', linestyle=':', alpha=0.5)
        self.ax.axhline(60, color='red', linestyle=':', alpha=0.5)
        self.canvas.draw()

    def update_visuals(self, db_level):
        if not self.running:
            return
            
        with self.processor.data_lock:
            self.processor.data_history.append(db_level)
            self.processor.timestamps.append(time.time())
            
            if len(self.processor.data_history) > self.max_data_points:
                self.processor.data_history.pop(0)
                self.processor.timestamps.pop(0)

    def update_graph(self):
        """Main graph update called from main thread"""
        if not self.running:
            return
            
        with self.processor.data_lock:
            if len(self.processor.timestamps) == 0:
                self.root.after(100, self.update_graph)
                return
                
            times = np.array(self.processor.timestamps)
            db_levels = np.array(self.processor.data_history)
        
        current_db = db_levels[-1] if len(db_levels) > 0 else -120
        self.noise_label.config(text=f"Noise Level: {current_db:.1f} dB")
        self.progress["value"] = np.clip(current_db, 0, 120)
        
        if current_db < 30:
            self.progress.config(style="green.Horizontal.TProgressbar")
        elif 30 <= current_db <= 60:
            self.progress.config(style="yellow.Horizontal.TProgressbar")
        else:
            self.progress.config(style="red.Horizontal.TProgressbar")
        
        times = times - times[0]
        
        self.ax.clear()
        if len(times) > 0:  # Only plot if we have data
            self.line, = self.ax.plot(times, db_levels, 'b-', linewidth=2, label='Noise Level')
            self.ax.set_ylim(0, 120)
            self.ax.set_xlim(max(0, times[-1]-60), times[-1]+1)
            self.ax.set_title("Real-Time Noise Levels", fontsize=12, pad=20)
            self.ax.set_xlabel("Time (seconds)", fontsize=10)
            self.ax.set_ylabel("Decibels (dB)", fontsize=10)
            self.ax.grid(True, linestyle='--', alpha=0.6)
            
            # Only create legend if we have data points
            if len(db_levels) > 0:
                self.ax.legend(loc='upper right')
                
            self.ax.axhline(30, color='green', linestyle=':', alpha=0.5)
            self.ax.axhline(60, color='red', linestyle=':', alpha=0.5)
        
        self.canvas.draw()
        self.root.after(100, self.update_graph)
        
    def export_to_csv(self):
        try:
            filename = f"noise_data_{time.strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Timestamp", "dB Level"])
                with self.processor.data_lock:
                    writer.writerows(zip(self.processor.timestamps, self.processor.data_history))
            messagebox.showinfo("Export Complete", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Error: {str(e)}")

    def close_app(self):
        if messagebox.askokcancel("Quit", "Do you want to close the application?"):
            self.running = False
            if self.thread and self.thread.is_alive():
                self.processor.close()
            self.root.destroy()

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self.processor.close()
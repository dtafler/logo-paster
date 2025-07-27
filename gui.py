import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from pathlib import Path
import sys
import io
from PIL import Image, ImageTk
from overlay_logo import stamp_folder, VerticalPosition, HorizontalPosition, _process_logo_on_image


class LogoStamperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Logo Stamper")
        self.root.geometry("1200x900")
        self.root.configure(bg='#f0f0f0')
        
        # Variables
        self.folder_path = tk.StringVar()
        self.logo_path = tk.StringVar()
        self.save_path = tk.StringVar()
        self.use_custom_save = tk.BooleanVar()
        
        # Logo positioning and appearance variables
        self.vertical_pos = tk.StringVar(value="bottom")
        self.horizontal_pos = tk.StringVar(value="center")
        self.padding = tk.IntVar(value=10)
        self.logo_scale = tk.DoubleVar(value=0.2)
        self.opacity = tk.DoubleVar(value=1.0)
        self.recursive = tk.BooleanVar(value=True)
        
        # Preview variables
        self.preview_image = None
        self.preview_photo = None
        self.full_size_preview = tk.BooleanVar(value=False)
        self.show_preview = tk.BooleanVar(value=False)  # Default to not showing preview
        self.zoom_factor = 1.0
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)  # Controls frame - expand when preview hidden
        self.main_frame.columnconfigure(1, weight=0)  # Preview frame - starts hidden
        self.main_frame.rowconfigure(0, weight=1)     # Allow vertical expansion
        
        # Left side - Controls
        controls_frame = ttk.Frame(self.main_frame, width=600)  # Increased width for better space
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        controls_frame.grid_propagate(False)  # Maintain the fixed width
        controls_frame.columnconfigure(1, weight=1)
        controls_frame.rowconfigure(13, weight=1)  # Allow output text area to expand
        
        # Right side - Preview (initially hidden)
        self.preview_frame = ttk.LabelFrame(self.main_frame, text="Preview", padding="10")
        # Don't grid it initially since show_preview defaults to False
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(controls_frame, text="Logo Stamper", 
                               font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Image folder selection
        ttk.Label(controls_frame, text="Image Folder:", 
                 font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        folder_frame = ttk.Frame(controls_frame)
        folder_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        folder_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(folder_frame, textvariable=self.folder_path, 
                 font=('Arial', 10)).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(folder_frame, text="Browse", 
                  command=self.browse_folder).grid(row=0, column=1)
        
        # Logo file selection
        ttk.Label(controls_frame, text="Logo File:", 
                 font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=5)
        
        logo_frame = ttk.Frame(controls_frame)
        logo_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        logo_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(logo_frame, textvariable=self.logo_path, 
                 font=('Arial', 10)).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(logo_frame, text="Browse", 
                  command=self.browse_logo).grid(row=0, column=1)
        
        # Recursive search option
        recursive_check = ttk.Checkbutton(controls_frame, text="Search subfolders recursively", 
                         variable=self.recursive, command=self.update_preview)
        recursive_check.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=10)
        
        # Custom save directory option
        save_check = ttk.Checkbutton(controls_frame, text="Use custom save directory", 
                                    variable=self.use_custom_save,
                                    command=self.toggle_save_directory)
        save_check.grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=10)
        
        # Save directory selection (initially disabled)
        self.save_label = ttk.Label(controls_frame, text="Save Directory:", 
                                   font=('Arial', 10, 'bold'), state='disabled')
        self.save_label.grid(row=7, column=0, sticky=tk.W, pady=5)
        
        self.save_frame = ttk.Frame(controls_frame)
        self.save_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        self.save_frame.columnconfigure(0, weight=1)
        
        self.save_entry = ttk.Entry(self.save_frame, textvariable=self.save_path, 
                                   font=('Arial', 10), state='disabled')
        self.save_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.save_button = ttk.Button(self.save_frame, text="Browse", 
                                     command=self.browse_save_dir, state='disabled')
        self.save_button.grid(row=0, column=1)
        
        # Logo positioning and appearance options
        options_frame = ttk.LabelFrame(controls_frame, text="Logo Options", padding="10")
        options_frame.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=20)
        options_frame.columnconfigure(1, weight=1)
        options_frame.columnconfigure(3, weight=1)
        
        # Position options
        ttk.Label(options_frame, text="Vertical Position:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        vertical_combo = ttk.Combobox(options_frame, textvariable=self.vertical_pos, 
                                     values=["top", "bottom"], state="readonly", width=15)
        vertical_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        vertical_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
        
        ttk.Label(options_frame, text="Horizontal Position:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        horizontal_combo = ttk.Combobox(options_frame, textvariable=self.horizontal_pos,
                                       values=["left", "center", "right"], state="readonly", width=15)
        horizontal_combo.grid(row=0, column=3, sticky=tk.W)
        horizontal_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
        
        # Padding
        ttk.Label(options_frame, text="Padding (pixels):").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        padding_frame = ttk.Frame(options_frame)
        padding_frame.grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 20))
        
        padding_scale = ttk.Scale(padding_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                 variable=self.padding, length=100)
        padding_scale.grid(row=0, column=0)
        
        self.padding_label = ttk.Label(padding_frame, text="10")
        self.padding_label.grid(row=0, column=1, padx=(10, 0))
        padding_scale.configure(command=self.update_padding_label)
        
        # Logo scale
        ttk.Label(options_frame, text="Logo Size (% of image):").grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        scale_frame = ttk.Frame(options_frame)
        scale_frame.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        scale_scale = ttk.Scale(scale_frame, from_=0.05, to=0.8, orient=tk.HORIZONTAL,
                               variable=self.logo_scale, length=100)
        scale_scale.grid(row=0, column=0)
        
        self.scale_label = ttk.Label(scale_frame, text="20%")
        self.scale_label.grid(row=0, column=1, padx=(10, 0))
        scale_scale.configure(command=self.update_scale_label)
        
        # Opacity
        ttk.Label(options_frame, text="Opacity:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        opacity_frame = ttk.Frame(options_frame)
        opacity_frame.grid(row=2, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 20))
        
        opacity_scale = ttk.Scale(opacity_frame, from_=0.1, to=1.0, orient=tk.HORIZONTAL,
                                 variable=self.opacity, length=100)
        opacity_scale.grid(row=0, column=0)
        
        self.opacity_label = ttk.Label(opacity_frame, text="100%")
        self.opacity_label.grid(row=0, column=1, padx=(10, 0))
        opacity_scale.configure(command=self.update_opacity_label)
        
        # Preview button and show preview checkbox on same row
        preview_button = ttk.Button(options_frame, text="Update Preview", 
                                   command=self.update_preview)
        preview_button.grid(row=2, column=2, pady=(10, 0), padx=(0, 10))
        
        # Show preview option (in controls frame so it's always visible)
        show_preview_check = ttk.Checkbutton(options_frame, text="Show preview", 
                                           variable=self.show_preview,
                                           command=self.toggle_preview)
        show_preview_check.grid(row=2, column=3, sticky=tk.W, pady=(10, 0))
        
        # Process button
        self.process_button = ttk.Button(controls_frame, text="Add Logo to Images", 
                                        command=self.process_images,
                                        style='Accent.TButton')
        self.process_button.grid(row=10, column=0, columnspan=3, pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(controls_frame, mode='indeterminate')
        self.progress.grid(row=11, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Output text area
        ttk.Label(controls_frame, text="Output:", 
                 font=('Arial', 10, 'bold')).grid(row=12, column=0, sticky=tk.W, pady=(10, 5))
        
        self.output_text = scrolledtext.ScrolledText(controls_frame, height=6, 
                                                    font=('Consolas', 9))
        self.output_text.grid(row=13, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Configure text area to expand
        controls_frame.rowconfigure(13, weight=1)
        
        # Preview section
        preview_info = ttk.Label(self.preview_frame, text="Select images and logo to see preview", 
                                font=('Arial', 10))
        preview_info.grid(row=0, column=0, pady=10)
        
        # Preview controls frame
        preview_controls = ttk.Frame(self.preview_frame)
        preview_controls.grid(row=1, column=0, pady=5, sticky=tk.W)
        
        # Full size preview option
        full_size_check = ttk.Checkbutton(preview_controls, text="Full size preview", 
                                         variable=self.full_size_preview,
                                         command=self.update_preview)
        full_size_check.grid(row=0, column=0)
        
        # Zoom info label
        self.zoom_info = ttk.Label(preview_controls, text="Zoom: 100% (Ctrl+Wheel to zoom)", 
                                  font=('Arial', 9), foreground='gray')
        self.zoom_info.grid(row=0, column=1, padx=(20, 0))
        
        # Reset zoom button
        reset_zoom_btn = ttk.Button(preview_controls, text="Reset Zoom", 
                                   command=self.reset_zoom)
        reset_zoom_btn.grid(row=0, column=2, padx=(10, 0))
        
        # Create scrollable canvas for preview
        self.preview_canvas = tk.Canvas(self.preview_frame, bg='white', cursor='hand2')
        self.preview_canvas.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(self.preview_frame, orient=tk.VERTICAL, command=self.preview_canvas.yview)
        v_scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
        self.preview_canvas.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(self.preview_frame, orient=tk.HORIZONTAL, command=self.preview_canvas.xview)
        h_scrollbar.grid(row=3, column=0, sticky=(tk.W, tk.E))
        self.preview_canvas.configure(xscrollcommand=h_scrollbar.set)
        
        # Configure canvas for mouse wheel scrolling and zooming
        def _on_mousewheel(event):
            # Check if Ctrl is held down for zooming
            if event.state & 0x4:  # Ctrl key is pressed
                # Zoom functionality
                if event.delta > 0:
                    self.zoom_factor *= 1.1
                else:
                    self.zoom_factor /= 1.1
                
                # Limit zoom range
                self.zoom_factor = max(0.1, min(5.0, self.zoom_factor))
                
                # Update zoom info
                zoom_percent = int(self.zoom_factor * 100)
                self.zoom_info.configure(text=f"Zoom: {zoom_percent}% (Ctrl+Wheel to zoom)")
                
                # Update preview with new zoom
                self.update_preview()
            else:
                # Normal scrolling
                self.preview_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _on_mousewheel_linux(event):
            # Check if Ctrl is held down for zooming
            if event.state & 0x4:  # Ctrl key is pressed
                # Zoom functionality for Linux
                if event.num == 4:
                    self.zoom_factor *= 1.1
                else:
                    self.zoom_factor /= 1.1
                
                # Limit zoom range
                self.zoom_factor = max(0.1, min(5.0, self.zoom_factor))
                
                # Update zoom info
                zoom_percent = int(self.zoom_factor * 100)
                self.zoom_info.configure(text=f"Zoom: {zoom_percent}% (Ctrl+Wheel to zoom)")
                
                # Update preview with new zoom
                self.update_preview()
            else:
                # Normal scrolling
                if event.num == 4:
                    self.preview_canvas.yview_scroll(-1, "units")
                else:
                    self.preview_canvas.yview_scroll(1, "units")
        
        self.preview_canvas.bind("<MouseWheel>", _on_mousewheel)
        self.preview_canvas.bind("<Button-4>", _on_mousewheel_linux)
        self.preview_canvas.bind("<Button-5>", _on_mousewheel_linux)
        
        # Configure canvas for mouse dragging
        self.last_x = 0
        self.last_y = 0
        
        def _start_drag(event):
            self.last_x = event.x
            self.last_y = event.y
            self.preview_canvas.configure(cursor='fleur')  # Change cursor while dragging
        
        def _drag(event):
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            
            # Get current scroll position as fraction
            x_view = self.preview_canvas.xview()
            y_view = self.preview_canvas.yview()
            
            # Get scrollable region
            scroll_region = self.preview_canvas.cget("scrollregion")
            if scroll_region:
                coords = [float(x) for x in scroll_region.split()]
                scroll_width = coords[2] - coords[0]
                scroll_height = coords[3] - coords[1]
                
                # Get canvas dimensions
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                
                # Only allow dragging if content is larger than canvas
                if scroll_width > canvas_width:
                    # Convert pixel movement to fractional movement for horizontal
                    dx_fraction = -dx / scroll_width
                    new_x = max(0, min(1, x_view[0] + dx_fraction))
                    self.preview_canvas.xview_moveto(new_x)
                
                if scroll_height > canvas_height:
                    # Convert pixel movement to fractional movement for vertical
                    dy_fraction = -dy / scroll_height
                    new_y = max(0, min(1, y_view[0] + dy_fraction))
                    self.preview_canvas.yview_moveto(new_y)
            
            self.last_x = event.x
            self.last_y = event.y
        
        def _end_drag(event):
            self.preview_canvas.configure(cursor='hand2')  # Reset cursor after dragging
        
        self.preview_canvas.bind("<Button-1>", _start_drag)
        self.preview_canvas.bind("<B1-Motion>", _drag)
        self.preview_canvas.bind("<ButtonRelease-1>", _end_drag)
        
        # Initial text label for when no preview is available
        self.preview_text_id = self.preview_canvas.create_text(
            200, 100, text="No preview available", font=('Arial', 12), fill='gray'
        )
        
        # Style configuration
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Arial', 10, 'bold'))
        
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Image Folder")
        if folder:
            self.folder_path.set(folder)
            self.reset_zoom()  # Reset zoom when changing folder
            self.update_preview()
            
    def browse_logo(self):
        logo = filedialog.askopenfilename(
            title="Select Logo File",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        if logo:
            self.logo_path.set(logo)
            self.reset_zoom()  # Reset zoom when changing logo
            self.update_preview()
            
    def browse_save_dir(self):
        save_dir = filedialog.askdirectory(title="Select Save Directory")
        if save_dir:
            self.save_path.set(save_dir)
            
    def toggle_save_directory(self):
        if self.use_custom_save.get():
            self.save_label.configure(state='normal')
            self.save_entry.configure(state='normal')
            self.save_button.configure(state='normal')
        else:
            self.save_label.configure(state='disabled')
            self.save_entry.configure(state='disabled')
            self.save_button.configure(state='disabled')
            self.save_path.set("")
    
    def toggle_preview(self):
        """Toggle preview visibility"""
        if self.show_preview.get():
            # Show the preview frame
            self.preview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
            # Adjust grid weights to give space to both controls and preview
            self.main_frame.columnconfigure(0, weight=0)  # Controls frame - fixed width
            self.main_frame.columnconfigure(1, weight=1)  # Preview frame - takes remaining space
            self.update_preview()
        else:
            # Hide the preview frame
            self.preview_frame.grid_remove()
            # Adjust grid weights to let controls frame use available space efficiently
            self.main_frame.columnconfigure(0, weight=1)  # Controls frame - can expand
            self.main_frame.columnconfigure(1, weight=0)  # Preview frame - no space
    
    def reset_zoom(self):
        """Reset zoom to 100%"""
        self.zoom_factor = 1.0
        self.zoom_info.configure(text="Zoom: 100% (Ctrl+Wheel to zoom)")
        self.update_preview()
    
    def update_padding_label(self, value):
        """Update the padding label with current value"""
        self.padding_label.configure(text=f"{int(float(value))}")
        self.update_preview()
    
    def update_scale_label(self, value):
        """Update the scale label with current value"""
        percentage = int(float(value) * 100)
        self.scale_label.configure(text=f"{percentage}%")
        self.update_preview()
    
    def update_opacity_label(self, value):
        """Update the opacity label with current value"""
        percentage = int(float(value) * 100)
        self.opacity_label.configure(text=f"{percentage}%")
        self.update_preview()
    
    def get_first_image(self):
        """Get the first image from the selected folder"""
        if not self.folder_path.get():
            return None
        
        try:
            folder_path = Path(self.folder_path.get())
            if not folder_path.exists():
                return None
                
            image_extensions = ('.jpg', '.jpeg', '.png')
            
            if self.recursive.get():
                image_files = [p for p in folder_path.rglob("*") if p.suffix.lower() in image_extensions]
            else:
                image_files = [p for p in folder_path.glob("*") if p.suffix.lower() in image_extensions]
            
            if image_files:
                return image_files[0]
                
        except Exception:
            pass
        
        return None
    
    def update_preview(self):
        """Update the preview image with current settings"""
        try:
            # Check if preview is enabled
            if not self.show_preview.get():
                self._show_preview_message("Preview disabled")
                return
            
            # Check if we have the required inputs
            if not self.folder_path.get() or not self.logo_path.get():
                self._show_preview_message("Select both image folder and logo file")
                return
            
            # Get first image
            first_image = self.get_first_image()
            if not first_image:
                self._show_preview_message("No images found in selected folder")
                return
            
            # Check if logo exists
            if not Path(self.logo_path.get()).exists():
                self._show_preview_message("Logo file not found")
                return
            
            # Load and process the image
            im = Image.open(first_image).convert('RGBA')
            logo = Image.open(self.logo_path.get()).convert('RGBA')
            
            # Get current settings
            vertical_pos = VerticalPosition(self.vertical_pos.get())
            horizontal_pos = HorizontalPosition(self.horizontal_pos.get())
            padding = self.padding.get()
            logo_scale = self.logo_scale.get()
            opacity = self.opacity.get()
            
            # Use the same processing function as the main application
            result_im = _process_logo_on_image(
                im, logo, vertical_pos, horizontal_pos,
                padding, logo_scale, opacity
            )
            
            # Convert to RGB for display (no alpha channel issues)
            result_im = result_im.convert('RGB')
            
            # Handle preview sizing
            if self.full_size_preview.get():
                # For full size, we might need to limit the display size to prevent GUI issues
                # If image is too large, we'll show it at actual size but with scrollbars
                im_width, im_height = result_im.size
                
                # Limit maximum display size to prevent memory/performance issues
                max_display_size = 1200
                if im_width > max_display_size or im_height > max_display_size:
                    ratio = min(max_display_size / im_width, max_display_size / im_height)
                    new_width = int(im_width * ratio)
                    new_height = int(im_height * ratio)
                    result_im = result_im.resize((new_width, new_height), Image.LANCZOS)
                # If smaller than max_display_size, show at actual size
            else:
                # Scale down for preview (max 400px on longest side)
                im_width, im_height = result_im.size
                max_size = 400
                ratio = min(max_size / im_width, max_size / im_height)
                if ratio < 1:
                    new_width = int(im_width * ratio)
                    new_height = int(im_height * ratio)
                    result_im = result_im.resize((new_width, new_height), Image.LANCZOS)
            
            # Apply zoom factor
            if self.zoom_factor != 1.0:
                current_width, current_height = result_im.size
                new_width = int(current_width * self.zoom_factor)
                new_height = int(current_height * self.zoom_factor)
                result_im = result_im.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage for display
            self.preview_photo = ImageTk.PhotoImage(result_im)
            
            # Clear canvas and display image
            self.preview_canvas.delete("all")
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            # Center the image on the canvas
            img_width, img_height = result_im.size
            x = max(0, (canvas_width - img_width) // 2) if canvas_width > img_width else 0
            y = max(0, (canvas_height - img_height) // 2) if canvas_height > img_height else 0
            
            self.preview_canvas.create_image(x, y, anchor=tk.NW, image=self.preview_photo)
            
            # Always set scroll region to enable dragging, even for small images
            # Use the larger of canvas size or image size for each dimension
            scroll_width = max(img_width, canvas_width or 1)
            scroll_height = max(img_height, canvas_height or 1)
            self.preview_canvas.configure(scrollregion=(0, 0, scroll_width, scroll_height))
            
        except Exception as e:
            self._show_preview_message(f"Preview error: {str(e)}")
            print(f"Preview error: {e}")
    
    def _show_preview_message(self, message):
        """Show a text message in the preview area"""
        self.preview_canvas.delete("all")
        canvas_width = self.preview_canvas.winfo_width() or 400
        canvas_height = self.preview_canvas.winfo_height() or 300
        self.preview_canvas.create_text(
            canvas_width // 2, canvas_height // 2, 
            text=message, font=('Arial', 12), fill='gray'
        )
        self.preview_canvas.configure(scrollregion=(0, 0, 0, 0))
            
    def log_output(self, text):
        """Add text to the output area"""
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_output(self):
        """Clear the output text area"""
        self.output_text.delete(1.0, tk.END)
        
    def validate_inputs(self):
        """Validate user inputs"""
        if not self.folder_path.get():
            messagebox.showerror("Error", "Please select an image folder.")
            return False
            
        if not self.logo_path.get():
            messagebox.showerror("Error", "Please select a logo file.")
            return False
            
        if not Path(self.folder_path.get()).exists():
            messagebox.showerror("Error", "Image folder does not exist.")
            return False
            
        if not Path(self.logo_path.get()).exists():
            messagebox.showerror("Error", "Logo file does not exist.")
            return False
            
        if self.use_custom_save.get() and not self.save_path.get():
            messagebox.showerror("Error", "Please select a save directory.")
            return False
            
        return True
        
    def process_images(self):
        """Process images in a separate thread"""
        if not self.validate_inputs():
            return
            
        # Disable the process button and start progress
        self.process_button.configure(state='disabled')
        self.progress.start()
        self.clear_output()
        
        # Start processing in a separate thread
        thread = threading.Thread(target=self._process_images_thread)
        thread.daemon = True
        thread.start()
        
    def _process_images_thread(self):
        """The actual processing logic that runs in a separate thread"""
        try:
            # Redirect stdout to capture print statements
            old_stdout = sys.stdout
            sys.stdout = output_capture = io.StringIO()
            
            # Determine save directory
            save_dir = None
            if self.use_custom_save.get():
                save_dir = self.save_path.get()
            
            # Get positioning and appearance options
            vertical_pos = VerticalPosition(self.vertical_pos.get())
            horizontal_pos = HorizontalPosition(self.horizontal_pos.get())
            padding = self.padding.get()
            logo_scale = self.logo_scale.get()
            opacity = self.opacity.get()
            recursive = self.recursive.get()
                
            # Process the images
            stamp_folder(
                im_dir=Path(self.folder_path.get()),
                logo_path=self.logo_path.get(),
                save_dir=save_dir,
                vertical_pos=vertical_pos,
                horizontal_pos=horizontal_pos,
                padding=padding,
                logo_scale=logo_scale,
                opacity=opacity,
                recursive=recursive
            )
            
            # Get the captured output
            output = output_capture.getvalue()
            
            # Restore stdout
            sys.stdout = old_stdout
            
            # Update UI in main thread
            self.root.after(0, self._processing_complete, output, True)
            
        except Exception as e:
            # Restore stdout
            sys.stdout = old_stdout
            
            # Update UI in main thread with error
            self.root.after(0, self._processing_complete, str(e), False)
            
    def _processing_complete(self, output, success):
        """Called when processing is complete"""
        # Stop progress and re-enable button
        self.progress.stop()
        self.process_button.configure(state='normal')
        
        # Show output
        if output:
            self.log_output(output)
            
        # Show completion message
        if success:
            self.log_output("✅ Processing completed successfully!")
            messagebox.showinfo("Success", "Logo stamping completed successfully!")
        else:
            self.log_output(f"❌ Error occurred: {output}")
            messagebox.showerror("Error", f"An error occurred during processing:\n{output}")


def main():
    root = tk.Tk()
    app = LogoStamperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

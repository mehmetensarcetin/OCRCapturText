import os
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import ctypes
import pyautogui
import pyperclip
import pytesseract
from PIL import Image, ImageTk, ImageOps
from concurrent.futures import ThreadPoolExecutor

def make_dpi_aware():
    """Makes the application DPI aware."""
    if os.name == 'nt':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

class ConfigurationManager:
    """Manages application configuration settings."""
    DEFAULT_CONFIG = {
        'tesseract_path': r'C:\Program Files\Tesseract-OCR\tesseract.exe' if os.name == 'nt' else '',
        'interface_language': 'tur'
    }
    CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.screen_capture_config.json')
    
    @classmethod
    def load_config(cls):
        """Loads configuration from file or returns default."""
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Ensure all default keys exist in loaded config
                for key, value in cls.DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
        
        return cls.DEFAULT_CONFIG.copy()
    
    @classmethod
    def save_config(cls, config):
        """Saves configuration to file."""
        try:
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False

class ConfigurationDialog:
    """Configuration dialog window."""
    
    def __init__(self, parent, config, ui_texts):
        self.parent = parent
        self.config = config.copy()  # Work with a copy
        self.ui_texts = ui_texts  # Add UI texts
        self.result = None  # Will be set to True if save is clicked
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(self.ui_texts['config_title'])
        self.dialog.geometry("550x250")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        x = parent.winfo_x() + (parent.winfo_width() - 550) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 250) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        
        # Make dialog modal
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.dialog.bind("<Escape>", self.on_cancel)
        
    def create_widgets(self):
        """Creates the dialog widgets."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Tesseract Path section
        path_frame = ttk.LabelFrame(main_frame, text=self.ui_texts['config_tesseract_path'], padding="10")
        path_frame.pack(fill='x', pady=10)
        
        # Path entry and browse button in one row
        path_row = ttk.Frame(path_frame)
        path_row.pack(fill='x', pady=5)
        
        self.tesseract_path_var = tk.StringVar(value=self.config.get('tesseract_path', ''))
        self.path_entry = ttk.Entry(path_row, textvariable=self.tesseract_path_var, width=50)
        self.path_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        # Browse button
        browse_button = ttk.Button(path_row, text=self.ui_texts['config_browse'], command=self.browse_tesseract_path)
        browse_button.pack(side='left')
        
        # Create a frame for the validation section within the path frame
        validate_container = ttk.Frame(path_frame)
        validate_container.pack(fill='x', pady=5)
        
        # Put the validation button directly below the browse button (right-aligned)
        validate_button = ttk.Button(validate_container, text=self.ui_texts['config_validate'], command=self.validate_tesseract_path)
        validate_button.pack(side='right')
        
        # Validation status label (to the left of the validate button)
        self.validation_label = ttk.Label(validate_container, text="")
        self.validation_label.pack(side='left', fill='x', expand=True)
        
        # Buttons frame for Save/Cancel
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', side='bottom', pady=10)
        
        # Cancel button on the right
        cancel_button = ttk.Button(button_frame, text=self.ui_texts['config_cancel'], command=self.on_cancel)
        cancel_button.pack(side='right', padx=5)
        
        # Save button to the left of Cancel
        save_button = ttk.Button(button_frame, text=self.ui_texts['config_save'], command=self.on_save)
        save_button.pack(side='right', padx=5)
        
        # Validate on start
        self.after_id = self.dialog.after(100, self.validate_tesseract_path)
        
    def browse_tesseract_path(self):
        """Opens a file dialog to select the Tesseract executable."""
        file_types = [("Executable files", "*.exe")] if os.name == 'nt' else [("All files", "*")]
        initial_dir = os.path.dirname(self.tesseract_path_var.get()) if self.tesseract_path_var.get() else "/"
        
        path = filedialog.askopenfilename(
            title=self.ui_texts['config_select_tesseract'],
            initialdir=initial_dir,
            filetypes=file_types
        )
        
        if path:
            self.tesseract_path_var.set(path)
            self.validate_tesseract_path()
            
    def validate_tesseract_path(self):
        """Validates the Tesseract path and updates the UI."""
        path = self.tesseract_path_var.get()
        
        if not path:
            self.validation_label.config(
                text=self.ui_texts['config_no_path'],
                foreground="red"
            )
            return False
            
        if not os.path.exists(path):
            self.validation_label.config(
                text=self.ui_texts['config_invalid_path'],
                foreground="red"
            )
            return False
            
        # Try to validate by running tesseract version command
        try:
            # Set the path temporarily
            original_path = pytesseract.pytesseract.tesseract_cmd
            pytesseract.pytesseract.tesseract_cmd = path
            
            # Try to get tesseract version
            version = pytesseract.get_tesseract_version()
            
            # Restore original path
            pytesseract.pytesseract.tesseract_cmd = original_path
            
            self.validation_label.config(
                text=self.ui_texts['config_validation_success'].format(version),
                foreground="green"
            )
            return True
            
        except Exception as e:
            # Restore original path
            pytesseract.pytesseract.tesseract_cmd = original_path
            
            self.validation_label.config(
                text=self.ui_texts['config_validation_error'].format(str(e)),
                foreground="red"
            )
            return False
            
    def on_save(self):
        """Handles save button click."""
        if self.validate_tesseract_path():
            # Update config with values from UI
            self.config['tesseract_path'] = self.tesseract_path_var.get()
            
            # Set result and close
            self.result = self.config
            self.dialog.destroy()
        else:
            messagebox.showwarning(
                self.ui_texts['config_invalid_config_title'],
                self.ui_texts['config_invalid_config_message']
            )
            
    def on_cancel(self, event=None):
        """Handles cancel button click or window close."""
        if self.after_id:
            self.dialog.after_cancel(self.after_id)
        self.dialog.destroy()
        
    def show(self):
        """Shows the dialog and returns the result."""
        self.dialog.wait_window()
        return self.result

class ScreenCapturer:
    """Manages screen capturing operations."""

    def __init__(self):
        self.selection_window = None
        self.canvas = None
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.captured_image = None

    def capture_screen(self, root, callback):
        """Starts the screen capture process."""
        self.selection_window = tk.Toplevel(root)
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-alpha', 0.3)
        self.selection_window.config(bg='gray')
        self.selection_window.lift()
        self.selection_window.attributes('-topmost', True)

        self.canvas = tk.Canvas(self.selection_window, cursor='cross')
        self.canvas.pack(fill='both', expand=True)

        self.canvas.bind('<ButtonPress-1>', self.on_button_press)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind(
            '<ButtonRelease-1>',
            lambda event: self.on_button_release(event, callback)
        )
        self.selection_window.bind('<Escape>', self.cancel_capture)

    def on_button_press(self, event):
        """Called when the mouse button is pressed."""
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.rect = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline='red', width=2
        )

    def on_mouse_drag(self, event):
        """Called when the mouse is dragged."""
        current_x, current_y = event.x, event.y
        self.canvas.coords(
            self.rect,
            self.start_x - self.selection_window.winfo_rootx(),
            self.start_y - self.selection_window.winfo_rooty(),
            current_x,
            current_y,
        )

    def on_button_release(self, event, callback):
        """Called when the mouse button is released."""
        end_x = event.x_root
        end_y = event.y_root

        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        self.selection_window.withdraw()
        self.selection_window.update_idletasks()
        time.sleep(0.1)

        self.captured_image = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
        self.selection_window.destroy()

        # Call the callback function
        callback(self.captured_image)

    def cancel_capture(self, event):
        """Cancels the screen capture process."""
        self.selection_window.destroy()

class OCRProcessor:
    """Manages text extraction from images."""

    def __init__(self, language='tur', tesseract_path=None):
        self.language = language
        # Specify the Tesseract path if provided
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_text(self, image):
        """
        Optimized text extraction with preprocessing steps for Tesseract OCR 5.x and later.
        """
        # Convert image to grayscale
        gray = image.convert('L')
        
        tesseract_config = '--oem 1 --psm 6'
        
        # Perform OCR
        text = pytesseract.image_to_string(gray, lang=self.language, config=tesseract_config)
        
        return text

class MainApplication:
    """Manages the main application interface."""

    def __init__(self, root):
        self.root = root
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Load configuration
        self.config = ConfigurationManager.load_config()

        self.delay_options = [0, 3, 5, 10]

        self.delay_var = tk.IntVar(value=0)
        self.language_var = tk.StringVar(value='Türkçe')

        self.captured_image = None
        self.tk_image = None  # To store the PhotoImage object
        self.original_image = None # To store the original PIL Image
        self.initial_window_size = "1280x720" # Define initial window size
        self.resize_job = None # To store the after job for debouncing resize

        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Capture closing event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.create_widgets()
        self.switch_language(self.config['interface_language'])  # Initialize UI with loaded language
        self.root.bind("<Configure>", self.on_window_resize) # Bind window resize event

    def on_closing(self):
        """Called when application is closing, shuts down ThreadPoolExecutor."""
        # Shut down ThreadPoolExecutor
        self.executor.shutdown(wait=False)
        # Close window
        self.root.destroy()

    def create_widgets(self):
        """Creates the interface widgets."""
        # Toolbar Frame
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side='top', fill='x')

        # "+ New" Button
        self.new_button = ttk.Button(toolbar, command=self.start_capture)
        self.new_button.pack(side='left', padx=5, pady=5)

        # Language Selection (OCR Language)
        self.language_label = ttk.Label(toolbar)
        self.language_label.pack(side='left', padx=5)

        self.language_combobox = ttk.Combobox(
            toolbar,
            textvariable=self.language_var,
            state='readonly',
            width=10
        )
        self.language_combobox.pack(side='left', padx=5)

        # Delay Selection
        self.delay_label = ttk.Label(toolbar)
        self.delay_label.pack(side='left', padx=5)

        self.delay_combobox = ttk.Combobox(
            toolbar,
            textvariable=self.delay_var,
            values=self.delay_options,
            state='readonly',
            width=5
        )
        self.delay_combobox.pack(side='left', padx=5)

        # "text" Button
        self.text_button = ttk.Button(toolbar, command=self.on_text_button, state='disabled')
        self.text_button.pack(side='left', padx=5)

        # "image" Button
        self.image_button = ttk.Button(toolbar, command=self.on_image_button, state='disabled')
        self.image_button.pack(side='left', padx=5)

        # 3-dot Menu Button
        menu_button = tk.Menubutton(toolbar, text="...")
        menu_button.pack(side='right', padx=5, pady=5)

        # Create the menu
        menu = tk.Menu(menu_button, tearoff=0)
        menu_button['menu'] = menu

        # Languages submenu
        languages_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label='', menu=languages_menu)
        
        # Configuration option
        menu.add_command(label='', command=self.show_configuration)
        
        # About option
        menu.add_command(label='', command=self.show_about)

        self.languages_menu = languages_menu
        self.menu_button = menu_button
        self.menu = menu

        # Image Display Area
        self.image_label = ttk.Label(self.root, anchor='center') # Added anchor='center' here
        self.image_label.pack(side='top', fill='both', expand=True, padx=5, pady=5)

    def switch_language(self, lang_code):
        """Switches the UI language."""
        # UI texts mapped by language code
        ui_texts_by_language = {
            'tur': {
                'title': 'Ekran Kesme-Kopyalama Aracı',
                'new_button': '+ Yeni',
                'language_label': 'OCR dili:',
                'delay_label': 'Gecikme (sn):',
                'text_button': 'Yazı',
                'image_button': 'Resim',
                'about_title': 'Hakkında',
                'about_message': 'Ekran Alıntısı Aracı\nSürüm 1.0',
                'warning_no_screenshot': 'Önce bir ekran görüntüsü alın.',
                'info_image_copied': 'Resim panoya kopyalandı.',
                'info_text_copied': 'Metin panoya kopyalandı.',
                'error_tesseract_not_found': 'Tesseract OCR bulunamadı. Lütfen Tesseract\'ı yükleyin.',
                'error_ocr': 'OCR işlemi sırasında bir hata oluştu:\n{}',
                'warning_screenshot_failed': 'Ekran görüntüsü alınamadı.',
                'menu_languages': 'Diller',
                'menu_configuration': 'Konfigürasyon',
                'menu_about': 'Hakkında',
                'ocr_languages': ['Türkçe', 'İngilizce'],
                'language_codes': {'Türkçe': 'tur', 'İngilizce': 'eng'},
                # Configuration Dialog texts
                'config_title': 'Konfigürasyon',
                'config_tesseract_path': 'Tesseract OCR Yolu',
                'config_browse': 'Değiştir',
                'config_validate': 'Doğrula',
                'config_save': 'Kaydet',
                'config_cancel': 'İptal',
                'config_no_path': 'Tesseract yolu belirtilmedi!',
                'config_invalid_path': 'Geçersiz yol: Dosya bulunamadı!',
                'config_validation_success': 'Tesseract OCR {} doğrulandı ✓',
                'config_validation_error': 'Doğrulama hatası: {}',
                'config_invalid_config_title': 'Geçersiz Konfigürasyon',
                'config_invalid_config_message': 'Tesseract yolunu doğrulayın ve tekrar deneyin.',
                'config_select_tesseract': 'Tesseract OCR Yürütülebilir Dosyasını Seçin'
            },
            'eng': {
                'title': 'Screen Cut-Copy Tool',
                'new_button': '+ New',
                'language_label': 'OCR lang:',
                'delay_label': 'Delay (s):',
                'text_button': 'Text',
                'image_button': 'Image',
                'about_title': 'About',
                'about_message': 'Screen Capture Tool\nVersion 1.0',
                'warning_no_screenshot': 'Please capture a screenshot first.',
                'info_image_copied': 'Image copied to clipboard.',
                'info_text_copied': 'Text copied to clipboard.',
                'error_tesseract_not_found': 'Tesseract OCR not found. Please install Tesseract.',
                'error_ocr': 'An error occurred during OCR:\n{}',
                'warning_screenshot_failed': 'Failed to capture the screenshot.',
                'menu_languages': 'Languages',
                'menu_configuration': 'Configuration',
                'menu_about': 'About',
                'ocr_languages': ['Turkish', 'English'],
                'language_codes': {'Turkish': 'tur', 'English': 'eng'},
                # Configuration Dialog texts
                'config_title': 'Configuration',
                'config_tesseract_path': 'Tesseract OCR Path',
                'config_browse': 'Browse',
                'config_validate': 'Validate',
                'config_save': 'Save',
                'config_cancel': 'Cancel',
                'config_no_path': 'Tesseract path not specified!',
                'config_invalid_path': 'Invalid path: File not found!',
                'config_validation_success': 'Tesseract OCR {} validated ✓',
                'config_validation_error': 'Validation error: {}',
                'config_invalid_config_title': 'Invalid Configuration',
                'config_invalid_config_message': 'Please validate the Tesseract path and try again.',
                'config_select_tesseract': 'Select Tesseract OCR Executable'
            }
        }

        self.ui_texts = ui_texts_by_language.get(lang_code, ui_texts_by_language['tur'])
        self.language_options = self.ui_texts['language_codes']
        
        # Save the language choice to config
        self.config['interface_language'] = lang_code
        ConfigurationManager.save_config(self.config)

        # Update UI texts
        self.update_ui_texts()

    def update_ui_texts(self):
        """Updates the UI texts based on the selected language."""
        ui = self.ui_texts  # Shortcut

        self.root.title(ui['title'])
        self.new_button.config(text=ui['new_button'])
        self.language_label.config(text=ui['language_label'])
        self.delay_label.config(text=ui['delay_label'])
        self.text_button.config(text=ui['text_button'])
        self.image_button.config(text=ui['image_button'])
        self.menu_button.config(text='...')

        # Update OCR language combobox values
        self.language_combobox.config(values=list(self.language_options.keys()))
        self.language_combobox.set(list(self.language_options.keys())[0])

        # Update menu items
        self.menu.delete(0, 'end')
        languages_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label=ui['menu_languages'], menu=languages_menu)
        for lang_name, lang_code in self.language_options.items():
            languages_menu.add_command(
                label=lang_name,
                command=lambda code=lang_code: self.switch_language(code)
            )
        self.menu.add_command(label=ui['menu_configuration'], command=self.show_configuration)
        self.menu.add_command(label=ui['menu_about'], command=self.show_about)

    def show_configuration(self):
        """Shows the configuration dialog."""
        dialog = ConfigurationDialog(self.root, self.config, self.ui_texts)
        result = dialog.show()
        
        if result:
            # Update configuration
            self.config = result
            # Save configuration
            ConfigurationManager.save_config(self.config)
    
    def start_capture(self):
        """Starts the screen capture process."""
        delay = self.delay_var.get()

        # Hide the main window immediately
        self.root.withdraw()

        # If there is a delay, use 'after' to delay the process
        if delay > 0:
            self.root.after(delay * 1000, self.capture_process)
        else:
            self.capture_process()

    def capture_process(self):
        """Performs the screen capture process."""
        capturer = ScreenCapturer()
        capturer.capture_screen(self.root, self.process_captured_image)

    def process_captured_image(self, captured_image):
        """Processes the captured image."""
        if captured_image:
            self.captured_image = captured_image
            self.original_image = captured_image.copy() # Store original image
            self.root.geometry(self.initial_window_size) # Set window size here
            # Submit image display to executor
            self.executor.submit(self.display_captured_image, captured_image)
            self.image_button.config(state='normal')
            self.text_button.config(state='normal')
        else:
            messagebox.showwarning('Warning', self.ui_texts['warning_screenshot_failed'])
        self.root.deiconify()

    def display_captured_image(self, image):
        """Displays the captured image in the main window in a separate thread."""
        self.resize_image() # Resize image
        # Update image label in main thread using root.after
        self.root.after(0, self._update_image_label)

    def _update_image_label(self):
        """Updates the image label with the resized image in the main thread."""
        self.image_label.configure(image=self.tk_image)
        self.image_label.image = self.tk_image  # Keep a reference

    def resize_image(self):
        """Resizes the image to fit the window size, maintaining aspect ratio and preventing enlargement."""
        if self.original_image is None:
            return

        label_width = self.image_label.winfo_width()
        label_height = self.image_label.winfo_height()

        if label_width <= 1 or label_height <= 1:
            # Label size not yet determined, or window minimized, skip resizing for now.
            # It will be called again when window is configured.
            return

        original_width, original_height = self.original_image.size

        if original_width <= label_width and original_height <= label_height:
            # No need to resize if original image is smaller than label
            resized_image = self.original_image
        else:
            width_ratio = label_width / original_width
            height_ratio = label_height / original_height
            scale_factor = min(width_ratio, height_ratio)

            if scale_factor < 1: # Only scale down, not up
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                resized_image = self.original_image # If no scaling needed, use original

        self.tk_image = ImageTk.PhotoImage(resized_image)

    def on_window_resize(self, event):
        """Handles window resize events with debouncing."""
        if self.original_image:
            if self.resize_job:
                self.root.after_cancel(self.resize_job)
            self.resize_job = self.root.after(50, self.debounced_resize_and_update_image)

    def debounced_resize_and_update_image(self):
        """Calls resize and update image and clears the resize job."""
        self.resize_and_update_image()
        self.resize_job = None # Clear the job after execution

    def resize_and_update_image(self):
        """Resizes the image and updates the label, ensuring thread safety."""
        self.resize_image()
        self.root.after(0, self._update_image_label) # Schedule label update on main thread

    def on_image_button(self):
        """Handles the 'image' button click."""
        if self.captured_image:
            self.executor.submit(self.copy_image_to_clipboard)
        else:
            messagebox.showwarning('Warning', self.ui_texts['warning_no_screenshot'])

    def on_text_button(self):
        """Handles the 'Text' button click."""
        if self.captured_image:
            self.executor.submit(self.perform_ocr)
        else:
            messagebox.showwarning('Warning', self.ui_texts['warning_no_screenshot'])

    def copy_image_to_clipboard(self):
        """Copies the image to the clipboard."""
        try:
            if os.name == 'nt':
                # Windows-specific code
                from io import BytesIO
                import win32clipboard
                output = BytesIO()
                self.captured_image.convert('RGB').save(output, 'BMP')
                data = output.getvalue()[14:]
                output.close()

                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                messagebox.showinfo('Info', self.ui_texts['info_image_copied'])
            else:
                # For other platforms, attempt to copy using PIL/Pyperclip
                try:
                    # Attempt to copy image to clipboard using Tkinter
                    self.root.clipboard_clear()
                    self.root.clipboard_append(self.captured_image)
                    messagebox.showinfo('Info', self.ui_texts['info_image_copied'])
                except Exception:
                    # If it fails, inform the user
                    messagebox.showinfo(
                        'Info',
                        'Cannot copy image to clipboard. This feature is not supported on the current platform.'
                    )
        except Exception as e:
            messagebox.showerror('Error', f'Failed to copy image to clipboard:\n{e}')

    def perform_ocr(self):
        """Performs OCR on the captured image."""
        try:
            selected_language = self.language_options.get(self.language_var.get(), 'tur')
            ocr_processor = OCRProcessor(
                language=selected_language, 
                tesseract_path=self.config.get('tesseract_path')
            )
            extracted_text = ocr_processor.extract_text(self.captured_image)
            pyperclip.copy(extracted_text)
            messagebox.showinfo('Info', self.ui_texts['info_text_copied'])
        except pytesseract.pytesseract.TesseractNotFoundError:
            messagebox.showerror(
                'Error', self.ui_texts['error_tesseract_not_found']
            )
        except Exception as e:
            messagebox.showerror('Error', self.ui_texts['error_ocr'].format(e))

    def show_about(self):
       """Displays the 'About' window."""
       messagebox.showinfo(self.ui_texts['about_title'], self.ui_texts['about_message'])

if __name__ == '__main__':
   make_dpi_aware()
   root = tk.Tk()
   app = MainApplication(root)
   root.mainloop()
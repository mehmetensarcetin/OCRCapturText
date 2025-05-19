import os
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import functools # Added for functools.wraps

import ctypes
import pyautogui
import pyperclip
import pytesseract
from PIL import Image, ImageTk, ImageOps
from concurrent.futures import ThreadPoolExecutor

def make_dpi_aware():
    """Makes the application DPI aware to ensure proper display scaling on Windows systems."""
    if os.name == 'nt':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

class ConfigurationManager:
    """Manages application configuration settings through loading and saving to a JSON file."""
    DEFAULT_CONFIG = {
        'tesseract_path': r'C:\Program Files\Tesseract-OCR\tesseract.exe' if os.name == 'nt' else '',
        'interface_language': 'tur'
    }
    CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.screen_capture_config.json')
    
    @classmethod
    def load_config(cls):
        """Loads configuration from file or returns default configuration if file not found or invalid."""
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
        """Saves configuration to file and returns success status."""
        try:
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False

class ConfigurationDialog:
    """Dialog window for configuring application settings with validation capabilities."""
    
    def __init__(self, parent, config, ui_texts):
        self.parent = parent
        self.config = config.copy()  # Work with a copy
        self.ui_texts = ui_texts
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(self.ui_texts['config_title'])
        self.dialog.geometry("550x250")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        x = parent.winfo_x() + (parent.winfo_width() - 550) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 250) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.dialog.bind("<Escape>", self.on_cancel)
        
    def _update_validation_label(self, message_key, color, *format_args):
        """Updates the validation label with formatted text and specified color."""
        text = self.ui_texts[message_key]
        if format_args:
            text = text.format(*format_args)
        self.validation_label.config(text=text, foreground=color)

    def _show_message_from_ui_texts(self, msg_func, title_key, message_key, *format_args):
        """Displays a messagebox with text from the UI translations dictionary."""
        title = self.ui_texts.get(title_key, title_key) 
        message = self.ui_texts[message_key]
        if format_args:
            message = message.format(*format_args)
        msg_func(title, message, parent=self.dialog) # Ensure message box is child of dialog

    def create_widgets(self):
        """Creates and arranges all dialog widgets including entry fields and buttons."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        path_frame = ttk.LabelFrame(main_frame, text=self.ui_texts['config_tesseract_path'], padding="10")
        path_frame.pack(fill='x', pady=10)
        
        path_row = ttk.Frame(path_frame)
        path_row.pack(fill='x', pady=5)
        
        self.tesseract_path_var = tk.StringVar(value=self.config.get('tesseract_path', ''))
        self.path_entry = ttk.Entry(path_row, textvariable=self.tesseract_path_var, width=50)
        self.path_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        browse_button = ttk.Button(path_row, text=self.ui_texts['config_browse'], command=self.browse_tesseract_path)
        browse_button.pack(side='left')
        
        validate_container = ttk.Frame(path_frame)
        validate_container.pack(fill='x', pady=5)
        
        validate_button = ttk.Button(validate_container, text=self.ui_texts['config_validate'], command=self.validate_tesseract_path)
        validate_button.pack(side='right')
        
        self.validation_label = ttk.Label(validate_container, text="")
        self.validation_label.pack(side='left', fill='x', expand=True)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', side='bottom', pady=10)
        
        cancel_button = ttk.Button(button_frame, text=self.ui_texts['config_cancel'], command=self.on_cancel)
        cancel_button.pack(side='right', padx=5)
        
        save_button = ttk.Button(button_frame, text=self.ui_texts['config_save'], command=self.on_save)
        save_button.pack(side='right', padx=5)
        
        self.after_id = self.dialog.after(100, self.validate_tesseract_path)
        
    def browse_tesseract_path(self):
        """Opens a file dialog to browse and select the Tesseract executable path."""
        file_types = [("Executable files", "*.exe")] if os.name == 'nt' else [("All files", "*")]
        initial_dir = os.path.dirname(self.tesseract_path_var.get()) if self.tesseract_path_var.get() else "/"
        
        path = filedialog.askopenfilename(
            title=self.ui_texts['config_select_tesseract'],
            initialdir=initial_dir,
            filetypes=file_types,
            parent=self.dialog # Ensure filedialog is child of dialog
        )
        
        if path:
            self.tesseract_path_var.set(path)
            self.validate_tesseract_path()
            
    def validate_tesseract_path(self):
        """Validates if the selected Tesseract path is correct and functional."""
        path = self.tesseract_path_var.get()
        
        if not path:
            self._update_validation_label('config_no_path', "red")
            return False
            
        if not os.path.exists(path):
            self._update_validation_label('config_invalid_path', "red")
            return False
            
        original_path = pytesseract.pytesseract.tesseract_cmd
        try:
            pytesseract.pytesseract.tesseract_cmd = path
            version = pytesseract.get_tesseract_version()
            self._update_validation_label('config_validation_success', "green", version)
            return True
        except Exception as e:
            self._update_validation_label('config_validation_error', "red", str(e))
            return False
        finally:
            pytesseract.pytesseract.tesseract_cmd = original_path # Ensure restoration
            
    def on_save(self):
        """Handles the save button click by validating and storing configuration changes."""
        if self.validate_tesseract_path():
            self.config['tesseract_path'] = self.tesseract_path_var.get()
            self.result = self.config
            self.dialog.destroy()
        else:
            self._show_message_from_ui_texts(
                messagebox.showwarning,
                'config_invalid_config_title',
                'config_invalid_config_message'
            )
            
    def on_cancel(self, event=None):
        """Handles dialog cancellation by closing without saving changes."""
        if hasattr(self, 'after_id') and self.after_id: # Check if after_id exists
            self.dialog.after_cancel(self.after_id)
            self.after_id = None # Clear it
        self.dialog.destroy()
        
    def show(self):
        """Shows the dialog modally and returns the result after it's closed."""
        self.dialog.wait_window()
        return self.result

class ScreenCapturer:
    """Manages the screen capture interface and process."""

    def __init__(self):
        self.selection_window = None
        self.canvas = None
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.captured_image = None

    def capture_screen(self, root, callback):
        """Creates a fullscreen overlay for selecting a screen area to capture."""
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
        """Handles mouse button press to start area selection."""
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.rect = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline='red', width=2
        )

    def on_mouse_drag(self, event):
        """Updates selection rectangle as mouse is dragged."""
        current_x, current_y = event.x, event.y
        self.canvas.coords(
            self.rect,
            self.start_x - self.selection_window.winfo_rootx(),
            self.start_y - self.selection_window.winfo_rooty(),
            current_x,
            current_y,
        )

    def on_button_release(self, event, callback):
        """Captures the selected screen area when mouse button is released."""
        end_x = event.x_root
        end_y = event.y_root

        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        self.selection_window.withdraw()

        try:
            # Ensure coordinates are valid
            width = x2 - x1
            height = y2 - y1
            if width > 0 and height > 0:
                self.captured_image = pyautogui.screenshot(region=(x1, y1, width, height))
            else:
                self.captured_image = None # No valid region selected
        except Exception as e:
            print(f"Error during screenshot: {e}") # Log error
            self.captured_image = None
        finally:
            self.selection_window.destroy()
            self.selection_window = None # Clear reference

        # Call the callback function
        callback(self.captured_image)

    def cancel_capture(self, event=None):
        """Cancels the screen capture process when Escape is pressed."""
        if self.selection_window:
            self.selection_window.destroy()
            self.selection_window = None

class OCRProcessor:
    """Handles text extraction from images using optical character recognition."""

    def __init__(self, language='tur', tesseract_path=None):
        self.language = language
        if tesseract_path: # This sets it globally for pytesseract if path is provided
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_text(self, image):
        """
        Extracts text from an image using Tesseract OCR with optimized settings.
        
        Args:
            image: PIL Image object containing the captured screen area
            
        Returns:
            Extracted text as a string
        """
        gray = image.convert('L')
        tesseract_config = '--oem 1 --psm 6'
        text = pytesseract.image_to_string(gray, lang=self.language, config=tesseract_config)
        return text

# Decorator to ensure a screenshot has been captured
def require_capture(func):
    """
    Decorator that ensures a screenshot has been captured before executing the decorated function.
    Shows a warning message if no screenshot is available.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.captured_image:
            return func(self, *args, **kwargs)
        else:
            self._show_message_from_ui_texts(
                messagebox.showwarning,
                'warning_title',
                'warning_no_screenshot'
            )
    return wrapper

class MainApplication:
    """Main application class that manages the overall UI and workflow."""

    UI_TEXTS_BY_LANGUAGE = {
        'tur': {
            'title': 'Ekran Kesme-Kopyalama Aracı',
            'new_button': '+ Yeni',
            'language_label': 'OCR dili:',
            'delay_label': 'Gecikme (sn):',
            'text_button': 'Yazı',
            'image_button': 'Resim',
            'about_title': 'Hakkında',
            'about_message': 'Ekran Alıntısı Aracı\nSürüm 1.1',
            'warning_no_screenshot': 'Önce bir ekran görüntüsü alın.',
            'info_image_copied': 'Resim panoya kopyalandı.',
            'info_text_copied': 'Metin panoya kopyalandı.',
            'error_tesseract_not_found': 'Tesseract OCR bulunamadı. Lütfen Tesseract\'ı yükleyin veya yolunu yapılandırın.',
            'error_ocr': 'OCR işlemi sırasında bir hata oluştu:\n{}',
            'warning_screenshot_failed': 'Ekran görüntüsü alınamadı.',
            'menu_languages': 'Diller',
            'menu_configuration': 'Ayarlar',
            'menu_about': 'Hakkında',
            'ocr_languages': ['Türkçe', 'İngilizce'],
            'language_codes': {'Türkçe': 'tur', 'İngilizce': 'eng'},
            'config_title': 'Ayarlar',
            'config_tesseract_path': 'Tesseract OCR Yolu',
            'config_browse': 'Gözat',
            'config_validate': 'Doğrula',
            'config_save': 'Kaydet',
            'config_cancel': 'İptal',
            'config_no_path': 'Tesseract yolu belirtilmedi!',
            'config_invalid_path': 'Geçersiz yol: Dosya bulunamadı!',
            'config_validation_success': 'Tesseract OCR {} doğrulandı ✓',
            'config_validation_error': 'Doğrulama hatası:\n{}',
            'config_invalid_config_title': 'Geçersiz Ayarlar',
            'config_invalid_config_message': 'Lütfen Tesseract yolunu doğrulayın ve tekrar deneyin.',
            'config_select_tesseract': 'Tesseract OCR Çalıştırılabilir Dosyasını Seçin',
            'error_copy_image_failed': 'Resmi panoya kopyalama başarısız:\n{}',
            'info_copy_not_supported': 'Resim panoya kopyalanamıyor. Bu özellik mevcut platformda desteklenmiyor.',
            'warning_title': 'Uyarı',
            'info_title': 'Bilgi',
            'error_title': 'Hata'
        },
        'eng': {
            'title': 'Screen Cut-Copy Tool',
            'new_button': '+ New',
            'language_label': 'OCR lang:',
            'delay_label': 'Delay (s):',
            'text_button': 'Text',
            'image_button': 'Image',
            'about_title': 'About',
            'about_message': 'Screen Capture Tool\nVersion 1.1',
            'warning_no_screenshot': 'Please capture a screenshot first.',
            'info_image_copied': 'Image copied to clipboard.',
            'info_text_copied': 'Text copied to clipboard.',
            'error_tesseract_not_found': 'Tesseract OCR not found. Please install Tesseract or configure its path.',
            'error_ocr': 'An error occurred during OCR:\n{}',
            'warning_screenshot_failed': 'Failed to capture the screenshot.',
            'menu_languages': 'Languages',
            'menu_configuration': 'Settings',
            'menu_about': 'About',
            'ocr_languages': ['Turkish', 'English'],
            'language_codes': {'Turkish': 'tur', 'English': 'eng'},
            'config_title': 'Settings',
            'config_tesseract_path': 'Tesseract OCR Path',
            'config_browse': 'Browse',
            'config_validate': 'Validate',
            'config_save': 'Save',
            'config_cancel': 'Cancel',
            'config_no_path': 'Tesseract path not specified!',
            'config_invalid_path': 'Invalid path: File not found!',
            'config_validation_success': 'Tesseract OCR {} validated ✓',
            'config_validation_error': 'Validation error:\n{}',
            'config_invalid_config_title': 'Invalid Settings',
            'config_invalid_config_message': 'Please validate the Tesseract path and try again.',
            'config_select_tesseract': 'Select Tesseract OCR Executable',
            'error_copy_image_failed': 'Failed to copy image to clipboard:\n{}',
            'info_copy_not_supported': 'Cannot copy image to clipboard. This feature is not supported on the current platform.',
            'warning_title': 'Warning',
            'info_title': 'Info',
            'error_title': 'Error'
        }
    }

    def __init__(self, root):
        self.root = root
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.config = ConfigurationManager.load_config()
        self.ui_texts = self.UI_TEXTS_BY_LANGUAGE.get(self.config['interface_language'], self.UI_TEXTS_BY_LANGUAGE['tur'])
        self.language_options = self.ui_texts['language_codes']

        self.delay_options = [0, 3, 5, 10]
        self.delay_var = tk.IntVar(value=0)
        # Initialize language_var with a value that exists in the current language_options
        # Find the key for the current OCR language (default to first if not found)
        current_ocr_lang_display = self.ui_texts['ocr_languages'][0] # Default to first ocr language display name
        self.language_var = tk.StringVar(value=current_ocr_lang_display)


        self.captured_image = None
        self.tk_image = None
        self.original_image = None
        self.initial_window_size = "1280x720"
        self.resize_job = None

        self.executor = ThreadPoolExecutor(max_workers=2)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.create_widgets()
        self.switch_language(self.config['interface_language']) 
        self.root.bind("<Configure>", self.on_window_resize)

    def _show_message_from_ui_texts(self, msg_func, title_key, message_key, *format_args):
        """Displays a message box with text from UI translations dictionary."""
        title = self.ui_texts.get(title_key, title_key) 
        message = self.ui_texts[message_key]
        if format_args:
            message = message.format(*format_args)
        msg_func(title, message)

    def on_closing(self):
        """Handles application shutdown by cleaning up resources."""
        self.executor.shutdown(wait=False)
        self.root.destroy()

    def create_widgets(self):
        """Creates and organizes all application UI elements."""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side='top', fill='x')

        self.new_button = ttk.Button(toolbar, command=self.start_capture)
        self.new_button.pack(side='left', padx=5, pady=5)

        self.language_label = ttk.Label(toolbar)
        self.language_label.pack(side='left', padx=5)

        self.language_combobox = ttk.Combobox(
            toolbar, textvariable=self.language_var, state='readonly', width=10
        )
        self.language_combobox.pack(side='left', padx=5)

        self.delay_label = ttk.Label(toolbar)
        self.delay_label.pack(side='left', padx=5)

        self.delay_combobox = ttk.Combobox(
            toolbar, textvariable=self.delay_var, values=self.delay_options, state='readonly', width=5
        )
        self.delay_combobox.pack(side='left', padx=5)

        self.text_button = ttk.Button(toolbar, command=self.on_text_button, state='disabled')
        self.text_button.pack(side='left', padx=5)

        self.image_button = ttk.Button(toolbar, command=self.on_image_button, state='disabled')
        self.image_button.pack(side='left', padx=5)

        self.menu_button = tk.Menubutton(toolbar, text="...") # Store as instance var for update_ui_texts
        self.menu_button.pack(side='right', padx=5, pady=5)

        self.menu = tk.Menu(self.menu_button, tearoff=0) # Store as instance var
        self.menu_button['menu'] = self.menu
        
        # Image Display Area
        self.image_label = ttk.Label(self.root, anchor='center')
        self.image_label.pack(side='top', fill='both', expand=True, padx=5, pady=5)

    def switch_language(self, lang_code):
        """Switches the interface language and updates all UI elements accordingly."""
        self.ui_texts = self.UI_TEXTS_BY_LANGUAGE.get(lang_code, self.UI_TEXTS_BY_LANGUAGE['tur'])
        self.language_options = self.ui_texts['language_codes']
        
        self.config['interface_language'] = lang_code
        ConfigurationManager.save_config(self.config)
        self.update_ui_texts()

    def update_ui_texts(self):
        """Updates all UI elements with text from the current language dictionary."""
        ui = self.ui_texts

        self.root.title(ui['title'])
        self.new_button.config(text=ui['new_button'])
        self.language_label.config(text=ui['language_label'])
        self.delay_label.config(text=ui['delay_label'])
        self.text_button.config(text=ui['text_button'])
        self.image_button.config(text=ui['image_button'])
        self.menu_button.config(text='...') # Or a localized version if desired

        # Update OCR language combobox values and selection
        self.language_combobox.config(values=ui['ocr_languages'])
        # Try to keep current selection if possible, or default
        current_selection = self.language_var.get()
        if current_selection not in ui['ocr_languages']:
            self.language_var.set(ui['ocr_languages'][0])
        else:
             self.language_var.set(current_selection) # Re-set to ensure it's valid

        # Rebuild menu with new texts
        self.menu.delete(0, 'end')
        
        # Interface Languages submenu
        interface_languages_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label=ui['menu_languages'], menu=interface_languages_menu)
        # Add options for English and Turkish interface languages
        interface_languages_menu.add_command(
            label="Türkçe", # Literal, as this is for language selection itself
            command=lambda: self.switch_language('tur')
        )
        interface_languages_menu.add_command(
            label="English", # Literal
            command=lambda: self.switch_language('eng')
        )
        
        self.menu.add_command(label=ui['menu_configuration'], command=self.show_configuration)
        self.menu.add_command(label=ui['menu_about'], command=self.show_about)

    def show_configuration(self):
        """Displays the configuration dialog and processes the result."""
        dialog = ConfigurationDialog(self.root, self.config, self.ui_texts)
        result = dialog.show()
        if result:
            self.config = result
            ConfigurationManager.save_config(self.config)
            # Potentially re-initialize OCRProcessor or update its path if it's an instance variable
            # For now, OCRProcessor is created on-demand in perform_ocr

    def start_capture(self):
        """Initiates the screen capture process with optional delay."""
        delay = self.delay_var.get()
        self.root.withdraw()
        if delay > 0:
            self.root.after(delay * 1000, self.capture_process)
        else:
            # A very small delay can sometimes help ensure the window is fully hidden
            self.root.after(50, self.capture_process) 

    def capture_process(self):
        """Executes the actual screen capture operation."""
        capturer = ScreenCapturer()
        capturer.capture_screen(self.root, self.process_captured_image)

    def process_captured_image(self, captured_image):
        """Processes and displays the captured image."""
        self.root.deiconify() # Show main window first
        if captured_image:
            self.captured_image = captured_image
            self.original_image = captured_image.copy()
            self.root.geometry(self.initial_window_size)
            self.executor.submit(self.display_captured_image, captured_image)
            self.image_button.config(state='normal')
            self.text_button.config(state='normal')
        else:
            self._show_message_from_ui_texts(messagebox.showwarning, 'warning_title', 'warning_screenshot_failed')

    def display_captured_image(self, image):
        """Prepares the captured image for display in the UI."""
        self.resize_image() 
        self.root.after(0, self._update_image_label)

    def _update_image_label(self):
        """Updates the image label with the currently resized image."""
        self.image_label.configure(image=self.tk_image)
        self.image_label.image = self.tk_image

    def resize_image(self):
        """Resizes the captured image to fit the display area while maintaining aspect ratio."""
        if self.original_image is None:
            return

        label_width = self.image_label.winfo_width()
        label_height = self.image_label.winfo_height()

        if label_width <= 1 or label_height <= 1:
            return

        original_width, original_height = self.original_image.size

        if original_width <= label_width and original_height <= label_height:
            resized_image = self.original_image
        else:
            width_ratio = label_width / original_width
            height_ratio = label_height / original_height
            scale_factor = min(width_ratio, height_ratio)
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            # Ensure new dimensions are at least 1px
            new_width = max(1, new_width)
            new_height = max(1, new_height)
            resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        self.tk_image = ImageTk.PhotoImage(resized_image)

    def on_window_resize(self, event):
        """Handles window resize events by debouncing and triggering image resizing."""
        if self.original_image:
            if self.resize_job:
                self.root.after_cancel(self.resize_job)
            self.resize_job = self.root.after(100, self.debounced_resize_and_update_image) # Increased debounce time

    def debounced_resize_and_update_image(self):
        """Executes image resize after debounce timeout to avoid excessive processing."""
        self.resize_and_update_image()
        self.resize_job = None

    def resize_and_update_image(self):
        """Performs image resize and schedules UI update."""
        self.resize_image()
        if self.tk_image: # Ensure tk_image was created
            self.root.after(0, self._update_image_label)

    @require_capture
    def on_image_button(self):
        """Handles image button click by copying the captured image to clipboard."""
        self.executor.submit(self.copy_image_to_clipboard)

    @require_capture
    def on_text_button(self):
        """Handles text button click by extracting and copying text from the image."""
        self.executor.submit(self.perform_ocr)

    def copy_image_to_clipboard(self):
        """Copies the captured image to the system clipboard if supported by the platform."""
        try:
            if os.name == 'nt':
                from io import BytesIO
                import win32clipboard # This import should ideally be at the top, guarded by os.name check
                
                output = BytesIO()
                # Ensure image is not RGBA if format is BMP which doesn't support alpha well for clipboard
                image_to_copy = self.captured_image
                if image_to_copy.mode == 'RGBA':
                    image_to_copy = image_to_copy.convert('RGB')
                
                image_to_copy.save(output, 'BMP')
                data = output.getvalue()[14:] # Skip BMP header
                output.close()

                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                self._show_message_from_ui_texts(messagebox.showinfo, 'info_title', 'info_image_copied')
            else:
                # For other platforms, this is often problematic or not supported directly by generic libraries
                # Pyperclip handles text, not images typically. Tkinter's clipboard_append for images is also limited.
                self._show_message_from_ui_texts(messagebox.showinfo, 'info_title', 'info_copy_not_supported')
        except Exception as e:
            self._show_message_from_ui_texts(messagebox.showerror, 'error_title', 'error_copy_image_failed', e)

    def perform_ocr(self):
        """Extracts text from the captured image using OCR and copies it to clipboard."""
        try:
            # Get the OCR language code from the selected display name
            selected_ocr_display_name = self.language_var.get()
            ocr_lang_code = 'tur' # Default
            for display_name, code in self.language_options.items():
                # This assumes self.language_options maps UI display name to code.
                # The current setup has self.ui_texts['ocr_languages'] for display and self.ui_texts['language_codes'] for mapping.
                # We need to map from the display name in combobox to the code.
                # Example: if combobox shows "Türkçe", we need "tur".
                # This requires a reverse lookup or a more direct mapping if combobox stored codes.
                # For simplicity, let's adjust how language_options is used or how combobox is populated.
                # Current: self.language_options = self.ui_texts['language_codes'] -> {'Türkçe': 'tur', 'İngilizce': 'eng'}
                # So, this is correct:
                if selected_ocr_display_name in self.language_options:
                     ocr_lang_code = self.language_options[selected_ocr_display_name]

            ocr_processor = OCRProcessor(
                language=ocr_lang_code, 
                tesseract_path=self.config.get('tesseract_path')
            )
            extracted_text = ocr_processor.extract_text(self.captured_image)
            pyperclip.copy(extracted_text)
            self._show_message_from_ui_texts(messagebox.showinfo, 'info_title', 'info_text_copied')
        except pytesseract.pytesseract.TesseractNotFoundError:
            self._show_message_from_ui_texts(messagebox.showerror, 'error_title', 'error_tesseract_not_found')
        except Exception as e:
            self._show_message_from_ui_texts(messagebox.showerror, 'error_title', 'error_ocr', e)

    def show_about(self):
       """Displays the about dialog with application information."""
       self._show_message_from_ui_texts(messagebox.showinfo, 'about_title', 'about_message')

if __name__ == '__main__':
   make_dpi_aware()
   # Conditional import for win32clipboard if it's only used in one place
   # However, it's better practice to have imports at the top.
   # If win32clipboard is Windows-only, the copy_image_to_clipboard already checks os.name.
   root = tk.Tk()
   app = MainApplication(root)
   root.mainloop()
# OCRCapturText

OCRCapturText is a lightweight, cross-platform screen capture tool with integrated OCR (Optical Character Recognition) capabilities. It allows users to capture a portion of their screen and extract text from the captured image or copy the image directly to the clipboard.

### Features

- **Screen Region Capture**: Select any area of your screen to capture
- **OCR Text Extraction**: Extract text from captured images using Tesseract OCR
- **Multi-language Support**: 
  - Interface available in English and Turkish
  - OCR supports various languages (Turkish and English included by default)
- **Configurable Delay**: Set a delay timer (0, 3, 5, or 10 seconds) before capture
- **Copy Options**: Copy either the image or the extracted text to clipboard
- **Multi-language interface**: English and Turkish(It can be increased in a simple way in the code)
- **Customizable Settings**: Configure Tesseract OCR path for better performance

### Demos

https://github.com/user-attachments/assets/d6386b4b-e2d6-4afe-b27d-87f9ca4c9c85

### Basic Workflow:
1. Click the "+ New" button to start a capture
2. Select a capture delay if needed (0, 3, 5, or 10 seconds)
3. Select the OCR language (Turkish or English)
4. When the screen dims, click and drag to select the region you want to capture
5. After capture, the image appears in the main window
6. Use "Text" button to extract text (copied to clipboard automatically)
7. Use "Image" button to copy the image to clipboard(Windows only)

### Known Limitations

- Image clipboard functionality is fully supported only on Windows
- The application requires Tesseract OCR to be installed and properly configured
- Low accuracy due to Tesseract OCR (accuracy can be improved with image processing)

OCRCapturText is an open source project developed for personal needs. You can shape the project according to your own needs and customize it easily thanks to its open source structure.

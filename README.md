# SimImageView

A simple and elegant image viewer built with PySide6, inspired by Microsoft's native image viewer.

## Features

- **Image Loading**: Open individual images or entire folders
- **Navigation**: Browse through multiple images in a folder
- **Zoom Controls**: Zoom in/out with mouse wheel or menu options
- **Image Rotation**: Rotate images 90 degrees left or right
- **Fit to Window**: Automatically fit images to window size
- **Drag & Drop**: Simply drag and drop images to open them
- **Copy to Clipboard**: Copy images directly to clipboard
- **Pan Support**: Middle-click and drag to pan around images
- **Modern UI**: Clean, minimalist interface with English text

## Installation

### Requirements
- Python 3.8 or higher
- PySide6
- Pillow

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Huskar-Silencer/SimImageView.git
cd SimImageView
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Usage

### Opening Images
- **File → Open**: Open a single image
- **File → Open Folder**: Open all images from a folder
- **Drag & Drop**: Drag and drop images onto the viewer

### Navigation
- **Up Arrow** or **Previous Button**: View previous image
- **Down Arrow** or **Next Button**: View next image

### Zoom & View
- **Mouse Wheel**: Zoom in/out
- **Ctrl+Plus**: Zoom in
- **Ctrl+Minus**: Zoom out
- **F**: Fit image to window
- **Ctrl+0**: Show at actual size

### Image Manipulation
- **Left Arrow**: Rotate left 90°
- **Right Arrow**: Rotate right 90°
- **Middle Mouse Button + Drag**: Pan around image

### Other
- **Ctrl+C**: Copy image to clipboard
- **Ctrl+Q**: Exit application

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open File | Ctrl+O |
| Open Folder | Ctrl+Shift+O |
| Exit | Ctrl+Q |
| Copy | Ctrl+C |
| Zoom In | Ctrl++ |
| Zoom Out | Ctrl+- |
| Fit to Window | F |
| Actual Size | Ctrl+0 |
| Rotate Left | Left Arrow |
| Rotate Right | Right Arrow |
| Previous Image | Up Arrow |
| Next Image | Down Arrow |

## Project Structure

```
SimImageView/
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── ui/
│   ├── __init__.py
│   ├── main_window.py  # Main application window
│   └── image_viewer.py # Image display widget
└── utils/
    ├── __init__.py
    ├── constants.py    # Application constants
    └── image_handler.py # Image loading and processing
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

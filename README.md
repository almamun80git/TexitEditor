# TexitEditor

![TexitEditor Logo](assets/images/logo.png)

## Overview
TexitEditor is a modern text editor application inspired by TextPad but with a contemporary UI and retro text styling. Perfect for note-taking and text editing with a nostalgic feel combined with modern functionality.

## Features
- **Clean, Modern Interface**: Responsive UI with intuitive controls
- **Retro Text Styling**: Enjoy the nostalgic feel of classic text editors
- **Custom Color Schemes**: Blue, green, and purple shade options to customize your experience
- **Basic Text Operations**: Cut, copy, paste, undo, redo
- **File Management**: Open, save, and create new text files
- **Find & Replace**: Quickly locate and modify text
- **Syntax Highlighting**: Support for common programming languages
- **Line Numbers**: Toggle-able line numbering
- **Auto-save**: Prevent data loss with automatic saving
- **Customizable Font Options**: Change font style and size

## Screenshots
![Main Interface](assets/images/screenshot1.png)
![Settings Panel](assets/images/screenshot2.png)

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Steps
1. Clone the repository:
```bash
git clone https://github.com/almamun80git/TexitEditor.git
cd TexitEditor
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Launch the application:
```bash
python src/main.py
```

## Usage
- **Creating a new file**: Click on File > New or use Ctrl+N
- **Opening a file**: Click on File > Open or use Ctrl+O
- **Saving a file**: Click on File > Save or use Ctrl+S
- **Changing theme**: Navigate to Settings > Themes and select your preferred color scheme
- **Find text**: Press Ctrl+F and enter the text you want to find
- **Replace text**: Press Ctrl+H to open the find and replace dialog

## Project Structure
```
TexitEditor/
├── assets/
│   ├── fonts/
│   │   └── retro_font.ttf
│   ├── images/
│   │   ├── logo.png
│   │   └── screenshots/
│   └── themes/
│       ├── blue_theme.json
│       ├── green_theme.json
│       └── purple_theme.json
├── src/
│   ├── main.py
│   ├── editor/
│   │   ├── __init__.py
│   │   ├── text_area.py
│   │   └── syntax_highlighter.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── menu_bar.py
│   │   └── dialogs.py
│   └── utils/
│       ├── __init__.py
│       ├── file_operations.py
│       └── settings_manager.py
├── tests/
│   ├── test_editor.py
│   └── test_file_operations.py
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## Technology Stack
- **Python**: Core programming language
- **Tkinter**: Standard GUI toolkit for the user interface
- **CustomTkinter**: Modern UI components for Tkinter
- **Pygments**: Syntax highlighting library
- **PyInstaller**: For creating standalone executables

## Customization
TexitEditor allows for extensive customization:

1. **Themes**: Choose from pre-defined themes or create your own in `assets/themes/`
2. **Fonts**: Add custom fonts to the `assets/fonts/` directory
3. **Keyboard Shortcuts**: Customize shortcuts in Settings > Keyboard

## Contributing
Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Commit your changes: `git commit -m 'Add some feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Inspired by the classic TextPad editor
- Special thanks to all contributors
- Icon and design elements from [source]

## Contact
- Developer: [Al Mamun](https://github.com/almamun80git)
- Project Link: [https://github.com/almamun80git/TexitEditor](https://github.com/almamun80git/TexitEditor)

---
Last updated: 2025-10-03
```

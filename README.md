# Logo Stamper

A Python application for adding logo watermarks to images with customizable positioning, size, and appearance options.

## Features

- **Flexible Positioning**: Place logos at top/bottom and left/center/right positions
- **Adjustable Padding**: Control the spacing around the logo
- **Scalable Logo Size**: Set logo size as a percentage of image width
- **Opacity Control**: Adjust logo transparency from 10% to 100%
- **Batch Processing**: Process entire folders of images at once
- **GUI Interface**: User-friendly graphical interface
- **Command Line Interface**: Scriptable command-line tool

## Supported Formats

- Input images: JPEG, PNG, and other PIL-supported formats
- Output: Preserves original format (PNG for images with transparency)

## Installation

```bash
# Install dependencies (if using pip)
pip install pillow

# Or if using the project's dependency management
uv sync
```

## Usage

### GUI Application

Run the graphical interface:

```bash
python gui.py
```

The GUI provides intuitive controls for:
- Selecting image folders and logo files
- Choosing save directories
- Adjusting logo position (vertical: top/bottom, horizontal: left/center/right)
- Setting padding (0-100 pixels)
- Controlling logo size (5%-80% of image width)
- Adjusting opacity (10%-100%)
- Enabling/disabling recursive subfolder search
- **Real-time preview** of the first image with logo applied
- **Full-size preview option** with scrollable view for detailed inspection
- **Mouse navigation**: Drag to pan around large images, scroll wheel for vertical scrolling

### Command Line Interface

```bash
python overlay_logo.py <image_folder> <logo_file> [options]
```

#### Options

- `--save-dir DIRECTORY`: Directory to save processed images (default: creates 'output' folder)
- `--vertical-pos {top,bottom}`: Vertical position of logo (default: bottom)
- `--horizontal-pos {left,center,right}`: Horizontal position of logo (default: center)
- `--padding PIXELS`: Padding around logo in pixels (default: 10)
- `--logo-scale SCALE`: Logo size as fraction of image width (default: 0.2)
- `--opacity OPACITY`: Logo opacity from 0.0 to 1.0 (default: 1.0)

#### Examples

```bash
# Basic usage - logo at bottom center
python overlay_logo.py ./photos ./logo.png

# Logo at top-right corner with custom settings
python overlay_logo.py ./photos ./logo.png --vertical-pos top --horizontal-pos right --padding 20

# Semi-transparent small logo
python overlay_logo.py ./photos ./logo.png --logo-scale 0.1 --opacity 0.5

# Custom save directory
python overlay_logo.py ./photos ./logo.png --save-dir ./watermarked_photos
```

## How It Works

1. **Image Processing**: Loads images and converts them to RGBA format for transparency support
2. **Logo Scaling**: Automatically resizes logos based on the specified scale factor
3. **Positioning**: Calculates exact pixel positions based on alignment and padding settings
4. **Opacity**: Applies transparency effects by modifying the alpha channel
5. **Format Preservation**: Saves in appropriate format (JPEG images are converted to RGB to remove alpha channel)

## Error Handling

- Validates file paths and image formats
- Handles corrupted images gracefully (skips with warning)
- Provides detailed error messages for common issues
- Validates parameter ranges (opacity 0.0-1.0, scale 0.01-1.0)
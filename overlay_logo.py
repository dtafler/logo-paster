import argparse
from pathlib import Path
from PIL import Image
from enum import Enum
from typing import Tuple, Optional
from image_analyzer import ImageAnalyzer

class VerticalPosition(Enum):
    TOP = "top"
    BOTTOM = "bottom"

class HorizontalPosition(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"

def stamp_folder(
    im_dir: str | Path, 
    logo_path: str | Path, 
    save_dir: str | Path = None,
    vertical_pos: VerticalPosition = VerticalPosition.BOTTOM,
    horizontal_pos: HorizontalPosition = HorizontalPosition.CENTER,
    padding: int = 10,
    logo_scale: float = 0.2,
    opacity: float = 1.0, 
    recursive: bool = True,
    suffix: str = "",
    use_ai_naming: bool = False,
    openai_api_key: Optional[str] = None,
    ai_model: str = "gpt-5-mini",
    max_filename_length: int = 50
) -> None:
    
    # Convert to Path objects
    im_dir = Path(im_dir)
    logo_path = Path(logo_path)
    
    image_extensions = ('.jpg', '.jpeg', '.png')
    
    if recursive:
        im_paths = [p for p in im_dir.rglob("*") if p.suffix.lower() in image_extensions]
    else:
        im_paths = [p for p in im_dir.glob("*") if p.suffix.lower() in image_extensions]
    
    # Check for duplicate filenames
    filename_dict = {}
    for path in im_paths:
        if path.name in filename_dict:
            raise ValueError(f"Duplicate filename detected: {path.name}\n  - {filename_dict[path.name]}\n  - {path}\nAn output directory from a previous run could be the cause. Either delete it or disable recursive image search.")
        else:
            filename_dict[path.name] = path
    
    # Initialize AI analyzer if needed
    analyzer = None
    if use_ai_naming:
        if not openai_api_key:
            raise ValueError("OpenAI API key is required when use_ai_naming is True")
        try:
            analyzer = ImageAnalyzer(openai_api_key, ai_model)
            print(f"[INFO] AI naming enabled using model: {ai_model}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize AI analyzer: {e}")
            return
    
    if save_dir is None:
        save_dir = Path(im_dir) / "output"
        print(f"[INFO] No save path given. Creating new directory image folder: {save_dir}")
        try:
            save_dir.mkdir()
        except FileExistsError:
            print(f"[ERROR] {save_dir} already exists. Please explicitly provide a save_dir.")
            return
    else:
        Path(save_dir).mkdir(exist_ok=True)
        
    for im_path in im_paths:
        try:
            _add_logo_single(
                im_path, 
                logo_path, 
                save_dir, 
                vertical_pos, 
                horizontal_pos, 
                padding, 
                logo_scale, 
                opacity,
                suffix,
                analyzer,
                max_filename_length
            )
        except ValueError as e:
            print(e)
            break            

def _add_logo_single(
    im_path: str | Path, 
    logo_path: str | Path, 
    save_dir: str | Path,
    vertical_pos: VerticalPosition = VerticalPosition.BOTTOM,
    horizontal_pos: HorizontalPosition = HorizontalPosition.CENTER,
    padding: int = 10,
    logo_scale: float = 0.2,
    opacity: float = 1.0,
    suffix: str = "",
    analyzer: Optional[ImageAnalyzer] = None,
    max_filename_length: int = 50
) -> None:
    
    try:
        im = Image.open(im_path).convert('RGBA')
    except Exception as e:
        print(f"[WARNING] Image {im_path} could not be opened. Continuing. {e}")
        return
        
    try:
        logo = Image.open(logo_path).convert('RGBA')
    except Exception as e:
        raise ValueError(f"[ERROR] Logo could not be opened: {e}")
        return
    
    # Process the image with logo
    result_im = _process_logo_on_image(
        im, logo, vertical_pos, horizontal_pos, 
        padding, logo_scale, opacity
    )

    # Save the resulting image
    im_path = Path(im_path)
    
    # Determine the filename
    if analyzer:
        print(f"[INFO] Analyzing image content for {im_path.name}...")
        ai_filename = analyzer.analyze_image(im_path, max_filename_length)
        if ai_filename:
            # Use AI-generated filename
            if suffix:
                save_path = Path(save_dir) / f"{ai_filename}{suffix}{im_path.suffix}"
            else:
                save_path = Path(save_dir) / f"{ai_filename}{im_path.suffix}"
            print(f"[INFO] AI generated filename: {ai_filename}")
        else:
            # Fallback to original filename if AI analysis fails
            print(f"[WARNING] AI analysis failed, using original filename")
            if suffix:
                save_path = Path(save_dir) / f"{im_path.stem}{suffix}{im_path.suffix}"
            else:
                save_path = Path(save_dir) / im_path.name
    else:
        # Use original filename with optional suffix
        if suffix:
            save_path = Path(save_dir) / f"{im_path.stem}{suffix}{im_path.suffix}"
        else:
            save_path = Path(save_dir) / im_path.name

    # no alpha channel for jpeg!
    file_extension = save_path.suffix.lower()
    if file_extension in ['.jpg', '.jpeg']:
        result_im = result_im.convert('RGB')

    result_im.save(save_path)
    print(f"[INFO] Saved image with logo to {save_path}")


def _calculate_position(
    im_width: int, 
    im_height: int, 
    logo_width: int, 
    logo_height: int,
    vertical_pos: VerticalPosition,
    horizontal_pos: HorizontalPosition,
    padding: int
) -> Tuple[int, int]:
    """Calculate the position for placing the logo on the image."""
    
    # Calculate horizontal position
    if horizontal_pos == HorizontalPosition.LEFT:
        x = padding
    elif horizontal_pos == HorizontalPosition.RIGHT:
        x = im_width - logo_width - padding
    else:  # CENTER
        x = (im_width - logo_width) // 2
    
    # Calculate vertical position
    if vertical_pos == VerticalPosition.TOP:
        y = padding
    else:  # BOTTOM
        y = im_height - logo_height - padding
    
    return (x, y)


def _process_logo_on_image(
    im: Image.Image,
    logo: Image.Image,
    vertical_pos: VerticalPosition,
    horizontal_pos: HorizontalPosition,
    padding: int,
    logo_scale: float,
    opacity: float
) -> Image.Image:
    """Apply logo processing to an image and return the result."""
    
    logo_width, logo_height = logo.size
    im_width, im_height = im.size

    # Resize logo based on scale factor
    new_width = int(im_width * logo_scale)
    scale_factor = new_width / logo_width
    new_height = int(logo_height * scale_factor)
    logo = logo.resize((new_width, new_height), Image.LANCZOS)
    logo_width, logo_height = logo.size

    # Apply opacity if less than 1.0
    if opacity < 1.0:
        # Create a copy to avoid modifying the original
        logo_with_opacity = logo.copy()
        # Apply opacity to alpha channel
        alpha = logo_with_opacity.split()[-1]  # Get alpha channel
        alpha = alpha.point(lambda p: int(p * opacity))
        logo_with_opacity.putalpha(alpha)
        logo = logo_with_opacity

    # Calculate position based on positioning options
    position = _calculate_position(
        im_width, im_height, 
        logo_width, logo_height, 
        vertical_pos, horizontal_pos, 
        padding
    )

    # Apply logo to image
    result_im = im.copy()  # Don't modify the original
    result_im.paste(logo, position, logo)
    
    return result_im
    
    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Add logo watermark to images")
    parser.add_argument("folder", help="path to directory containing the image files", type=str)
    parser.add_argument("logo", help="path to the logo", type=str)
    parser.add_argument("--save-dir", help="directory to save processed images", type=str, default=None)
    parser.add_argument("--vertical-pos", help="vertical position of logo", 
                       choices=[pos.value for pos in VerticalPosition], default="bottom")
    parser.add_argument("--horizontal-pos", help="horizontal position of logo", 
                       choices=[pos.value for pos in HorizontalPosition], default="center")
    parser.add_argument("--padding", help="padding around logo in pixels", type=int, default=10)
    parser.add_argument("--logo-scale", help="logo size as fraction of image width", type=float, default=0.2)
    parser.add_argument("--opacity", help="logo opacity (0.0 to 1.0)", type=float, default=1.0)
    parser.add_argument("--suffix", help="suffix to add to output filenames (before extension)", type=str, default="")
    parser.add_argument("--no-rec", help="turn off recursive image search", action="store_true")
    
    # AI naming options
    parser.add_argument("--use-ai-naming", help="use AI to generate descriptive filenames", action="store_true")
    parser.add_argument("--openai-api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)", type=str)
    parser.add_argument("--ai-model", help="OpenAI model to use for image analysis", type=str, default="gpt-4o-mini")
    parser.add_argument("--max-filename-length", help="maximum length for AI-generated filenames", type=int, default=50)
    
    args = parser.parse_args()
    
    # Validate opacity
    if not 0.0 <= args.opacity <= 1.0:
        parser.error("Opacity must be between 0.0 and 1.0")
    
    # Validate logo scale
    if not 0.01 <= args.logo_scale <= 1.0:
        parser.error("Logo scale must be between 0.01 and 1.0")
    
    # Handle AI naming options
    openai_api_key = args.openai_api_key
    if args.use_ai_naming and not openai_api_key:
        # Try to get from environment variable
        import os
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            parser.error("OpenAI API key is required when using --use-ai-naming. Provide via --openai-api-key or set OPENAI_API_KEY environment variable.")
    
    # Validate filename length
    if args.max_filename_length < 10 or args.max_filename_length > 100:
        parser.error("max-filename-length must be between 10 and 100 characters")
    
    # Convert string arguments to enums
    vertical_pos = VerticalPosition(args.vertical_pos)
    horizontal_pos = HorizontalPosition(args.horizontal_pos)
    
    stamp_folder(
        args.folder, 
        args.logo, 
        args.save_dir,
        vertical_pos,
        horizontal_pos,
        args.padding,
        args.logo_scale,
        args.opacity, 
        not(args.no_rec),
        args.suffix,
        args.use_ai_naming,
        openai_api_key,
        args.ai_model,
        args.max_filename_length
    )
    
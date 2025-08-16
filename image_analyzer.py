"""
Image analysis module using OpenAI API to generate descriptive filenames.
"""

import base64
import io
import re
from pathlib import Path
from typing import Optional
from PIL import Image
from openai import OpenAI
import time
import random

class SimpleLimiter:
    """Fixed spacing between calls (e.g., 2 req/sec = 0.5s spacing)."""
    def __init__(self, min_interval_s: float = 0.5):
        self.min_interval_s = max(0.0, min_interval_s)
        self._last = 0.0

    def wait(self):
        now = time.time()
        wait_s = max(0.0, self._last + self.min_interval_s - now)
        if wait_s:
            time.sleep(wait_s)
        self._last = time.time()

def simple_retry(call, *, max_retries: int = 3):
    """Retry on common transient failures with tiny exponential backoff."""
    for attempt in range(max_retries):
        try:
            return call()
        except Exception as e:
            # Try to detect rate limit / transient errors
            status = getattr(e, "status_code", None) or getattr(e, "http_status", None)
            retry_after = None
            headers = getattr(e, "headers", None) or getattr(e, "response_headers", None) or {}
            if isinstance(headers, dict):
                ra = headers.get("Retry-After") or headers.get("retry-after")
                try:
                    retry_after = float(ra) if ra is not None else None
                except Exception:
                    retry_after = None

            transient = status in (429, 500, 502, 503, 504) or status is None
            if attempt == max_retries - 1 or not transient:
                raise

            # sleep: prefer Retry-After, else tiny backoff with jitter
            base = retry_after if retry_after is not None else (1.0 * (2 ** attempt))
            time.sleep(base * (0.8 + 0.4 * random.random()))

class ImageAnalyzer:
    """Analyzes images using OpenAI API to generate descriptive filenames."""
    
    def __init__(self, api_key: str, model: str = "gpt-5-mini", min_interval_s: float = 0.25):
        """
        Initialize the ImageAnalyzer.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use for image analysis
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._limiter = SimpleLimiter(min_interval_s=min_interval_s)  

    def _call_responses(self, **kwargs):
        def _do():
            self._limiter.wait()
            return self.client.responses.create(**kwargs)
        return simple_retry(_do)

        
    def analyze_image(self, image_path: str | Path, max_filename_length: int = 50) -> Optional[str]:
        """
        Analyze an image and generate a descriptive filename.
        
        Args:
            image_path: Path to the image file
            max_filename_length: Maximum length for the generated filename
            
        Returns:
            Generated filename (without extension) or None if analysis fails
        """
        try:
            # Load and prepare image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize image if it's too large (OpenAI has size limits)
            max_size = 1024
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Create the prompt
            prompt = (
                f"Analyze this image and generate a descriptive filename (maximum {max_filename_length} characters). "
                "Focus on the main subject, setting, or key visual elements. "
                "Use only letters, numbers, hyphens, and underscores. "
                "Make it concise but descriptive. "
                "Do not include file extensions. "
                "Examples: 'modern_kitchen_white_cabinets', 'sunset_mountain_landscape', 'red_sports_car_parked'"
            )
            prompt2 = (
                f"Analyze the provided image and create a concise, descriptive filename (maximum {max_filename_length} characters)"
                "The filename should: "
                "- Focus on the main subject, setting, or key visual elements. "
                "- Use only letters, numbers, hyphens, and underscores "
                "- Exclude file extensions "
                "- Be as informative as possible within the character limit. "
                "Examples: 'modern_kitchen_white_cabinets', 'sunset_mountain_landscape', 'red_sports_car_parked'"
            )
            
            # Make API call
            response = self._call_responses(
                model=self.model,
                input=[{
                    "role": "user", 
                    "content": [
                        {"type": "input_text", "text": prompt2},
                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{img_base64}"}
                    ]
                }],
                max_output_tokens=500,
                reasoning={"effort": "low"},
                text={"verbosity": "low"}
            )
            print(response)
            
            # Extract and clean the filename
            generated_name = (getattr(response, "output_text", "") or "").strip()
            orig_filename = Path(image_path).name.split('.')[0]
            cleaned_name = self._clean_filename(generated_name, max_filename_length, orig_filename)
            print("generated name: ", generated_name)
            print("cleaned name: ", cleaned_name)
            
            return cleaned_name
            
        except Exception as e:
            print(f"[WARNING] Failed to analyze image {image_path}: {e}")
            return None
    
    def _clean_filename(self, filename: str, max_length: int, orig_filename: str) -> str:
        """
        Clean and validate the generated filename.
        
        Args:
            filename: Raw filename from API
            max_length: Maximum allowed length
            
        Returns:
            Cleaned filename
        """
        # Remove any quotes or extra formatting
        filename = filename.strip().strip('"').strip("'")
        
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        
        # Remove any characters that aren't alphanumeric, hyphens, or underscores
        filename = re.sub(r'[^a-zA-Z0-9_-]', '', filename)
        
        # Remove multiple consecutive underscores/hyphens
        filename = re.sub(r'[_-]+', '_', filename)
        
        # Ensure it doesn't start or end with underscore/hyphen
        filename = filename.strip('_-')
        
        # Truncate if too long
        if len(filename) > max_length:
            filename = filename[:max_length].rstrip('_-')
        
        # Fallback if filename is empty or too short
        if len(filename) < 3:
            filename = orig_filename
        
        return filename


def test_analyzer():
    """Test function for the ImageAnalyzer (requires API key)."""
    import os
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable to test")
        return
    
    analyzer = ImageAnalyzer(api_key)
    
    # Test with sample images if they exist
    test_dir = Path("apartments")
    if test_dir.exists():
        for img_path in test_dir.glob("*.jpg"):
            print(f"Analyzing {img_path.name}...")
            result = analyzer.analyze_image(img_path)
            print(f"Generated filename: {result}")
            break  # Just test one image
    else:
        print("No test images found in 'apartments' directory")


if __name__ == "__main__":
    test_analyzer()

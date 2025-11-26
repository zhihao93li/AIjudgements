
import os
import sys
from pathlib import Path
from PIL import Image

# Add project root to path
sys.path.append("/Users/zhihaoli/Documents/项目/show5")

from app.judges.stage_one import build_multimodal_message

def reproduce_issue():
    # Setup: Create a dummy image in frontend/uploads
    upload_dir = Path("/Users/zhihaoli/Documents/项目/show5/frontend/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    dummy_image_path = upload_dir / "test_reproduce.jpg"
    
    img = Image.new('RGB', (100, 100), color = 'red')
    img.save(dummy_image_path)
    
    # Test case: Relative URL
    image_url = "/static/uploads/test_reproduce.jpg"
    entry_id = "test_entry"
    competition_type = "outfit"
    
    print(f"Testing with image_url: {image_url}")
    
    try:
        msg = build_multimodal_message(image_url, entry_id, competition_type)
        print("SUCCESS: MultiModalMessage built successfully.")
    except Exception as e:
        print(f"FAILURE: Caught expected exception: {e}")

if __name__ == "__main__":
    reproduce_issue()

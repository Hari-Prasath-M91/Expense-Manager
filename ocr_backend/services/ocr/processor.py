import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import time
from typing import Tuple

# To use pytesseract, you might need to specify the path to the executable if not in PATH
from backend.core.config import settings
if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

class OCRProcessor:
    def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        # Load image from bytes
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Failed to decode image.")

        # 1. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Resize to 2x (helps Tesseract enormously)
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

        return gray

    def deskew_image(self, image: np.ndarray) -> np.ndarray:
        coords = np.column_stack(np.where(image > 0))
        if len(coords) == 0:
            return image
            
        angle = cv2.minAreaRect(coords)[-1]
        
        # Adjust angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated

    def extract_text(self, image_bytes: bytes) -> Tuple[str, dict]:
        start_time = time.time()
        
        try:
            # Preprocess
            processed_img = self.preprocess_image(image_bytes)
            
            # Convert back to PIL Image for pytesseract
            pil_img = Image.fromarray(processed_img)
            
            # Extract text (psm 4 handles sparse columns like receipts well)
            custom_config = r'--oem 3 --psm 4'
            text = pytesseract.image_to_string(pil_img, config=custom_config)
            
            # Debug log
            print("--- RAW OCR TEXT START ---")
            print(text)
            print("--- RAW OCR TEXT END ---")
            
            # Get detailed data for confidence (using image_to_data)
            # data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
            # Avg confidence could be computed, but for simplicity we will estimate or just use raw text.
            
            processing_time = time.time() - start_time
            
            # Dummy confidence calculation logic for now (tesseract confidence is word level)
            avg_confidence = 85.0 
            
            metrics = {
                "processing_time": processing_time,
                "confidence": avg_confidence
            }
            return text, metrics
            
        except Exception as e:
            raise RuntimeError(f"OCR Processing failed: {str(e)}")

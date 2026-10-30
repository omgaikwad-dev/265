import cv2
import numpy as np
import logging

logger = logging.getLogger("fdrsetu.ocr.preprocessor")

class ImagePreprocessor:
    @staticmethod
    def preprocess_image(image_bytes: bytes) -> np.ndarray:
        """
        Applies OpenCV image preprocessing pipeline:
        1. Decode byte buffer into BGR image.
        2. Convert to Grayscale.
        3. Denoise and enhance contrast via CLAHE.
        4. Detect and correct skew angle.
        5. Adaptive thresholding for crisp OCR text binarization.
        """
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes with OpenCV")

            # 1. Grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 2. Contrast Limited Adaptive Histogram Equalization (CLAHE)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            contrast_enhanced = clahe.apply(gray)

            # 3. Bilateral filter for noise reduction while preserving edges
            denoised = cv2.bilateralFilter(contrast_enhanced, d=9, sigmaColor=75, sigmaSpace=75)

            # 4. Deskewing
            deskewed = ImagePreprocessor._deskew(denoised)

            # 5. Adaptive Thresholding for sharp document text
            thresh = cv2.adaptiveThreshold(
                deskewed, 255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 
                15, 6
            )

            return thresh
        except Exception as e:
            logger.warning(f"Advanced preprocessing encountered an issue ({e}). Returning fallback grayscale.")
            nparr = np.frombuffer(image_bytes, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

    @staticmethod
    def _deskew(image: np.ndarray) -> np.ndarray:
        """Estimates skew angle from horizontal text lines and rotates the image."""
        try:
            coords = np.column_stack(np.where(image > 0))
            if len(coords) == 0:
                return image
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            if abs(angle) > 0.5 and abs(angle) < 45:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    image, M, (w, h), 
                    flags=cv2.INTER_CUBIC, 
                    borderMode=cv2.BORDER_REPLICATE
                )
                return rotated
        except Exception:
            pass
        return image


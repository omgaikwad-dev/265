import os
import fitz # PyMuPDF
import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import logging
from typing import Tuple, List, Dict
from app.ocr.preprocessor import ImagePreprocessor

logger = logging.getLogger("fdrsetu.ocr.engine")

class OCREngine:
    @staticmethod
    def extract_text_and_confidence(file_path: str, mime_type: str) -> Tuple[str, float, List[Dict], str]:
        """
        Multi-modal document intelligence pipeline:
        1. Native PDF vector extraction with PyMuPDF.
        2. Optical Character Recognition (OCR) for scanned PDFs and images using OpenCV & Tesseract.
        
        Returns:
            (raw_text, average_confidence, word_tokens_with_confidence, engine_name)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf" or mime_type == "application/pdf":
            return OCREngine._process_pdf(file_path)
        else:
            return OCREngine._process_image_file(file_path)

    @staticmethod
    def _process_pdf(file_path: str) -> Tuple[str, float, List[Dict], str]:
        """Extracts text from PDF via PyMuPDF native layer, falling back to OCR on rendered pages."""
        doc = fitz.open(file_path)
        full_text_parts = []
        tokens = []

        # 1. Attempt native text extraction
        native_text_detected = False
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_text = page.get_text("text")
            if len(page_text.strip()) > 30:
                native_text_detected = True
                full_text_parts.append(page_text)
                for w in page_text.split():
                    tokens.append({"word": w, "conf": 98.0})

        if native_text_detected:
            full_text = "\n".join(full_text_parts)
            avg_conf = 98.5
            return full_text, avg_conf, tokens, "PyMuPDF (Native Digital Text)"

        # 2. Scanned PDF fallback: render each page at 300 DPI and run OCR
        logger.info(f"PDF {file_path} contains scanned imagery. Running OpenCV + Tesseract OCR pipeline.")
        ocr_text_parts = []
        all_confidences = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")

            # Preprocess with OpenCV
            preprocessed = ImagePreprocessor.preprocess_image(img_bytes)
            
            # Tesseract OCR extraction with word confidence
            page_text, page_tokens, page_avg_conf = OCREngine._run_tesseract(preprocessed)
            ocr_text_parts.append(page_text)
            tokens.extend(page_tokens)
            if page_avg_conf > 0:
                all_confidences.append(page_avg_conf)

        full_text = "\n".join(ocr_text_parts)
        avg_conf = float(np.mean(all_confidences)) if all_confidences else 85.0
        return full_text, avg_conf, tokens, "PyMuPDF + OpenCV + Tesseract (OCR)"

    @staticmethod
    def _process_image_file(file_path: str) -> Tuple[str, float, List[Dict], str]:
        """Runs OpenCV enhancement and Tesseract OCR on standalone image files."""
        with open(file_path, "rb") as f:
            img_bytes = f.read()

        preprocessed = ImagePreprocessor.preprocess_image(img_bytes)
        text, tokens, avg_conf = OCREngine._run_tesseract(preprocessed)
        return text, avg_conf, tokens, "OpenCV + Tesseract (OCR)"

    @staticmethod
    def _run_tesseract(image_array: np.ndarray) -> Tuple[str, List[Dict], float]:
        """Runs Tesseract image_to_data to capture words, coordinates, and confidence values."""
        try:
            # Convert to PIL Image for pytesseract
            pil_img = Image.fromarray(image_array)
            data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)

            words = []
            tokens = []
            valid_confs = []

            n_boxes = len(data["text"])
            for i in range(n_boxes):
                w = data["text"][i].strip()
                c = float(data["conf"][i])
                if w:
                    words.append(w)
                    if c >= 0:
                        tokens.append({"word": w, "conf": c})
                        valid_confs.append(c)
                    else:
                        tokens.append({"word": w, "conf": 75.0})

            extracted_text = " ".join(words)
            avg_confidence = float(np.mean(valid_confs)) if valid_confs else 80.0
            return extracted_text, tokens, avg_confidence
        except Exception as err:
            logger.error(f"Tesseract execution error: {err}")
            # Fallback simple string extraction
            try:
                pil_img = Image.fromarray(image_array)
                simple_text = pytesseract.image_to_string(pil_img)
                return simple_text, [{"word": w, "conf": 75.0} for w in simple_text.split()], 75.0
            except Exception as e:
                return "", [], 0.0


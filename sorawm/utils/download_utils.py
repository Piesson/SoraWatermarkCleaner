from pathlib import Path

import requests
from loguru import logger
from tqdm import tqdm

from sorawm.configs import WATER_MARK_DETECT_YOLO_WEIGHTS

DETECTOR_URL = "https://github.com/linkedlist771/SoraWatermarkCleaner/releases/download/V0.0.1/best.pt"


def download_detector_weights():
    if not WATER_MARK_DETECT_YOLO_WEIGHTS.exists():
        logger.debug(f"llama weights not found, downloading from {DETECTOR_URL}")
        WATER_MARK_DETECT_YOLO_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)

        try:
            response = requests.get(DETECTOR_URL, stream=True, timeout=300)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            with open(WATER_MARK_DETECT_YOLO_WEIGHTS, "wb") as f:
                with tqdm(
                    total=total_size, unit="B", unit_scale=True, desc="Downloading"
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

            logger.success(f"✓ Weights downloaded: {WATER_MARK_DETECT_YOLO_WEIGHTS}")

        except requests.exceptions.RequestException as e:
            if WATER_MARK_DETECT_YOLO_WEIGHTS.exists():
                WATER_MARK_DETECT_YOLO_WEIGHTS.unlink()
            raise RuntimeError(f"Downing failed: {e}")

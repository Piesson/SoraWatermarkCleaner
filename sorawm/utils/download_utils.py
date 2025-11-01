from pathlib import Path

import requests
from loguru import logger
from tqdm import tqdm
import hashlib
import json
from sorawm.configs import WATER_MARK_DETECT_YOLO_WEIGHTS, WATER_MARK_DETECT_YOLO_WEIGHTS_HASH_JSON

DETECTOR_URL = "https://github.com/linkedlist771/SoraWatermarkCleaner/releases/download/V0.0.1/best.pt"
REMOTE_MODEL_VERSION_URL = "https://raw.githubusercontent.com/linkedlist771/SoraWatermarkCleaner/main/version/model_version.json"


def generate_sha256_hash(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def download_detector_weights(force_download: bool = False):
    ## 1. check if model exists and if we need to download
    if not WATER_MARK_DETECT_YOLO_WEIGHTS.exists() or force_download:
        logger.debug(f"Downloading weights from {DETECTOR_URL}")
        WATER_MARK_DETECT_YOLO_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)        
        temp_file = WATER_MARK_DETECT_YOLO_WEIGHTS.with_suffix(".tmp")
        
        try:
            response = requests.get(DETECTOR_URL, stream=True, timeout=300)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))            
            with open(temp_file, "wb") as f:
                with tqdm(
                    total=total_size, unit="B", unit_scale=True, desc="Downloading"
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))            
            if WATER_MARK_DETECT_YOLO_WEIGHTS.exists():
                WATER_MARK_DETECT_YOLO_WEIGHTS.unlink() 
            temp_file.rename(WATER_MARK_DETECT_YOLO_WEIGHTS)  
            
            logger.success(f"✓ Weights downloaded: {WATER_MARK_DETECT_YOLO_WEIGHTS}")
            new_hash = generate_sha256_hash(WATER_MARK_DETECT_YOLO_WEIGHTS)
            WATER_MARK_DETECT_YOLO_WEIGHTS_HASH_JSON.parent.mkdir(parents=True, exist_ok=True)
            with WATER_MARK_DETECT_YOLO_WEIGHTS_HASH_JSON.open("w") as f:
                json.dump({"sha256": new_hash}, f)
            logger.debug(f"Hash updated: {new_hash[:8]}...")
            return 
            
        except requests.exceptions.RequestException as e:
            if temp_file.exists():
                temp_file.unlink()
            raise RuntimeError(f"Download failed: {e}")

    ## 2. check the local hash, if it exits, compare it with the remote one(with timeout)
    ## if not, generate it then compare.
    local_sha256_hash = None 
    # WATER_MARK_DETECT_YOLO_WEIGHTS_HASH_JSON
    if not WATER_MARK_DETECT_YOLO_WEIGHTS_HASH_JSON.exists():
        pass 
    else:
        # if it has not hash,
        with WATER_MARK_DETECT_YOLO_WEIGHTS_HASH_JSON.open("r") as f:
            hash_data = json.load(f)
            local_sha256_hash = hash_data.get("sha256", None)

    if local_sha256_hash is None:
        
        # generate the hash and update the config
        logger.info(f"Generating sha256 hash for {WATER_MARK_DETECT_YOLO_WEIGHTS}")
        local_sha256_hash = generate_sha256_hash(WATER_MARK_DETECT_YOLO_WEIGHTS)
        WATER_MARK_DETECT_YOLO_WEIGHTS_HASH_JSON.parent.mkdir(parents=True, exist_ok=True)
        with WATER_MARK_DETECT_YOLO_WEIGHTS_HASH_JSON.open("w") as f:
            json.dump({"sha256": local_sha256_hash}, f)
    remote_sha256_hash = None 
    try:
        response = requests.get(REMOTE_MODEL_VERSION_URL, timeout=3)
        response.raise_for_status()
        remote_sha256_hash = response.json().get("sha256", None)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get remote sha256 hash: {e}")
        remote_sha256_hash = None

    ## 3. after the compare, if there is a new version, download it and replace the local and 
    ## update the hash
            
    if remote_sha256_hash is None:
       pass 
    else:
        if local_sha256_hash != remote_sha256_hash:
            logger.info(f"Hash mismatch detected, updating model...")
            download_detector_weights(force_download=True)
        else:
            logger.debug("Model is up-to-date")  # 🔧 修改5: 添加日志
from pathlib import Path

from sorawm.utils.video_utils import VideoLoader
from sorawm.utils.watermark_utls import (detect_watermark, get_bounding_box,
                                         h_tmpl, w_tmpl)
from sorawm.watermark_cleaner import WaterMarkCleaner
from sorawm.watermark_detector import SoraWaterMarkDetector
import ffmpeg
from loguru import logger
import numpy as np
from tqdm import tqdm

# based on the sora tempalte to detect the whole, and then got the icon part area.


class SoraWM:
    def __init__(self):
        self.detector = SoraWaterMarkDetector()
        self.cleaner = WaterMarkCleaner()

    def run(self, input_video_path: Path, output_video_path: Path):
        input_video_loader = VideoLoader(input_video_path)
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        width = input_video_loader.width
        height = input_video_loader.height
        fps = input_video_loader.fps
        total_frames = input_video_loader.total_frames

        # Create temporary output path for video without audio
        temp_output_path = output_video_path.parent / f"temp_{output_video_path.name}"

        process_out = (
            ffmpeg.input(
                "pipe:",
                format="rawvideo",
                pix_fmt="bgr24",
                s=f"{width}x{height}",
                r=fps,
            )
            .output(str(temp_output_path), pix_fmt="yuv420p", vcodec="libx264")
            .overwrite_output()
            .run_async(pipe_stdin=True, pipe_stderr=True)
        )

        try:
            for frame in tqdm(
                input_video_loader, total=total_frames, desc="processing all frames"
            ):
                detection_result = self.detector.detect(frame)

                if detection_result["detected"]:
                    x1, y1, x2, y2 = detection_result["bbox"]
                    mask = np.zeros((height, width), dtype=np.uint8)
                    mask[y1:y2, x1:x2] = 255
                    cleaned_frame = self.cleaner.clean(frame, mask)
                else:
                    cleaned_frame = frame
                process_out.stdin.write(cleaned_frame.tobytes())

        finally:
            process_out.stdin.close()
            process_out.wait()

        # Merge audio from original video
        logger.info("Merging audio track...")
        video_stream = ffmpeg.input(str(temp_output_path))
        audio_stream = ffmpeg.input(str(input_video_path)).audio

        (
            ffmpeg.output(video_stream, audio_stream, str(output_video_path),
                         vcodec="copy", acodec="aac")
            .overwrite_output()
            .run(quiet=True)
        )

        # Clean up temporary file
        temp_output_path.unlink()

        logger.info(f"Saved no watermark video with audio at: {output_video_path}")


if __name__ == "__main__":
    from pathlib import Path
    input_video_path = Path(
        "resources/19700121_1645_68e0a027836c8191a50bea3717ea7485.mp4"
    )
    output_video_path = Path("outputs/sora_watermark_removed.mp4")
    sora_wm = SoraWM()
    sora_wm.run(input_video_path, output_video_path)

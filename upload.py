import argparse
from youtube_uploader_selenium import YouTubeUploader
from typing import Optional
from pathlib import Path


def main(video_path: str,
         metadata_path: Optional[str] = None,
         thumbnail_path: Optional[str] = None,
         profile_path: Optional[Path] = None):
    uploader = YouTubeUploader(video_path, metadata_path, thumbnail_path, profile_path)
    success = uploader.upload()
    assert success


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",
                        help='Path to the video file',
                        required=True)
    parser.add_argument("-t",
                        "--thumbnail",
                        help='Path to the thumbnail image',)
    parser.add_argument("--meta_file", help='Path to JSON formatted file with metadata')
    parser.add_argument("--profile", help='Path to the chrome profile')
    args = parser.parse_args()

    main(args.video, args.meta, args.thumbnail, profile_path=Path(args.profile))

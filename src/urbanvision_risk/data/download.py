from __future__ import annotations

import argparse
import hashlib
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from urbanvision_risk.errors import ProjectError, report_error
from urbanvision_risk.paths import get_paths

RDD2022_CHINA_MOTORBIKE_URL = (
    "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/"
    "2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/"
    "RDD2022_China_MotorBike.zip"
)
ARCHIVE_NAME = "RDD2022_China_MotorBike.zip"
RAW_RELATIVE_PATH = Path("rdd2022/china-motorbike")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(
    url: str,
    destination: Path,
    opener: Callable[..., Any] = urlopen,
    chunk_size: int = 1024 * 1024,
) -> str:
    partial = destination.with_suffix(destination.suffix + ".part")
    if destination.exists() or partial.exists():
        raise ProjectError(
            "E204",
            "下载目标或未完成文件已存在",
            "Download target or partial file already exists",
            "确认内容后使用新的路径，或把旧文件移入废纸篓",
            "Use a new path or move the old file to Trash after inspection",
            str(destination),
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    try:
        with opener(url) as response, partial.open("xb") as output:
            while chunk := response.read(chunk_size):
                output.write(chunk)
                digest.update(chunk)
    except OSError as error:
        raise ProjectError(
            "E201",
            "数据集下载失败，未完成文件已保留",
            "Dataset download failed; the partial file was preserved",
            "检查网络；确认后把 .part 文件移入废纸篓再重试",
            (
                "Check the network; inspect and move the .part file to Trash "
                "before retrying"
            ),
            str(partial),
        ) from error
    partial.rename(destination)
    return digest.hexdigest()


def safe_extract_zip(archive: Path, destination: Path) -> tuple[Path, ...]:
    if not archive.is_file():
        raise ProjectError(
            "E201",
            "压缩包不存在",
            "Archive does not exist",
            "先运行数据下载命令",
            "Run the dataset download command first",
            str(archive),
        )
    if destination.exists() and any(destination.iterdir()):
        raise ProjectError(
            "E204",
            "原始数据目录已经包含文件",
            "Raw-data directory already contains files",
            "保留现有数据，或检查后把整个目录移入废纸篓",
            "Keep the existing data or inspect and move the directory to Trash",
            str(destination),
        )

    destination_root = destination.resolve()
    try:
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            targets: list[Path] = []
            for member in members:
                target = (destination / member.filename).resolve()
                if member.filename.startswith("/") or not target.is_relative_to(
                    destination_root
                ):
                    raise ProjectError(
                        "E203",
                        "压缩包包含不安全路径",
                        "Archive contains an unsafe path",
                        "不要解压该文件，重新从官方来源下载",
                        "Do not extract it; redownload from the official source",
                        member.filename,
                    )
                if not member.is_dir():
                    targets.append(target)
            destination.mkdir(parents=True, exist_ok=True)
            bundle.extractall(destination)
    except zipfile.BadZipFile as error:
        raise ProjectError(
            "E202",
            "压缩包损坏",
            "Archive is corrupt",
            "检查后把压缩包移入废纸篓并重新下载",
            "Inspect, move the archive to Trash, and redownload it",
            str(archive),
        ) from error
    return tuple(targets)


def main(debug: bool = False) -> int:
    paths = get_paths()
    archive = paths.downloads / ARCHIVE_NAME
    raw_destination = paths.raw / RAW_RELATIVE_PATH
    try:
        if archive.exists():
            digest = sha256_file(archive)
            print(f"[INFO] 使用已有压缩包 / Reusing archive: {archive}")
        else:
            print(f"[INFO] 开始下载 / Starting download: {RDD2022_CHINA_MOTORBIKE_URL}")
            digest = download_file(RDD2022_CHINA_MOTORBIKE_URL, archive)
        if raw_destination.exists() and any(raw_destination.iterdir()):
            print(f"[INFO] 使用已有原始数据 / Reusing raw data: {raw_destination}")
        else:
            safe_extract_zip(archive, raw_destination)
        print(
            "[PASS] 下载与解压完成 / Download and extraction complete\n"
            f"SHA-256: {digest}"
        )
        return 0
    except ProjectError as error:
        return report_error(error, debug=debug)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download RDD2022 / 下载 RDD2022")
    parser.add_argument("--debug", action="store_true")
    raise SystemExit(main(debug=parser.parse_args().debug))

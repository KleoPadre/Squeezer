#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
import zipfile
import urllib.request


def log(message):
    """Вывод сообщения в консоль"""
    print(f"[BUILD] {message}")


def download_file(url, target_path):
    """
    Скачивание файла из интернета

    Args:
        url (str): URL файла для скачивания
        target_path (str): Путь для сохранения файла
    """
    log(f"Скачивание {url} в {target_path}")

    with urllib.request.urlopen(url) as response:
        with open(target_path, "wb") as f:
            f.write(response.read())


def prepare_ffmpeg():
    """
    Скачивание и подготовка FFmpeg для сборки

    Returns:
        bool: True если подготовка прошла успешно, иначе False
    """
    # Создание директории для бинарных файлов, если еще не существует
    bin_dir = Path("bin")
    bin_dir.mkdir(exist_ok=True)

    # Проверка существования бинарных файлов
    ffmpeg_path = bin_dir / "ffmpeg"
    ffprobe_path = bin_dir / "ffprobe"

    if ffmpeg_path.exists() and ffprobe_path.exists():
        log("FFmpeg и FFprobe уже скачаны")
        return True

    log("Скачивание FFmpeg и FFprobe...")

    # Временная директория для архивов
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # Пути для архивов
            ffmpeg_zip = Path(tmp_dir) / "ffmpeg.zip"
            ffprobe_zip = Path(tmp_dir) / "ffprobe.zip"

            # Скачивание архивов
            download_file(
                "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip", ffmpeg_zip
            )
            download_file(
                "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip", ffprobe_zip
            )

            # Распаковка архивов
            with zipfile.ZipFile(ffmpeg_zip, "r") as zip_ref:
                zip_ref.extractall(bin_dir)

            with zipfile.ZipFile(ffprobe_zip, "r") as zip_ref:
                zip_ref.extractall(bin_dir)

            # Установка прав на выполнение
            os.chmod(ffmpeg_path, 0o755)
            os.chmod(ffprobe_path, 0o755)

            log("FFmpeg и FFprobe успешно скачаны и подготовлены")
            return True

        except Exception as e:
            log(f"Ошибка при подготовке FFmpeg: {str(e)}")
            return False


def build_app():
    """
    Сборка приложения с помощью PyInstaller

    Returns:
        bool: True если сборка прошла успешно, иначе False
    """
    try:
        # Установка PyInstaller, если не установлен
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"], check=True
        )

        # Сборка приложения
        log("Сборка приложения с PyInstaller...")

        # Для macOS на ARM
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--windowed",
            "--name=Squeezer",
            "--icon=icon.icns",  # Добавьте иконку если она есть
            "--add-data=bin/ffmpeg:bin",
            "--add-data=bin/ffprobe:bin",
            "main.py",
        ]

        # Если иконки нет, уберем параметр
        if not os.path.exists("icon.icns"):
            cmd.remove("--icon=icon.icns")

        subprocess.run(cmd, check=True)

        log("Приложение успешно собрано!")
        log(f"Исполняемый файл: {os.path.abspath('dist/Squeezer')}")
        return True

    except Exception as e:
        log(f"Ошибка при сборке приложения: {str(e)}")
        return False


if __name__ == "__main__":
    log("Начало сборки приложения Squeezer")

    # Подготовка FFmpeg
    if not prepare_ffmpeg():
        log("Не удалось подготовить FFmpeg. Сборка прервана.")
        sys.exit(1)

    # Сборка приложения
    if not build_app():
        log("Не удалось собрать приложение. Сборка прервана.")
        sys.exit(1)

    log("Сборка приложения Squeezer завершена успешно!")
    sys.exit(0)

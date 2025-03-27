#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import logging
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import pyheif
import subprocess
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("squeezer.log"), logging.StreamHandler()],
)
logger = logging.getLogger("ImageProcessor")


class ImageProcessor:
    """Класс для обработки и сжатия изображений"""

    def __init__(self):
        # Соответствие уровней качества значениям для сжатия
        self.quality_map = {"Высокое": 80, "Среднее": 65, "Низкое": 50}

        # Специальные значения для HEIC файлов (более агрессивное сжатие)
        self.heic_quality_map = {"Высокое": 75, "Среднее": 60, "Низкое": 40}

        # Поддерживаемые форматы
        self.supported_formats = [".jpg", ".jpeg", ".png", ".gif", ".heic"]

    def can_process(self, file_path):
        """Проверка, может ли процессор обработать данный файл"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_formats

    def compress_image(self, image_path, output_dir, quality_level):
        """
        Сжатие изображения с сохранением метаданных

        Args:
            image_path (str): Путь к исходному изображению
            output_dir (str): Директория для сохранения сжатого изображения
            quality_level (str): Уровень качества (Высокое, Среднее, Низкое)

        Returns:
            str: Путь к сжатому изображению
        """
        # Получение имени файла и расширения
        file_name = os.path.basename(image_path)
        file_ext = os.path.splitext(file_name)[1].lower()

        # Определение пути для сохранения
        output_path = os.path.join(output_dir, file_name)

        # Проверка на HEIC формат
        if file_ext == ".heic":
            return self._process_heic(image_path, output_path, quality_level)

        try:
            # Открытие изображения и сохранение EXIF данных
            img = Image.open(image_path)

            # Получение метаданных (если есть)
            exif_data = None
            if hasattr(img, "_getexif") and img._getexif() is not None:
                exif_data = img.info.get("exif")

            # Сохранение с выбранным качеством
            quality = self.quality_map[quality_level]

            # Сохранение с сохранением формата
            if file_ext.lower() in [".jpg", ".jpeg"]:
                if exif_data:
                    img.save(output_path, "JPEG", quality=quality, exif=exif_data)
                else:
                    img.save(output_path, "JPEG", quality=quality)
            elif file_ext.lower() == ".png":
                # Для PNG используем оптимизацию
                img.save(output_path, "PNG", optimize=True)
            elif file_ext.lower() == ".gif":
                # Для GIF просто копируем, т.к. сжатие может испортить анимацию
                shutil.copy2(image_path, output_path)
            else:
                # Для других форматов - конвертируем в JPEG
                img = img.convert("RGB")
                img.save(output_path, "JPEG", quality=quality)

            return output_path

        except Exception as e:
            raise Exception(f"Ошибка при сжатии изображения {file_name}: {str(e)}")

    def _process_jpeg(self, input_path: str, output_path: str, quality: str) -> str:
        """Обработка JPEG файлов"""
        try:
            # Открываем изображение
            with Image.open(input_path) as img:
                # Получаем размеры изображения
                width, height = img.size

                # Если изображение слишком большое, уменьшаем его размер
                max_dimension = 4096  # Максимальный размер стороны
                if width > max_dimension or height > max_dimension:
                    ratio = min(max_dimension / width, max_dimension / height)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Сохраняем с оптимизированными настройками
                img.save(
                    output_path,
                    "JPEG",
                    quality=self.quality_map[quality],
                    optimize=True,
                    progressive=True,
                    subsampling=0,  # Отключаем субдискретизацию для лучшего качества
                )
            return output_path
        except Exception as e:
            logger.error(f"Ошибка при обработке JPEG: {str(e)}")
            raise

    def _process_heic(self, input_path: str, output_path: str, quality: str) -> str:
        """Обработка HEIC файлов"""
        try:
            # Сначала пробуем использовать pyheif
            try:
                with Image.open(input_path) as img:
                    # Получаем размеры изображения
                    width, height = img.size

                    # Если изображение слишком большое, уменьшаем его размер
                    max_dimension = 4096  # Максимальный размер стороны
                    if width > max_dimension or height > max_dimension:
                        ratio = min(max_dimension / width, max_dimension / height)
                        new_width = int(width * ratio)
                        new_height = int(height * ratio)
                        img = img.resize(
                            (new_width, new_height), Image.Resampling.LANCZOS
                        )

                    # Сохраняем с оптимизированными настройками
                    img.save(
                        output_path,
                        "JPEG",
                        quality=self.heic_quality_map[quality],
                        optimize=True,
                        progressive=True,
                        subsampling=0,  # Отключаем субдискретизацию для лучшего качества
                    )
                return output_path
            except Exception as e:
                logger.warning(f"pyheif не смог обработать файл: {str(e)}")

            # Если pyheif не сработал, пробуем sips (macOS)
            try:
                if sys.platform == "darwin":  # Проверяем, что это macOS
                    subprocess.run(
                        [
                            "sips",
                            "-s",
                            "format",
                            "jpeg",
                            "--out",
                            output_path,
                            input_path,
                        ],
                        check=True,
                        capture_output=True,
                    )
                    return output_path
            except Exception as e:
                logger.warning(f"sips не смог обработать файл: {str(e)}")

            # Если sips не сработал, пробуем ImageMagick
            try:
                if shutil.which("convert"):  # Проверяем наличие ImageMagick
                    subprocess.run(
                        [
                            "convert",
                            input_path,
                            "-quality",
                            str(self.heic_quality_map[quality]),
                            output_path,
                        ],
                        check=True,
                        capture_output=True,
                    )
                    return output_path
            except Exception as e:
                logger.warning(f"ImageMagick не смог обработать файл: {str(e)}")

            # Если все предыдущие методы не сработали, пробуем FFmpeg
            try:
                if shutil.which("ffmpeg"):  # Проверяем наличие FFmpeg
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-i",
                            input_path,
                            "-vf",
                            "scale=iw*min(4096/iw\,1):ih*min(4096/ih\,1):force_original_aspect_ratio=decrease",
                            "-q:v",
                            str(self.heic_quality_map[quality]),
                            output_path,
                        ],
                        check=True,
                        capture_output=True,
                    )
                    return output_path
            except Exception as e:
                logger.error(f"FFmpeg не смог обработать файл: {str(e)}")
                raise

            raise Exception(
                "Не удалось обработать HEIC файл ни одним из доступных методов"
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке HEIC: {str(e)}")
            raise

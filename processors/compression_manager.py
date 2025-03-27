#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from .image_processor import ImageProcessor
from .video_processor import VideoProcessor


class CompressionManager:
    """
    Менеджер сжатия медиа-файлов.
    Определяет подходящий процессор для каждого типа файла и
    управляет процессом сжатия.
    """

    def __init__(self):
        """Инициализация менеджера сжатия"""
        self.processors = [ImageProcessor(), VideoProcessor()]

    def compress_file(self, file_path, output_dir, quality_level):
        """
        Сжатие файла с определением подходящего процессора

        Args:
            file_path (str): Путь к исходному файлу
            output_dir (str): Директория для сохранения сжатого файла
            quality_level (str): Уровень качества (Высокое, Среднее, Низкое)

        Returns:
            str: Путь к сжатому файлу или None, если файл не поддерживается
        """
        # Проверка существования файла
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл {file_path} не найден")

        # Проверка существования директории для сохранения
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Определяем расширение файла
        ext = os.path.splitext(file_path)[1].lower()

        # Определяем тип файла по расширению
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".heic"]
        video_extensions = [".mp4", ".mov", ".avi"]

        # Выбираем подходящий процессор
        if ext in image_extensions:
            for processor in self.processors:
                if isinstance(processor, ImageProcessor) and processor.can_process(
                    file_path
                ):
                    return processor.compress_image(
                        file_path, output_dir, quality_level
                    )
        elif ext in video_extensions:
            for processor in self.processors:
                if isinstance(processor, VideoProcessor) and processor.can_process(
                    file_path
                ):
                    return processor.compress_video(
                        file_path, output_dir, quality_level
                    )

        # Если подходящий процессор не найден
        raise ValueError(
            f"Неподдерживаемый тип файла: {file_path}. "
            f"Поддерживаемые форматы: изображения {', '.join(image_extensions)}, "
            f"видео {', '.join(video_extensions)}"
        )

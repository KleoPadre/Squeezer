#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


class VideoProcessor:
    """Класс для обработки и сжатия видео"""

    def __init__(self):
        # Соответствие уровней качества для сжатия видео
        self.quality_map = {
            "Высокое": {"crf": "23", "preset": "medium"},
            "Среднее": {"crf": "26", "preset": "medium"},
            "Низкое": {"crf": "28", "preset": "fast"},
        }

        # Поддерживаемые форматы
        self.supported_formats = [".mp4", ".mov", ".avi"]

        # Пути к бинарным файлам FFmpeg
        self.ffmpeg_path = self._get_ffmpeg_path()
        self.ffprobe_path = self._get_ffprobe_path()

    def _get_resource_path(self, relative_path):
        """Получение абсолютного пути к ресурсу"""
        if hasattr(sys, "_MEIPASS"):
            # PyInstaller создает временную папку и хранит путь в _MEIPASS
            return os.path.join(sys._MEIPASS, relative_path)

        # Если запускается не из бинарника, используем текущий путь
        base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(base_path, relative_path)

    def _get_ffmpeg_path(self):
        """Получение пути к исполняемому файлу FFmpeg"""
        # Проверяем встроенный FFmpeg
        embedded_ffmpeg = self._get_resource_path(os.path.join("bin", "ffmpeg"))
        if os.path.exists(embedded_ffmpeg):
            # Делаем файл исполняемым, если он еще не исполняемый
            if not os.access(embedded_ffmpeg, os.X_OK):
                try:
                    os.chmod(embedded_ffmpeg, 0o755)
                except Exception:
                    pass
            return embedded_ffmpeg

        # Если встроенного нет, пытаемся использовать системный
        return "ffmpeg"

    def _get_ffprobe_path(self):
        """Получение пути к исполняемому файлу FFprobe"""
        # Проверяем встроенный FFprobe
        embedded_ffprobe = self._get_resource_path(os.path.join("bin", "ffprobe"))
        if os.path.exists(embedded_ffprobe):
            # Делаем файл исполняемым, если он еще не исполняемый
            if not os.access(embedded_ffprobe, os.X_OK):
                try:
                    os.chmod(embedded_ffprobe, 0o755)
                except Exception:
                    pass
            return embedded_ffprobe

        # Если встроенного нет, пытаемся использовать системный
        return "ffprobe"

    def can_process(self, file_path):
        """Проверка, может ли процессор обработать данный файл"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_formats

    def _check_ffmpeg(self):
        """Проверка наличия FFmpeg"""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            # Если встроенный FFmpeg недоступен, пробуем использовать системный
            try:
                subprocess.run(
                    ["ffmpeg", "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
                self.ffmpeg_path = "ffmpeg"
                self.ffprobe_path = "ffprobe"
                return True
            except (subprocess.SubprocessError, FileNotFoundError):
                return False

    def _get_video_metadata(self, video_path):
        """Получение метаданных видеофайла"""
        try:
            cmd = [
                self.ffprobe_path,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                video_path,
            ]

            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )

            return json.loads(result.stdout)
        except subprocess.SubprocessError as e:
            raise Exception(f"Ошибка при получении метаданных видео: {str(e)}")

    def compress_video(self, video_path, output_dir, quality_level):
        """
        Сжатие видео с сохранением метаданных

        Args:
            video_path (str): Путь к исходному видео
            output_dir (str): Директория для сохранения сжатого видео
            quality_level (str): Уровень качества (Высокое, Среднее, Низкое)

        Returns:
            str: Путь к сжатому видео
        """
        if not self._check_ffmpeg():
            raise Exception(
                "FFmpeg не доступен. Пожалуйста, свяжитесь с разработчиком."
            )

        # Получение имени файла
        file_name = os.path.basename(video_path)

        # Определение пути для сохранения (всегда mp4)
        output_name = os.path.splitext(file_name)[0] + ".mp4"
        output_path = os.path.join(output_dir, output_name)

        # Получение настроек качества
        quality = self.quality_map[quality_level]
        crf = quality["crf"]
        preset = quality["preset"]

        try:
            # Получение метаданных для сохранения
            metadata = self._get_video_metadata(video_path)

            # Настройка команды FFmpeg для сжатия с сохранением метаданных
            cmd = [
                self.ffmpeg_path,
                "-i",
                video_path,
                "-c:v",
                "libx264",  # H.264 кодек для видео
                "-crf",
                crf,  # Фактор постоянного качества
                "-preset",
                preset,  # Пресет сжатия
                "-c:a",
                "aac",  # AAC кодек для аудио
                "-b:a",
                "128k",  # Битрейт аудио
                "-map_metadata",
                "0",  # Копирование метаданных
                "-movflags",
                "faststart",  # Оптимизация для стриминга
                "-y",  # Перезапись файла если существует
                output_path,
            ]

            # Запуск процесса сжатия
            process = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )

            return output_path

        except subprocess.SubprocessError as e:
            raise Exception(f"Ошибка при сжатии видео {file_name}: {str(e)}")
        except Exception as e:
            raise Exception(f"Ошибка обработки видео {file_name}: {str(e)}")

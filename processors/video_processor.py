#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Класс для обработки и сжатия видео"""

    def __init__(self):
        # Соответствие уровней качества для сжатия видео
        self.quality_map = {
            "Максимальное": {
                "crf": 18,  # Высококачественное сжатие с небольшим уменьшением размера
                "preset": "slow",  # Более медленный пресет для лучшего качества
                "scale": "iw:ih",  # Сохраняем оригинальное разрешение
                "audio_bitrate": "320k",  # Высокий битрейт для аудио
                "threads": "0",
                "profile": "high",
                "level": "4.2",
                "x264opts": "ref=5:me=umh:subme=8:trellis=1:rc-lookahead=60:deblock=0:0:psy-rd=0.8,0.1",
            },
            "Высокое": {
                "crf": 20,  # Улучшенное качество для высокого уровня
                "preset": "medium",
                "scale": "iw*min(1920/iw\,1):ih*min(1080/ih\,1):force_original_aspect_ratio=decrease",
                "audio_bitrate": "256k",
                "threads": "0",
                "profile": "high",
                "level": "4.1",
                "x264opts": "ref=4:me=hex:subme=7:trellis=1:rc-lookahead=50:deblock=1,1:psy-rd=0.8,0.1",
            },
            "Среднее": {
                "crf": 23,  # Улучшенное качество для среднего уровня
                "preset": "faster",
                "scale": "iw*min(1280/iw\,1):ih*min(720/ih\,1):force_original_aspect_ratio=decrease",
                "audio_bitrate": "192k",
                "threads": "0",
                "profile": "high",
                "level": "4.0",
                "x264opts": "ref=3:me=hex:subme=6:trellis=1:rc-lookahead=40:deblock=1,1:psy-rd=0.6,0.1",
            },
            "Низкое": {
                "crf": 26,  # Улучшенное качество для низкого уровня
                "preset": "veryfast",
                "scale": "iw*min(854/iw\,1):ih*min(480/ih\,1):force_original_aspect_ratio=decrease",
                "audio_bitrate": "128k",
                "threads": "0",
                "profile": "main",
                "level": "3.1",
                "x264opts": "ref=2:me=dia:subme=4:trellis=0:rc-lookahead=30:deblock=1,1:psy-rd=0.4,0.0",
            },
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
            path = os.path.join(sys._MEIPASS, relative_path)
            logger.info(f"Путь к ресурсу (PyInstaller): {path}")
            return path

        # Если запускается не из бинарника, используем текущий путь
        base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        path = os.path.join(base_path, relative_path)
        logger.info(f"Путь к ресурсу (обычный): {path}")
        return path

    def _get_ffmpeg_path(self):
        """Получение пути к исполняемому файлу FFmpeg"""
        # Проверяем встроенный FFmpeg
        embedded_ffmpeg = self._get_resource_path(os.path.join("bin", "ffmpeg"))
        logger.info(f"Проверяем встроенный FFmpeg: {embedded_ffmpeg}")
        if os.path.exists(embedded_ffmpeg):
            # Делаем файл исполняемым, если он еще не исполняемый
            if not os.access(embedded_ffmpeg, os.X_OK):
                try:
                    os.chmod(embedded_ffmpeg, 0o755)
                    logger.info("Установлены права на выполнение для FFmpeg")
                except Exception as e:
                    logger.error(f"Ошибка при установке прав на выполнение: {str(e)}")
            return embedded_ffmpeg

        # Если встроенного нет, пытаемся использовать системный
        logger.info("Встроенный FFmpeg не найден, используем системный")
        return "ffmpeg"

    def _get_ffprobe_path(self):
        """Получение пути к исполняемому файлу FFprobe"""
        # Проверяем встроенный FFprobe
        embedded_ffprobe = self._get_resource_path(os.path.join("bin", "ffprobe"))
        logger.info(f"Проверяем встроенный FFprobe: {embedded_ffprobe}")
        if os.path.exists(embedded_ffprobe):
            # Делаем файл исполняемым, если он еще не исполняемый
            if not os.access(embedded_ffprobe, os.X_OK):
                try:
                    os.chmod(embedded_ffprobe, 0o755)
                    logger.info("Установлены права на выполнение для FFprobe")
                except Exception as e:
                    logger.error(f"Ошибка при установке прав на выполнение: {str(e)}")
            return embedded_ffprobe

        # Если встроенного нет, пытаемся использовать системный
        logger.info("Встроенный FFprobe не найден, используем системный")
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

    def _get_available_hw_accels(self) -> list:
        """Получает список доступных аппаратных ускорителей"""
        try:
            logger.info(
                f"Проверяем аппаратные ускорители с помощью FFmpeg: {self.ffmpeg_path}"
            )
            result = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-hwaccels"],
                capture_output=True,
                text=True,
            )

            available_accels = []
            output = result.stdout.lower()
            logger.info(f"Вывод команды -hwaccels: {output}")

            # Проверяем поддержку различных ускорителей
            if "videotoolbox" in output:
                available_accels.append("videotoolbox")
                logger.info("Найден ускоритель VideoToolbox")
            if "cuda" in output:
                available_accels.append("cuda")
                logger.info("Найден ускоритель CUDA")
            if "qsv" in output:
                available_accels.append("qsv")
                logger.info("Найден ускоритель QSV")

            if not available_accels:
                logger.warning("Аппаратные ускорители не найдены")

            return available_accels
        except Exception as e:
            logger.error(f"Ошибка при определении аппаратных ускорителей: {str(e)}")
            return []

    def compress_video(self, video_path, output_dir, quality_level):
        """
        Сжатие видео с сохранением метаданных

        Args:
            video_path (str): Путь к исходному видео
            output_dir (str): Директория для сохранения сжатого видео
            quality_level (str): Уровень качества (Максимальное, Высокое, Среднее, Низкое)

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

        # Получаем настройки качества
        settings = self.quality_map[quality_level]
        logger.info(f"Используем настройки качества: {quality_level}")

        # Определяем настройки битрейта в зависимости от качества
        bitrates = {
            "Максимальное": "8M",
            "Высокое": "6M",
            "Среднее": "4M",
            "Низкое": "2M",
        }

        bitrate = bitrates.get(quality_level, "4M")

        try:
            # Для всех уровней качества используем CRF
            cmd = [
                self.ffmpeg_path,
                "-i",
                video_path,
                "-c:v",
                "libx264",
                "-crf",
                str(settings["crf"]),
                "-preset",
                settings["preset"],
                "-profile:v",
                settings["profile"],
                "-level",
                settings["level"],
                "-vf",
                settings["scale"],
                "-c:a",
                "aac",
                "-b:a",
                settings["audio_bitrate"],
                "-threads",
                settings["threads"],
                "-map_metadata",
                "0",
                "-movflags",
                "faststart",
                "-y",
                output_path,
            ]

            logger.info(f"Выполняем команду: {' '.join(cmd)}")

            # Запускаем FFmpeg
            process = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )

            return output_path

        except subprocess.SubprocessError as e:
            logger.error(f"Ошибка при выполнении команды FFmpeg: {str(e)}")

            # Пробуем резервный вариант
            try:
                logger.info("Пробуем запасной вариант сжатия...")

                cmd = [
                    self.ffmpeg_path,
                    "-i",
                    video_path,
                    "-c:v",
                    "libx264",
                    "-crf",
                    "20",
                    "-preset",
                    "medium",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-y",
                    output_path,
                ]

                logger.info(f"Выполняем команду: {' '.join(cmd)}")

                process = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
                )

                return output_path

            except subprocess.SubprocessError as e2:
                logger.error(f"Ошибка при выполнении запасной команды: {str(e2)}")
                stderr = (
                    e2.stderr.decode("utf-8", errors="replace")
                    if hasattr(e2, "stderr")
                    else "Нет дополнительной информации"
                )
                logger.error(f"Вывод ошибки: {stderr}")
                raise Exception(
                    f"Не удалось сжать видео. Формат файла может быть несовместим."
                )
        except Exception as e:
            logger.error(f"Непредвиденная ошибка: {str(e)}")
            raise Exception(f"Ошибка при обработке видео: {str(e)}")

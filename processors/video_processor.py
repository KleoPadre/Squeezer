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

    def _compress_video(self, input_path: str, output_path: str, quality: str) -> str:
        """Сжатие видео файла"""
        try:
            # Получаем путь к FFmpeg
            ffmpeg_path = self._get_ffmpeg_path()
            if not ffmpeg_path:
                raise Exception("FFmpeg не найден в системе")

            # Получаем информацию о видео через ffprobe
            probe_cmd = [
                self.ffprobe_path,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                input_path,
            ]

            probe_result = subprocess.run(
                probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )

            video_info = json.loads(probe_result.stdout)
            video_stream = next(
                s for s in video_info["streams"] if s["codec_type"] == "video"
            )
            width = int(video_stream["width"])
            height = int(video_stream["height"])

            # Определяем параметры сжатия в зависимости от качества
            quality_settings = {
                "Высокое": {
                    "crf": 23,
                    "preset": "medium",
                    "scale": "iw*min(1920/iw\,1):ih*min(1080/ih\,1):force_original_aspect_ratio=decrease",
                    "audio_bitrate": "192k",
                    "threads": "0",  # Автоматический выбор количества потоков
                },
                "Среднее": {
                    "crf": 28,
                    "preset": "faster",
                    "scale": "iw*min(1280/iw\,1):ih*min(720/ih\,1):force_original_aspect_ratio=decrease",
                    "audio_bitrate": "128k",
                    "threads": "0",
                },
                "Низкое": {
                    "crf": 33,
                    "preset": "veryfast",
                    "scale": "iw*min(854/iw\,1):ih*min(480/ih\,1):force_original_aspect_ratio=decrease",
                    "audio_bitrate": "96k",
                    "threads": "0",
                },
            }

            settings = quality_settings[quality]

            # Формируем базовую команду FFmpeg
            cmd = [
                ffmpeg_path,
                "-i",
                input_path,
                "-c:v",
                "libx264",
                "-crf",
                str(settings["crf"]),
                "-preset",
                settings["preset"],
                "-vf",
                settings["scale"],
                "-c:a",
                "aac",
                "-b:a",
                settings["audio_bitrate"],
                "-threads",
                settings["threads"],
                "-y",  # Перезаписать существующий файл
                output_path,
            ]

            # Автоматически определяем и используем доступное аппаратное ускорение
            try:
                # Проверяем доступные аппаратные ускорители
                hw_accels = self._get_available_hw_accels()

                if hw_accels:
                    # Используем первый доступный ускоритель
                    hw_accel = hw_accels[0]
                    if hw_accel == "videotoolbox":
                        cmd.insert(1, "-hwaccel")
                        cmd.insert(2, "videotoolbox")
                        cmd.insert(3, "-c:v")
                        cmd.insert(4, "h264_videotoolbox")
                    elif hw_accel == "cuda":
                        cmd.insert(1, "-hwaccel")
                        cmd.insert(2, "cuda")
                        cmd.insert(3, "-c:v")
                        cmd.insert(4, "h264_nvenc")
                    elif hw_accel == "qsv":
                        cmd.insert(1, "-hwaccel")
                        cmd.insert(2, "qsv")
                        cmd.insert(3, "-c:v")
                        cmd.insert(4, "h264_qsv")
            except Exception as e:
                logger.warning(
                    f"Не удалось использовать аппаратное ускорение: {str(e)}"
                )

            # Запускаем процесс сжатия
            process = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )

            return output_path

        except Exception as e:
            logger.error(f"Ошибка при сжатии видео: {str(e)}")
            raise

    def _get_available_hw_accels(self) -> list:
        """Получает список доступных аппаратных ускорителей"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-hwaccels"],
                capture_output=True,
                text=True,
            )

            available_accels = []
            output = result.stdout.lower()

            # Проверяем поддержку различных ускорителей
            if "videotoolbox" in output:
                available_accels.append("videotoolbox")
            if "cuda" in output:
                available_accels.append("cuda")
            if "qsv" in output:
                available_accels.append("qsv")

            return available_accels
        except Exception as e:
            logger.warning(f"Ошибка при определении аппаратных ускорителей: {str(e)}")
            return []

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

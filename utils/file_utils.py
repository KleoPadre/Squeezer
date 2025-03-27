#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from pathlib import Path


def get_file_size(file_path):
    """
    Получение размера файла в человекочитаемом формате

    Args:
        file_path (str): Путь к файлу

    Returns:
        str: Размер файла в человекочитаемом формате
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return format_size(size_bytes)
    except (FileNotFoundError, OSError):
        return "0 Б"


def format_size(size_bytes):
    """
    Форматирование размера в байтах в человекочитаемый формат

    Args:
        size_bytes (int): Размер в байтах

    Returns:
        str: Форматированный размер
    """
    for unit in ["Б", "КБ", "МБ", "ГБ", "ТБ"]:
        if size_bytes < 1024.0 or unit == "ТБ":
            break
        size_bytes /= 1024.0

    return f"{size_bytes:.2f} {unit}"


def filter_media_files(files, include_images=True, include_videos=True):
    """
    Фильтрация списка файлов по медиа-типам

    Args:
        files (list): Список путей к файлам
        include_images (bool): Включать изображения
        include_videos (bool): Включать видео

    Returns:
        list: Список отфильтрованных файлов
    """
    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".heic"]
    video_extensions = [".mp4", ".mov", ".avi"]

    result = []

    for file_path in files:
        ext = os.path.splitext(file_path)[1].lower()

        if include_images and ext in image_extensions:
            result.append(file_path)
        elif include_videos and ext in video_extensions:
            result.append(file_path)

    return result


def create_output_filename(input_path, output_dir, suffix="_compressed"):
    """
    Создание имени выходного файла с учетом уже существующих файлов

    Args:
        input_path (str): Путь к исходному файлу
        output_dir (str): Директория для сохранения
        suffix (str): Суффикс для добавления к имени файла

    Returns:
        str: Путь к выходному файлу
    """
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)

    # Создание нового имени файла
    new_name = f"{name}{suffix}{ext}"
    output_path = os.path.join(output_dir, new_name)

    # Проверка на существование файла
    counter = 1
    while os.path.exists(output_path):
        new_name = f"{name}{suffix}_{counter}{ext}"
        output_path = os.path.join(output_dir, new_name)
        counter += 1

    return output_path


def format_time_estimate(seconds):
    """
    Форматирование оценки времени в человекочитаемый формат

    Args:
        seconds (float): Количество секунд

    Returns:
        str: Форматированное время
    """
    if seconds < 60:
        return f"{seconds:.0f} сек"
    elif seconds < 3600:
        mins = seconds / 60
        return f"{mins:.0f} мин"
    else:
        hours = seconds / 3600
        mins = (seconds % 3600) / 60
        return f"{hours:.0f} ч {mins:.0f} мин"

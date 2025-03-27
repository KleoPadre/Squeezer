#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path


class Settings:
    """Класс для хранения и загрузки настроек приложения"""

    def __init__(self):
        """Инициализация настроек по умолчанию"""
        self.settings_path = Path.home() / ".squeezer_settings.json"

        # Настройки по умолчанию
        self.default_settings = {
            "output_dir": str(Path.home() / "Downloads" / "Squeezer"),
            "quality_level": "Максимальное",
            "preserve_metadata": True,
            "recent_folders": [],
        }

        # Загрузка сохраненных настроек или использование значений по умолчанию
        self.settings = self.load_settings()

    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            if not self.settings_path.exists():
                return self.default_settings.copy()

            with open(self.settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)

            # Проверка наличия всех необходимых настроек
            for key, value in self.default_settings.items():
                if key not in settings:
                    settings[key] = value

            return settings
        except Exception:
            # При любой ошибке загружаем настройки по умолчанию
            return self.default_settings.copy()

    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def get(self, key, default=None):
        """Получение значения настройки"""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Установка значения настройки"""
        self.settings[key] = value
        self.save_settings()

    def add_recent_folder(self, folder_path):
        """Добавление папки в список недавних"""
        recent_folders = self.get("recent_folders", [])

        # Удаление этой папки из списка, если она там уже есть
        if folder_path in recent_folders:
            recent_folders.remove(folder_path)

        # Добавление папки в начало списка
        recent_folders.insert(0, folder_path)

        # Ограничение списка до 10 элементов
        if len(recent_folders) > 10:
            recent_folders = recent_folders[:10]

        self.set("recent_folders", recent_folders)

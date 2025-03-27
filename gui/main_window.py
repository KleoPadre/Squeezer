#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QFileDialog,
    QListWidget,
    QGroupBox,
    QMessageBox,
    QComboBox,
    QTextEdit,
    QProgressDialog,
    QDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QPalette, QPixmap
import logging

from processors.compression_manager import CompressionManager
from utils.settings import Settings
from utils.file_utils import format_size


logger = logging.getLogger("MainWindow")


class CompressionThread(QThread):
    """Поток для выполнения сжатия файлов"""

    progress_update = pyqtSignal(dict)
    compression_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    file_processed = pyqtSignal(dict)  # Новый сигнал для информации о сжатом файле

    def __init__(self, files, output_dir, quality_level):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.quality_level = quality_level
        self.manager = CompressionManager()
        self.stopped = False

    def run(self):
        total_files = len(self.files)
        processed_files = 0
        total_original_size = 0
        total_compressed_size = 0
        failed_files = []

        # Статистика для каждого файла
        file_stats = []

        # Отправляем начальное обновление прогресса
        self.progress_update.emit(
            {
                "file": "",
                "total": total_files,
                "processed": processed_files,
                "percent": 0,
                "remaining_time": None,
            }
        )

        start_time = time.time()

        for file_info in self.files:
            if self.stopped:
                break

            if isinstance(file_info, tuple):
                file_path, rel_path = file_info
            else:
                file_path = file_info
                rel_path = os.path.basename(file_path)

            try:
                # Обновляем информацию о текущем файле
                self.progress_update.emit(
                    {
                        "file": rel_path,
                        "total": total_files,
                        "processed": processed_files,
                        "percent": int(processed_files / total_files * 100),
                        "remaining_time": self._estimate_remaining_time(
                            start_time, processed_files, total_files
                        ),
                    }
                )

                # Получаем оригинальный размер файла
                original_size = os.path.getsize(file_path)
                total_original_size += original_size

                # Создаем директорию для сохранения файла с учетом структуры подпапок
                output_subdir = os.path.dirname(os.path.join(self.output_dir, rel_path))
                if output_subdir and not os.path.exists(output_subdir):
                    os.makedirs(output_subdir, exist_ok=True)

                # Выполняем сжатие файла
                compressed_file = self.manager.compress_file(
                    file_path, output_subdir, self.quality_level
                )

                # Получаем размер сжатого файла
                compressed_size = os.path.getsize(compressed_file)
                total_compressed_size += compressed_size

                # Рассчитываем процент изменения размера
                size_change_percent = (
                    (original_size - compressed_size) / original_size * 100
                    if original_size > 0
                    else 0
                )

                # Обновляем статистику
                file_stat = {
                    "file": rel_path,
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "change_percent": size_change_percent,
                }
                file_stats.append(file_stat)

                # Отправляем сигнал с информацией о сжатом файле
                self.file_processed.emit(file_stat)

            except Exception as e:
                error_message = f"Ошибка при обработке файла {rel_path}: {str(e)}"
                failed_files.append((rel_path, str(e)))
                self.error_occurred.emit(error_message)

            finally:
                processed_files += 1

                # Обновляем прогресс
                progress_percent = int(processed_files / total_files * 100)
                remaining_time = self._estimate_remaining_time(
                    start_time, processed_files, total_files
                )

                self.progress_update.emit(
                    {
                        "file": rel_path,
                        "total": total_files,
                        "processed": processed_files,
                        "percent": progress_percent,
                        "remaining_time": remaining_time,
                    }
                )

        # Отправляем информацию о завершении сжатия
        if failed_files:
            error_msg = "Следующие файлы не удалось обработать:\n\n"
            for file_name, error in failed_files:
                error_msg += f"• {file_name}: {error}\n\n"
            self.error_occurred.emit(error_msg)

        # Отправляем финальное обновление прогресса
        self.progress_update.emit(
            {
                "file": "",
                "total": total_files,
                "processed": processed_files,
                "percent": 100,
                "remaining_time": 0,
            }
        )

        self.compression_finished.emit()

    def stop(self):
        """Остановка процесса сжатия"""
        self.stopped = True

    def _estimate_remaining_time(self, start_time, processed_files, total_files):
        if processed_files == 0:
            return None
        elapsed = time.time() - start_time
        estimated_total = (elapsed / processed_files) * total_files
        remaining = estimated_total - elapsed
        return remaining


class TestCompressionWorker(QObject):
    """Рабочий объект для тестирования сжатия на одном файле"""

    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(dict)

    def __init__(self, file_path, output_dir, quality_level):
        super().__init__()
        self.file_path = file_path
        self.output_dir = output_dir
        self.quality_level = quality_level
        self.manager = CompressionManager()

    def run(self):
        """Запуск тестового сжатия"""
        try:
            # Получаем размер исходного файла
            original_size = os.path.getsize(self.file_path)
            file_name = os.path.basename(self.file_path)

            # Эмуляция прогресса
            self.progress_updated.emit(10)

            # Сжимаем файл
            compressed_path = self.manager.compress_file(
                self.file_path, self.output_dir, self.quality_level
            )

            self.progress_updated.emit(90)

            # Получаем размер сжатого файла
            compressed_size = os.path.getsize(compressed_path)

            # Вычисляем соотношение сжатия
            ratio = (
                (original_size - compressed_size) / original_size
                if original_size > 0
                else 0
            )

            # Формируем результат
            result = {
                "original_path": self.file_path,
                "compressed_path": compressed_path,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "original_size_str": format_size(original_size),
                "compressed_size_str": format_size(compressed_size),
                "ratio": ratio,
                "quality_level": self.quality_level,
            }

            self.progress_updated.emit(100)
            self.finished.emit(result)

        except Exception as e:
            logger.error(f"Ошибка при тестовом сжатии: {str(e)}")
            self.finished.emit({"error": str(e)})


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()

        self.settings = Settings()
        self.files_to_compress = []
        self.compression_thread = None
        self.start_time = (
            None  # Добавляем переменную для отслеживания времени начала сжатия
        )
        self.elapsed_time = (
            0  # Добавляем переменную для хранения общего времени выполнения
        )
        self.compression_stats = []  # Для хранения статистики сжатия

        self.init_ui()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("Squeezer - Программа для сжатия медиафайлов")
        self.setGeometry(100, 100, 800, 600)

        # Основной макет
        main_layout = QVBoxLayout()
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Группа для выбора файлов
        files_group = QGroupBox("Выбор файлов")
        files_layout = QVBoxLayout()

        # Кнопки для выбора файлов
        buttons_layout = QHBoxLayout()
        self.select_files_btn = QPushButton("Выбрать файлы")
        self.select_files_btn.clicked.connect(self.select_files)
        self.select_folder_btn = QPushButton("Выбрать папку")
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.clear_selection_btn = QPushButton("Очистить выбор")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        self.clear_selection_btn.setEnabled(False)

        # Кнопка для предварительной проверки сжатия
        self.test_compress_btn = QPushButton("Тест сжатия")
        self.test_compress_btn.clicked.connect(self.test_compression)
        self.test_compress_btn.setEnabled(False)

        buttons_layout.addWidget(self.select_files_btn)
        buttons_layout.addWidget(self.select_folder_btn)
        buttons_layout.addWidget(self.clear_selection_btn)
        buttons_layout.addWidget(self.test_compress_btn)
        files_layout.addLayout(buttons_layout)

        # Список выбранных файлов
        self.files_list = QListWidget()
        files_layout.addWidget(self.files_list)

        files_group.setLayout(files_layout)
        main_layout.addWidget(files_group)

        # Настройки сжатия
        settings_group = QGroupBox("Настройки")
        settings_layout = QHBoxLayout()

        # Выбор качества
        quality_layout = QVBoxLayout()
        quality_label = QLabel("Качество сжатия:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Максимальное", "Высокое", "Среднее", "Низкое"])
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)

        # Выбор папки сохранения
        output_layout = QVBoxLayout()
        output_label = QLabel("Папка сохранения:")
        self.output_path_label = QLabel(str(Path.home() / "Downloads" / "Squeezer"))
        self.output_path_label.setWordWrap(True)
        self.select_output_btn = QPushButton("Выбрать")
        self.select_output_btn.clicked.connect(self.select_output_folder)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path_label)
        output_layout.addWidget(self.select_output_btn)

        settings_layout.addLayout(quality_layout)
        settings_layout.addLayout(output_layout)
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # Прогресс сжатия
        progress_group = QGroupBox("Прогресс")
        progress_layout = QVBoxLayout()

        # Текущий файл
        self.current_file_label = QLabel("Готов к сжатию")
        progress_layout.addWidget(self.current_file_label)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.set_progress_bar_color("processing")
        progress_layout.addWidget(self.progress_bar)

        # Информация о прогрессе
        self.progress_info_label = QLabel("0/0 файлов | Оставшееся время: -")
        progress_layout.addWidget(self.progress_info_label)

        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        # Кнопки управления
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Начать сжатие")
        self.stop_btn = QPushButton("Остановить")

        self.start_btn.clicked.connect(self.start_compression)
        self.stop_btn.clicked.connect(self.stop_compression)
        self.stop_btn.setEnabled(False)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        main_layout.addLayout(control_layout)

    def select_files(self):
        """Выбор файлов для сжатия"""
        # Определяем поддерживаемые форматы
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".heic"]
        video_extensions = [".mp4", ".mov", ".avi"]
        supported_extensions = image_extensions + video_extensions

        # Формируем строку фильтра для диалога выбора файлов
        filter_str = "Все поддерживаемые файлы ("
        for ext in supported_extensions:
            filter_str += f"*{ext} "
        filter_str = filter_str.strip() + ");;"

        filter_str += "Изображения ("
        for ext in image_extensions:
            filter_str += f"*{ext} "
        filter_str = filter_str.strip() + ");;"

        filter_str += "Видео ("
        for ext in video_extensions:
            filter_str += f"*{ext} "
        filter_str = filter_str.strip() + ");;"

        filter_str += "Все файлы (*.*)"

        # Показываем диалог выбора файлов
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выбор файлов для сжатия", "", filter_str
        )

        if files:
            self.add_files(files)

    def select_folder(self):
        """Выбор папки с файлами для сжатия"""
        folder = QFileDialog.getExistingDirectory(
            self, "Выбор папки с файлами для сжатия", ""
        )

        if folder:
            self.add_folder(folder)

    def add_folder(self, folder_path):
        """Добавление всех файлов из папки и подпапок с сохранением структуры"""
        # Определяем поддерживаемые форматы
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".heic"]
        video_extensions = [".mp4", ".mov", ".avi"]
        supported_extensions = image_extensions + video_extensions

        base_folder = os.path.normpath(folder_path)
        files_added = 0

        # Рекурсивно обходим все подпапки
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file_path)[1].lower()

                # Если расширение поддерживается, добавляем файл
                if ext in supported_extensions:
                    # Сохраняем относительный путь от базовой папки
                    rel_path = os.path.relpath(file_path, base_folder)

                    # Добавляем кортеж (полный путь, относительный путь)
                    if (file_path, rel_path) not in self.files_to_compress:
                        self.files_to_compress.append((file_path, rel_path))
                        self.files_list.addItem(rel_path)
                        files_added += 1

        # Обновляем интерфейс
        self.clear_selection_btn.setEnabled(True)
        self.test_compress_btn.setEnabled(bool(self.files_to_compress))
        self.start_btn.setEnabled(True)

        # Сообщаем пользователю о количестве добавленных файлов
        if files_added > 0:
            QMessageBox.information(
                self,
                "Файлы добавлены",
                f"Добавлено {files_added} файлов из папки {folder_path}",
                QMessageBox.StandardButton.Ok,
            )
        else:
            QMessageBox.warning(
                self,
                "Нет подходящих файлов",
                f"В папке {folder_path} не найдено поддерживаемых файлов.",
                QMessageBox.StandardButton.Ok,
            )

    def add_files(self, files):
        """Добавление файлов в список для сжатия"""
        # Определяем поддерживаемые форматы
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".heic"]
        video_extensions = [".mp4", ".mov", ".avi"]
        supported_extensions = image_extensions + video_extensions

        # Проверяем каждый файл
        unsupported_files = []
        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in supported_extensions:
                # Используем кортеж (полный путь, имя файла), чтобы сохранить структуру
                file_name = os.path.basename(file_path)
                if (file_path, file_name) not in self.files_to_compress:
                    self.files_to_compress.append((file_path, file_name))
                    self.files_list.addItem(file_name)
            else:
                unsupported_files.append(os.path.basename(file_path))

        # Если есть неподдерживаемые файлы, показываем предупреждение
        if unsupported_files:
            warning_dialog = QMessageBox(self)
            warning_dialog.setIcon(QMessageBox.Icon.Warning)
            warning_dialog.setWindowTitle("Неподдерживаемые файлы")
            warning_dialog.setText(
                "Некоторые файлы не были добавлены, так как имеют неподдерживаемый формат."
            )

            detailed_text = "Следующие файлы не были добавлены:\n" + "\n".join(
                f"- {file}" for file in unsupported_files
            ) + "\n\nПрограмма поддерживает следующие форматы:\n\n" "Изображения:\n" + "\n".join(
                f"- {ext}" for ext in image_extensions
            ) + "\n\nВидео:\n" + "\n".join(
                f"- {ext}" for ext in video_extensions
            )

            warning_dialog.setDetailedText(detailed_text)
            warning_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            warning_dialog.exec()

        # Обновляем состояние кнопок
        self.clear_selection_btn.setEnabled(bool(self.files_to_compress))
        self.test_compress_btn.setEnabled(bool(self.files_to_compress))
        self.start_btn.setEnabled(bool(self.files_to_compress))

    def clear_selection(self):
        """Очистка списка выбранных файлов"""
        self.files_to_compress = []
        self.files_list.clear()

    def select_output_folder(self):
        """Выбор папки для сохранения сжатых файлов"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сохранения сжатых файлов",
            self.output_path_label.text(),
        )

        if folder:
            self.output_path_label.setText(folder)

    def start_compression(self):
        """Запуск процесса сжатия"""
        if not self.files_to_compress:
            QMessageBox.warning(
                self,
                "Внимание",
                "Не выбраны файлы для сжатия",
                QMessageBox.StandardButton.Ok,
            )
            return

        # Получение настроек
        output_dir = self.output_path_label.text()
        quality_level = self.quality_combo.currentText()

        # Создание папки, если её нет
        os.makedirs(output_dir, exist_ok=True)

        # Запоминаем время начала сжатия
        self.start_time = time.time()

        # Подготовка UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.select_files_btn.setEnabled(False)
        self.select_folder_btn.setEnabled(False)
        self.clear_selection_btn.setEnabled(False)
        self.select_output_btn.setEnabled(False)

        # Очищаем предыдущую статистику
        self.compression_stats = []

        # Извлекаем пути к файлам для CompressionThread
        file_infos = self.files_to_compress

        # Запуск потока сжатия
        self.compression_thread = CompressionThread(
            file_infos, output_dir, quality_level
        )
        self.compression_thread.progress_update.connect(self.update_progress)
        self.compression_thread.compression_finished.connect(
            self.on_compression_finished
        )
        self.compression_thread.error_occurred.connect(self.on_error)
        self.compression_thread.file_processed.connect(self.on_file_processed)
        self.compression_thread.start()

    def set_progress_bar_color(self, state):
        """Установка цвета прогресс-бара в зависимости от состояния"""
        palette = QPalette()

        if state == "processing":
            # Синий цвет для процесса обработки
            color = QColor(0, 120, 215)  # Синий
        elif state == "finished":
            # Зеленый цвет для завершенного процесса
            color = QColor(0, 170, 0)  # Зеленый
        elif state == "error":
            # Красный цвет для ошибки
            color = QColor(232, 17, 35)  # Красный
        else:
            # Серый цвет для неактивного состояния
            color = QColor(128, 128, 128)

        palette.setColor(QPalette.ColorRole.Highlight, color)
        self.progress_bar.setPalette(palette)

    def update_progress(self, progress_data):
        """Обновление информации о прогрессе сжатия"""
        self.current_file_label.setText(f"Обработка: {progress_data['file']}")

        # Подсветка HEIC файлов особым цветом
        current_file = progress_data["file"]
        if os.path.splitext(current_file)[1].lower() == ".heic":
            self.current_file_label.setText(f"Обработка HEIC: {current_file}")

        self.progress_bar.setValue(progress_data["percent"])

        # Форматирование оставшегося времени
        mins, secs = divmod(int(progress_data["remaining_time"]), 60)

        # Более информативное отображение оставшегося времени
        if progress_data["remaining_time"] > 0:
            time_str = f"{mins} мин {secs} сек"
        else:
            # Если файл последний и прогресс почти завершен
            if (
                progress_data["processed"] == progress_data["total"]
                and progress_data["percent"] >= 95
            ):
                time_str = "завершается..."
            else:
                time_str = "рассчитывается..."

        self.progress_info_label.setText(
            f"{progress_data['processed']}/{progress_data['total']} файлов | Оставшееся время: {time_str}"
        )

        # Устанавливаем цвет в зависимости от прогресса
        self.set_progress_bar_color("processing")

        # Принудительное обновление UI
        self.repaint()

    def stop_compression(self):
        """Остановка процесса сжатия"""
        if self.compression_thread and self.compression_thread.isRunning():
            # Запоминаем время завершения
            if self.start_time is not None:
                self.elapsed_time = time.time() - self.start_time

            self.compression_thread.stop()
            self.compression_thread.wait()
            self.on_compression_finished()

    def on_file_processed(self, file_data):
        """Обработка информации о завершенном файле"""
        # Добавляем информацию о размерах в читаемом формате
        file_data["original_size_str"] = format_size(file_data["original_size"])
        file_data["compressed_size_str"] = format_size(file_data["compressed_size"])

        if "file" in file_data:
            # Сохраняем статистику для отдельного файла
            self.compression_stats.append(file_data)

            # Логируем информацию о сжатии
            ratio_percent = file_data["change_percent"]
            sign = "-" if ratio_percent > 0 else "+"
            abs_percent = abs(ratio_percent)

            logger.info(
                f"Файл: {file_data['file']} | "
                f"Исходный размер: {format_size(file_data['original_size'])} | "
                f"Размер после сжатия: {format_size(file_data['compressed_size'])} | "
                f"Изменение: {sign}{abs_percent:.1f}%"
            )

            if ratio_percent < 0:
                logger.warning(
                    f"Файл {file_data['file']} увеличился в размере после обработки! "
                    f"Было: {format_size(file_data['original_size'])}, стало: {format_size(file_data['compressed_size'])}"
                )
        else:
            # Это итоговая статистика
            self.summary_stats = file_data

    def on_compression_finished(self):
        """Обработка завершения сжатия"""
        # Рассчитываем общее время выполнения
        if self.start_time is not None:
            self.elapsed_time = time.time() - self.start_time
            self.start_time = None

        # Форматируем время выполнения
        mins, secs = divmod(int(self.elapsed_time), 60)
        hours, mins = divmod(mins, 60)

        if hours > 0:
            time_str = f"{hours} ч {mins} мин {secs} сек"
        elif mins > 0:
            time_str = f"{mins} мин {secs} сек"
        else:
            time_str = f"{secs} сек"

        # Восстановление UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.select_files_btn.setEnabled(True)
        self.select_folder_btn.setEnabled(True)
        self.clear_selection_btn.setEnabled(True)
        self.select_output_btn.setEnabled(True)

        # Обновление информации с более заметным индикатором завершения
        self.current_file_label.setText("✅ Сжатие завершено")

        # Если есть итоговая статистика, добавляем ее в сообщение
        if hasattr(self, "summary_stats"):
            ratio_percent = self.summary_stats["ratio"] * 100
            if ratio_percent > 0:
                efficiency_msg = f"Уменьшение размера: {ratio_percent:.1f}%"
            else:
                efficiency_msg = f"Увеличение размера: {abs(ratio_percent):.1f}%"

            self.progress_info_label.setText(
                f"Обработано файлов: {len(self.files_to_compress)} | "
                f"Время выполнения: {time_str} | "
                f"{efficiency_msg}"
            )

            # Записываем итоговую информацию в лог
            logger.info("\n" + "=" * 50)
            logger.info("ИТОГИ СЖАТИЯ:")
            logger.info(f"Время выполнения: {time_str}")
            logger.info(f"Обработано файлов: {len(self.files_to_compress)}")
            logger.info(
                f"Общий размер до сжатия: {self.summary_stats['original_size_str']}"
            )
            logger.info(
                f"Общий размер после сжатия: {self.summary_stats['compressed_size_str']}"
            )
            if ratio_percent > 0:
                logger.info(f"Общее уменьшение размера: {ratio_percent:.1f}%")
            else:
                logger.info(f"Общее увеличение размера: {abs(ratio_percent):.1f}%")

            # Добавляем детальную информацию по каждому файлу
            logger.info("\nДетальная информация по файлам:")
            for stat in self.compression_stats:
                ratio = stat["change_percent"] * 100
                sign = "-" if ratio > 0 else "+"
                abs_ratio = abs(ratio)
                logger.info(
                    f"Файл: {stat['file']}\n"
                    f"  Исходный размер: {stat['original_size_str']}\n"
                    f"  Размер после сжатия: {stat['compressed_size_str']}\n"
                    f"  Изменение: {sign}{abs_ratio:.1f}%"
                )
            logger.info("=" * 50 + "\n")

        else:
            self.progress_info_label.setText(
                f"Обработано файлов: {len(self.files_to_compress)} | "
                f"Время выполнения: {time_str}"
            )

        # Меняем цвет прогресс-бара на зеленый
        self.set_progress_bar_color("finished")

    def on_error(self, error_message):
        """Обработка ошибки при сжатии"""
        # Записываем ошибку в лог
        logger.error(f"Произошла ошибка при сжатии: {error_message}")

        # Определяем тип ошибки
        if "HEIC" in error_message or "heif" in error_message:
            # Ошибка связана с HEIC файлами
            error_dialog = QMessageBox(self)
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Ошибка при обработке HEIC файла")
            error_dialog.setText(
                "Возникла проблема при обработке файла в формате HEIC."
            )

            detailed_text = (
                "Проблемы с обработкой HEIC могут возникать из-за несовместимости версий библиотек.\n\n"
                "Возможные решения:\n"
                "1. Установите утилиту ImageMagick: brew install imagemagick\n"
                "2. Преобразуйте HEIC файлы в JPEG перед загрузкой в программу\n"
                "3. Проверьте наличие FFmpeg и убедитесь, что он работает корректно\n\n"
                f"Техническая информация об ошибке:\n{error_message}"
            )
            error_dialog.setDetailedText(detailed_text)

        elif "Неподдерживаемый тип файла" in error_message:
            # Ошибка неподдерживаемого формата
            error_dialog = QMessageBox(self)
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Неподдерживаемый формат файла")
            error_dialog.setText("Выбран файл неподдерживаемого формата.")

            detailed_text = (
                "Программа поддерживает следующие форматы:\n\n"
                "Изображения:\n"
                "- JPEG (.jpg, .jpeg)\n"
                "- PNG (.png)\n"
                "- GIF (.gif)\n"
                "- HEIC (.heic)\n\n"
                "Видео:\n"
                "- MP4 (.mp4)\n"
                "- MOV (.mov)\n"
                "- AVI (.avi)\n\n"
                f"Техническая информация об ошибке:\n{error_message}"
            )
            error_dialog.setDetailedText(detailed_text)

        elif "FFmpeg" in error_message:
            # Ошибка связана с FFmpeg
            error_dialog = QMessageBox(self)
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Ошибка при обработке видео")
            error_dialog.setText("Возникла проблема при обработке видео файла.")

            detailed_text = (
                "Проблемы с обработкой видео могут возникать из-за отсутствия или неправильной настройки FFmpeg.\n\n"
                "Возможные решения:\n"
                "1. Установите FFmpeg: brew install ffmpeg\n"
                "2. Убедитесь, что FFmpeg доступен в системном пути\n"
                "3. Проверьте, что видео файл не поврежден\n\n"
                f"Техническая информация об ошибке:\n{error_message}"
            )
            error_dialog.setDetailedText(detailed_text)

        elif "Следующие файлы не удалось обработать" in error_message:
            # Итоговое сообщение об ошибках
            error_dialog = QMessageBox(self)
            error_dialog.setIcon(QMessageBox.Icon.Warning)
            error_dialog.setWindowTitle("Не все файлы обработаны")
            error_dialog.setText("Некоторые файлы не удалось обработать.")
            error_dialog.setDetailedText(error_message)

        else:
            # Общая ошибка
            error_dialog = QMessageBox(self)
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Ошибка")
            error_dialog.setText("Произошла ошибка при обработке файла.")
            error_dialog.setDetailedText(
                f"Техническая информация об ошибке:\n{error_message}"
            )

        error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        error_dialog.exec()

        # Если это не итоговое сообщение об ошибках, продолжаем обработку
        if "Следующие файлы не удалось обработать" not in error_message:
            # Меняем цвет прогресс-бара на красный только для текущего файла
            self.set_progress_bar_color("error")
            # Не останавливаем процесс, просто показываем, что текущий файл не удалось обработать
            self.current_file_label.setText("❌ Ошибка при обработке текущего файла")
        else:
            # Для итогового сообщения об ошибках вызываем завершение
            self.on_compression_finished()

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        if self.compression_thread and self.compression_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                "Процесс сжатия не завершен. Вы уверены, что хотите выйти?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.compression_thread.stop()
                self.compression_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def _show_compression_summary(self):
        """Показывает подробную информацию о результатах сжатия"""
        if not hasattr(self, "summary_stats") or not self.compression_stats:
            return

        # Создаем диалог с подробной информацией о сжатии
        info_dialog = QMessageBox(self)
        info_dialog.setIcon(QMessageBox.Icon.Information)
        info_dialog.setWindowTitle("Результаты сжатия")

        # Основная информация
        ratio_percent = self.summary_stats["ratio"] * 100
        if ratio_percent > 0:
            main_text = (
                f"Сжатие завершено успешно.\n"
                f"Общий размер файлов уменьшен на {ratio_percent:.1f}%.\n"
                f"Было: {self.summary_stats['original_size_str']}, стало: {self.summary_stats['compressed_size_str']}"
            )
        else:
            main_text = (
                f"Сжатие завершено, но общий размер файлов увеличился на {abs(ratio_percent):.1f}%.\n"
                f"Было: {self.summary_stats['original_size_str']}, стало: {self.summary_stats['compressed_size_str']}\n"
                f"Возможно, стоит использовать более низкое качество сжатия."
            )

        info_dialog.setText(main_text)

        # Подробная информация по каждому файлу
        detailed_text = "Информация по отдельным файлам:\n\n"

        for stat in self.compression_stats:
            ratio = stat["change_percent"] * 100
            sign = "-" if ratio > 0 else "+"
            abs_ratio = abs(ratio)

            detailed_text += (
                f"Файл: {stat['file']}\n"
                f"Исходный размер: {stat['original_size_str']}\n"
                f"Размер после сжатия: {stat['compressed_size_str']}\n"
                f"Изменение: {sign}{abs_ratio:.1f}%\n\n"
            )

        info_dialog.setDetailedText(detailed_text)
        info_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        info_dialog.exec()

    def update_file_list(self):
        """Обновление списка файлов"""
        self.files_list.clear()
        for file_path, rel_path in self.files_to_compress:
            self.files_list.addItem(rel_path)

        # Активация/деактивация кнопок
        has_files = len(self.files_to_compress) > 0
        self.clear_selection_btn.setEnabled(has_files)
        self.start_btn.setEnabled(has_files)
        self.stop_btn.setEnabled(has_files)
        self.select_files_btn.setEnabled(has_files)
        self.select_output_btn.setEnabled(has_files)

    def remove_selected(self):
        """Удаление выбранных файлов из списка"""
        selected_items = self.files_list.selectedItems()
        if not selected_items:
            return

        # Получаем индексы выбранных элементов
        selected_indices = [self.files_list.row(item) for item in selected_items]

        # Удаляем файлы из списка в обратном порядке
        for index in sorted(selected_indices, reverse=True):
            del self.files_to_compress[index]

        # Обновляем список файлов
        self.update_file_list()

    def clear_files(self):
        """Очистка списка файлов"""
        self.files_to_compress = []
        self.update_ui()

    def test_compression(self):
        """Тестирование сжатия на одном файле"""
        if not self.files_to_compress:
            QMessageBox.warning(
                self,
                "Внимание",
                "Не выбраны файлы для тестирования",
                QMessageBox.StandardButton.Ok,
            )
            return

        # Получаем первый файл из списка
        file_info = self.files_to_compress[0]
        if isinstance(file_info, tuple):
            test_file, rel_path = file_info
        else:
            test_file = file_info
            rel_path = os.path.basename(test_file)

        output_dir = self.output_path_label.text()
        quality_level = self.quality_combo.currentText()

        # Создаем диалог прогресса
        progress_dialog = QProgressDialog("Тестирование сжатия...", None, 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoReset(False)
        progress_dialog.setAutoClose(False)
        progress_dialog.show()

        # Создаем и запускаем тестовый поток
        self.test_worker = TestCompressionWorker(test_file, output_dir, quality_level)
        self.test_worker.progress_updated.connect(progress_dialog.setValue)
        self.test_worker.finished.connect(
            lambda result: self.on_test_finished(result, progress_dialog)
        )
        self.test_worker.run()

    def on_test_finished(self, result, progress_dialog):
        """Обработка завершения тестового сжатия"""
        progress_dialog.close()

        if "error" in result:
            QMessageBox.critical(
                self,
                "Ошибка тестирования",
                f"Произошла ошибка при тестировании: {result['error']}",
                QMessageBox.StandardButton.Ok,
            )
            return

        # Формируем сообщение с результатами
        ratio_percent = result["ratio"] * 100
        if ratio_percent > 0:
            message = (
                f"Тестирование завершено успешно.\n\n"
                f"Исходный размер: {result['original_size_str']}\n"
                f"Размер после сжатия: {result['compressed_size_str']}\n"
                f"Уменьшение размера: {ratio_percent:.1f}%\n\n"
                f"Качество сжатия: {result['quality_level']}"
            )
        else:
            message = (
                f"Тестирование завершено.\n\n"
                f"Исходный размер: {result['original_size_str']}\n"
                f"Размер после сжатия: {result['compressed_size_str']}\n"
                f"Увеличение размера: {abs(ratio_percent):.1f}%\n\n"
                f"Качество сжатия: {result['quality_level']}\n"
                f"Рекомендуется использовать более низкое качество."
            )

        QMessageBox.information(
            self,
            "Результаты тестирования",
            message,
            QMessageBox.StandardButton.Ok,
        )

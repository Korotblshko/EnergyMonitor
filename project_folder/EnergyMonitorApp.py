import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox, QComboBox, QListWidget, QProgressBar, QTimeEdit, QHBoxLayout, QListWidgetItem, QCheckBox
from PyQt6.QtCore import QTimer, QTime
from PyQt6.QtGui import QColor
from database import init_db, get_latest_data, add_device, add_consumption, get_daily_data, get_weekly_data, get_monthly_data, get_achievements, update_achievement, add_scenario, get_scenarios, delete_scenario, get_device_name, update_device_name, get_level
import asyncio
from qasync import QEventLoop
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from datetime import datetime, timedelta
import sqlite3
import os
from tapo_api import get_device_data, turn_on_device, turn_off_device, rename_device

IP_ADDRESS = "192.168.1.4"
EMAIL = "stvbobah@gmail.com"
PASSWORD = "Pinokio555TAPO"

class EnergyMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EnergyMonitor")
        self.setGeometry(100, 100, 820, 600)
        self.is_dark_theme = False

        self.device_info = {"id": "test_id", "name": "Неизвестно"}
        self.is_on = False

        try:
            init_db()
            print("Инициализация базы данных выполнена")
        except Exception as e:
            print(f"Ошибка инициализации базы данных: {e}")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.devices_tab = QWidget()
        self.setup_devices_tab()
        self.tabs.addTab(self.devices_tab, "Устройства")

        self.graphs_tab = QWidget()
        self.setup_graphs_tab()
        self.tabs.addTab(self.graphs_tab, "Графики")

        self.current_tab = QWidget()
        self.setup_current_tab()
        self.tabs.addTab(self.current_tab, "Текущий расход")

        self.achievements_tab = QWidget()
        self.setup_achievements_tab()
        self.tabs.addTab(self.achievements_tab, "Достижения")

        self.settings_tab = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.settings_tab, "Настройки")

        self.scenarios_tab = QWidget()
        self.setup_scenarios_tab()
        self.tabs.addTab(self.scenarios_tab, "Сценарии")

        self.apply_light_theme()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000)

        self.graph_timer = QTimer()
        self.graph_timer.timeout.connect(self.update_graph)
        self.graph_timer.start(10000)

        self.achievement_timer = QTimer()
        self.achievement_timer.timeout.connect(self.check_achievements)
        self.achievement_timer.start(60000)

        self.start_data_collector()
        self.update_scenarios_list()

    def apply_light_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #E6F0FA; }
            QWidget { background-color: #E6F0FA; }
            QTabWidget::pane { background-color: #E6F0FA; }
            QTabBar::tab {
                background: #003087;
                color: white;
                font: bold 10pt Arial;
                padding: 5px;
                min-width: 120px;
            }
            QTabBar::tab:selected { background: #0057B8; }
            QTabBar::tab:hover { background: #0072CE; }
            QLabel { color: #003087; background-color: #E6F0FA; }
            QPushButton {
                background-color: #0057B8;
                color: white;
                font: 12pt Arial;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #0072CE; }
            QLineEdit {
                font: 12pt Arial;
                padding: 5px;
                background-color: white;
                border: 1px solid #003087;
                color: black;
            }
            QLineEdit:focus {
                border: 2px solid #0057B8;
                background-color: #F0F8FF;
                color: black;
            }
            QTimeEdit {
                font: 14pt Arial;
                padding: 5px;
                background-color: white;
                border: 1px solid #003087;
                color: black;
            }
            QTimeEdit:focus {
                border: 2px solid #0057B8;
                background-color: #F0F8FF;
            }
            QComboBox {
                font: 12pt Arial;
                padding: 5px;
                background-color: white;
                border: 1px solid #003087;
                color: black;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #0057B8;
                selection-color: white;
                font: 12pt Arial;
            }
            QProgressBar {
                border: 1px solid #003087;
                background-color: #E6F0FA;
                text-align: center;
                font: 12pt Arial;
                color: black;
            }
            QProgressBar::chunk { background-color: #0057B8; }
            QListWidget {
                color: black;
                background-color: #E6F0FA;
                font: 12pt Arial;
            }
            QListWidget::item { color: black; }
            QCheckBox {
                font: 12pt Arial;
                color: #003087;
            }
        """)
        self.is_dark_theme = False

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2E2E2E; }
            QWidget { background-color: #2E2E2E; }
            QTabWidget::pane { background-color: #2E2E2E; }
            QTabBar::tab {
                background: #1A4A7A;
                color: white;
                font: bold 10pt Arial;
                padding: 5px;
                min-width: 120px;
            }
            QTabBar::tab:selected { background: #2A6AB8; }
            QTabBar::tab:hover { background: #3A8ACE; }
            QLabel { color: #A0C0FF; background-color: #2E2E2E; }
            QPushButton {
                background-color: #2A6AB8;
                color: white;
                font: 12pt Arial;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #3A8ACE; }
            QLineEdit {
                font: 12pt Arial;
                padding: 5px;
                background-color: #3E3E3E;
                border: 1px solid #1A4A7A;
                color: white;
            }
            QLineEdit:focus {
                border: 2px solid #2A6AB8;
                background-color: #4E4E4E;
                color: white;
            }
            QTimeEdit {
                font: 14pt Arial;
                padding: 5px;
                background-color: #3E3E3E;
                border: 1px solid #1A4A7A;
                color: white;
            }
            QTimeEdit:focus {
                border: 2px solid #2A6AB8;
                background-color: #4E4E4E;
            }
            QComboBox {
                font: 12pt Arial;
                padding: 5px;
                background-color: #3E3E3E;
                border: 1px solid #1A4A7A;
                color: white;
            }
            QComboBox QAbstractItemView {
                background-color: #3E3E3E;
                color: white;
                selection-background-color: #2A6AB8;
                selection-color: white;
                font: 12pt Arial;
            }
            QProgressBar {
                border: 1px solid #1A4A7A;
                background-color: #2E2E2E;
                text-align: center;
                font: 12pt Arial;
                color: white;
            }
            QProgressBar::chunk { background-color: #2A6AB8; }
            QListWidget {
                color: white;
                background-color: #2E2E2E;
                font: 12pt Arial;
            }
            QListWidget::item { color: white; }
            QCheckBox {
                font: 12pt Arial;
                color: #A0C0FF;
            }
        """)
        self.is_dark_theme = True

    def toggle_theme(self):
        if self.is_dark_theme:
            self.apply_light_theme()
        else:
            self.apply_dark_theme()
        self.update_graph()  # Обновляем график при смене темы

    def setup_devices_tab(self):
        layout = QVBoxLayout(self.devices_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Управление устройством")
        title.setStyleSheet("font: bold 16pt Arial;")
        layout.addWidget(title)

        self.device_name_label = QLabel(f"Имя: {self.device_info['name']}")
        self.device_id_label = QLabel(f"ID: {self.device_info['id']}")
        self.device_status_label = QLabel(f"Статус: {'Включено' if self.is_on else 'Выключено'}")
        layout.addWidget(self.device_name_label)
        layout.addWidget(self.device_id_label)
        layout.addWidget(self.device_status_label)

        rename_layout = QVBoxLayout()
        self.rename_entry = QLineEdit()
        self.rename_entry.setText(self.device_info["name"])
        rename_button = QPushButton("Переименовать")
        rename_button.clicked.connect(self.rename_plug)
        rename_layout.addWidget(self.rename_entry)
        rename_layout.addWidget(rename_button)
        layout.addLayout(rename_layout)

        self.toggle_button = QPushButton("Включить" if not self.is_on else "Выключить")
        self.toggle_button.clicked.connect(self.toggle_plug)
        layout.addWidget(self.toggle_button)

        layout.addStretch()

    def setup_graphs_tab(self):
        layout = QVBoxLayout(self.graphs_tab)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        title = QLabel("Графики энергопотребления")
        title.setStyleSheet("font: bold 16pt Arial;")
        layout.addWidget(title)

        self.graph_selector = QComboBox()
        start_date = datetime.now() - timedelta(days=datetime.now().weekday())
        end_date = start_date + timedelta(days=6)
        week_label = f"Расход за неделю ({start_date.strftime('%d %b')} – {end_date.strftime('%d %b')})"
        month_label = f"Расход за месяц ({datetime.now().strftime('%B').lower()})"
        self.graph_selector.addItems(["Расход за сегодня", week_label, month_label])
        self.graph_selector.currentIndexChanged.connect(self.update_graph)
        layout.addWidget(self.graph_selector)

        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.ax.set_facecolor("#E6F0FA" if not self.is_dark_theme else "#2E2E2E")
        self.figure.patch.set_facecolor("#E6F0FA" if not self.is_dark_theme else "#2E2E2E")
        self.ax.grid(True)
        layout.addWidget(self.canvas)

        self.update_graph()

    def setup_current_tab(self):
        layout = QVBoxLayout(self.current_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Текущий расход энергии")
        title.setStyleSheet("font: bold 16pt Arial;")
        layout.addWidget(title)

        self.power_label = QLabel("0.00 Вт")
        self.power_label.setStyleSheet("font: bold 36pt Arial;")
        layout.addWidget(self.power_label)

        self.voltage_label = QLabel("Напряжение: 0.00 В")
        self.current_label = QLabel("Ток: 0.00 А")
        self.voltage_label.setStyleSheet("font: 16pt Arial;")
        self.current_label.setStyleSheet("font: 16pt Arial;")
        layout.addWidget(self.voltage_label)
        layout.addWidget(self.current_label)

        self.eco_meter = QProgressBar()
        self.eco_meter.setMaximum(1000)
        self.eco_meter.setValue(0)
        self.eco_meter.setFormat("Эко-метр: %v Вт")
        layout.addWidget(self.eco_meter)

        layout.addStretch()

    def setup_achievements_tab(self):
        layout = QVBoxLayout(self.achievements_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Достижения")
        title.setStyleSheet("font: bold 16pt Arial;")
        layout.addWidget(title)

        self.level_label = QLabel(f"Ваш текущий уровень - {get_level()}")
        self.level_label.setStyleSheet("font: 14pt Arial;")
        layout.addWidget(self.level_label)

        self.achievements_list = QListWidget()
        self.update_achievements_list()
        layout.addWidget(self.achievements_list)

        layout.addStretch()

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Настройки")
        title.setStyleSheet("font: bold 16pt Arial;")
        layout.addWidget(title)

        theme_button = QPushButton("Переключить тему")
        theme_button.clicked.connect(self.toggle_theme)
        layout.addWidget(theme_button)

        autostart_checkbox = QCheckBox("Автозапуск при старте системы")
        autostart_checkbox.setChecked(False)
        layout.addWidget(autostart_checkbox)

        layout.addStretch()

    def setup_scenarios_tab(self):
        layout = QVBoxLayout(self.scenarios_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Сценарии")
        title.setStyleSheet("font: bold 16pt Arial;")
        layout.addWidget(title)

        create_button = QPushButton("Создать сценарий")
        create_button.setStyleSheet("font: 14pt Arial;")
        create_button.clicked.connect(self.show_create_scenario_form)
        layout.addWidget(create_button)

        self.scenario_form = QWidget()
        form_layout = QVBoxLayout(self.scenario_form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        time_layout = QHBoxLayout()
        on_time_label = QLabel("Время включения:")
        on_time_label.setStyleSheet("font: 14pt Arial;")
        self.on_time_edit = QTimeEdit()
        self.on_time_edit.setDisplayFormat("HH:mm")
        self.on_time_edit.setTime(QTime(8, 0))
        self.on_time_edit.setEnabled(True)
        off_time_label = QLabel("Время выключения:")
        off_time_label.setStyleSheet("font: 14pt Arial;")
        self.off_time_edit = QTimeEdit()
        self.off_time_edit.setDisplayFormat("HH:mm")
        self.off_time_edit.setTime(QTime(20, 0))
        self.off_time_edit.setEnabled(True)
        time_layout.addWidget(on_time_label)
        time_layout.addWidget(self.on_time_edit)
        time_layout.addWidget(off_time_label)
        time_layout.addWidget(self.off_time_edit)
        form_layout.addLayout(time_layout)

        save_button = QPushButton("Сохранить сценарий")
        save_button.setStyleSheet("font: 14pt Arial;")
        save_button.clicked.connect(self.save_scenario)
        form_layout.addWidget(save_button)

        self.scenario_form.hide()
        layout.addWidget(self.scenario_form)

        self.scenarios_list = QListWidget()
        self.scenarios_list.setStyleSheet("font: 14pt Arial;")
        self.scenarios_list.itemClicked.connect(self.show_delete_button)
        layout.addWidget(self.scenarios_list)

        self.delete_button = QPushButton("Удалить сценарий")
        self.delete_button.setStyleSheet("font: 14pt Arial;")
        self.delete_button.clicked.connect(self.delete_scenario)
        self.delete_button.hide()
        layout.addWidget(self.delete_button)

        layout.addStretch()

    def show_create_scenario_form(self):
        self.scenario_form.show()
        self.delete_button.hide()

    def show_delete_button(self, item):
        self.delete_button.show()
        self.selected_scenario_index = self.scenarios_list.row(item)

    def delete_scenario(self):
        if not hasattr(self, 'selected_scenario_index'):
            return

        scenarios = get_scenarios()
        if 0 <= self.selected_scenario_index < len(scenarios):
            scenario_id = scenarios[self.selected_scenario_index]["id"]
            delete_scenario(scenario_id)
            self.update_scenarios_list()
            self.delete_button.hide()

    def save_scenario(self):
        on_time = self.on_time_edit.time().toString("HH:mm")
        off_time = self.off_time_edit.time().toString("HH:mm")
        device_id = self.device_info["id"]

        if device_id == "Неизвестно":
            QMessageBox.critical(self, "Ошибка", "Устройство не определено")
            return

        add_scenario(device_id, on_time, off_time)
        self.update_scenarios_list()
        self.scenario_form.hide()

        scenarios = get_scenarios()
        if len(scenarios) == 1:
            db_path = "C:/Users/Vladimir/PycharmProjects/api+app/plugs.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT unlocked FROM achievements WHERE name = 'Режиссер'")
            result = cursor.fetchone()
            if not result or not result[0]:
                update_achievement("Режиссер")
                QMessageBox.information(self, "Достижение!", "Режиссер разблокирован!")
                self.update_achievements_list()
            conn.close()

    def update_scenarios_list(self):
        self.scenarios_list.clear()
        scenarios = get_scenarios()
        device_name = self.device_info["name"] if self.device_info["id"] != "Неизвестно" else "Неизвестно"
        for scenario in scenarios:
            if scenario["device_id"] == self.device_info["id"]:
                item = f"{device_name}: Вкл: {scenario['on_time']}, Выкл: {scenario['off_time']}"
                self.scenarios_list.addItem(item)

    def update_data(self):
        try:
            data = get_latest_data()
            self.power_label.setText(f"{data['power_w']:.2f} Вт")
            self.voltage_label.setText(f"Напряжение: {data['voltage_v']:.2f} В")
            self.current_label.setText(f"Ток: {data['current_a']:.2f} А")

            power = data["power_w"]
            self.eco_meter.setValue(int(power))
            if power < 100:
                self.eco_meter.setStyleSheet("QProgressBar::chunk { background-color: green; }")
            elif power < 500:
                self.eco_meter.setStyleSheet("QProgressBar::chunk { background-color: yellow; }")
            else:
                self.eco_meter.setStyleSheet("QProgressBar::chunk { background-color: red; }")

            print(f"Обновлены данные: {data}")
        except Exception as e:
            print(f"Ошибка при обновлении данных: {e}")
            self.power_label.setText("0.00 Вт")
            self.voltage_label.setText("Напряжение: 0.00 В")
            self.current_label.setText("Ток: 0.00 А")
            self.eco_meter.setValue(0)

    def update_graph(self):
        try:
            self.ax.clear()
            current_date = datetime.now().strftime("%Y-%m-%d")
            graph_type = self.graph_selector.currentText()

            if graph_type.startswith("Расход за сегодня"):
                data = get_daily_data(current_date)
                print(f"Данные за сегодня: {data}")
                hours, avg_watts = zip(*data)
                avg_kw = [w / 1000 for w in avg_watts]  # Переводим в кВт
                self.ax.plot(range(24), avg_kw, "o-", color="#003087" if not self.is_dark_theme else "#A0C0FF", linewidth=2, markersize=6)
                self.ax.set_title(f"Расход за сегодня ({current_date})")
                self.ax.set_ylabel("Мощность (кВт)")
                self.ax.set_xlabel("Часы")
                self.ax.set_xticks(range(24))
                self.ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45)
                self.ax.set_ylim(0.0, 1.0)  # Диапазон от 0.0 до 1.0 кВт
                self.ax.set_xlim(0, 23)
                self.ax.grid(True, color="white" if not self.is_dark_theme else "#4E4E4E")
                for i, value in enumerate(avg_kw):
                    if value >= 0.00001:  # Уменьшаем порог для отображения
                        self.ax.text(i, value + 0.05, f"{value*1000:.1f} Вт", ha="center", va="bottom", fontsize=8, rotation=45,
                                    color="#003087" if not self.is_dark_theme else "#A0C0FF")

            elif graph_type.startswith("Расход за неделю"):
                start_date = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
                end_date = (datetime.now() + timedelta(days=6 - datetime.now().weekday())).strftime("%Y-%m-%d")
                data = get_weekly_data(start_date, end_date)
                print(f"Данные за неделю: {data}")
                days, kw = zip(*data)
                weekdays = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
                bars = self.ax.bar(range(7), kw, color="#003087" if not self.is_dark_theme else "#A0C0FF", align="center")
                self.ax.set_title("Расход за неделю")
                self.ax.set_ylabel("Мощность (кВт)")
                self.ax.set_xlabel("Дни недели")
                self.ax.set_xticks(range(7))
                self.ax.set_xticklabels(weekdays, rotation=0)
                self.ax.set_ylim(0.0, 5.0)  # Диапазон от 0.0 до 5.0 кВт
                self.ax.grid(True, axis="y", color="white" if not self.is_dark_theme else "#4E4E4E")
                for i, bar in enumerate(bars):
                    height = bar.get_height()
                    if height >= 0.00001:
                        self.ax.text(bar.get_x() + bar.get_width()/2, height + 0.25, f"{height*1000:.1f} Вт",
                                     ha="center", va="bottom", fontsize=8,
                                     color="#003087" if not self.is_dark_theme else "#A0C0FF")

            elif graph_type.startswith("Расход за месяц"):
                month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
                data = get_monthly_data(month_start)
                print(f"Данные за месяц: {data}")
                days, kw = zip(*data)
                days_short = [str(int(d[-2:])) for d in days]
                bars = self.ax.bar(range(len(days)), kw, color="#003087" if not self.is_dark_theme else "#A0C0FF")
                self.ax.set_title(f"Расход за месяц ({datetime.now().strftime('%B %Y')})")
                self.ax.set_xlabel("День")
                self.ax.set_ylabel("Мощность (кВт)")
                self.ax.set_xticks(range(len(days)))
                self.ax.set_xticklabels(days_short, rotation=0)
                self.ax.set_ylim(0.0, 10.0)  # Диапазон от 0.0 до 10.0 кВт
                self.ax.grid(True, axis="y", color="white" if not self.is_dark_theme else "#4E4E4E")
                for i, bar in enumerate(bars):
                    height = bar.get_height()
                    if height >= 0.00001:
                        self.ax.text(bar.get_x() + bar.get_width()/2, height + 0.5, f"{height*1000:.1f} Вт",
                                     ha="center", va="bottom", fontsize=8,
                                     color="#003087" if not self.is_dark_theme else "#A0C0FF")
                self.figure.subplots_adjust(left=0.15, bottom=0.2, right=0.95, top=0.9)

            self.ax.set_facecolor("#E6F0FA" if not self.is_dark_theme else "#2E2E2E")
            self.figure.patch.set_facecolor("#E6F0FA" if not self.is_dark_theme else "#2E2E2E")
            self.ax.tick_params(axis='both', colors="#003087" if not self.is_dark_theme else "#A0C0FF")
            self.ax.set_title(self.ax.get_title(), color="#003087" if not self.is_dark_theme else "#A0C0FF")
            self.ax.set_xlabel(self.ax.get_xlabel(), color="#003087" if not self.is_dark_theme else "#A0C0FF")
            self.ax.set_ylabel(self.ax.get_ylabel(), color="#003087" if not self.is_dark_theme else "#A0C0FF")
            self.canvas.draw()
            print(f"График обновлён: {graph_type}")
        except Exception as e:
            print(f"Ошибка при обновлении графика: {e}")
            self.ax.clear()
            self.ax.set_facecolor("#E6F0FA" if not self.is_dark_theme else "#2E2E2E")
            self.ax.grid(True)
            self.canvas.draw()

    def update_achievements_list(self):
        self.achievements_list.clear()
        achievements = get_achievements()
        print(f"Полученные достижения: {achievements}")
        self.level_label.setText(f"Ваш текущий уровень - {get_level()}")
        for achievement in achievements:
            if achievement["name"] == "Initial":
                continue
            status = "✅" if achievement["unlocked"] else "🔒"
            date = f" ({achievement['date_unlocked'][:10]})" if achievement["unlocked"] and achievement["date_unlocked"] else ""
            item_text = f"{achievement['name']}: {achievement['description']} {status}{date}"
            item = QListWidgetItem(item_text)
            if achievement["unlocked"]:
                item.setForeground(QColor("#0057B8" if not self.is_dark_theme else "#A0C0FF"))
            self.achievements_list.addItem(item)

    def check_achievements(self):
        try:
            db_path = "C:/Users/Vladimir/PycharmProjects/api+app/plugs.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("SELECT SUM(power) FROM consumption WHERE date(timestamp) = ?", (today,))
            daily_watts = cursor.fetchone()[0] or 0
            print(f"Проверка достижений: SUM(power) за сегодня ({today}) = {daily_watts} Вт")
            if daily_watts > 0 and daily_watts < 1000:  # Условие для "Эко-новичок"
                cursor.execute("SELECT unlocked FROM achievements WHERE name = 'Эко-новичок'")
                result = cursor.fetchone()
                if not result or not result[0]:
                    update_achievement("Эко-новичок")
                    QMessageBox.information(self, "Достижение!", "Эко-новичок разблокирован!")
                    self.update_achievements_list()

            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            cursor.execute("SELECT SUM(power) FROM consumption WHERE date(timestamp) = ?", (yesterday,))
            yesterday_watts = cursor.fetchone()[0] or 0
            print(f"Проверка достижений: SUM(power) за вчера ({yesterday}) = {yesterday_watts} Вт")
            if yesterday_watts > 0 and daily_watts < yesterday_watts:
                pass  # Здесь можно добавить новое достижение, если нужно

            conn.close()
        except Exception as e:
            print(f"Ошибка проверки достижений: {e}")

    def rename_plug(self):
        new_name = self.rename_entry.text().strip()
        if not new_name:
            QMessageBox.critical(self, "Ошибка", "Введите новое имя")
            return

        def run_rename():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(rename_device(IP_ADDRESS, EMAIL, PASSWORD, new_name))
            if success:
                self.device_info["name"] = new_name
                update_device_name(self.device_info["id"], new_name)
                self.device_name_label.setText(f"Имя: {new_name}")
                self.update_scenarios_list()
                QMessageBox.information(self, "Успех", "Розетка переименована")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось переименовать розетку")
            QApplication.processEvents()
            loop.close()

        threading.Thread(target=run_rename, daemon=True).start()

    def toggle_plug(self):
        def run_toggle():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            if self.is_on:
                success = loop.run_until_complete(turn_off_device(IP_ADDRESS, EMAIL, PASSWORD))
                if success:
                    self.is_on = False
                    self.device_status_label.setText("Статус: Выключено")
                    self.toggle_button.setText("Включить")
            else:
                success = loop.run_until_complete(turn_on_device(IP_ADDRESS, EMAIL, PASSWORD))
                if success:
                    self.is_on = True
                    self.device_status_label.setText("Статус: Включено")
                    self.toggle_button.setText("Выключить")
            QApplication.processEvents()
            loop.close()

        threading.Thread(target=run_toggle, daemon=True).start()

    async def async_data_collector(self):
        while True:
            try:
                device_info, energy_data = await get_device_data(IP_ADDRESS, EMAIL, PASSWORD)
                if device_info and energy_data:
                    add_device(device_info)
                    add_consumption(device_info["id"], energy_data)
                    print(f"Данные сохранены: {energy_data}")
                    self.device_info["id"] = device_info["id"]
                    self.device_info["name"] = get_device_name(device_info["id"])
                    self.is_on = device_info.get("status", "off") == "on"
                    self.device_name_label.setText(f"Имя: {self.device_info['name']}")
                    self.device_id_label.setText(f"ID: {device_info['id']}")
                    self.device_status_label.setText(f"Статус: {'Включено' if self.is_on else 'Выключено'}")
                    self.toggle_button.setText("Выключить" if self.is_on else "Включить")
                    QApplication.processEvents()
                else:
                    print("Не удалось получить данные с устройства")
            except Exception as e:
                print(f"Ошибка в data_collector: {e}")
            await asyncio.sleep(0.2)

    def start_data_collector(self):
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.async_data_collector())

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    try:
        init_db()
        print("База данных инициализирована")
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")

    window = EnergyMonitorApp()
    window.show()

    with loop:
        loop.run_forever()
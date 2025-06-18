import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "C:/Users/Vladimir/PycharmProjects/api+app/plugs.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            timestamp DATETIME,
            power REAL,
            voltage_v REAL,
            current_a REAL,
            today_energy_kwh REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            unlocked INTEGER DEFAULT 0,
            date_unlocked DATETIME,
            level INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            on_time TEXT,
            off_time TEXT
        )
    ''')
    conn.commit()

    # Добавляем все достижения сразу
    achievements = [
        ("Initial", "Начальный уровень", 0, 0),
        ("Эко-новичок", "Потребление за день менее 1000 Вт", 0, 0),
        ("Режиссер", "Создайте свой первый сценарий", 0, 0)
    ]
    for name, description, unlocked, level in achievements:
        cursor.execute("INSERT OR IGNORE INTO achievements (name, description, unlocked, level) VALUES (?, ?, ?, ?)",
                       (name, description, unlocked, level))
    conn.commit()

    cursor.execute("SELECT * FROM achievements")
    achievements = cursor.fetchall()
    print(f"После инициализации базы данных, содержимое таблицы achievements: {achievements}")

    conn.close()

def get_device_name(device_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM devices WHERE id = ?", (device_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "Неизвестно"

def add_device(device_info):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO devices (id, name) VALUES (?, ?)",
                   (device_info["id"], device_info["name"]))
    conn.commit()
    conn.close()

def update_device_name(device_id, new_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE devices SET name = ? WHERE id = ?", (new_name, device_id))
    conn.commit()
    conn.close()

def get_latest_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT power, voltage_v, current_a, today_energy_kwh FROM consumption ORDER BY timestamp DESC LIMIT 1")
    data = cursor.fetchone()
    conn.close()
    if data:
        return {"power_w": data[0], "voltage_v": data[1], "current_a": data[2], "today_energy_kwh": data[3]}
    return {"power_w": 0.0, "voltage_v": 0.0, "current_a": 0.0, "today_energy_kwh": 0.0}

def add_consumption(device_id, energy_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO consumption (device_id, timestamp, power, voltage_v, current_a, today_energy_kwh)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (device_id, energy_data["timestamp"], energy_data["power_w"], energy_data["voltage_v"],
          energy_data["current_a"], energy_data["today_energy_kwh"]))
    conn.commit()
    conn.close()

def get_daily_data(date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT strftime('%H', timestamp) as hour, AVG(power) as avg_power_w 
        FROM consumption 
        WHERE date(timestamp) = ? 
        GROUP BY hour
    ''', (date,))
    data = cursor.fetchall()
    conn.close()
    result = [0.0] * 24
    for hour, avg_power_w in data:
        hour = int(hour)
        if 0 <= hour < 24:
            result[hour] = avg_power_w if avg_power_w else 0.0
    return list(enumerate(result))

def get_weekly_data(start_date, end_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT strftime('%w', timestamp) as day, SUM(power) / 1000 as kw 
        FROM consumption 
        WHERE date(timestamp) BETWEEN ? AND ? 
        GROUP BY day
    ''', (start_date, end_date))
    data = cursor.fetchall()
    conn.close()
    result = [0.0] * 7
    for day, kw in data:
        if day.isdigit():
            day_idx = (int(day) + 6) % 7
            result[day_idx] = kw if kw else 0.0
    return list(enumerate(result))

def get_monthly_data(month_start):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT strftime('%Y-%m-%d', timestamp) as day, SUM(power) / 1000 as kw 
        FROM consumption 
        WHERE date(timestamp) >= ? 
        GROUP BY day
    ''', (month_start,))
    data = cursor.fetchall()
    conn.close()
    month_end = datetime.strptime(month_start, "%Y-%m-%d").replace(day=28) + timedelta(days=4)
    last_day = (month_end - timedelta(days=month_end.day)).day
    result = [0.0] * last_day
    for day, kw in data:
        day_num = int(day[-2:]) - 1
        if 0 <= day_num < last_day:
            result[day_num] = kw if kw else 0.0
    return [(f"2025-05-{i+1:02d}", result[i]) for i in range(last_day)]

def get_achievements():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, unlocked, date_unlocked, level FROM achievements")
    achievements = [{"name": row[0], "description": row[1], "unlocked": bool(row[2]), "date_unlocked": row[3], "level": row[4]} for row in cursor.fetchall()]
    conn.close()
    return achievements

def update_achievement(achievement_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT level FROM achievements WHERE name = 'Initial'")
    current_level = cursor.fetchone()[0] or 0
    new_level = current_level + 1
    cursor.execute("UPDATE achievements SET level = ? WHERE name = 'Initial'", (new_level,))
    cursor.execute("UPDATE achievements SET unlocked = 1, date_unlocked = ?, level = ? WHERE name = ?",
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), new_level, achievement_name))
    conn.commit()
    conn.close()

def get_level():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT level FROM achievements WHERE name = 'Initial'")
    level = cursor.fetchone()
    conn.close()
    return level[0] if level else 0

def add_scenario(device_id, on_time, off_time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scenarios (device_id, on_time, off_time) VALUES (?, ?, ?)",
                   (device_id, on_time, off_time))
    conn.commit()
    conn.close()

def get_scenarios():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, device_id, on_time, off_time FROM scenarios")
    scenarios = [{"id": row[0], "device_id": row[1], "on_time": row[2], "off_time": row[3]} for row in cursor.fetchall()]
    conn.close()
    return scenarios

def delete_scenario(scenario_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
    conn.commit()
    conn.close()
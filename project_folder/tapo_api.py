import asyncio
from kasa import Discover, Credentials
import aiohttp
from datetime import datetime


async def get_device_data(ip_address, email, password):
    session = aiohttp.ClientSession()
    try:
        credentials = Credentials(username=email, password=password)
        device = await Discover.discover_single(ip_address, credentials=credentials)

        for _ in range(2):
            await device.update()
            await asyncio.sleep(1)

        device_info = {
            "id": device.device_id,
            "name": device.alias,
            "status": "on" if device.is_on else "off",
            "model": device.model
        }

        energy_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "power_w": 0.0,
            "voltage_v": 0.0,
            "current_a": 0.0,
            "today_energy_kwh": 0.0
        }

        print(f"Доступные модули: {list(device.modules.keys())}")  # Отладка
        if "Module.Energy" in device.modules:
            energy = device.modules["Module.Energy"]
            energy_data.update({
                "power_w": energy.power / 1000,
                "voltage_v": energy.voltage / 1000,
                "current_a": energy.current,
                "today_energy_kwh": energy.today_energy / 1000
            })
            print(
                f"Сырые данные: power={energy.power}, voltage={energy.voltage}, current={energy.current}, today_energy={energy.today_energy}")  # Отладка
        elif hasattr(device, "emeter_realtime"):
            energy = device.emeter_realtime
            energy_data.update({
                "power_w": energy['power_mw'] / 1000,
                "voltage_v": energy['voltage_mv'] / 1000,
                "current_a": energy['current_ma'] / 1000,
                "today_energy_kwh": energy.get('energy_wh', 0) / 1000
            })
            print(f"Сырые данные (emeter): {energy}")  # Отладка
        else:
            print("Энергопотребление не поддерживается")

        return device_info, energy_data

    except Exception as e:
        print(f"Ошибка при получении данных: {str(e)}")
        return None, None
    finally:
        await session.close()
        if session.connector:
            await session.connector.close()
            await asyncio.sleep(0.1)


async def turn_on_device(ip_address, email, password):
    session = aiohttp.ClientSession()
    try:
        credentials = Credentials(username=email, password=password)
        device = await Discover.discover_single(ip_address, credentials=credentials)
        await device.turn_on()
        await device.update()
        print("Розетка включена")
        return True
    except Exception as e:
        print(f"Ошибка при включении розетки: {str(e)}")
        return False
    finally:
        await session.close()
        if session.connector:
            await session.connector.close()
            await asyncio.sleep(0.1)


async def turn_off_device(ip_address, email, password):
    session = aiohttp.ClientSession()
    try:
        credentials = Credentials(username=email, password=password)
        device = await Discover.discover_single(ip_address, credentials=credentials)
        await device.turn_off()
        await device.update()
        print("Розетка выключена")
        return True
    except Exception as e:
        print(f"Ошибка при выключении розетки: {str(e)}")
        return False
    finally:
        await session.close()
        if session.connector:
            await session.connector.close()
            await asyncio.sleep(0.1)


async def rename_device(ip_address, email, password, new_name):
    session = aiohttp.ClientSession()
    try:
        credentials = Credentials(username=email, password=password)
        device = await Discover.discover_single(ip_address, credentials=credentials)
        await device.set_alias(new_name)
        await device.update()
        print(f"Розетка переименована в {new_name}")
        return True
    except Exception as e:
        print(f"Ошибка при переименовании розетки: {str(e)}")
        return False
    finally:
        await session.close()
        if session.connector:
            await session.connector.close()
            await asyncio.sleep(0.1)
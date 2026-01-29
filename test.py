import requests
import time
import json
import socket
from datetime import datetime

class LicenseClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.installation_id = None
        self.product_id = 1  # ID продукта в системе
        self.license_key = None
    
    def get_hostname(self):
        """Получение имени хоста"""
        return socket.gethostname()
    
    def register_device(self, license_key):
        """
        Регистрация устройства в системе
        """
        self.license_key = license_key
        
        url = f"{self.base_url}/api/v1/device/{self.product_id}/{license_key}/register"
        
        data = {
            "hostname": self.get_hostname()
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            
            # Проверяем статус код
            if response.status_code == 200:
                result = response.json()
                self.installation_id = result["installation_id"]
                print(f"✅ Устройство успешно зарегистрировано")
                print(f"   Installation ID: {self.installation_id}")
                print(f"   Device ID: {result.get('device_id')}")
                print(f"   Сообщение: {result.get('message')}")
                return True
            else:
                try:
                    result = response.json()
                    print(f"❌ Ошибка регистрации: {result.get('error')}")
                except:
                    print(f"❌ Ошибка регистрации (код {response.status_code}): {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка соединения: {e}")
            return False
    
    def check_license(self):
        """
        Проверка лицензии
        """
        if not self.installation_id:
            print("❌ Сначала зарегистрируйте устройство")
            return False
        
        url = f"{self.base_url}/api/v1/license/{self.product_id}/{self.license_key}"
        
        data = {
            "installation_id": self.installation_id
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Лицензия действительна")
                print(f"   Продукт: {result['license']['name']}")
                
                if result['license']['valid_until']:
                    valid_until = datetime.fromisoformat(result['license']['valid_until'].replace('Z', '+00:00'))
                    now = datetime.utcnow()
                    days_left = (valid_until - now).days
                    print(f"   Действует до: {valid_until.strftime('%Y-%m-%d %H:%M')} (осталось {days_left} дней)")
                else:
                    print(f"   Действует до: Бессрочно")
                    
                print(f"   Устройств: {result['license']['current_devices']}/{result['license']['max_devices']}")
                return True
            else:
                try:
                    result = response.json()
                    print(f"❌ Ошибка проверки: {result.get('error')}")
                except:
                    print(f"❌ Ошибка проверки (код {response.status_code}): {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка соединения: {e}")
            return False
    
    def get_license_status(self):
        """
        Получение статуса лицензии
        """
        if not self.license_key:
            print("❌ Укажите ключ лицензии")
            return
        
        url = f"{self.base_url}/api/v1/license/{self.product_id}/{self.license_key}/status"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print("\n📋 Информация о лицензии:")
                print(f"   Ключ: {result['license']['key']}")
                print(f"   Название: {result['license']['name']}")
                print(f"   Статус: {'Активна' if result['license']['is_active'] else 'Неактивна'}")
                
                if result['license']['valid_until']:
                    valid_until = datetime.fromisoformat(result['license']['valid_until'].replace('Z', '+00:00'))
                    now = datetime.utcnow()
                    days_left = (valid_until - now).days
                    status = "🟢" if days_left > 0 else "🔴"
                    print(f"   Действует до: {valid_until.strftime('%Y-%m-%d')} {status} ({days_left} дней)")
                else:
                    print(f"   Действует до: Бессрочно 🟢")
                    
                print(f"   Продукт: {result['license']['product']}")
                print(f"   Тариф: {result['tariff']['name']}")
                print(f"   Макс. устройств: {result['tariff']['max_devices']}")
                print(f"   Текущее кол-во: {result['device_count']}")
                
                if result['devices']:
                    print("\n📱 Зарегистрированные устройства:")
                    for device in result['devices']:
                        if device['last_seen']:
                            last_seen = datetime.fromisoformat(device['last_seen'].replace('Z', '+00:00'))
                            now = datetime.utcnow()
                            hours_ago = (now - last_seen).total_seconds() / 3600
                            status = "🟢" if hours_ago < 24 else "🟡" if hours_ago < 168 else "🔴"
                            last_seen_str = f"{int(hours_ago)} ч. назад"
                        else:
                            status = "🔴"
                            last_seen_str = "никогда"
                            
                        print(f"   {status} {device['name']} ({device['ip_address'] or 'Нет IP'})")
                        print(f"     ID: {device['installation_id'][:16]}...")
                        print(f"     Последняя активность: {last_seen_str}")
                
                return True
            else:
                try:
                    result = response.json()
                    print(f"❌ Ошибка: {result.get('error')}")
                except:
                    print(f"❌ Ошибка (код {response.status_code}): {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка соединения: {e}")
            return False
    
    def continuous_validation(self, interval=60):
        """
        Непрерывная проверка лицензии
        """
        if not self.installation_id:
            print("❌ Сначала зарегистрируйте устройство")
            return
        
        print(f"\n🔍 Начинаем непрерывную проверку лицензии (интервал: {interval} сек)")
        print("Нажмите Ctrl+C для остановки\n")
        
        check_count = 0
        success_count = 0
        
        try:
            while True:
                check_count += 1
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Проверка #{check_count}...")
                
                if self.check_license():
                    success_count += 1
                    print(f"   Успешных проверок: {success_count}/{check_count}")
                else:
                    print(f"❌ Лицензия недействительна. Выход...")
                    break
                
                if check_count % 10 == 0:
                    print(f"\n📊 Статистика: {success_count}/{check_count} успешных проверок ({success_count/check_count*100:.1f}%)")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Проверка остановлена пользователем")
            print(f"📊 Итоговая статистика: {success_count}/{check_count} успешных проверок ({success_count/check_count*100:.1f}%)")

def test_api_endpoints(base_url="http://localhost:5000"):
    """Тестирование всех API эндпоинтов"""
    print("=== Тестирование API эндпоинтов ===\n")
    
    # Тест 1: Получение статуса лицензии
    print("1. Тестирование /api/v1/license/{product_id}/{key}/status")
    test_key = input("Введите тестовый ключ лицензии: ").strip()
    
    if test_key:
        url = f"{base_url}/api/v1/license/1/{test_key}/status"
        try:
            response = requests.get(url, timeout=10)
            print(f"   Статус код: {response.status_code}")
            print(f"   Ответ: {response.text[:200]}...")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Лицензия найдена: {data['license']['name']}")
            elif response.status_code == 404:
                print("   Лицензия не найдена")
            else:
                print("   Неизвестная ошибка")
        except Exception as e:
            print(f"   Ошибка: {e}")
    
    # Тест 2: Регистрация устройства
    print("\n2. Тестирование /api/v1/device/{product_id}/{key}/register")
    if test_key:
        url = f"{base_url}/api/v1/device/1/{test_key}/register"
        data = {"hostname": "test-device"}
        try:
            response = requests.post(url, json=data, timeout=10)
            print(f"   Статус код: {response.status_code}")
            print(f"   Ответ: {response.text}")
        except Exception as e:
            print(f"   Ошибка: {e}")

def main():
    # Сначала проверим доступность сервера
    try:
        test_response = requests.get("http://localhost:5000", timeout=5)
        print(f"✅ Сервер доступен (статус: {test_response.status_code})")
    except:
        print("⚠️  Сервер недоступен. Запустите сервер командой: python run.py")
        print("   Проверить API вручную? (y/n): ", end="")
        if input().lower() == 'y':
            test_api_endpoints()
        return
    
    client = LicenseClient()
    
    print("\n=== Клиент проверки лицензий ===\n")
    
    while True:
        print("\nВыберите действие:")
        print("1. Регистрация устройства")
        print("2. Проверка лицензии")
        print("3. Получить статус лицензии")
        print("4. Непрерывная проверка")
        print("5. Тестирование API")
        print("6. Выход")
        
        choice = input("\nВаш выбор: ").strip()
        
        if choice == "1":
            license_key = input("Введите ключ лицензии: ").strip()
            product_id = input("Введите ID продукта (по умолчанию 1): ").strip()
            if product_id:
                client.product_id = int(product_id)
            client.register_device(license_key)
            
        elif choice == "2":
            if client.installation_id:
                client.check_license()
            else:
                print("❌ Сначала зарегистрируйте устройство")
                
        elif choice == "3":
            if not client.license_key:
                license_key = input("Введите ключ лицензии: ").strip()
                client.license_key = license_key
            product_id = input("Введите ID продукта (по умолчанию 1): ").strip()
            if product_id:
                client.product_id = int(product_id)
            client.get_license_status()
            
        elif choice == "4":
            if client.license_key:
                try:
                    interval = int(input("Интервал проверки (сек, по умолчанию 60): ").strip() or "60")
                    client.continuous_validation(interval)
                except ValueError:
                    print("❌ Неверный интервал")
            else:
                print("❌ Сначала зарегистрируйте устройство")
                
        elif choice == "5":
            test_api_endpoints()
            
        elif choice == "6":
            print("👋 До свидания!")
            break
            
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    main()
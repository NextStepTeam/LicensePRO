import secrets
import string
from datetime import datetime, timedelta

def generate_license_key(prefix, length=20):
    """Генерация ключа лицензии"""
    alphabet = string.ascii_uppercase + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}-{random_part}"

def generate_installation_id():
    """Генерация ID установки"""
    return secrets.token_hex(16)

def validate_license_key_format(key):
    """Проверка формата ключа лицензии"""
    if not key or '-' not in key:
        return False
    prefix, rest = key.split('-', 1)
    return len(prefix) > 0 and len(rest) >= 10

def format_datetime(dt):
    """Форматирование даты"""
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M')
    return "Бессрочно"

def calculate_expiry_date(start_date=None, days=0):
    """Расчет даты окончания"""
    if days <= 0:
        return None
    if not start_date:
        start_date = datetime.utcnow()
    return start_date + timedelta(days=days)
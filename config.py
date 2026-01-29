# config.py
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Безопасность
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # База данных
    if SECRET_KEY.startswith("dev"):
        DATABASE_URL = 'sqlite:///' + os.path.join(basedir, 'license_system.db')
    else:
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or \
                              'sqlite:///' + os.path.join(basedir, 'license_system.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }

    # Настройки безопасности
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Настройки лицензий
    LICENSE_KEY_LENGTH = int(os.environ.get('LICENSE_KEY_LENGTH', 25))
    INSTALLATION_ID_LENGTH = int(os.environ.get('INSTALLATION_ID_LENGTH', 32))
    MAX_DEVICES_DEFAULT = int(os.environ.get('MAX_DEVICES_DEFAULT', 5))
from flask import jsonify, request
from datetime import datetime
from app import db
from app.models import Product, License, Device, Notification, User
from flask import Blueprint
bp = Blueprint('api', __name__)

@bp.route('/device/<int:product_id>/<key>/register', methods=['POST'])
def device_register(product_id, key):
    """
    Регистрация устройства
    Возвращает: {"installation_id": "xxx"} или {"error": "message"}
    """
    data = request.get_json(silent=True) or {}
    hostname = data.get('hostname', 'Unknown Device')
    ip_address = request.remote_addr
    
    # Поиск лицензии
    license = License.query.filter_by(
        product_id=product_id,
        key=key
    ).first()
    
    if not license:
        return jsonify({"error": "Лицензия не найдена"}), 404
    
    # Проверка активности лицензии
    if not license.is_valid():
        return jsonify({"error": "Лицензия не активна"}), 403
    
    # Проверка IP в черном списке
    if ip_address in license.get_blacklisted_ips():
        return jsonify({"error": "IP адрес заблокирован"}), 403
    
    # Проверка срока действия
    if license.valid_until and license.valid_until < datetime.utcnow():
        return jsonify({"error": "Срок действия лицензии истек"}), 403
    
    # Проверка лимита устройств
    current_devices = Device.query.filter_by(license_id=license.id).count()
    
    # Проверяем, есть ли уже устройство с таким IP
    existing_device = Device.query.filter_by(
        license_id=license.id,
        ip_address=ip_address
    ).first()
    
    if existing_device:
        # Обновляем последнюю активность и имя
        existing_device.last_seen = datetime.utcnow()
        existing_device.name = hostname
        db.session.commit()
        
        return jsonify({
            "installation_id": existing_device.installation_id,
            "device_id": existing_device.id,
            "message": "Устройство уже зарегистрировано. Возвращен существующий ID."
        }), 200
    
    # Если устройство с таким IP не найдено, проверяем лимит
    if current_devices >= license.tariff.max_devices:
        return jsonify({"error": "Достигнут лимит устройств"}), 403
    
    # Создаем новое устройство
    device = Device(
        license_id=license.id,
        installation_id=Device.generate_installation_id(),
        name=hostname,
        ip_address=ip_address,
        last_seen=datetime.utcnow()
    )
    
    db.session.add(device)
    
    # Создаем уведомление о новом устройстве
    license.notify_new_device(device.name, device.ip_address)
    
    db.session.commit()
    
    return jsonify({
        "installation_id": device.installation_id,
        "device_id": device.id,
        "message": "Устройство успешно зарегистрировано"
    }), 200

@bp.route('/license/<int:product_id>/<key>', methods=['POST'])
def license_check(product_id, key):
    """
    Проверка лицензии
    Возвращает статус лицензии
    """
    data = request.get_json(silent=True) or {}
    installation_id = data.get('installation_id')
    
    if not installation_id:
        return jsonify({"error": "installation_id обязателен"}), 400
    
    # Поиск лицензии
    license = License.query.filter_by(
        product_id=product_id,
        key=key
    ).first()
    
    if not license:
        return jsonify({"error": "Лицензия не найдена"}), 404
    
    # Поиск устройства
    device = Device.query.filter_by(
        license_id=license.id,
        installation_id=installation_id
    ).first()
    
    if not device:
        return jsonify({"error": "Устройство не найдено"}), 404
    
    # Проверки лицензии
    if not license.is_valid():
        return jsonify({
            "valid": False,
            "error": "Лицензия не активна"
        }), 403
    
    if license.valid_until and license.valid_until < datetime.utcnow():
        return jsonify({
            "valid": False,
            "error": "Срок действия лицензии истек"
        }), 403
    
    ip_address = request.remote_addr
    if ip_address in license.get_blacklisted_ips():
        return jsonify({
            "valid": False,
            "error": "IP адрес заблокирован"
        }), 403
    
    # Обновляем время последней активности
    device.last_seen = datetime.utcnow()
    device.ip_address = ip_address
    db.session.commit()
    user = User.query.filter_by(id=license.user_id).first()
    
    # Возвращаем информацию о лицензии
    return jsonify({
        "valid": True,
        "license": {
            "name": license.name,
            "product_id": license.product_id,
            "valid_until": license.valid_until.isoformat() if license.valid_until else None,
            "max_devices": license.tariff.max_devices,
            "current_devices": Device.query.filter_by(license_id=license.id).count(),
            "owner": user.username
        },
        "device": {
            "id": device.id,
            "name": device.name,
            "last_seen": device.last_seen.isoformat()
        }
    }), 200

@bp.route('/license/<int:product_id>/<key>/status', methods=['GET'])
def license_status(product_id, key):
    """
    Получение статуса лицензии (без проверки устройства)
    """
    license = License.query.filter_by(
        product_id=product_id,
        key=key
    ).first()
    
    if not license:
        return jsonify({"error": "Лицензия не найдена"}), 404
    
    devices = Device.query.filter_by(license_id=license.id).all()
    
    return jsonify({
        "license": {
            "key": license.key,
            "name": license.name,
            "is_active": license.is_active,
            "valid_until": license.valid_until.isoformat() if license.valid_until else None,
            "created_at": license.created_at.isoformat(),
            "product": license.product.name
        },
        "tariff": {
            "name": license.tariff.name,
            "max_devices": license.tariff.max_devices,
            "period_days": license.tariff.period_days
        },
        "devices": [
            {
                "id": device.id,
                "name": device.name,
                "installation_id": device.installation_id,
                "ip_address": device.ip_address,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "created_at": device.created_at.isoformat()
            }
            for device in devices
        ],
        "device_count": len(devices),
        "is_valid": license.is_valid()
    }), 200
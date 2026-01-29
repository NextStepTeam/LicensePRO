from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models import Product, License, Tariff, Device, BalanceHistory, Notification
from app.forms import LicenseForm, DeviceForm, ProfileForm
from flask import Blueprint
import re 

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    products = Product.query.filter_by(is_active=True).all()
    licenses = License.query.filter_by(user_id=current_user.id).all()
    
    # Получаем непрочитанные уведомления
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('dashboard/products.html', 
                         products=products, 
                         licenses=licenses,
                         notifications=notifications)

@bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    tariffs = Tariff.query.filter_by(product_id=product_id, is_active=True).all()
    licenses = License.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).all()
    
    return render_template('dashboard/product.html', 
                         product=product, 
                         tariffs=tariffs,
                         licenses=licenses)

@bp.route('/license/create', methods=['POST'])
@login_required
def create_license():
    product_id = request.form.get('product_id')
    tariff_id = request.form.get('tariff_id')
    name = request.form.get('name')
    
    if not all([product_id, tariff_id, name]):
        flash('Заполните все поля', 'danger')
        return redirect(request.referrer)
    
    product = Product.query.get_or_404(product_id)
    tariff = Tariff.query.get_or_404(tariff_id)
    
    if not current_user.can_afford(tariff.price):
        flash('Недостаточно средств на балансе', 'danger')
        return redirect(request.referrer)
    
    # Создаем лицензию
    license = License(
        key=License.generate_key(tariff.key_prefix),
        product_id=product.id,
        tariff_id=tariff.id,
        user_id=current_user.id,
        name=name,
        valid_until=datetime.utcnow() if tariff.period_days <= 0 else 
                   datetime.utcnow() + timedelta(days=tariff.period_days)
    )
    
    # Списание средств
    if current_user.charge(tariff.price, f"Покупка лицензии {license.key}"):
        db.session.add(license)
        db.session.commit()
        
        # Уведомление
        notification = Notification(
            user_id=current_user.id,
            title='Лицензия создана',
            message=f'Лицензия "{name}" успешно создана. Ключ: {license.key}'
        )
        db.session.add(notification)
        db.session.commit()
        
        flash(f'Лицензия создана успешно! Ключ: {license.key}', 'success')
    else:
        flash('Ошибка при списании средств', 'danger')
    
    return redirect(url_for('main.product_detail', product_id=product_id))

@bp.route('/license/<int:license_id>')
@login_required
def license_detail(license_id):
    license = License.query.get_or_404(license_id)
    
    # Проверка прав доступа
    if license.user_id != current_user.id and not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    devices = Device.query.filter_by(license_id=license_id).all()
    
    return render_template('dashboard/license.html', 
                         license=license,
                         devices=devices,
                         now=datetime.utcnow())

@bp.route('/license/<int:license_id>/extend', methods=['POST'])
@login_required
def extend_license(license_id):
    license = License.query.get_or_404(license_id)
    
    if license.user_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    tariff = Tariff.query.get_or_404(license.tariff_id)
    
    if not current_user.can_afford(tariff.price):
        flash('Недостаточно средств на балансе', 'danger')
        return redirect(url_for('main.license_detail', license_id=license_id))
    
    # Продление лицензии
    if current_user.charge(tariff.price, f"Продление лицензии {license.key}"):
        if tariff.period_days > 0:
            license.add_time(tariff.period_days)
        
        db.session.commit()
        
        notification = Notification(
            user_id=current_user.id,
            title='Лицензия продлена',
            message=f'Лицензия "{license.name}" успешно продлена'
        )
        db.session.add(notification)
        db.session.commit()
        
        flash('Лицензия успешно продлена!', 'success')
    else:
        flash('Ошибка при списании средств', 'danger')
    
    return redirect(url_for('main.license_detail', license_id=license_id))

@bp.route('/license/<int:license_id>/add_device', methods=['POST'])
@login_required
def add_device(license_id):
    license = License.query.get_or_404(license_id)
    
    if license.user_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    name = request.form.get('name')
    if not name:
        flash('Введите имя устройства', 'danger')
        return redirect(url_for('main.license_detail', license_id=license_id))
    
    # Проверка максимального количества устройств
    current_devices = Device.query.filter_by(license_id=license_id).count()
    if current_devices >= license.tariff.max_devices:
        flash('Достигнут лимит устройств для этой лицензии', 'danger')
        return redirect(url_for('main.license_detail', license_id=license_id))
    
    # Создание устройства
    device = Device(
        license_id=license.id,
        installation_id=Device.generate_installation_id(),
        name=name
    )
    
    db.session.add(device)
    db.session.commit()
    
    flash('Устройство добавлено успешно!', 'success')
    return redirect(url_for('main.license_detail', license_id=license_id))

@bp.route('/license/<int:license_id>/device/<int:device_id>/delete', methods=['POST'])
@login_required
def delete_device(license_id, device_id):
    license = License.query.get_or_404(license_id)
    device = Device.query.get_or_404(device_id)
    
    if license.user_id != current_user.id or device.license_id != license_id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    db.session.delete(device)
    db.session.commit()
    
    flash('Устройство удалено успешно!', 'success')
    return redirect(url_for('main.license_detail', license_id=license_id))

@bp.route('/license/<int:license_id>/update', methods=['POST'])
@login_required
def update_license(license_id):
    license = License.query.get_or_404(license_id)
    
    if license.user_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    name = request.form.get('name')
    if name:
        license.name = name
    
    db.session.commit()
    flash('Лицензия обновлена успешно!', 'success')
    return redirect(url_for('main.license_detail', license_id=license_id))

@bp.route('/license/<int:license_id>/toggle', methods=['POST'])
@login_required
def toggle_license(license_id):
    license = License.query.get_or_404(license_id)
    
    if license.user_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    license.is_active = not license.is_active
    db.session.commit()
    
    status = "активирована" if license.is_active else "деактивирована"
    flash(f'Лицензия {status} успешно!', 'success')
    return redirect(url_for('main.license_detail', license_id=license_id))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.username = request.form.get('username', current_user.username)
        current_user.email = request.form.get('email', current_user.email)
        
        new_password = request.form.get('new_password')
        if new_password:
            current_user.set_password(new_password)
        
        db.session.commit()
        flash('Профиль обновлен успешно!', 'success')
        return redirect(url_for('main.profile'))
    
    # Получаем историю баланса
    balance_history = BalanceHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(BalanceHistory.created_at.desc()).limit(20).all()
    
    return render_template('dashboard/profile.html', 
                         balance_history=balance_history)

@bp.route('/notifications/mark_read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    notification.is_read = True
    db.session.commit()
    
    return redirect(request.referrer or url_for('main.dashboard'))

@bp.route('/balance/deposit')
@login_required
def deposit_balance():
    # В реальной системе здесь была бы интеграция с платежной системой
    # Для демо просто покажем информацию
    flash('Для пополнения баланса свяжитесь с администратором', 'info')
    return redirect(url_for('main.profile'))

@bp.route('/license/<int:license_id>/add_blacklisted_ip', methods=['POST'])
@login_required
def add_blacklisted_ip(license_id):
    """Добавить IP в черный список (для обычных пользователей)"""
    license = License.query.get_or_404(license_id)
    
    if license.user_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    ip = request.form.get('ip')
    if ip:
        # Простая валидация IP
        import re
        ip_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
        
        if ip_pattern.match(ip):
            license.add_blacklisted_ip(ip)
            db.session.commit()
            flash(f'IP {ip} добавлен в черный список', 'success')
        else:
            flash('Неверный формат IP адреса', 'danger')
    
    return redirect(url_for('main.license_detail', license_id=license_id))

@bp.route('/license/<int:license_id>/remove_blacklisted_ip', methods=['POST'])
@login_required
def remove_blacklisted_ip(license_id):
    """Удалить IP из черного списка (для обычных пользователей)"""
    license = License.query.get_or_404(license_id)
    
    if license.user_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    ip = request.form.get('ip')
    if ip:
        license.remove_blacklisted_ip(ip)
        db.session.commit()
        flash(f'IP {ip} удален из черного списка', 'success')
    
    return redirect(url_for('main.license_detail', license_id=license_id))

@bp.route('/license/<int:license_id>/reset_key', methods=['POST'])
@login_required
def reset_license_key(license_id):
    """Сбросить ключ лицензии (генерация нового)"""
    license = License.query.get_or_404(license_id)
    
    if license.user_id != current_user.id and not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Генерируем новый ключ с тем же префиксом
    old_key = license.key
    prefix = license.key.split('-')[0]
    license.key = License.generate_key(prefix)
    
    db.session.commit()
    
    # Уведомление
    notification = Notification(
        user_id=license.user_id,
        title='Ключ лицензии сброшен',
        message=f'Ключ лицензии "{license.name}" был сброшен. Старый ключ: {old_key}, новый ключ: {license.key}'
    )
    db.session.add(notification)
    db.session.commit()
    
    flash(f'Ключ лицензии сброшен! Новый ключ: {license.key}', 'success')
    return redirect(url_for('main.license_detail', license_id=license_id))

@bp.route('/license/<int:license_id>/change_tariff', methods=['POST'])
@login_required
def change_license_tariff(license_id):
    """Сменить тариф лицензии"""
    license = License.query.get_or_404(license_id)
    
    if license.user_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.dashboard'))
    
    new_tariff_id = request.form.get('tariff_id')
    if not new_tariff_id:
        flash('Выберите тариф', 'danger')
        return redirect(url_for('main.license_detail', license_id=license_id))
    
    new_tariff = Tariff.query.get_or_404(new_tariff_id)
    
    # Проверяем, нужна ли доплата
    price_difference = new_tariff.price - license.tariff.price
    
    if price_difference > 0 and not current_user.can_afford(price_difference):
        flash('Недостаточно средств для смены тарифа', 'danger')
        return redirect(url_for('main.license_detail', license_id=license_id))
    
    # Если новый тариф имеет меньше устройств, проверяем
    if new_tariff.max_devices < len(license.devices):
        flash(f'Новый тариф поддерживает только {new_tariff.max_devices} устройств, а у вас {len(license.devices)}. Удалите лишние устройства.', 'danger')
        return redirect(url_for('main.license_detail', license_id=license_id))
    
    # Списание средств если нужно
    if price_difference > 0:
        if not current_user.charge(price_difference, f"Смена тарифа лицензии {license.key}"):
            flash('Ошибка при списании средств', 'danger')
            return redirect(url_for('main.license_detail', license_id=license_id))
    
    # Меняем тариф
    old_tariff_name = license.tariff.name
    license.tariff_id = new_tariff.id
    
    # Если новый тариф имеет другой период, обновляем дату окончания
    if new_tariff.period_days > 0:
        if license.valid_until and license.valid_until > datetime.utcnow():
            # Продлеваем с текущей даты окончания
            license.valid_until = license.valid_until + timedelta(days=new_tariff.period_days)
        else:
            # Начинаем с текущего времени
            license.valid_until = datetime.utcnow() + timedelta(days=new_tariff.period_days)
    else:
        # Бессрочный тариф
        license.valid_until = None
    
    db.session.commit()
    
    # Уведомление
    notification = Notification(
        user_id=current_user.id,
        title='Тариф лицензии изменен',
        message=f'Тариф лицензии "{license.name}" изменен с "{old_tariff_name}" на "{new_tariff.name}"'
    )
    db.session.add(notification)
    db.session.commit()
    
    flash(f'Тариф лицензии изменен на "{new_tariff.name}"', 'success')
    return redirect(url_for('main.license_detail', license_id=license_id))
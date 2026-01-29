from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from flask import Blueprint
from app.models import User, Product, Tariff, License, Device, BalanceHistory, Notification
bp = Blueprint('admin', __name__)
@bp.before_request
def restrict_to_admins():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/')
@login_required
def admin_index():
    stats = {
        'total_users': User.query.count(),
        'total_licenses': License.query.count(),
        'total_products': Product.query.count(),
        'active_licenses': License.query.filter_by(is_active=True).count(),
        'recent_users': User.query.order_by(User.created_at.desc()).limit(5).all(),
        'recent_licenses': License.query.order_by(License.created_at.desc()).limit(5).all()
    }
    
    return render_template('admin/index.html', stats=stats)

@bp.route('/users')
@login_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@bp.route('/user/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
def toggle_user_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    # Не позволяем снять админку с себя
    if user.id == current_user.id:
        flash('Нельзя снять права администратора с себя', 'danger')
        return redirect(url_for('admin.admin_users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = "назначен администратором" if user.is_admin else "лишен прав администратора"
    flash(f'Пользователь {user.username} {status}', 'success')
    return redirect(url_for('admin.admin_users'))

@bp.route('/user/<int:user_id>/balance', methods=['POST'])
@login_required
def update_user_balance(user_id):
    user = User.query.get_or_404(user_id)
    amount = float(request.form.get('amount', 0))
    description = request.form.get('description', '')
    
    if amount > 0:
        user.deposit(amount, description)
        db.session.commit()
        
        # Уведомление пользователю
        notification = Notification(
            user_id=user.id,
            title='Пополнение баланса',
            message=f'Ваш баланс пополнен на {amount} ₽. {description}'
        )
        db.session.add(notification)
        db.session.commit()
        
        flash(f'Баланс пользователя {user.username} пополнен на {amount} ₽', 'success')
    elif amount < 0:
        if user.can_afford(abs(amount)):
            user.charge(abs(amount), description)
            db.session.commit()
            
            notification = Notification(
                user_id=user.id,
                title='Списание с баланса',
                message=f'С вашего баланса списано {abs(amount)} ₽. {description}'
            )
            db.session.add(notification)
            db.session.commit()
            
            flash(f'С баланса пользователя {user.username} списано {abs(amount)} ₽', 'success')
        else:
            flash('Недостаточно средств на балансе пользователя', 'danger')
    
    return redirect(url_for('admin.admin_users'))

@bp.route('/products')
@login_required
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@bp.route('/product/create', methods=['POST'])
@login_required
def create_product():
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('Введите название продукта', 'danger')
        return redirect(url_for('admin.admin_products'))
    
    product = Product(name=name, description=description)
    db.session.add(product)
    db.session.commit()
    
    flash(f'Продукт "{name}" создан успешно', 'success')
    return redirect(url_for('admin.admin_products'))

@bp.route('/product/<int:product_id>/toggle', methods=['POST'])
@login_required
def toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    
    status = "активирован" if product.is_active else "деактивирован"
    flash(f'Продукт "{product.name}" {status}', 'success')
    return redirect(url_for('admin.admin_products'))

@bp.route('/tariffs')
@login_required
def admin_tariffs():
    tariffs = Tariff.query.join(Product).all()
    products = Product.query.filter_by(is_active=True).all()
    return render_template('admin/tariffs.html', tariffs=tariffs, products=products)

@bp.route('/tariff/create', methods=['POST'])
@login_required
def create_tariff():
    product_id = request.form.get('product_id')
    name = request.form.get('name')
    description = request.form.get('description')
    price = float(request.form.get('price', 0))
    period_days = int(request.form.get('period_days', 0))
    max_devices = int(request.form.get('max_devices', 1))
    key_prefix = request.form.get('key_prefix', '')
    
    if not all([product_id, name, key_prefix]):
        flash('Заполните все обязательные поля', 'danger')
        return redirect(url_for('admin.admin_tariffs'))
    
    tariff = Tariff(
        product_id=product_id,
        name=name,
        description=description,
        price=price,
        period_days=period_days,
        max_devices=max_devices,
        key_prefix=key_prefix.upper()
    )
    
    db.session.add(tariff)
    db.session.commit()
    
    flash(f'Тариф "{name}" создан успешно', 'success')
    return redirect(url_for('admin.admin_tariffs'))

@bp.route('/licenses')
@login_required
def admin_licenses():
    licenses = License.query.order_by(License.created_at.desc()).all()
    return render_template('admin/licenses.html', licenses=licenses, now=datetime.now())

@bp.route('/license/<int:license_id>/toggle', methods=['POST'])
@login_required
def admin_toggle_license(license_id):
    license = License.query.get_or_404(license_id)
    license.is_active = not license.is_active
    db.session.commit()
    
    status = "активирована" if license.is_active else "деактивирована"
    flash(f'Лицензия {license.key} {status}', 'success')
    return redirect(url_for('admin.admin_licenses'))

@bp.route('/license/<int:license_id>/add_blacklist', methods=['POST'])
@login_required
def add_to_blacklist(license_id):
    license = License.query.get_or_404(license_id)
    ip = request.form.get('ip')
    
    if ip:
        license.add_blacklisted_ip(ip)
        db.session.commit()
        flash(f'IP {ip} добавлен в черный список', 'success')
    
    return redirect(url_for('main.license_detail', license_id=license.id))

@bp.route('/license/<int:license_id>/remove_blacklist', methods=['POST'])
@login_required
def remove_from_blacklist(license_id):
    license = License.query.get_or_404(license_id)
    ip = request.form.get('ip')
    
    if ip:
        license.remove_blacklisted_ip(ip)
        db.session.commit()
        flash(f'IP {ip} удален из черного списка', 'success')
    
    return redirect(url_for('main.license_detail', license_id=license.id))

@bp.route('/notifications')
@login_required
def admin_notifications():
    notifications = Notification.query.order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    
    return render_template('admin/notifications.html', notifications=notifications)

@bp.route('/statistics')
@login_required
def admin_statistics():
    # Базовая статистика
    from sqlalchemy import func
    
    revenue = db.session.query(func.sum(Tariff.price)).\
        join(License).\
        scalar() or 0
    
    active_licenses_count = License.query.filter_by(is_active=True).count()
    expired_licenses = License.query.filter(
        License.valid_until < datetime.utcnow(),
        License.is_active == True
    ).count()
    
    # Распределение по продуктам
    product_stats = db.session.query(
        Product.name,
        func.count(License.id),
        func.sum(Tariff.price)
    ).join(License, Product.id == License.product_id).\
      join(Tariff, License.tariff_id == Tariff.id).\
      group_by(Product.id).all()
    
    return render_template('admin/statistics.html',
                         revenue=revenue,
                         active_licenses_count=active_licenses_count,
                         expired_licenses=expired_licenses,
                         product_stats=product_stats)
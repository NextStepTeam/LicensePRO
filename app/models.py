from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string
from app import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    balance = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    licenses = db.relationship('License', backref='owner', lazy=True)
    balance_history = db.relationship('BalanceHistory', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def can_afford(self, amount):
        return self.balance >= amount
    
    def charge(self, amount, description=""):
        if self.can_afford(amount):
            self.balance -= amount
            history = BalanceHistory(
                user_id=self.id,
                amount=-amount,
                description=description,
                balance_after=self.balance
            )
            db.session.add(history)
            return True
        return False
    
    def deposit(self, amount, description=""):
        self.balance += amount
        history = BalanceHistory(
            user_id=self.id,
            amount=amount,
            description=description,
            balance_after=self.balance
        )
        db.session.add(history)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    tariffs = db.relationship('Tariff', backref='product', lazy=True)
    licenses = db.relationship('License', backref='product', lazy=True)

class Tariff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    period_days = db.Column(db.Integer, nullable=False)  # 0 = бессрочно
    max_devices = db.Column(db.Integer, nullable=False)
    key_prefix = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Связи
    licenses = db.relationship('License', backref='tariff', lazy=True)

class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariff.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    valid_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    blacklisted_ips = db.Column(db.Text, default="")  # CSV список IP
    
    # Связи
    devices = db.relationship('Device', backref='license', lazy=True)
    
    @classmethod
    def generate_key(cls, prefix):
        alphabet = string.ascii_uppercase + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(20))
        return f"{prefix}-{random_part}"
    
    def is_valid(self):
        if not self.is_active:
            return False
        if self.valid_until and self.valid_until < datetime.utcnow():
            return False
        return True
    
    def add_time(self, days):
        if self.valid_until:
            if self.valid_until < datetime.utcnow():
                self.valid_until = datetime.utcnow() + timedelta(days=days)
            else:
                self.valid_until += timedelta(days=days)
        else:
            self.valid_until = datetime.utcnow() + timedelta(days=days)
    
    def get_blacklisted_ips(self):
        return [ip.strip() for ip in self.blacklisted_ips.split(',') if ip.strip()]
    
    def add_blacklisted_ip(self, ip):
        ips = self.get_blacklisted_ips()
        if ip not in ips:
            ips.append(ip)
            self.blacklisted_ips = ','.join(ips)
    
    def remove_blacklisted_ip(self, ip):
        ips = self.get_blacklisted_ips()
        if ip in ips:
            ips.remove(ip)
            self.blacklisted_ips = ','.join(ips)
            
    def notify_new_device(self, device_name, ip_address):
        """Создать уведомление о новом устройстве"""
        notification = Notification(
            user_id=self.user_id,
            title="Новое устройство",
            message=f"У лицензии {self.name} новое устройство\nIP: {ip_address}\nИмя устройства: {device_name}",
            is_read=False
        )
        db.session.add(notification)
        db.session.flush()

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey('license.id'), nullable=False)
    installation_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    @classmethod
    def generate_installation_id(cls):
        return secrets.token_hex(16)

class BalanceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    balance_after = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
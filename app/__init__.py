from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
from datetime import datetime

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    login_manager.init_app(app)
    
    # Регистрация blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.main import bp as main_bp
    from app.routes.api import bp as api_bp
    from app.routes.admin import bp as admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    with app.app_context():
        db.create_all()
        # Создаем первого администратора если его нет
        from app.models import User
        if User.query.first() is None:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    
    @app.template_filter('timeago')
    def timeago_filter(dt):
        """Фильтр для отображения времени в относительном формате"""
        if not dt:
            return ""

        now = datetime.now()
        diff = now - dt

        seconds = diff.total_seconds()
        if seconds < 60:
            return "только что"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} мин назад"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} ч назад"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} дн назад"
        else:
            return dt.strftime('%d.%m.%Y')
    
    return app
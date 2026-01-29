from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, FloatField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app.models import User

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Это имя пользователя уже занято')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Этот email уже используется')

class LicenseForm(FlaskForm):
    name = StringField('Название лицензии', validators=[DataRequired(), Length(max=100)])
    product_id = SelectField('Продукт', coerce=int, validators=[DataRequired()])
    tariff_id = SelectField('Тариф', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Создать лицензию')

class DeviceForm(FlaskForm):
    name = StringField('Имя устройства', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Добавить устройство')

class ProfileForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    current_password = PasswordField('Текущий пароль')
    new_password = PasswordField('Новый пароль', validators=[Length(min=6)])
    new_password2 = PasswordField('Повторите новый пароль', validators=[EqualTo('new_password')])
    submit = SubmitField('Сохранить изменения')

class TariffForm(FlaskForm):
    name = StringField('Название тарифа', validators=[DataRequired(), Length(max=100)])
    product_id = SelectField('Продукт', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Описание')
    price = FloatField('Цена', validators=[DataRequired()])
    period_days = IntegerField('Период (дней, 0=бессрочно)', default=30)
    max_devices = IntegerField('Максимум устройств', default=1)
    key_prefix = StringField('Префикс ключа', validators=[DataRequired(), Length(min=2, max=10)])
    submit = SubmitField('Создать тариф')
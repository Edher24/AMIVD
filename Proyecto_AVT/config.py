# Autor: Adriana Nicole Guzman Ahuatzi
#23/03/2026
# Descripción: Configuración general de la aplicación: conexión a la base de datos MySQL,
#              clave secreta y parámetros del servidor de correo SMTP.
import os
class Config:
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', '3306'))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'root')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'base_datos_amivd')
    MYSQL_CURSORCLASS = 'DictCursor'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'voleibol_avt_tlaxcala_2026'

    # Mail config
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'avt@gmail.com'
    MAIL_PASSWORD = '1234'
    MAIL_DEFAULT_SENDER = 'avt@gmail.com'
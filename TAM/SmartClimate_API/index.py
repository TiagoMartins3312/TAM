# Nova publicacao para aplicar as variaveis de ambiente atualizadas do vercel
import os
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import Flask, jsonify, request

import db

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mysecretkey')

NOT_FOUND_CODE = 401
OK_CODE = 200
SUCCESS_CODE = 201
NO_CONTENT_CODE = 204
BAD_REQUEST_CODE = 400
UNAUTHORIZED_CODE = 401
FORBIDDEN_CODE = 403
NOT_FOUND = 404

# Token simples para os pedidos enviados pelo dispositivo embebido.
# Pode ser definido como variável de ambiente API_TOKEN_ESPERADO.
API_TOKEN_ESPERADO = os.getenv(
    'API_TOKEN_ESPERADO', 'TokenSecreto_Licenciatura_2026'
)


@app.route('/', methods=['GET'])
def home():
    return 'Welcome to Smart Climate API!'


def verificar_token_dispositivo():
    auth_header = request.headers.get('Authorization', '')
    return auth_header == f'Bearer {API_TOKEN_ESPERADO}'


@app.route('/login', methods=['POST'])
def login():
    print("DEBUG: PEDIDO LOGIN RECEBIDO", flush=True)
    data = request.get_json(silent=True) or {}
    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'invalid parameters'}), BAD_REQUEST_CODE

    user = db.login(data['username'], data['password'])
    if user is None:
        return jsonify({'error': 'Check credentials'}), NOT_FOUND_CODE

    token = jwt.encode(
        {
            'user_id': user['id'],
            'exp': datetime.utcnow() + timedelta(minutes=5)
        },
        app.config['SECRET_KEY'],
        algorithm='HS256'
    )

    # Compatibilidade com versões do PyJWT que devolvem bytes.
    if isinstance(token, bytes):
        token = token.decode('UTF-8')

    user['token'] = token
    return jsonify(user), OK_CODE


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'invalid parameters'}), BAD_REQUEST_CODE

    if not data['username'] or not data['password']:
        return jsonify({'error': 'username and password cannot be empty'}), BAD_REQUEST_CODE

    if db.user_exists(data):
        return jsonify({'error': 'user already exists'}), BAD_REQUEST_CODE

    user = db.add_user(data)
    return jsonify(user), SUCCESS_CODE


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token not provided'}), FORBIDDEN_CODE

        token = auth_header.split(' ', 1)[1]
        try:
            data = jwt.decode(
                token,
                app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado', 'expired': True}), UNAUTHORIZED_CODE
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), FORBIDDEN_CODE

        user = db.get_user(data['user_id'])
        if user is None:
            return jsonify({'error': 'Utilizador não encontrado'}), UNAUTHORIZED_CODE

        request.user = user
        return f(*args, **kwargs)
    return decorated


# A aplicação Android do professor já consulta a rota /data.
@app.route('/data', methods=['GET'])
@auth_required
def get_data():
    return jsonify(db.get_all_readings()), OK_CODE


# A aplicação Android consulta e altera o estado pretendido do sistema.
@app.route('/actuators', methods=['GET'])
@auth_required
def get_actuators():
    state = db.get_actuator_state()
    if state is None:
        return jsonify({'error': 'Estado dos atuadores não encontrado'}), NOT_FOUND
    return jsonify(state), OK_CODE


@app.route('/actuators', methods=['POST'])
@auth_required
def set_actuators():
    data = request.get_json(silent=True) or {}
    campos_permitidos = (
        'fan_on', 'fan_speed', 'led_1', 'led_2',
        'mode', 'temp_on', 'temp_off'
    )

    if not any(campo in data for campo in campos_permitidos):
        return jsonify({'error': 'invalid parameters'}), BAD_REQUEST_CODE

    try:
        state = db.update_actuator_state(data)
    except (ValueError, TypeError) as error:
        return jsonify({'error': str(error)}), BAD_REQUEST_CODE

    return jsonify(state), OK_CODE


# O dispositivo envia as leituras de temperatura para esta rota.
@app.route('/api/sensores', methods=['POST'])
def receber_sensores():
    if not verificar_token_dispositivo():
        return jsonify({'erro': 'Nao autorizado'}), UNAUTHORIZED_CODE

    data = request.get_json(silent=True) or {}
    if 'sensor' not in data or 'value' not in data:
        return jsonify({'erro': 'JSON invalido: são necessários sensor e value'}), BAD_REQUEST_CODE

    reading = db.add_reading(data['sensor'], data['value'])

    # Se o dispositivo também enviar o estado efetivo, guardamos essa informação.
    campos_estado = (
        'fan_on', 'fan_speed', 'led_1', 'led_2',
        'mode', 'temp_on', 'temp_off'
    )
    estado_enviado = {campo: data[campo] for campo in campos_estado if campo in data}
    if estado_enviado:
        try:
            db.update_actuator_state(estado_enviado)
        except (ValueError, TypeError) as error:
            return jsonify({'erro': str(error)}), BAD_REQUEST_CODE

    return jsonify({'status': 'Leitura guardada', 'reading': reading}), SUCCESS_CODE


# O dispositivo consulta os comandos/estado pretendido guardado na base de dados.
@app.route('/api/atuadores', methods=['GET'])
def ler_atuadores():
    if not verificar_token_dispositivo():
        return jsonify({'erro': 'Nao autorizado'}), UNAUTHORIZED_CODE

    state = db.get_actuator_state()
    if state is None:
        return jsonify({'erro': 'Estado dos atuadores não encontrado'}), NOT_FOUND
    return jsonify(state), OK_CODE


if __name__ == '__main__':
    app.run()

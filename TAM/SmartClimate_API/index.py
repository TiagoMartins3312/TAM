import os
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import Flask, jsonify, request

import db
import db2

app = Flask(__name__)
app.debug = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mysecretkey')

NOT_FOUND_CODE = 401
OK_CODE = 200
SUCCESS_CODE = 201
NO_CONTENT_CODE = 204
BAD_REQUEST_CODE = 400
UNAUTHORIZED_CODE = 401
FORBIDDEN_CODE = 403
NOT_FOUND = 404

# token do arduino, está nas variáveis do vercel
API_TOKEN_ESPERADO = os.getenv('API_TOKEN_ESPERADO', '').strip()


# rota para testar se a api está a funcionar
@app.route('/', methods=['GET'])
def home():
    return 'Welcome to Smart Climate API!'


# ver se o pedido vem mesmo do nosso arduino
def verificar_token_dispositivo():
    # se não houver token definido no vercel ninguém entra
    if API_TOKEN_ESPERADO == '':
        return False

    # o arduino manda o token no cabeçalho
    auth_header = request.headers.get('Authorization', '')
    if auth_header == 'Bearer ' + API_TOKEN_ESPERADO:
        return True

    # ou no json (simulador mokxi)
    dados = request.get_json(silent=True) or {}
    return dados.get('device_token', '') == API_TOKEN_ESPERADO


# login da app, devolve o token jwt
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'invalid parameters'}), BAD_REQUEST_CODE

    user = db.login(data['username'], data['password'])
    if user is None:
        return jsonify({'error': 'Check credentials'}), NOT_FOUND_CODE

    # o token dura 12 horas
    token = jwt.encode(
        {
            'user_id': user['id'],
            'exp': datetime.utcnow() + timedelta(hours=12)
        },
        app.config['SECRET_KEY'],
        algorithm='HS256'
    )

    # algumas versões do PyJWT devolvem bytes
    if isinstance(token, bytes):
        token = token.decode('UTF-8')

    user['token'] = token
    return jsonify(user), OK_CODE


# criar conta
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


# verifica o token jwt antes de entrar nas rotas protegidas
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

        # se a bd estiver cheia de ligações devolve 503
        try:
            user = db.get_user(data['user_id'])
        except Exception:
            app.logger.exception("Erro ao validar o utilizador")
            return jsonify({'error': 'Base de dados ocupada, tenta outra vez.'}), 503

        if user is None:
            return jsonify({'error': 'Utilizador não encontrado'}), UNAUTHORIZED_CODE

        request.user = user
        return f(*args, **kwargs)
    return decorated


# histórico das temperaturas
@app.route('/data', methods=['GET'])
@auth_required
def get_data():
    return jsonify(db.get_all_readings()), OK_CODE


# a app vê o estado da ventoinha, leds e standby
@app.route('/actuators', methods=['GET'])
@auth_required
def get_actuators():
    state = db.get_actuator_display_state()
    if state is None:
        return jsonify({'error': 'Estado dos atuadores não encontrado'}), NOT_FOUND
    return jsonify(state), OK_CODE


# a app manda os comandos
@app.route('/actuators', methods=['POST'])
@auth_required
def set_actuators():
    data = request.get_json(silent=True) or {}
    campos_permitidos = (
        'fan_on', 'standby', 'led_1', 'led_2',
        'mode', 'temp_on', 'temp_off'
    )

    if not any(campo in data for campo in campos_permitidos):
        return jsonify({'error': 'invalid parameters'}), BAD_REQUEST_CODE

    try:
        state = db.update_actuator_state(data)
    except (ValueError, TypeError) as error:
        return jsonify({'error': str(error)}), BAD_REQUEST_CODE
    except Exception:
        # normalmente é a bd da escola com demasiadas ligações
        app.logger.exception("Erro ao guardar o comando da app")
        return jsonify({'error': 'Base de dados ocupada, tenta outra vez.'}), 503

    return jsonify(state), OK_CODE


# o arduino envia a temperatura e recebe os comandos da app na resposta
@app.route('/api/sensores', methods=['POST'])
def receber_sensores():
    if not verificar_token_dispositivo():
        return jsonify({'erro': 'Nao autorizado'}), UNAUTHORIZED_CODE

    data = request.get_json(silent=True) or {}

    if 'sensor' not in data or 'value' not in data or 'mac' not in data:
        return jsonify({
            'erro': 'São necessários os campos sensor, value e mac.'
        }), BAD_REQUEST_CODE

    try:
        # o standby só vem quando carregam no botão do arduino
        reading, estado = db2.guardar_leitura_e_obter_comandos(
            mac=data['mac'],
            sensor=data['sensor'],
            value=data['value'],
            ip=request.remote_addr,
            fan_actual_on=data.get('fan_actual_on'),
            led_1=data.get('led_1'),
            led_2=data.get('led_2'),
            standby_local=data.get('standby')
        )
    except Exception as error:
        app.logger.exception("Erro ao processar dados do dispositivo")
        return jsonify({'erro': str(error)}), 500

    return jsonify({
        'status': 'Leitura guardada',
        'reading': reading,
        'actuators': estado
    }), SUCCESS_CODE


# o arduino também pode só consultar os comandos
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

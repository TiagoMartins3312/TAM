import os
from flask import Flask, request, jsonify
import db2

app = Flask(__name__)

# chave que o arduino tem de mandar no cabeçalho X-API-Key
API_KEY = os.environ.get("API_KEY", "muda-esta-chave")


# corre antes de todos os pedidos
@app.before_request
def verificar_autenticacao():
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"erro": "API key inválida."}), 401


# registar um arduino
@app.route("/devices/register", methods=["POST"])
def api_register_device():
    data = request.get_json(silent=True)
    if not data or not data.get("mac"):
        return jsonify({"erro": "O campo 'mac' é obrigatório."}), 400

    try:
        device = db2.register_device(
            mac=data["mac"],
            name=data.get("name"),
            ip=data.get("ip"),
            firmware=data.get("firmware")
        )
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    return jsonify(device), 201


# lista dos arduinos
@app.route("/devices", methods=["GET"])
def api_list_devices():
    try:
        devices = db2.get_all_devices()
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    return jsonify(devices)


# dados de um arduino
@app.route("/devices/<mac>", methods=["GET"])
def api_get_device(mac):
    try:
        device = db2.get_device(mac)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    if device is None:
        return jsonify({"erro": "Dispositivo não encontrado."}), 404
    return jsonify(device)


# guardar uma temperatura
@app.route("/readings", methods=["POST"])
def api_add_reading():
    data = request.get_json(silent=True)
    if not data or not data.get("mac"):
        return jsonify({"erro": "O campo 'mac' é obrigatório."}), 400
    if "value" not in data:
        return jsonify({"erro": "O campo 'value' é obrigatório."}), 400

    try:
        reading = db2.add_reading_by_device(
            mac=data["mac"],
            sensor=data.get("sensor", "temp"),
            value=data["value"],
        )
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    return jsonify(reading), 201


# guardar várias temperaturas
@app.route("/readings/bulk", methods=["POST"])
def api_add_readings_bulk():
    data = request.get_json(silent=True)
    if not data or not data.get("mac"):
        return jsonify({"erro": "O campo 'mac' é obrigatório."}), 400
    readings = data.get("readings")
    if not isinstance(readings, list) or not readings:
        return jsonify({"erro": "O campo 'readings' tem de ser uma lista não vazia."}), 400

    try:
        gravadas = db2.add_readings_by_device_bulk(data["mac"], readings)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    return jsonify({"count": len(gravadas), "items": gravadas}), 201


# temperaturas de um arduino
@app.route("/readings/<mac>", methods=["GET"])
def api_get_readings(mac):
    limit = request.args.get("limit", default=100, type=int)
    try:
        readings = db2.get_readings_by_device(mac, limit=limit)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    return jsonify(readings)


# ver os comandos, o mac não é usado porque só há um arduino
@app.route("/actuators", methods=["GET"])
@app.route("/actuators/<mac>", methods=["GET"])
def api_get_actuators(mac=None):
    try:
        state = db2.get_actuator_state()
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    if state is None:
        return jsonify({"erro": "Estado dos atuadores não existe."}), 404
    return jsonify(state)


# alterar os comandos
@app.route("/actuators", methods=["PUT"])
@app.route("/actuators/<mac>", methods=["PUT"])
def api_update_actuators(mac=None):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"erro": "Corpo JSON obrigatório."}), 400

    try:
        state = db2.update_actuator_state(data)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    return jsonify(state)

# Quando o programa é executado a partir deste ficheiro
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

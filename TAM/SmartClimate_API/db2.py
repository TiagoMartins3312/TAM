# a ligação e as funções dos atuadores são as mesmas do db.py
from db import get_connection, get_actuator_state, update_actuator_state


# registar o arduino, se o mac já existir só atualiza os dados
def register_device(mac, name=None, ip=None, firmware=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "TAM_Android".devices '
                '(mac, name, ip, firmware, last_seen) '
                'VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP) '
                'ON CONFLICT (mac) DO UPDATE '
                'SET ip        = COALESCE(EXCLUDED.ip,       "TAM_Android".devices.ip), '
                '    name      = COALESCE(EXCLUDED.name,     "TAM_Android".devices.name), '
                '    firmware  = COALESCE(EXCLUDED.firmware, "TAM_Android".devices.firmware), '
                '    last_seen = CURRENT_TIMESTAMP '
                'RETURNING id, mac, name, ip, firmware, last_seen',
                (mac, name, ip, firmware)
            )
            row = cur.fetchone()

    return {
        "id": row[0],
        "mac": row[1],
        "name": row[2],
        "ip": row[3],
        "firmware": row[4],
        "last_seen": row[5].strftime("%d/%m/%Y %H:%M:%S")
    }


# dados de um arduino pelo mac
def get_device(mac):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, mac, name, ip, firmware, last_seen '
                'FROM "TAM_Android".devices WHERE mac = %s',
                (mac,)
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "mac": row[1],
        "name": row[2],
        "ip": row[3],
        "firmware": row[4],
        "last_seen": row[5].strftime("%d/%m/%Y %H:%M:%S")
    }


# todos os arduinos registados
def get_all_devices():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, mac, name, ip, firmware, last_seen '
                'FROM "TAM_Android".devices '
                'ORDER BY last_seen DESC'
            )
            rows = cur.fetchall()

    devices = []
    for row in rows:
        devices.append({
            "id": row[0],
            "mac": row[1],
            "name": row[2],
            "ip": row[3],
            "firmware": row[4],
            "last_seen": row[5].strftime("%d/%m/%Y %H:%M:%S")
        })
    return devices


# guardar uma temperatura de um arduino
def add_reading_by_device(mac, sensor, value):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM "TAM_Android".devices WHERE mac = %s',
                (mac,)
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("O dispositivo %s não está registado." % mac)
            device_id = row[0]

            cur.execute(
                'UPDATE "TAM_Android".devices '
                'SET last_seen = CURRENT_TIMESTAMP WHERE id = %s',
                (device_id,)
            )
            cur.execute(
                'INSERT INTO "TAM_Android".readings '
                '(device_id, sensor, value) '
                'VALUES (%s, %s, %s) '
                'RETURNING sensor, value, criado_em',
                (device_id, str(sensor), str(value))
            )
            reading_tuple = cur.fetchone()

    return {
        "sensor": reading_tuple[0],
        "value": reading_tuple[1],
        "criado_em": reading_tuple[2].strftime("%d/%m/%Y %H:%M:%S")
    }


# guardar várias temperaturas de uma vez
def add_readings_by_device_bulk(mac, readings):
    if not readings:
        raise ValueError("A lista de leituras não pode estar vazia.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM "TAM_Android".devices WHERE mac = %s',
                (mac,)
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("O dispositivo %s não está registado." % mac)
            device_id = row[0]

            cur.execute(
                'UPDATE "TAM_Android".devices '
                'SET last_seen = CURRENT_TIMESTAMP WHERE id = %s',
                (device_id,)
            )

            gravadas = []
            for r in readings:
                cur.execute(
                    'INSERT INTO "TAM_Android".readings '
                    '(device_id, sensor, value) '
                    'VALUES (%s, %s, %s) '
                    'RETURNING sensor, value, criado_em',
                    (
                        device_id,
                        str(r.get("sensor", "temp")),
                        str(r["value"])
                    )
                )
                t = cur.fetchone()
                gravadas.append({
                    "sensor": t[0],
                    "value": t[1],
                    "criado_em": t[2].strftime("%d/%m/%Y %H:%M:%S")
                })

    return gravadas


# temperaturas de um arduino
def get_readings_by_device(mac, limit=100):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT r.sensor, r.value, r.criado_em '
                'FROM "TAM_Android".readings r '
                'JOIN "TAM_Android".devices d ON d.id = r.device_id '
                'WHERE d.mac = %s '
                'ORDER BY r.criado_em DESC LIMIT %s',
                (mac, int(limit))
            )
            rows = cur.fetchall()

    readings = []
    for row in rows:
        readings.append({
            "sensor": row[0],
            "value": row[1],
            "criado_em": row[2].strftime("%d/%m/%Y %H:%M:%S")
        })
    return readings


# função que o arduino usa: guarda o que ele enviou e devolve os comandos da app
# é tudo na mesma ligação para não abrir várias à bd
def guardar_leitura_e_obter_comandos(mac, sensor, value, ip=None,
                                     fan_actual_on=None, led_1=None,
                                     led_2=None, standby_local=None):
    with get_connection() as conn:
        with conn.cursor() as cur:

            # estado real do arduino, fica noutras colunas para não apagar os comandos da app
            if fan_actual_on is not None:
                cur.execute(
                    'UPDATE "TAM_Android".actuator_state '
                    'SET fan_actual_on = %s, '
                    'led_1_actual = COALESCE(%s, led_1_actual), '
                    'led_2_actual = COALESCE(%s, led_2_actual) '
                    'WHERE id = 1',
                    (fan_actual_on, led_1, led_2)
                )

            # só vem preenchido quando alguém carregou no botão do arduino
            if standby_local is not None:
                cur.execute(
                    'UPDATE "TAM_Android".actuator_state '
                    'SET standby = %s, updated_at = CURRENT_TIMESTAMP '
                    'WHERE id = 1',
                    (standby_local,)
                )

            # registar o arduino
            cur.execute(
                'INSERT INTO "TAM_Android".devices '
                '(mac, name, ip, firmware, last_seen) '
                'VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP) '
                'ON CONFLICT (mac) DO UPDATE '
                'SET ip = COALESCE(EXCLUDED.ip, "TAM_Android".devices.ip), '
                'name = COALESCE(EXCLUDED.name, "TAM_Android".devices.name), '
                'firmware = COALESCE(EXCLUDED.firmware, "TAM_Android".devices.firmware), '
                'last_seen = CURRENT_TIMESTAMP '
                'RETURNING id',
                (mac, 'Smart Climate Mokxi', ip, 'Mokxi')
            )

            device_id = cur.fetchone()[0]

            # guardar a temperatura
            cur.execute(
                'INSERT INTO "TAM_Android".readings '
                '(device_id, sensor, value) '
                'VALUES (%s, %s, %s) '
                'RETURNING sensor, value, criado_em',
                (device_id, str(sensor), str(value))
            )

            leitura = cur.fetchone()

            # ir buscar os comandos da app
            cur.execute(
                'SELECT fan_on, fan_speed, led_1, led_2, mode, '
                'temp_on, temp_off, updated_at, standby '
                'FROM "TAM_Android".actuator_state WHERE id = 1'
            )

            estado = cur.fetchone()

    if estado is None:
        raise ValueError("Estado dos atuadores não encontrado.")

    reading = {
        "sensor": leitura[0],
        "value": leitura[1],
        "criado_em": leitura[2].strftime("%d/%m/%Y %H:%M:%S")
    }

    actuators = {
        "fan_on": estado[0],
        "fan_speed": estado[1],
        "led_1": estado[2],
        "led_2": estado[3],
        "mode": estado[4],
        "temp_on": float(estado[5]),
        "temp_off": float(estado[6]),
        "updated_at": estado[7].strftime("%d/%m/%Y %H:%M:%S"),
        "standby": estado[8]
    }

    return reading, actuators

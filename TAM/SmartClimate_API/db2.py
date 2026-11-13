import os
import psycopg2
from contextlib import contextmanager

# Reexporta as funções de atuadores de db.py — o estado é o mesmo (id = 1)
# para a app Android e para o Arduino; não há duplicação de lógica.
from db import get_actuator_state, update_actuator_state


# Liga à base de dados e fecha sempre a ligação no final.
@contextmanager
def get_connection():
    conn = psycopg2.connect(
        host=os.environ.get("DATABASE_HOST"),
        port=int(os.environ.get("DATABASE_PORT", "5432")),
        database=os.environ.get("DATABASE_NAME"),
        user=os.environ.get("DATABASE_USER"),
        password=os.environ.get("PASSWORD")
    )

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ==========================
# Dispositivos (Arduino)
# ==========================

def device_exists(mac):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT COUNT(*) FROM "TAM_Android".devices WHERE mac = %s',
                (mac,)
            )
            count = cur.fetchone()[0]
    return count > 0


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


# ==========================
# Leituras por dispositivo (Arduino)
# ==========================

def add_reading_by_device(mac, sensor, value):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM "TAM_Android".devices WHERE mac = %s',
                (mac,)
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(
                    "O dispositivo %s não está registado." % mac
                )
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
                raise ValueError(
                    "O dispositivo %s não está registado." % mac
                )
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


def update_actuator_outputs(fan_on, led_1, led_2):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE "TAM_Android".actuator_state '
                'SET fan_on = %s, led_1 = %s, led_2 = %s, '
                'updated_at = CURRENT_TIMESTAMP '
                'WHERE id = 1',
                (fan_on, led_1, led_2)
            )

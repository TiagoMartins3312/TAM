import os
import psycopg2
from contextlib import contextmanager


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
# Utilizadores e autenticação
# ==========================

def user_exists(user):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT COUNT(*) FROM "TAM_Android".users WHERE username = %s',
                (user["username"],)
            )
            count = cur.fetchone()[0]
    return count > 0


def login(username, password):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, username FROM "TAM_Android".users '
                'WHERE username = %s AND password = crypt(%s, password)',
                (username, password)
            )
            user_tuple = cur.fetchone()

    if user_tuple is None:
        return None

    return {
        "id": user_tuple[0],
        "username": user_tuple[1]
    }


def get_user(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, username FROM "TAM_Android".users WHERE id = %s',
                (user_id,)
            )
            user_tuple = cur.fetchone()

    if user_tuple is None:
        return None

    return {
        "id": user_tuple[0],
        "username": user_tuple[1]
    }


def add_user(user):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "TAM_Android".users (username, password) '
                "VALUES (%s, crypt(%s, gen_salt('bf'))) RETURNING id, username",
                (user["username"], user["password"])
            )
            user_tuple = cur.fetchone()

    return {
        "id": user_tuple[0],
        "username": user_tuple[1]
    }


# ==========================
# Leituras de temperatura
# ==========================

def add_reading(sensor, value):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "TAM_Android".readings (sensor, value) '
                'VALUES (%s, %s) RETURNING sensor, value, criado_em',
                (str(sensor), str(value))
            )
            reading_tuple = cur.fetchone()

    return {
        "sensor": reading_tuple[0],
        "value": reading_tuple[1],
        "criado_em": reading_tuple[2].strftime("%d/%m/%Y %H:%M:%S")
    }


def get_all_readings():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT sensor, value, criado_em '
                'FROM "TAM_Android".readings '
                'ORDER BY criado_em DESC LIMIT 100'
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


# ==========================
# Estado da ventoinha e LEDs
# ==========================


def get_actuator_state():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT fan_on, fan_speed, led_1, led_2, mode, '
                'temp_on, temp_off, updated_at '
                'FROM "TAM_Android".actuator_state WHERE id = 1'
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "fan_on": row[0],
        "fan_speed": row[1],
        "led_1": row[2],
        "led_2": row[3],
        "mode": row[4],
        "temp_on": float(row[5]),
        "temp_off": float(row[6]),
        "updated_at": row[7].strftime("%d/%m/%Y %H:%M:%S")
    }


def update_actuator_state(data):
    current = get_actuator_state()

    if current is None:
        raise ValueError(
            "O estado inicial dos atuadores não existe na base de dados."
        )

    fan_on = data.get("fan_on", current["fan_on"])
    fan_speed = int(data.get("fan_speed", current["fan_speed"]))
    led_1 = data.get("led_1", current["led_1"])
    led_2 = data.get("led_2", current["led_2"])
    mode = data.get("mode", current["mode"])
    temp_on = float(data.get("temp_on", current["temp_on"]))
    temp_off = float(data.get("temp_off", current["temp_off"]))

    if not 0 <= fan_speed <= 100:
        raise ValueError("A velocidade tem de estar entre 0 e 100.")

    if mode not in ("automatico", "manual", "noturno"):
        raise ValueError(
            "O modo tem de ser automatico, manual ou noturno."
        )

    if temp_on <= temp_off:
        raise ValueError(
            "A temperatura de ativação tem de ser superior à de desativação."
        )

    if mode == "noturno" or fan_speed == 0:
        fan_on = False

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE "TAM_Android".actuator_state '
                'SET fan_on = %s, fan_speed = %s, '
                'led_1 = %s, led_2 = %s, mode = %s, '
                'temp_on = %s, temp_off = %s, '
                'updated_at = CURRENT_TIMESTAMP '
                'WHERE id = 1',
                (
                    fan_on, fan_speed, led_1, led_2,
                    mode, temp_on, temp_off
                )
            )

    return get_actuator_state()
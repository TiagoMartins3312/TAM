import os
import psycopg2
from contextlib import contextmanager


# abre a ligação à base de dados e fecha sempre no fim
# (sem isto a bd da escola dava erro de demasiadas ligações)
# os.environ.get vai buscar variáveis de ambiente a outro ficheiro, para evitar hardcoding.
@contextmanager
def get_connection():
    conn = psycopg2.connect(
        host=os.environ.get("DATABASE_HOST"),
        port=int(os.environ.get("DATABASE_PORT", "5432")),
        database=os.environ.get("DATABASE_NAME"),
        user=os.environ.get("DATABASE_USER"),
        password=os.environ.get("PASSWORD")
    )
# Cria um novo objeto capaz de conectar com a base de dados.
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ver se o username já existe
def user_exists(user):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT COUNT(*) FROM "TAM_Android".users WHERE username = %s',
                (user["username"],)
            )
            count = cur.fetchone()[0]
    return count > 0


# login, o crypt compara a password com a que está encriptada na bd
# O cursor cria um canal capaz de executar e devolver os resultados de uma querry
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


# ir buscar um utilizador pelo id
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


# criar utilizador com a password encriptada
# gen_salt cria mais uma camada de interpretação, garante que seja impossivel imediatamente ver
# que duas palavras passes iguais (em texto normal) sejam perceptiveis.
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


# últimas 100 temperaturas, a mais recente vem primeiro
def get_all_readings():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT sensor, value, criado_em '
                'FROM "TAM_Android".readings '
                'ORDER BY criado_em DESC LIMIT 100'
            )
            rows = cur.fetchall()
# A função strftime serve para tornar uma timestamp em algo perceptivel para o ver do utilizador
    readings = []
    for row in rows:
        readings.append({
            "sensor": row[0],
            "value": row[1],
            "criado_em": row[2].strftime("%d/%m/%Y %H:%M:%S")
        })
    return readings


# comandos que a app pediu (só existe uma linha na tabela, por isso id = 1).
# Em futuras versões será possivel uma atualização para permitir a manipulação de mais dispositivos arduino.
def get_actuator_state():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT fan_on, fan_speed, led_1, led_2, mode, '
                'temp_on, temp_off, updated_at, standby '
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
        "updated_at": row[7].strftime("%d/%m/%Y %H:%M:%S"),
        "standby": row[8]
    }


# estado para mostrar na app: o comando e o que o arduino está mesmo a fazer
def get_actuator_display_state():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT fan_on, fan_actual_on, fan_speed, '
                'led_1_actual, led_2_actual, mode, temp_on, temp_off, '
                'updated_at, standby '
                'FROM "TAM_Android".actuator_state WHERE id = 1'
            )
            row = cur.fetchone()

    if row is None:
        return None

    return {
        # fan_on é o que a app pediu, fan_actual_on é o que o arduino diz
        "fan_on": row[0],
        "fan_actual_on": row[1],
        "fan_speed": row[2],
        "led_1": row[3],
        "led_2": row[4],
        "mode": row[5],
        "temp_on": float(row[6]),
        "temp_off": float(row[7]),
        "updated_at": row[8].strftime("%d/%m/%Y %H:%M:%S"),
        "standby": row[9]
    }



# guardar os comandos que vêm da app
def update_actuator_state(data):
    current = get_actuator_state()

    if current is None:
        raise ValueError("O estado inicial dos atuadores não existe na base de dados.")

    # se um campo não vier no pedido fica o valor que já estava
    fan_on = data.get("fan_on", current["fan_on"])
    standby = data.get("standby", current["standby"])
    led_1 = data.get("led_1", current["led_1"])
    led_2 = data.get("led_2", current["led_2"])
    mode = data.get("mode", current["mode"])
    temp_on = float(data.get("temp_on", current["temp_on"]))
    temp_off = float(data.get("temp_off", current["temp_off"]))

    # a velocidade não é usada, fica sempre 50
    fan_speed = 50

    # não há modo manual, por isso passa a automático
    if mode == "manual":
        mode = "automatico"

    if mode not in ("automatico", "noturno"):
        raise ValueError("O modo tem de ser automatico ou noturno.")

    if temp_on <= temp_off:
        raise ValueError("A temperatura de ativação tem de ser superior à de desativação.")

    # à noite a ventoinha fica desligada
    if mode == "noturno":
        fan_on = False
    # Atualiza os valores do actuator
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE "TAM_Android".actuator_state '
                'SET fan_on = %s, fan_speed = %s, '
                'led_1 = %s, led_2 = %s, mode = %s, '
                'temp_on = %s, temp_off = %s, standby = %s, '
                'updated_at = CURRENT_TIMESTAMP '
                'WHERE id = 1',
                (
                    fan_on, fan_speed, led_1, led_2,
                    mode, temp_on, temp_off, standby
                )
            )

    return get_actuator_display_state()

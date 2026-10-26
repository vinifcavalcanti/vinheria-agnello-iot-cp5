from fastapi import FastAPI, HTTPException
import requests
from io import BytesIO
from datetime import datetime, timedelta, timezone
from fastapi.responses import Response
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.dates import AutoDateLocator, DateFormatter
import json
import paho.mqtt.client as mqtt
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from threading import Event, Thread, Lock
from typing import Literal
from pathlib import Path
from pydantic import ConfigDict, model_validator
from tempfile import NamedTemporaryFile
from pydantic import ValidationError

app = FastAPI(title="API CP5 — Monitoramento e Controle")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

IP_SERVIDOR = "100.53.117.116"
ORION = f"http://{IP_SERVIDOR}:1026"

CABECALHOS = {
    "fiware-service": "smart",
    "fiware-servicepath": "/"
}


@app.get("/")
def inicio():
    return {"mensagem": "API do CP5 funcionando!"}


@app.get("/sensores")
def consultar_sensores():
    url = f"{ORION}/v2/entities/urn:ngsi-ld:Environment:001"

    try:
        resposta = requests.get(
            url,
            headers=CABECALHOS,
            params={"type": "Environment"},
            timeout=10
        )
        resposta.raise_for_status()
        dados = resposta.json()

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="O FIWARE demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao consultar o FIWARE. Confira o servidor e o IP."
        )

    return {
        "temperatura": dados["temperature"]["value"],
        "umidade": dados["humidity"]["value"],
        "luminosidade_bruta": dados["luminosityRaw"]["value"],
        "ultima_atualizacao": dados["TimeInstant"]["value"]
    }

@app.get("/atuador")
def consultar_atuador():
    url = f"{ORION}/v2/entities/urn:ngsi-ld:Actuator:001"

    try:
        resposta = requests.get(
            url,
            headers=CABECALHOS,
            params={"type": "Actuator"},
            timeout=10
        )
        resposta.raise_for_status()
        dados = resposta.json()

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="O FIWARE demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao consultar o atuador no FIWARE."
        )

    return {
        "brilho": dados["brightness"]["value"],
        "ultima_atualizacao": dados["TimeInstant"]["value"]
    }

@app.get("/historico/{sensor}")
def consultar_historico(sensor: str):
    configuracoes = {
        "temperatura": (
            "Environment", "urn:ngsi-ld:Environment:001", "temperature"
        ),
        "umidade": (
            "Environment", "urn:ngsi-ld:Environment:001", "humidity"
        ),
        "luminosidade": (
            "Environment", "urn:ngsi-ld:Environment:001", "luminosityRaw"
        ),
        "brilho": (
            "Actuator", "urn:ngsi-ld:Actuator:001", "brightness"
        ),
    }

    if sensor not in configuracoes:
        raise HTTPException(
            status_code=400,
            detail="Use temperatura, umidade, luminosidade ou brilho."
        )

    tipo, entidade, atributo = configuracoes[sensor]

    url = (
        f"http://{IP_SERVIDOR}:8666/STH/v1"
        f"/contextEntities/type/{tipo}"
        f"/id/{entidade}"
        f"/attributes/{atributo}"
    )

    try:
        resposta = requests.get(
            url,
            headers=CABECALHOS,
            params={"lastN": 30},
            timeout=10
        )
        resposta.raise_for_status()
        dados = resposta.json()

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="O historico demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao consultar o STH-Comet."
        )

    registros = (
        dados["contextResponses"][0]
        ["contextElement"]["attributes"][0]["values"]
    )

    return [
        {
            "data": registro["recvTime"],
            "valor": registro["attrValue"]
        }
        for registro in registros
    ]

def luz_percentual(adc: float) -> int:
    # Indice relativo para exibicao (nao e lux). ADC maior = menos luz:
    # 0 ADC -> 100% (muito claro), 4095 ADC -> 0% (escuro).
    porcentagem = round((4095 - adc) * 100 / 4095)
    return max(0, min(100, porcentagem))


@app.get("/graficos/{sensor}")
def gerar_grafico(sensor: str):
    configuracoes = {
        "temperatura": ("Historico de temperatura", "Temperatura (°C)", "#2563eb"),
        "umidade": ("Historico de umidade", "Umidade (%)", "#16a34a"),
        "luminosidade": ("Historico de luminosidade", "Luminosidade relativa (%)", "#d97706"),
        "brilho": ("Historico do atuador", "Brilho do LED (%)", "#9333ea"),
    }

    if sensor not in configuracoes:
        raise HTTPException(
            status_code=400,
            detail="Use temperatura, umidade, luminosidade ou brilho."
        )

    registros = consultar_historico(sensor)

    if not registros:
        raise HTTPException(
            status_code=404,
            detail="Ainda nao existem leituras para o grafico."
        )

    titulo, unidade, cor = configuracoes[sensor]
    horario_brasilia = timezone(timedelta(hours=-3))

    datas = [
        datetime.fromisoformat(
            registro["data"].replace("Z", "+00:00")
        ).astimezone(horario_brasilia)
        for registro in registros
    ]

    valores = [float(registro["valor"]) for registro in registros]

    # Somente o grafico mostra a luminosidade em %; dados e rotas seguem em ADC.
    if sensor == "luminosidade":
        valores = [luz_percentual(valor) for valor in valores]

    figura = Figure(figsize=(9, 4), layout="constrained")
    FigureCanvasAgg(figura)
    eixo = figura.subplots()

    if sensor == "brilho":
        eixo.step(
            datas, valores,
            where="post",
            color=cor,
            marker="o"
        )
        eixo.set_ylim(-5, 105)
    else:
        eixo.plot(datas, valores, color=cor, marker="o")
        if sensor == "luminosidade":
            eixo.set_ylim(-5, 105)
    eixo.set_title(titulo)
    eixo.set_xlabel("Horario de Brasilia")
    eixo.set_ylabel(unidade)
    eixo.grid(True, alpha=0.3)

    eixo.xaxis.set_major_locator(
        AutoDateLocator(minticks=3, maxticks=6)
    )
    eixo.xaxis.set_major_formatter(
        DateFormatter("%H:%M:%S", tz=horario_brasilia)
    )

    with BytesIO() as imagem:
        figura.savefig(imagem, format="png", dpi=120)

        return Response(
            content=imagem.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": "no-store"}
        )

@app.get("/dispositivos")
def listar_dispositivos():
    url = f"http://{IP_SERVIDOR}:4041/iot/devices"

    try:
        resposta = requests.get(
            url,
            headers=CABECALHOS,
            timeout=10
        )
        resposta.raise_for_status()
        return resposta.json()

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="O IoT Agent demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao consultar os dispositivos no IoT Agent."
        )

@app.post("/dispositivos", status_code=201)
def cadastrar_dispositivo(dados: dict):
    url = f"http://{IP_SERVIDOR}:4041/iot/devices"

    try:
        resposta = requests.post(
            url,
            headers=CABECALHOS,
            json=dados,
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="O cadastro demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao IoT Agent."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {"mensagem": "Dispositivo cadastrado com sucesso!"}

@app.delete("/dispositivos/{device_id}")
def excluir_dispositivo(device_id: str):
    url = f"http://{IP_SERVIDOR}:4041/iot/devices/{device_id}"

    try:
        resposta = requests.delete(
            url,
            headers=CABECALHOS,
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A exclusao demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao IoT Agent."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {
        "mensagem": "Dispositivo excluido com sucesso!",
        "device_id": device_id
    }

@app.get("/servicos")
def listar_servicos():
    url = f"http://{IP_SERVIDOR}:4041/iot/services"

    try:
        resposta = requests.get(
            url,
            headers=CABECALHOS,
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A consulta dos servicos demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao IoT Agent."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return resposta.json()

@app.post("/servicos", status_code=201)
def cadastrar_servico(dados: dict):
    url = f"http://{IP_SERVIDOR}:4041/iot/services"

    try:
        resposta = requests.post(
            url,
            headers=CABECALHOS,
            json=dados,
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="O cadastro do servico demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao IoT Agent."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {"mensagem": "Servico cadastrado com sucesso!"}

@app.delete("/servicos")
def excluir_servico(apikey: str, resource: str = ""):
    url = f"http://{IP_SERVIDOR}:4041/iot/services"

    try:
        resposta = requests.delete(
            url,
            headers=CABECALHOS,
            params={
                "apikey": apikey,
                "resource": resource
            },
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A exclusao do servico demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao IoT Agent."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {
        "mensagem": "Servico excluido com sucesso!",
        "apikey": apikey
    }

@app.get("/assinaturas")
def listar_assinaturas():
    url = f"{ORION}/v2/subscriptions"

    try:
        resposta = requests.get(
            url,
            headers=CABECALHOS,
            params={"limit": 100},
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A consulta das assinaturas demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return resposta.json()

@app.post("/assinaturas", status_code=201)
def cadastrar_assinatura(dados: dict):
    url = f"{ORION}/v2/subscriptions"

    try:
        resposta = requests.post(
            url,
            headers=CABECALHOS,
            json=dados,
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="O cadastro da assinatura demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    localizacao = resposta.headers.get("Location", "")

    return {
        "mensagem": "Assinatura cadastrada com sucesso!",
        "id": localizacao.rstrip("/").split("/")[-1]
    }

@app.patch("/assinaturas/{assinatura_id}")
def editar_assinatura(assinatura_id: str, dados: dict):
    url = f"{ORION}/v2/subscriptions/{assinatura_id}"

    try:
        resposta = requests.patch(
            url,
            headers=CABECALHOS,
            json=dados,
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A edicao da assinatura demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {
        "mensagem": "Assinatura atualizada com sucesso!",
        "id": assinatura_id
    }

@app.delete("/assinaturas/{assinatura_id}")
def excluir_assinatura(assinatura_id: str):
    url = f"{ORION}/v2/subscriptions/{assinatura_id}"

    try:
        resposta = requests.delete(
            url,
            headers=CABECALHOS,
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A exclusao da assinatura demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {
        "mensagem": "Assinatura excluida com sucesso!",
        "id": assinatura_id
    }

@app.get("/entidades")
def listar_entidades():
    url = f"{ORION}/v2/entities"

    try:
        resposta = requests.get(
            url,
            headers=CABECALHOS,
            params={"limit": 100},
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A consulta das entidades demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return resposta.json()

@app.post("/entidades", status_code=201)
def cadastrar_entidade(dados: dict):
    url = f"{ORION}/v2/entities"

    try:
        resposta = requests.post(
            url,
            headers=CABECALHOS,
            json=dados,
            timeout=10
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="O cadastro da entidade demorou para responder."
        )

    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {
        "mensagem": "Entidade cadastrada com sucesso!",
        "id": dados.get("id")
    }

@app.patch("/entidades/{entidade_id}/attrs")
def atualizar_entidade(entidade_id: str, dados: dict):
    url = f"{ORION}/v2/entities/{entidade_id}/attrs"

    try:
        resposta = requests.patch(
            url,
            headers=CABECALHOS,
            json=dados,
            timeout=10
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A atualização da entidade demorou para responder."
        )
    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {
        "mensagem": "Entidade atualizada com sucesso!",
        "id": entidade_id
    }

@app.delete("/entidades/{entidade_id}")
def excluir_entidade(entidade_id: str):
    url = f"{ORION}/v2/entities/{entidade_id}"

    try:
        resposta = requests.delete(
            url,
            headers=CABECALHOS,
            timeout=10
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A exclusão da entidade demorou para responder."
        )
    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {
        "mensagem": "Entidade excluída com sucesso!",
        "id": entidade_id
    }

@app.get("/registros")
def listar_registros():
    url = f"{ORION}/v2/registrations"

    try:
        resposta = requests.get(
            url,
            headers=CABECALHOS,
            params={"limit": 100},
            timeout=10
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A consulta dos registros demorou para responder."
        )
    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return resposta.json()

@app.post("/registros", status_code=201)
def cadastrar_registro(dados: dict):
    url = f"{ORION}/v2/registrations"

    try:
        resposta = requests.post(
            url,
            headers=CABECALHOS,
            json=dados,
            timeout=10
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="O cadastro do registro demorou para responder."
        )
    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    localizacao = resposta.headers.get("Location", "")
    registro_id = localizacao.rstrip("/").split("/")[-1]

    return {
        "mensagem": "Registro cadastrado com sucesso!",
        "id": registro_id
    }

@app.delete("/registros/{registro_id}")
def excluir_registro(registro_id: str):
    url = f"{ORION}/v2/registrations/{registro_id}"

    try:
        resposta = requests.delete(
            url,
            headers=CABECALHOS,
            timeout=10
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A exclusão do registro demorou para responder."
        )
    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao Orion."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {
        "mensagem": "Registro excluído com sucesso!",
        "id": registro_id
    }

@app.get("/dispositivos/{device_id}")
def consultar_dispositivo(device_id: str):
    url = f"http://{IP_SERVIDOR}:4041/iot/devices/{device_id}"

    try:
        resposta = requests.get(
            url,
            headers=CABECALHOS,
            timeout=10
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A consulta do dispositivo demorou para responder."
        )
    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao IoT Agent."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return resposta.json()

@app.put("/dispositivos/{device_id}")
def atualizar_dispositivo(device_id: str, dados: dict):
    url = f"http://{IP_SERVIDOR}:4041/iot/devices/{device_id}"

    try:
        resposta = requests.put(
            url,
            headers=CABECALHOS,
            json=dados,
            timeout=10
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A atualização do dispositivo demorou para responder."
        )
    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao IoT Agent."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {
        "mensagem": "Dispositivo atualizado com sucesso!",
        "device_id": device_id
    }

@app.put("/servicos")
def atualizar_servico(dados: dict, apikey: str, resource: str = ""):
    url = f"http://{IP_SERVIDOR}:4041/iot/services"

    try:
        resposta = requests.put(
            url,
            headers=CABECALHOS,
            params={"apikey": apikey, "resource": resource},
            json=dados,
            timeout=10
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="A atualização do serviço demorou para responder."
        )
    except requests.exceptions.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Falha ao conectar ao IoT Agent."
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=resposta.status_code,
            detail=resposta.text
        )

    return {
        "mensagem": "Serviço atualizado com sucesso!",
        "apikey": apikey
    }

TOPICO_CONTROLE = "cp5/agnello-8ea14fa3/lampada/controle"


class ComandoBrilho(BaseModel):
    brilho: int = Field(strict=True, ge=0, le=100)


def enviar_controle_mqtt(
    comando: dict,
    topico: str = TOPICO_CONTROLE,
    retain: bool = False
):
    cliente_mqtt = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    cliente_mqtt.connect_timeout = 5

    try:
        cliente_mqtt.connect(IP_SERVIDOR, 1883, keepalive=60)
        cliente_mqtt.loop_start()

        envio = cliente_mqtt.publish(
            topico,
            payload=json.dumps(comando),
            qos=1,
            retain=retain
        )

        envio.wait_for_publish(timeout=5)

        if not envio.is_published():
            raise HTTPException(
                status_code=504,
                detail="O servidor MQTT não confirmou o envio."
            )

    except (OSError, RuntimeError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="Falha ao enviar o comando pelo MQTT."
        )

    finally:
        cliente_mqtt.disconnect()
        cliente_mqtt.loop_stop()


@app.post("/atuador/manual", status_code=202)
def controlar_brilho_manual(dados: ComandoBrilho):
    comando = {
        "modo": "manual",
        "brilho": dados.brilho
    }

    enviar_controle_mqtt(comando)

    return {
        "mensagem": "Comando enviado ao servidor MQTT.",
        "modo_solicitado": "manual",
        "brilho_solicitado": dados.brilho
    }

@app.post("/atuador/automatico", status_code=202)
def ativar_modo_automatico():
    enviar_controle_mqtt({"modo": "automatico"})

    return {
        "mensagem": "Comando enviado ao servidor MQTT.",
        "modo_solicitado": "automatico"
    }

TOPICO_CONTROLE_ESTADO = (
    "cp5/agnello-8ea14fa3/lampada/controle/estado"
)

# Decisões que o atuador mostra no LCD (atuação simbólica).
ESTADOS_AMBIENTE = {
    "temperatura": {"AQUECER", "RESFRIAR", "NORMAL"},
    "umidade": {"UMIDIFICAR", "DESUMIDIFICAR", "NORMAL"},
    "luminosidade": {"AUMENTAR LUZ", "DIMINUIR LUZ", "LUZ NORMAL"}
}
ESTADOS_SEM_DECISAO = {"AGUARDANDO", "DADOS ANTIGOS", "DESATIVADO"}


def validar_ambiente(ambiente):
    # Campo opcional: firmwares antigos respondem sem ele.
    if not isinstance(ambiente, dict):
        return None

    validado = {}

    for campo, permitidos in ESTADOS_AMBIENTE.items():
        valor = ambiente.get(campo)
        if valor not in permitidos and valor not in ESTADOS_SEM_DECISAO:
            return None
        validado[campo] = valor

    if type(ambiente.get("led_atuacao")) is not bool:
        return None
    if ambiente.get("limites") not in ("sincronizados", "padrao"):
        return None

    validado["led_atuacao"] = ambiente["led_atuacao"]
    validado["limites"] = ambiente["limites"]
    return validado


# Ultimo estado confirmado pelo ESP32 Atuador
ultimo_estado_atuador = None
lock_estado_atuador = Lock()



@app.get("/atuador/estado")

def consultar_estado_controle():
    global ultimo_estado_atuador

    resposta_recebida = Event()
    resultado = {}

    cliente_consulta = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )

    def estado_em_cache():
        with lock_estado_atuador:
            if ultimo_estado_atuador is None:
                return None
            return dict(ultimo_estado_atuador)

    def resposta_indisponivel(detalhe, status_code):
        estado = estado_em_cache()

        if estado is not None:
            estado["desatualizado"] = True
            return estado

        raise HTTPException(
            status_code=status_code,
            detail=detalhe
        )

    def ao_conectar(cliente, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            resultado["erro"] = "O servidor MQTT recusou a conexão."
            resposta_recebida.set()
            return

        cliente.subscribe(TOPICO_CONTROLE_ESTADO, qos=1)

    def ao_assinar(cliente, userdata, mid, reason_codes, properties):
        if any(codigo.is_failure for codigo in reason_codes):
            resultado["erro"] = "Não foi possível assinar o tópico de estado."
            resposta_recebida.set()
            return

        cliente.publish(
            TOPICO_CONTROLE,
            payload=json.dumps({"modo": "consultar"}),
            qos=1,
            retain=False
        )

    def ao_receber(cliente, userdata, mensagem):
        if mensagem.retain:
            return

        try:
            dados = json.loads(mensagem.payload.decode())

            if not isinstance(dados, dict):
                return

            modo = dados.get("modo")
            brilho = dados.get("brilho")

            if modo not in ("manual", "automatico"):
                return

            if type(brilho) is not int or not 0 <= brilho <= 100:
                return

            estado = {
                "modo": modo,
                "brilho": brilho,
                "recebido_em": datetime.now(timezone.utc).isoformat()
            }

            ambiente = validar_ambiente(dados.get("ambiente"))
            if ambiente is not None:
                estado["ambiente"] = ambiente

            resultado["estado"] = estado
            resposta_recebida.set()

        except (ValueError, UnicodeError):
            return

    cliente_consulta.on_connect = ao_conectar
    cliente_consulta.on_subscribe = ao_assinar
    cliente_consulta.on_message = ao_receber

    try:
        cliente_consulta.connect(IP_SERVIDOR, 1883, keepalive=60)
        cliente_consulta.loop_start()

        if not resposta_recebida.wait(timeout=6):
            return resposta_indisponivel(
                "Não chegou uma resposta do atuador. Confira o Wokwi.",
                504
            )

        if "erro" in resultado:
            return resposta_indisponivel(resultado["erro"], 502)

        estado = resultado["estado"]

        with lock_estado_atuador:
            ultimo_estado_atuador = dict(estado)

        estado["desatualizado"] = False
        return estado

    except (OSError, RuntimeError, ValueError):
        return resposta_indisponivel(
            "Falha ao consultar o estado pelo MQTT.",
            502
        )

    finally:
        cliente_consulta.disconnect()
        cliente_consulta.loop_stop()


TOPICO_ALERTAS = "cp5/agnello-8ea14fa3/monitor/alertas"


class ComandoAlertas(BaseModel):
    alertas: list[
        Literal["temperatura", "umidade", "luminosidade"]
    ] = Field(max_length=3)


@app.post("/monitor/alertas", status_code=202)
def enviar_alertas_monitor(dados: ComandoAlertas):
    tipos = list(dict.fromkeys(dados.alertas))

    enviar_controle_mqtt(
        {"alertas": tipos},
        topico=TOPICO_ALERTAS
    )

    return {
        "mensagem": "Comando enviado ao servidor MQTT.",
        "alertas_solicitados": tipos
    }

# Localiza o arquivo na mesma pasta deste main.py.
ARQUIVO_LIMITES = Path(__file__).resolve().parent / "limites.json"


@app.get("/limites")
def consultar_limites():
    try:
        with ARQUIVO_LIMITES.open("r", encoding="utf-8") as arquivo:
            return json.load(arquivo)

    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="O arquivo limites.json não foi encontrado."
        )

    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=500,
            detail="O arquivo limites.json está inválido."
        )

    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Não foi possível ler o arquivo de limites."
        )

class FaixaLimite(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        allow_inf_nan=False
    )

    ativo: bool
    minimo: float
    maximo: float

    @model_validator(mode="after")
    def validar_ordem(self):
        if self.minimo >= self.maximo:
            raise ValueError(
                "O mínimo precisa ser menor que o máximo."
            )
        return self


class FaixaUmidade(FaixaLimite):
    minimo: float = Field(ge=0, le=100)
    maximo: float = Field(ge=0, le=100)


class FaixaLuminosidade(FaixaLimite):
    minimo: int = Field(ge=0, le=4095)
    maximo: int = Field(ge=0, le=4095)


class ConfiguracaoLimites(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperatura: FaixaLimite
    umidade: FaixaUmidade
    luminosidade_bruta: FaixaLuminosidade


# Os ESP32 assinam este tópico. Com retain, um ESP que se reconecta
# recebe imediatamente a configuração atual.
TOPICO_LIMITES = "cp5/agnello-8ea14fa3/config/limites"


def publicar_limites(limites: dict) -> bool:
    try:
        enviar_controle_mqtt(limites, topico=TOPICO_LIMITES, retain=True)
        return True
    except HTTPException:
        return False


def publicar_limites_salvos():
    try:
        limites = ConfiguracaoLimites.model_validate(consultar_limites())
    except (HTTPException, ValidationError):
        print("[limites] limites.json inválido; nada foi publicado.")
        return

    if publicar_limites(limites.model_dump()):
        print("[limites] Configuração publicada no MQTT (retain).")
    else:
        print("[limites] Broker MQTT indisponível; os ESPs usam a última configuração retida ou o padrão do firmware.")


@app.on_event("startup")
def sincronizar_limites_ao_iniciar():
    # Em segundo plano: um broker fora do ar não atrasa a API.
    Thread(target=publicar_limites_salvos, daemon=True).start()


@app.put("/limites")
def atualizar_limites(dados: ConfiguracaoLimites):
    temporario = None

    try:
        # Prepara o novo arquivo antes de substituir o anterior.
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=ARQUIVO_LIMITES.parent,
            suffix=".tmp",
            delete=False
        ) as arquivo:
            temporario = Path(arquivo.name)
            json.dump(
                dados.model_dump(),
                arquivo,
                ensure_ascii=False,
                indent=2
            )

        temporario.replace(ARQUIVO_LIMITES)

    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Não foi possível salvar os limites."
        )

    finally:
        if temporario is not None:
            try:
                temporario.unlink(missing_ok=True)
            except OSError:
                pass

    sincronizado = publicar_limites(dados.model_dump())

    return {
        "mensagem": (
            "Limites atualizados e enviados aos ESPs."
            if sincronizado
            else "Limites salvos, mas o envio pelo MQTT falhou."
        ),
        "limites": dados.model_dump(),
        "sincronizado": sincronizado
    }

@app.get("/alertas")
def consultar_alertas():
    leituras = consultar_sensores()

    try:
        limites = ConfiguracaoLimites.model_validate(
            consultar_limites()
        )
    except ValidationError:
        raise HTTPException(
            status_code=500,
            detail="A configuração do limites.json está inválida."
        )

    sensores = [
        ("temperatura", "temperatura", limites.temperatura),
        ("umidade", "umidade", limites.umidade),
        (
            "luminosidade_bruta",
            "luminosidade",
            limites.luminosidade_bruta
        )
    ]

    alertas = []
    detalhes = {}

    for campo, nome_alerta, faixa in sensores:
        valor = leituras[campo]

        fora_da_faixa = (
            valor < faixa.minimo or valor > faixa.maximo
        )

        if not faixa.ativo:
            estado = "desativado"
        elif fora_da_faixa:
            estado = "fora_da_faixa"
            alertas.append(nome_alerta)
        else:
            estado = "normal"

        detalhes[campo] = {
            "valor": valor,
            "minimo": faixa.minimo,
            "maximo": faixa.maximo,
            "estado": estado
        }

    return {
        "alertas": alertas,
        "sensores": detalhes,
        "ultima_atualizacao": leituras["ultima_atualizacao"]
    }


@app.get("/status")
def consultar_status():
    servicos = {}

    try:
        resposta = requests.get(f"{ORION}/version", timeout=4)
        resposta.raise_for_status()
        servicos["fiware"] = {"ok": True, "detalhe": "Orion respondeu."}
    except requests.exceptions.RequestException:
        servicos["fiware"] = {
            "ok": False,
            "detalhe": "Orion não respondeu. Confira o IP, a EC2 ou o filtro da rede."
        }

    cliente_teste = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    cliente_teste.connect_timeout = 4

    try:
        cliente_teste.connect(IP_SERVIDOR, 1883, keepalive=10)
        cliente_teste.disconnect()
        servicos["mqtt"] = {"ok": True, "detalhe": "Broker aceitou a conexão."}
    except (OSError, ValueError):
        servicos["mqtt"] = {
            "ok": False,
            "detalhe": "Broker MQTT inacessível na porta 1883."
        }

    try:
        ConfiguracaoLimites.model_validate(consultar_limites())
        servicos["limites"] = {"ok": True, "detalhe": "limites.json válido."}
    except (HTTPException, ValidationError):
        servicos["limites"] = {
            "ok": False,
            "detalhe": "limites.json ausente ou inválido."
        }

    return {
        "servidor": IP_SERVIDOR,
        "servicos": servicos,
        "verificado_em": datetime.now(timezone.utc).isoformat()
    }

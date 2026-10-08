from machine import Pin, ADC, PWM
from umqtt.simple import MQTTClient
import dht
import network
import time
import json
from machine import I2C
from i2c_lcd import I2cLcd

# Inicializa o LCD 16x2 I2C
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
lcd = I2cLcd(i2c, 0x27, 2, 16)


# Estado das informacoes exibidas no LCD
temperatura_lcd = None
umidade_lcd = None
luminosidade_lcd = None
brilho_confirmado = None

# Alternancia automatica das telas
tela_atual = 0
ultima_troca_lcd = time.ticks_ms()
ultima_renderizacao_lcd = 0

lcd.clear()
lcd.move_to(0, 0)
lcd.putstr("AGNELLO CP5")
lcd.move_to(0, 1)
lcd.putstr("Iniciando...")






SERVIDOR = "34.228.116.107"

TOPICO = b"cp5/agnello-8ea14fa3/lampada"
TOPICO_ESTADO = b"cp5/agnello-8ea14fa3/lampada/estado"
TOPICO_DADOS = b"/ul/TEF/monitor001/attrs"
TOPICO_ALERTAS = b"cp5/agnello-8ea14fa3/monitor/alertas"

sensor = dht.DHT22(Pin(15))

ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)
ldr.width(ADC.WIDTH_12BIT)

led_alerta = Pin(2, Pin.OUT)
led_alerta.value(0)

buzzer = PWM(Pin(25), freq=1000)
buzzer.duty_u16(0)

# Cada anomalia tem um tom diferente.
TONS = {
    "temperatura": 1200,
    "umidade": 1800,
    "luminosidade": 2400
}

alertas_ativos = []
inicio_alerta = time.ticks_ms()


def atualizar_lcd():
    global tela_atual
    global ultima_troca_lcd
    global ultima_renderizacao_lcd

    agora = time.ticks_ms()

    # Alterna a tela a cada 3 segundos.
    if time.ticks_diff(agora, ultima_troca_lcd) >= 3000:
        tela_atual = (tela_atual + 1) % 2
        ultima_troca_lcd = agora

    # Evita reescrever o LCD a cada passagem do loop.
    if time.ticks_diff(agora, ultima_renderizacao_lcd) < 500:
        return

    ultima_renderizacao_lcd = agora

    if tela_atual == 0:
        linha1 = (
            "TEMP: {:.1f} C".format(temperatura_lcd)
            if temperatura_lcd is not None
            else "TEMP: --"
        )
        linha2 = (
            "UMID: {:.1f} %".format(umidade_lcd)
            if umidade_lcd is not None
            else "UMID: --"
        )
    else:
        linha1 = (
            "LDR: {} ADC".format(luminosidade_lcd)
            if luminosidade_lcd is not None
            else "LDR: --"
        )
        linha2 = (
            "LED: {}%".format(brilho_confirmado)
            if brilho_confirmado is not None
            else "LED: aguardando"
        )

    lcd.move_to(0, 0)
    lcd.putstr((linha1 + " " * 16)[:16])

    lcd.move_to(0, 1)
    lcd.putstr((linha2 + " " * 16)[:16])



def atualizar_alerta():
    if not alertas_ativos:
        led_alerta.value(0)
        buzzer.duty_u16(0)
        return

    decorrido = time.ticks_diff(
        time.ticks_ms(), inicio_alerta
    )

    # Pisca a cada 300 ms.
    led_alerta.value(1 if (decorrido // 300) % 2 == 0 else 0)

    # Alterna os tons quando existem várias anomalias.
    indice = (decorrido // 600) % len(alertas_ativos)
    tipo = alertas_ativos[indice]

    if decorrido % 600 < 300:
        buzzer.freq(TONS[tipo])
        buzzer.duty_u16(32768)
    else:
        buzzer.duty_u16(0)


def esperar_com_alerta(segundos):
    inicio = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), inicio) < segundos * 1000:
        atualizar_alerta()
        time.sleep(0.05)


def receber_mensagem(topico, mensagem):
    global alertas_ativos, inicio_alerta, brilho_confirmado

    if topico == TOPICO_ESTADO:
        try:
            valor = int(mensagem.decode())
            if 0 <= valor <= 100:
                brilho_confirmado = valor
        except ValueError:
            pass
        print("Atuador confirmou brilho de:", mensagem.decode(), "%")
        return

    if topico != TOPICO_ALERTAS:
        return

    try:
        comando = json.loads(mensagem.decode())

        if not isinstance(comando, dict):
            print("Comando de alerta precisa ser um objeto JSON.")
            return

        tipos = comando.get("alertas")

        if not isinstance(tipos, list):
            print("O campo alertas precisa ser uma lista.")
            return

        for tipo in tipos:
            if not isinstance(tipo, str) or tipo not in TONS:
                print("Tipo de alerta invalido:", tipo)
                return

        # Remove repetições e mantém a ordem dos tons.
        novos_alertas = [
            tipo for tipo in TONS if tipo in tipos
        ]

        # Comandos repetidos não reiniciam o ritmo do alerta.
        if novos_alertas != alertas_ativos:
            alertas_ativos = novos_alertas
            inicio_alerta = time.ticks_ms()

            if alertas_ativos:
                print("Alertas recebidos:", alertas_ativos)
            else:
                print("Alertas encerrados.")

        atualizar_alerta()

    except (ValueError, TypeError):
        print("Comando de alerta invalido:", mensagem)


wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("Wokwi-GUEST", "")

print("Conectando ao Wi-Fi...")
inicio = time.ticks_ms()

while not wifi.isconnected():
    if time.ticks_diff(time.ticks_ms(), inicio) > 20000:
        raise RuntimeError("Falha no Wi-Fi. Reinicie a simulacao.")
    time.sleep(0.2)

print("Wi-Fi conectado!")

cliente = MQTTClient(
    b"cp5-monitor-8ea14fa3",
    SERVIDOR,
    keepalive=60
)
cliente.set_callback(receber_mensagem)


def conectar_mqtt():
    while True:
        try:
            cliente.connect()
            cliente.subscribe(TOPICO_ESTADO)
            cliente.subscribe(TOPICO_ALERTAS)
            print("MQTT conectado! Escutando confirmacoes e alertas.")
            return

        except OSError:
            print("MQTT indisponivel. Tentando novamente...")
            try:
                cliente.disconnect()
            except OSError:
                pass
            esperar_com_alerta(2)


conectar_mqtt()

while True:
    atualizar_alerta()
    dados_sensor = None

    try:
        sensor.measure()
        temperatura = sensor.temperature()
        umidade = sensor.humidity()
        temperatura_lcd = temperatura
        umidade_lcd = umidade

        print("Temperatura:", temperatura, "°C")
        print("Umidade:", umidade, "%")

        dados_sensor = "t|{}|h|{}".format(
            temperatura, umidade
        ).encode()

    except OSError:
        print("Nao consegui ler o DHT22.")

    leitura = ldr.read()
    luminosidade_lcd = leitura
    print("Leitura do LDR:", leitura)

    if leitura > 2500:
        brilho = 100
        print("Pouca luz: aumentando a lampada.")
    elif leitura < 1000:
        brilho = 0
        print("Muita luz: apagando a lampada.")
    else:
        brilho = 50
        print("Luz intermediaria: lampada em 50%.")

    try:
        if dados_sensor is not None:
            cliente.publish(TOPICO_DADOS, dados_sensor)

        dados_luz = "l|" + str(leitura)
        cliente.publish(TOPICO_DADOS, dados_luz.encode())
        cliente.publish(TOPICO, str(brilho).encode())

        print("Leituras publicadas para o FIWARE.")
        print("Comando enviado:", brilho, "%")
        print("--------------------")

        # Continua recebendo comandos e atualizando o alerta
        # enquanto aguarda a próxima leitura.
        for _ in range(40):
            cliente.check_msg()
            atualizar_alerta()
            atualizar_lcd()
            time.sleep(0.05)

    except OSError:
        print("Conexao MQTT caiu. Tentando reconectar...")

        try:
            cliente.disconnect()
        except OSError:
            pass

        esperar_com_alerta(2)
        conectar_mqtt()
from machine import Pin, PWM, I2C
from umqtt.simple import MQTTClient
import network
import time
import json

from i2c_lcd import I2cLcd

# Inicializa o LCD 16x2 I2C
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
lcd = I2cLcd(i2c, 0x27, 2, 16)

# Teste inicial do LCD
lcd.clear()
lcd.move_to(0, 0)
lcd.putstr("AGNELLO CP5")
lcd.move_to(0, 1)
lcd.putstr("ESP32 ATUADOR")




SERVIDOR = "34.228.116.107"

# Comandos automaticos enviados pelo monitor
TOPICO = b"cp5/agnello-8ea14fa3/lampada"

# Confirmacao de brilho para o monitor
TOPICO_ESTADO = b"cp5/agnello-8ea14fa3/lampada/estado"

# Comandos e confirmacoes da dashboard
TOPICO_CONTROLE = b"cp5/agnello-8ea14fa3/lampada/controle"
TOPICO_CONTROLE_ESTADO = b"cp5/agnello-8ea14fa3/lampada/controle/estado"

# Dados enviados ao FIWARE
TOPICO_DADOS = b"/ul/TEF/atuador001/attrs"

lampada = PWM(Pin(26), freq=1000)
lampada.duty_u16(0)

modo = "automatico"
brilho_atual = 0

def atualizar_lcd():
    # Exibe o modo atual de funcionamento.
    if modo == "automatico":
        linha1 = "Modo: Automatico"
    else:
        linha1 = "Modo: Manual"

    # Exibe o brilho realmente aplicado ao LED.
    linha2 = "Brilho: {}%".format(brilho_atual)

    lcd.move_to(0, 0)
    lcd.putstr((linha1 + " " * 16)[:16])

    lcd.move_to(0, 1)
    lcd.putstr((linha2 + " " * 16)[:16])



def publicar_estado_controle():
    estado = {
        "modo": modo,
        "brilho": brilho_atual
    }

    cliente.publish(
        TOPICO_CONTROLE_ESTADO,
        json.dumps(estado).encode()
    )


def aplicar_brilho(brilho):
    global brilho_atual

    intensidade = int(brilho * 65535 / 100)
    lampada.duty_u16(intensidade)
    brilho_atual = brilho
    atualizar_lcd()

    # Registra o brilho aplicado no FIWARE
    dados = "b|" + str(brilho)
    cliente.publish(TOPICO_DADOS, dados.encode())

    # Mantem a confirmacao que o monitor ja recebe
    cliente.publish(TOPICO_ESTADO, str(brilho).encode())

    publicar_estado_controle()
    print("Brilho aplicado:", brilho, "% | Modo:", modo)


def receber_comando(topico, mensagem):
    global modo

    try:
        # Canal automatico: recebe um numero de 0 a 100
        if topico == TOPICO:
            if modo != "automatico":
                return

            brilho = int(mensagem.decode())

            if not 0 <= brilho <= 100:
                print("O brilho precisa estar entre 0 e 100.")
                return

            aplicar_brilho(brilho)

        # Canal da dashboard: recebe um JSON
        elif topico == TOPICO_CONTROLE:
            comando = json.loads(mensagem.decode())

            if not isinstance(comando, dict):
                print("O comando de controle precisa ser um objeto JSON.")
                return

            novo_modo = comando.get("modo")

            if novo_modo == "manual":
                brilho = comando.get("brilho")

                # Aceita apenas numeros inteiros entre 0 e 100
                if type(brilho) is not int or not 0 <= brilho <= 100:
                    print("Informe um brilho inteiro entre 0 e 100.")
                    return

                modo = "manual"
                aplicar_brilho(brilho)

            elif novo_modo == "automatico":
                modo = "automatico"
                atualizar_lcd()
                publicar_estado_controle()
                print("Modo automatico: aguardando o monitor.")
            elif novo_modo == "consultar":
                publicar_estado_controle()        

            else:
                print("Modo invalido. Use manual ou automatico.")

    except (ValueError, TypeError):
        print("Comando invalido:", mensagem)


# Conecta ao Wi-Fi
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
    b"cp5-atuador-8ea14fa3",
    SERVIDOR,
    keepalive=60
)

cliente.set_callback(receber_comando)


def conectar_mqtt():
    while True:
        try:
            cliente.connect()
            cliente.subscribe(TOPICO)
            cliente.subscribe(TOPICO_CONTROLE)

            # Restaura o brilho manual depois de uma reconexao
            aplicar_brilho(brilho_atual)

            print("MQTT conectado! Modo:", modo)
            return

        except OSError:
            print("MQTT indisponivel. Tentando novamente...")

            try:
                cliente.disconnect()
            except OSError:
                pass

            time.sleep(2)


conectar_mqtt()
ultimo_ping = time.ticks_ms()

while True:
    try:
        cliente.check_msg()

        if time.ticks_diff(time.ticks_ms(), ultimo_ping) > 20000:
            cliente.ping()
            ultimo_ping = time.ticks_ms()

    except OSError as erro:
        print("Conexao MQTT caiu:", repr(erro))
        print("Tentando reconectar...")

        lampada.duty_u16(0)

        try:
            cliente.disconnect()
        except OSError:
            pass

        atualizar_lcd()
        conectar_mqtt()
        ultimo_ping = time.ticks_ms()

    time.sleep(0.1)
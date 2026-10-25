from machine import Pin, PWM, I2C
from umqtt.simple import MQTTClient
import network
import time
import json

from i2c_lcd import I2cLcd

# Inicializa o LCD 16x2 I2C
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
lcd = I2cLcd(i2c, 0x27, 2, 16)


SERVIDOR = "34.201.44.234"

# Comandos automaticos enviados pelo monitor
TOPICO = b"cp5/agnello-8ea14fa3/lampada"

# Confirmacao de brilho para o monitor
TOPICO_ESTADO = b"cp5/agnello-8ea14fa3/lampada/estado"

# Comandos e confirmacoes da dashboard
TOPICO_CONTROLE = b"cp5/agnello-8ea14fa3/lampada/controle"
TOPICO_CONTROLE_ESTADO = b"cp5/agnello-8ea14fa3/lampada/controle/estado"

# Dados enviados ao FIWARE
TOPICO_DADOS = b"/ul/TEF/atuador001/attrs"

# Leituras que o monitor ja publica para o FIWARE (t|..|h|.. e l|..)
TOPICO_MEDICOES = b"/ul/TEF/monitor001/attrs"

# Limites da dashboard, publicados pelo backend com retain
TOPICO_LIMITES = b"cp5/agnello-8ea14fa3/config/limites"

# Tempos em milissegundos
TEMPO_TELA = 3000
TEMPO_PISCA = 500
VALIDADE_LEITURA = 15000
TEMPO_PING = 20000

lampada = PWM(Pin(26), freq=1000)
lampada.duty_u16(0)

# LED indicador de atuacao ambiental
led_atuacao = Pin(27, Pin.OUT)
led_atuacao.value(0)

modo = "automatico"
brilho_atual = 0

# Fallback: mesmos valores do backend/limites.json do repositorio.
# Usado somente ate o backend enviar a configuracao pelo MQTT.
# Enquanto isso, o LCD mostra "*" no fim da segunda linha.
LIMITES_PADRAO = {
    "temperatura": {"ativo": True, "minimo": 10.0, "maximo": 30.0},
    "umidade": {"ativo": True, "minimo": 50.0, "maximo": 80.0},
    "luminosidade_bruta": {"ativo": True, "minimo": 1000, "maximo": 2500}
}
limites = LIMITES_PADRAO
limites_sincronizados = False
ultimo_limite_recebido = None

# Ultimas leituras do monitor e o instante em que chegaram
leituras = {"t": None, "h": None, "l": None}
instantes = {"t": 0, "h": 0, "l": 0}
FAIXAS_LEITURA = {"t": (-40, 80), "h": (0, 100), "l": (0, 4095)}

CHAVES = {"temperatura": "t", "umidade": "h", "luminosidade_bruta": "l"}

# Acao abaixo do minimo e acima do maximo.
# No LDR, ADC maior significa MENOS luz no ambiente.
ACOES = {
    "temperatura": ("AQUECER", "RESFRIAR"),
    "umidade": ("UMIDIFICAR", "DESUMIDIFICAR"),
    "luminosidade_bruta": ("DIMINUIR LUZ", "AUMENTAR LUZ")
}


# ---------- Decisoes ambientais (atuacao simbolica) ----------

def leitura_recente(chave):
    if leituras[chave] is None:
        return False
    return time.ticks_diff(time.ticks_ms(), instantes[chave]) <= VALIDADE_LEITURA


def decidir(sensor):
    # Indica a correcao necessaria. Nao altera o ambiente fisicamente.
    chave = CHAVES[sensor]

    if leituras[chave] is None:
        return "AGUARDANDO"

    if not leitura_recente(chave):
        return "DADOS ANTIGOS"

    faixa = limites[sensor]

    if not faixa["ativo"]:
        return "DESATIVADO"

    valor = leituras[chave]
    abaixo, acima = ACOES[sensor]

    if valor < faixa["minimo"]:
        return abaixo
    if valor > faixa["maximo"]:
        return acima

    return "LUZ NORMAL" if sensor == "luminosidade_bruta" else "NORMAL"


def precisa_atuar():
    # O LED vermelho considera apenas temperatura e umidade.
    return (
        decidir("temperatura") in ACOES["temperatura"]
        or decidir("umidade") in ACOES["umidade"]
    )


def atualizar_led_atuacao():
    if precisa_atuar():
        aceso = (time.ticks_ms() // TEMPO_PISCA) % 2 == 0
        led_atuacao.value(1 if aceso else 0)
    else:
        led_atuacao.value(0)


ultimas_decisoes = None


def registrar_decisoes():
    # Mostra no serial apenas quando alguma decisao muda.
    global ultimas_decisoes

    decisoes = (
        decidir("temperatura"),
        decidir("umidade"),
        decidir("luminosidade_bruta")
    )

    if decisoes != ultimas_decisoes:
        ultimas_decisoes = decisoes
        print(
            "Atuacao -> Temp:", decisoes[0],
            "| Umid:", decisoes[1],
            "| Luz:", decisoes[2],
            "| Limites:", "dashboard" if limites_sincronizados else "padrao"
        )


# ---------- LCD ----------

linhas_lcd = [None, None]


def escrever_lcd(linha1, linha2):
    # Reescreve somente as linhas que mudaram, evitando flicker.
    for numero, texto in enumerate((linha1, linha2)):
        texto = (texto + " " * 16)[:16]

        if texto != linhas_lcd[numero]:
            lcd.move_to(0, numero)
            lcd.putstr(texto)
            linhas_lcd[numero] = texto


def limpar_lcd():
    lcd.clear()
    linhas_lcd[0] = None
    linhas_lcd[1] = None


def tela_iluminacao():
    # Exibe o modo atual e o brilho realmente aplicado ao LED.
    if modo == "automatico":
        linha1 = "Modo: Automatico"
    else:
        linha1 = "Modo: Manual"

    return linha1, "Brilho: {}%".format(brilho_atual)


def tela_sensor(sensor, rotulo, formato):
    valor = leituras[CHAVES[sensor]]

    if valor is None:
        linha1 = rotulo + "--"
    else:
        linha1 = rotulo + formato.format(valor)

    linha2 = decidir(sensor)

    # "*" indica que os limites ainda sao os padroes do firmware
    if not limites_sincronizados:
        linha2 = (linha2 + " " * 16)[:15] + "*"

    return linha1, linha2


TELAS = (
    tela_iluminacao,
    lambda: tela_sensor("temperatura", "Temp: ", "{:.1f} C"),
    lambda: tela_sensor("umidade", "Umid: ", "{:.0f}%"),
    lambda: tela_sensor("luminosidade_bruta", "Luz: ", "{} ADC")
)

tela_atual = 0
inicio_tela = time.ticks_ms()


def atualizar_lcd():
    global tela_atual, inicio_tela

    # Alterna a tela a cada 3 segundos.
    if time.ticks_diff(time.ticks_ms(), inicio_tela) >= TEMPO_TELA:
        tela_atual = (tela_atual + 1) % len(TELAS)
        inicio_tela = time.ticks_ms()

    linha1, linha2 = TELAS[tela_atual]()
    escrever_lcd(linha1, linha2)


def digitar(coluna, linha, texto, pausa_ms):
    lcd.move_to(coluna, linha)

    for caractere in texto:
        lcd.putstr(caractere)
        time.sleep_ms(pausa_ms)


def animacao_inicial():
    # Apresentacao do grupo: cerca de 3 segundos no total.
    limpar_lcd()
    digitar(5, 0, "GRUPO", 60)
    digitar(3, 1, "DEBUGGERS", 60)
    time.sleep_ms(800)

    limpar_lcd()
    digitar(0, 0, "VINHERIA AGNELLO", 25)
    digitar(1, 1, "ESP32 ATUADOR", 25)
    time.sleep_ms(800)


# ---------- MQTT ----------

def estado_ambiente():
    return {
        "temperatura": decidir("temperatura"),
        "umidade": decidir("umidade"),
        "luminosidade": decidir("luminosidade_bruta"),
        "led_atuacao": precisa_atuar(),
        "limites": "sincronizados" if limites_sincronizados else "padrao"
    }


def publicar_estado_controle():
    estado = {
        "modo": modo,
        "brilho": brilho_atual,
        "ambiente": estado_ambiente()
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

    # Registra o brilho aplicado no FIWARE
    dados = "b|" + str(brilho)
    cliente.publish(TOPICO_DADOS, dados.encode())

    # Mantem a confirmacao que o monitor ja recebe
    cliente.publish(TOPICO_ESTADO, str(brilho).encode())

    publicar_estado_controle()
    print("Brilho aplicado:", brilho, "% | Modo:", modo)


def receber_medicoes(mensagem):
    # Formato UltraLight do monitor: "t|25.0|h|60.0" ou "l|1800"
    partes = mensagem.decode().split("|")

    if len(partes) % 2:
        print("Medicao invalida:", mensagem)
        return

    novas = {}

    for i in range(0, len(partes), 2):
        chave = partes[i]

        if chave not in leituras:
            continue

        valor = float(partes[i + 1])
        menor, maior = FAIXAS_LEITURA[chave]

        if not menor <= valor <= maior:
            print("Medicao fora da faixa do sensor:", mensagem)
            return

        novas[chave] = int(valor) if chave == "l" else valor

    agora = time.ticks_ms()

    for chave in novas:
        leituras[chave] = novas[chave]
        instantes[chave] = agora


def faixa_valida(faixa, menor, maior):
    if not isinstance(faixa, dict):
        return False

    minimo = faixa.get("minimo")
    maximo = faixa.get("maximo")

    if type(faixa.get("ativo")) is not bool:
        return False

    # bool nao e aceito como numero
    if type(minimo) not in (int, float) or type(maximo) not in (int, float):
        return False

    if menor is not None and (minimo < menor or maximo > maior):
        return False

    return minimo < maximo


def receber_limites(mensagem):
    global limites, limites_sincronizados, ultimo_limite_recebido

    # A mensagem retida chega de novo a cada reconexao.
    if mensagem == ultimo_limite_recebido:
        return

    dados = json.loads(mensagem.decode())

    if not isinstance(dados, dict):
        print("Limites precisam ser um objeto JSON.")
        return

    regras = (
        ("temperatura", None, None),
        ("umidade", 0, 100),
        ("luminosidade_bruta", 0, 4095)
    )
    novos = {}

    for sensor, menor, maior in regras:
        faixa = dados.get(sensor)

        if not faixa_valida(faixa, menor, maior):
            print("Limites rejeitados: faixa invalida em", sensor)
            return

        novos[sensor] = {
            "ativo": faixa["ativo"],
            "minimo": faixa["minimo"],
            "maximo": faixa["maximo"]
        }

    limites = novos
    limites_sincronizados = True
    ultimo_limite_recebido = mensagem

    print(
        "Limites da dashboard aplicados: Temp",
        novos["temperatura"]["minimo"], "-", novos["temperatura"]["maximo"],
        "| Umid", novos["umidade"]["minimo"], "-", novos["umidade"]["maximo"],
        "| LDR", novos["luminosidade_bruta"]["minimo"], "-",
        novos["luminosidade_bruta"]["maximo"]
    )


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
                publicar_estado_controle()
                print("Modo automatico: aguardando o monitor.")

            elif novo_modo == "consultar":
                publicar_estado_controle()

            else:
                print("Modo invalido. Use manual ou automatico.")

        # Leituras do monitor para as decisoes ambientais
        elif topico == TOPICO_MEDICOES:
            receber_medicoes(mensagem)

        # Limites configurados na dashboard
        elif topico == TOPICO_LIMITES:
            receber_limites(mensagem)

    except (ValueError, TypeError, IndexError):
        print("Comando invalido:", mensagem)


# Conecta ao Wi-Fi enquanto a animacao inicial roda
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("Wokwi-GUEST", "")

print("Conectando ao Wi-Fi...")
animacao_inicial()
escrever_lcd("Conectando WiFi", "Aguarde...")
inicio = time.ticks_ms()

while not wifi.isconnected():
    if time.ticks_diff(time.ticks_ms(), inicio) > 20000:
        escrever_lcd("Falha no WiFi", "Reinicie o ESP")
        raise RuntimeError("Falha no Wi-Fi. Reinicie a simulacao.")
    time.sleep(0.2)

print("Wi-Fi conectado!")

cliente = MQTTClient(
    b"cp5-atuador-8ea14fa3",
    SERVIDOR,
    keepalive=60
)

cliente.set_callback(receber_comando)


def conectar_mqtt(titulo="Conectando MQTT"):
    tentativa = 0

    while True:
        tentativa += 1
        escrever_lcd(titulo, "Tentativa {}".format(tentativa))

        try:
            cliente.connect()
            cliente.subscribe(TOPICO)
            cliente.subscribe(TOPICO_CONTROLE)
            cliente.subscribe(TOPICO_MEDICOES)
            cliente.subscribe(TOPICO_LIMITES)

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

        if time.ticks_diff(time.ticks_ms(), ultimo_ping) > TEMPO_PING:
            cliente.ping()
            ultimo_ping = time.ticks_ms()

    except OSError as erro:
        print("Conexao MQTT caiu:", repr(erro))
        print("Tentando reconectar...")

        lampada.duty_u16(0)
        led_atuacao.value(0)

        try:
            cliente.disconnect()
        except OSError:
            pass

        conectar_mqtt("Reconect. MQTT")
        ultimo_ping = time.ticks_ms()

    atualizar_led_atuacao()
    atualizar_lcd()
    registrar_decisoes()
    time.sleep(0.1)

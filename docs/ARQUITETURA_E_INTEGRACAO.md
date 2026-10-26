# Arquitetura e Integração — Vinheria Agnello (CP5)

## Objetivo

Explicar **como as partes já desenvolvidas se comunicam**, para que o grupo possa montar o hardware real e continuar a evolução do projeto sem alterar inadvertidamente a lógica validada em Wokwi.

## Arquitetura lógica

```text
                    +-----------------------+
                    |   ESP32 Monitor       |
                    | DHT, LDR, buzzer,     |
                    | LED de alerta e LCD  |
                    +-----------+-----------+
                                |
                     MQTT (Wi-Fi / 1883)
                                |
                    +-----------v-----------+
                    |      Mosquitto        |
                    |      AWS EC2          |
                    +----+-------------+----+
                         |             |
              UltraLight |             | Comandos/estados
                         v             v
                   +-----------+  +---------------------+
                   | IoT Agent |  | ESP32 Atuador       |
                   |    UL     |  | LED PWM + LCD       |
                   +-----+-----+  +---------------------+
                         |
                         v
                   +-----------+       +------------------+
                   |   Orion   |<----->| Backend FastAPI  |
                   +-----+-----+       +--------+---------+
                         |                      |
                 Assinaturas/histórico          | HTTP
                         v                      v
                   +-----------+       +------------------+
                   | STH-Comet |       | Dashboard Web    |
                   | + MongoDB |       | HTML/CSS/JS      |
                   +-----------+       +------------------+
```

Diagrama conceitual: determinados comandos passam por tópicos MQTT e pelo backend, não necessariamente pelo Orion. A representação serve para orientar a integração, não para substituir a leitura dos códigos.

## 1. ESP32 Monitor

O Monitor usa **MicroPython** e executa no Wokwi, com os seguintes pinos usados na simulação:

| Componente | GPIO / conexão |
|---|---|
| DHT22 (Wokwi) / DHT11 (hands-on) | GPIO 15 |
| LDR (entrada ADC) | GPIO 34 |
| LED azul de alerta | GPIO 2 |
| Buzzer PWM | GPIO 25 |
| LCD 16x2 I2C | SDA 21, SCL 22 (endereço `0x27` na simulação) |

Publica leituras de temperatura, umidade e luminosidade; calcula comandos de brilho automático conforme o LDR; recebe alertas para sinalização visual/sonora; exibe informações no LCD.

**Lógica de iluminação implementada no simulador:**

| Leitura LDR (ADC) | Brilho automático |
|---|---|
| Maior que o máximo da faixa de luminosidade | 100% |
| Menor que o mínimo da faixa de luminosidade | 0% |
| Dentro da faixa | 50% |

A faixa vem da dashboard (`luminosidade_bruta` em `limites.json`), recebida pelo tópico de limites. Até essa mensagem chegar, o Monitor usa o padrão **1000–2500**, igual ao `limites.json` do repositório.

**Luminosidade em porcentagem (só na apresentação):** o LDR é lido como ADC (0–4095) e o sistema inteiro continua usando esse valor: FIWARE, histórico, API, limites, alertas e controle do brilho. Para facilitar a leitura, os LCDs, a dashboard e o gráfico de luminosidade mostram um **índice relativo de luz**:

```text
luz (%) = round((4095 - ADC) * 100 / 4095), limitado a 0–100
```

| ADC | Luz exibida |
|---|---|
| 0 | 100% (muito claro) |
| 1000 | 76% |
| 2500 | 39% |
| 4019 | 2% |
| 4095 | 0% (escuro) |

A escala é invertida em relação ao ADC (ADC maior = menos luz) e é uma estimativa relativa: **não equivale a lux**.

**LCD do Monitor:** ao ligar, mostra a mesma apresentação do Atuador ("GRUPO DEBUGGERS" e "VINHERIA AGNELLO / ESP32 MONITOR", cerca de 3 s, enquanto o Wi-Fi conecta). Depois alterna duas telas a cada 3 s: `TEMP` / `UMID` e `Luz: 2%` / `LED: 100%` (brilho confirmado pelo Atuador).

Na montagem física, **valide o sentido da leitura ADC**: na ligação do Wokwi usada nos testes, valores maiores correspondiam a menos luz ambiente. O comportamento pode mudar conforme o divisor resistivo e o módulo LDR reais.

## 2. ESP32 Atuador

Também usa MicroPython.

| Componente | GPIO / conexão |
|---|---|
| LED amarelo de iluminação (PWM) | GPIO 26, com resistor de 220 Ω |
| LED vermelho de atuação ambiental | GPIO 27, com resistor de 220 Ω |
| LCD 16x2 I2C | SDA 21, SCL 22 (endereço `0x27`) |

**Iluminação (sem mudança de comportamento):** recebe comandos automáticos do Monitor e manuais da dashboard, aplica o brilho por PWM e publica as confirmações. No modo manual, os comandos automáticos são ignorados.

**Atuação ambiental simbólica:** o Atuador assina as leituras que o Monitor já envia ao FIWARE e compara com os limites da dashboard. Ele **indica** a correção necessária, mas **não altera fisicamente a temperatura nem a umidade**, pois não há aquecedor, resfriador ou umidificador na montagem.

| Sensor | Abaixo do mínimo | Dentro da faixa | Acima do máximo |
|---|---|---|---|
| Temperatura | `AQUECER` | `NORMAL` | `RESFRIAR` |
| Umidade | `UMIDIFICAR` | `NORMAL` | `DESUMIDIFICAR` |
| Luminosidade (ADC) | `DIMINUIR LUZ` (muita luz) | `LUZ NORMAL` | `AUMENTAR LUZ` (pouca luz) |

Os próprios limites contam como dentro da faixa. Outros estados:

- `AGUARDANDO`: nenhuma leitura recebida desde que o ESP ligou.
- `DADOS ANTIGOS`: a última leitura tem mais de 15 s (Monitor desligado ou sem rede). Nenhuma ação é indicada.
- `DESATIVADO`: o sensor está com o alerta desligado na dashboard.

**LED vermelho:** pisca (500 ms aceso / 500 ms apagado) quando temperatura ou umidade pede correção. Fica apagado quando tudo está normal, sem leituras recentes ou durante a reconexão MQTT. A luminosidade não aciona o LED, porque a luz já é corrigida pelo LED amarelo.

**LCD:** ao ligar, mostra a apresentação "GRUPO DEBUGGERS" e "VINHERIA AGNELLO / ESP32 ATUADOR" (cerca de 3 s, enquanto o Wi-Fi conecta). Depois alterna quatro telas a cada 3 s:

| Tela | Linha 1 | Linha 2 |
|---|---|---|
| Iluminação | `Modo: Automatico` / `Modo: Manual` | `Brilho: 50%` (brilho realmente aplicado) |
| Temperatura | `Temp: 25.0 C` | ação ou estado |
| Umidade | `Umid: 65%` | ação ou estado |
| Luminosidade | `Luz: 56%` (% relativa, calculada do ADC) | ação ou estado |

Um `*` no fim da segunda linha indica que o Atuador ainda usa os **limites padrão** do firmware (cópia do `limites.json` do repositório: temperatura 10–30 °C, umidade 50–80%, LDR 1000–2500), porque a configuração da dashboard ainda não chegou. O LCD também mostra `Conectando WiFi`, `Conectando MQTT` e `Reconect. MQTT` com o número da tentativa.

**Resposta de estado:** a mensagem em `lampada/controle/estado` ganhou o campo opcional `ambiente`, com as decisões, o estado do LED vermelho e a origem dos limites (`sincronizados` ou `padrao`). Os campos `modo` e `brilho` não mudaram.

## 3. Tópicos MQTT usados

| Tópico | Direção / finalidade |
|---|---|
| `/ul/TEF/monitor001/attrs` | Monitor → IoT Agent UL: leituras ambientais |
| `/ul/TEF/atuador001/attrs` | Atuador → IoT Agent UL: brilho aplicado |
| `cp5/agnello-8ea14fa3/lampada` | Monitor → Atuador: brilho automático |
| `cp5/agnello-8ea14fa3/lampada/controle` | Backend/dashboard → Atuador: comandos manuais e consulta de estado |
| `cp5/agnello-8ea14fa3/lampada/estado` | Atuador → Monitor: confirmação do brilho aplicado |
| `cp5/agnello-8ea14fa3/lampada/controle/estado` | Atuador → Backend/dashboard: modo e brilho confirmados |
| `cp5/agnello-8ea14fa3/monitor/alertas` | Backend → Monitor: acionamento de alertas |
| `cp5/agnello-8ea14fa3/config/limites` | Backend → Monitor e Atuador: limites da dashboard em JSON, publicados com **retain** |

O Atuador também **assina** `/ul/TEF/monitor001/attrs` para receber as leituras ambientais. Assim, nenhuma mensagem nova foi criada no Monitor e o IoT Agent continua recebendo exatamente o mesmo conteúdo.

**Sincronização dos limites:** o backend publica o conteúdo do `limites.json` ao iniciar e a cada `PUT /limites`. Como a mensagem fica retida no broker (o Mosquitto está com `persistence true`), um ESP que liga ou reconecta recebe a configuração atual na hora, sem precisar reiniciar. Os ESPs rejeitam faixas inválidas, mantêm a configuração anterior e ignoram a mesma mensagem recebida de novo. Se o backend nunca tiver publicado, os ESPs ficam com o padrão do firmware e o Atuador mostra `*` no LCD.

Os payloads dependem do tópico: as telemetrias UltraLight usam campos compactos (por exemplo, `t|...|h|...` e `l|...`), enquanto os comandos/estados de controle podem utilizar JSON. **Consulte os `main.py` para o formato exato antes de alterar um produtor ou consumidor.**

## 4. FIWARE e persistência

- **Mosquitto** recebe as mensagens MQTT.
- **IoT Agent UltraLight** converte telemetria MQTT para entidades NGSI-v2 no **Orion**.
- **Orion** armazena o estado atual e permite consultas HTTP.
- **STH-Comet** fornece acesso a histórico alimentado por assinaturas FIWARE e MongoDB.
- **FastAPI** consulta a infraestrutura e oferece rotas usadas pela dashboard, incluindo sensores, estados, alertas, limites e recursos administrativos.

Na instalação testada, o Orion estava conectado ao serviço Docker `mongo-db-historical`; o IoT Agent usava `mongo-db-internal`. O arquivo em `infraestrutura/docker-compose.yml` documenta essa topologia.

**Cabeçalhos FIWARE utilizados nas consultas:**

```http
fiware-service: smart
fiware-servicepath: /
```

**Entidades presentes no ambiente de testes:**

- `urn:ngsi-ld:Environment:001` — monitor ambiental.
- `urn:ngsi-ld:Actuator:001` — atuador.
- `urn:ngsi-ld:Lamp:001` — entidade existente no cenário inicial.

Evite excluir/recriar essas entidades sem verificar seus relacionamentos, provisionamento e assinaturas.

## 5. FastAPI e dashboard

O backend fica em `backend/main.py`. As configurações de limites são mantidas em `backend/limites.json` usando caminho relativo ao próprio script. A dashboard estática fica em `dashboard/` e usa requisições HTTP para a API. As telas e chamadas podem ser identificadas em `dashboard/app.js` e `dashboard/core.js`.

**Endpoints confirmados nas etapas de desenvolvimento:** `/`, `/docs`, `/sensores`, `/atuador/estado`, `/alertas`, `/status` (além de rotas para histórico, limites e administração FIWARE).

- `PUT /limites` salva o arquivo e publica os limites no MQTT. A resposta traz `"sincronizado": true/false`. Se o broker estiver fora, o arquivo é salvo mesmo assim e a dashboard avisa que os ESPs mantêm a configuração anterior.
- O mínimo precisa ser **menor** que o máximo. Faixas com mínimo igual ao máximo são recusadas pela dashboard, pela API e pelos ESPs.
- `GET /status` faz um diagnóstico rápido do FIWARE (Orion), do broker MQTT e do `limites.json`. A dashboard usa essa rota no botão "Verificar serviços". Para a lista autoritativa e atualizada, abra `http://127.0.0.1:8000/docs` com o backend em execução.

## 6. Pontos críticos na adaptação para hardware real

- Revisar **alimentação e nível lógico** dos módulos (especialmente I2C/LCD e entradas analógicas).
- Confirmar pinagem física, resistores, GPIOs e aterramento comum.
- Ajustar conexão Wi-Fi em `WIFI_SSID` / `WIFI_SENHA`: `Wokwi-GUEST` não é uma rede do ambiente físico. No Monitor, use `MODELO_DHT = "DHT11"` com o sensor físico.
- Verificar ADC e calibrar limites conforme medições reais do LDR.
- Testar PWM e LEDs sem exceder a corrente permitida pelo GPIO.
- Verificar latência, reconexão MQTT e disponibilidade da AWS.
- Validar os alarmes sem expor os componentes a condições inseguras.

## Referências do projeto

- [Repositório GitHub](https://github.com/vinifcavalcanti/vinheria-agnello-iot-cp5)
- [Wokwi Monitor](https://wokwi.com/projects/477273550482344961)
- [Wokwi Atuador](https://wokwi.com/projects/477273561317281793)

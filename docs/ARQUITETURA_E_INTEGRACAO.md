# Arquitetura e Integração — Vinheria Agnello (CP5)

## Objetivo

Explicar **como as partes já desenvolvidas se comunicam**, para que o grupo possa montar o hardware real e continuar a evolução do projeto sem alterar inadvertidamente a lógica validada em Wokwi.

## Arquitetura lógica

```text
                    +-----------------------+
                    |   ESP32 Monitor       |
                    | DHT22, LDR, buzzer,   |
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
| DHT22 | GPIO 15 |
| LDR (entrada ADC) | GPIO 34 |
| LED azul de alerta | GPIO 2 |
| Buzzer PWM | GPIO 25 |
| LCD 16x2 I2C | SDA 21, SCL 22 (endereço `0x27` na simulação) |

Publica leituras de temperatura, umidade e luminosidade; calcula comandos de brilho automático conforme o LDR; recebe alertas para sinalização visual/sonora; exibe informações no LCD.

**Lógica de iluminação implementada no simulador:**

| Leitura LDR (ADC) | Brilho automático |
|---|---|
| Maior que 2500 | 100% |
| Menor que 1000 | 0% |
| Entre esses limites | 50% |

Na montagem física, **valide o sentido da leitura ADC**: na ligação do Wokwi usada nos testes, valores maiores correspondiam a menos luz ambiente. O comportamento pode mudar conforme o divisor resistivo e o módulo LDR reais.

## 2. ESP32 Atuador

Também usa MicroPython. O LED simulado é acionado em **PWM no GPIO 26** (com resistor), e o LCD I2C utiliza SDA 21 / SCL 22. O atuador recebe comandos automáticos e manuais, aplica o brilho e publica confirmação de estado. O LCD apresenta modo de operação e brilho.

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

**Endpoints confirmados nas etapas de desenvolvimento:** `/`, `/docs`, `/sensores`, `/atuador/estado`, `/alertas` (além de rotas para histórico, limites e administração FIWARE). Para a lista autoritativa e atualizada, abra `http://127.0.0.1:8000/docs` com o backend em execução.

## 6. Pontos críticos na adaptação para hardware real

- Revisar **alimentação e nível lógico** dos módulos (especialmente I2C/LCD e entradas analógicas).
- Confirmar pinagem física, resistores, GPIOs e aterramento comum.
- Ajustar conexão Wi-Fi: `Wokwi-GUEST` não é uma rede do ambiente físico.
- Verificar ADC e calibrar limites conforme medições reais do LDR.
- Testar PWM e LEDs sem exceder a corrente permitida pelo GPIO.
- Verificar latência, reconexão MQTT e disponibilidade da AWS.
- Validar os alarmes sem expor os componentes a condições inseguras.

## Referências do projeto

- [Repositório GitHub](https://github.com/vinifcavalcanti/vinheria-agnello-iot-cp5)
- [Wokwi Monitor](https://wokwi.com/projects/477273550482344961)
- [Wokwi Atuador](https://wokwi.com/projects/477273561317281793)

# 🍷 Vinheria Agnello
### Sistema IoT de Monitoramento Ambiental e Controle Inteligente de Iluminação

**FIAP | Edge Computing | Checkpoint 5 — Vinheria Full**

Desenvolvido pelo **Grupo DEBUGGERS**.

## 👥 Integrantes

| Nome | RM |
|---|---|
| Enrico Vieira de Almeida Vidal | 569217 |
| Vinicius Fuentes Cavalcanti | 570818 |
| Guilherme De Rosa Peres | 569193 |
| Thiago Fernandes Kulesza | 568922 |
| Marcela Pinheiro Silva | 569457 |
| Isabella Yogui Kohara | 569777 |

---

## 📖 Sobre o projeto

O projeto Vinheria Agnello apresenta uma solução de Internet das Coisas (IoT) para monitorar as condições ambientais de uma vinheria e controlar sua iluminação de forma inteligente.

A solução usa dois ESP32 (simulados no Wokwi e montados no hands-on), comunicação MQTT, serviços FIWARE hospedados na AWS e uma aplicação web para centralizar o monitoramento e o gerenciamento dos dispositivos.

A solução permite acompanhar temperatura, umidade e luminosidade, consultar dados históricos em gráficos dinâmicos, configurar os limites de alerta (triggers), cadastrar dispositivos IoT e controlar a intensidade da iluminação em tempo real.

## 🎯 Objetivos

- Monitorar temperatura, umidade e luminosidade.
- Automatizar o controle da iluminação conforme a luz ambiente.
- Permitir controle manual do brilho pela dashboard.
- Emitir alertas visuais e sonoros para condições fora dos limites.
- Exibir informações em displays LCD nos dispositivos.
- Registrar e consultar dados por meio da plataforma FIWARE.
- Disponibilizar uma interface web para monitoramento e administração.

## 🏗️ Arquitetura em camadas

```text
┌──────────────────────────────────────────────────────────────────┐
│ 5. APLICAÇÃO                                                     │
│    Dashboard web (HTML/CSS/JS): leituras, gráficos dinâmicos,    │
│    cadastro de dispositivos, triggers, alertas e iluminação      │
├──────────────────────────────────────────────────────────────────┤
│ 4. SERVIÇOS / BACKEND                                            │
│    FastAPI (Python): integra FIWARE, gera gráficos, valida e     │
│    salva os limites, envia comandos MQTT aos ESP32               │
├──────────────────────────────────────────────────────────────────┤
│ 3. PLATAFORMA IoT (FIWARE na AWS EC2, Docker)                    │
│    IoT Agent UltraLight → Orion Context Broker → STH-Comet       │
│    (histórico, API :8666) + MongoDB                              │
├──────────────────────────────────────────────────────────────────┤
│ 2. COMUNICAÇÃO                                                   │
│    MQTT (Mosquitto :1883) — telemetria UltraLight e comandos     │
│    HTTP/REST — dashboard ↔ backend ↔ FIWARE (NGSI-v2)            │
├──────────────────────────────────────────────────────────────────┤
│ 1. DISPOSITIVOS (Edge)                                           │
│    ESP32 Monitor: DHT11/DHT22, LDR, LED azul, buzzer, LCD        │
│    ESP32 Atuador: LED amarelo PWM, LED vermelho, LCD             │
└──────────────────────────────────────────────────────────────────┘
```

| Camada | Componente | Papel |
|---|---|---|
| 1. Dispositivos | **ESP32 Monitor** | Lê DHT e LDR, publica a telemetria, envia o brilho automático e emite os alertas (LED azul + buzzer). |
| 1. Dispositivos | **ESP32 Atuador** | Aplica o brilho por PWM e indica a correção ambiental (LCD + LED vermelho). |
| 2. Comunicação | **Mosquitto** | Broker MQTT entre ESP32, IoT Agent e backend. |
| 3. Plataforma | **IoT Agent UL, Orion, STH-Comet, MongoDB** | Convertem a telemetria em entidades NGSI-v2 e guardam o histórico. |
| 4. Serviços | **Backend FastAPI** | Expõe a API usada pela dashboard e conversa com o FIWARE e com o MQTT. |
| 5. Aplicação | **Dashboard Web** | Interface de monitoramento, análise e administração. |

### Fluxo simplificado

```text
ESP32 Monitor ── MQTT ── Mosquitto ── IoT Agent ── Orion
      │                                              │
      └── Comandos de brilho ── ESP32 Atuador        │
                                                     │
                                STH-Comet / MongoDB (:8666)
                                                     │
                                    Backend FastAPI
                                            │
                                     Dashboard Web
```

Detalhes de tópicos MQTT e integração: [`docs/ARQUITETURA_E_INTEGRACAO.md`](docs/ARQUITETURA_E_INTEGRACAO.md).

## 🔌 Hardware

### ESP32 Monitor

- ESP32 com MicroPython.
- Sensor **DHT11** (hands-on) ou **DHT22** (simulação Wokwi) para temperatura e umidade.
- Sensor LDR para luminosidade.
- LED azul para alertas.
- Buzzer para avisos sonoros (um tom diferente para cada anomalia).
- Display LCD 16x2 com comunicação I2C (opcional no hardware físico).

O monitor realiza leituras ambientais, publica os dados via MQTT e emite alertas conforme os limites configurados.

### ESP32 Atuador

- ESP32 com MicroPython.
- LED amarelo de iluminação controlado por PWM (GPIO 26).
- LED vermelho de atuação ambiental (GPIO 27).
- Um resistor de proteção para cada LED.
- Display LCD 16x2 com comunicação I2C.

O atuador recebe comandos de intensidade luminosa, aplica o brilho solicitado e publica confirmações de estado. Ele também compara as leituras do monitor com os limites da dashboard e indica, no LCD e no LED vermelho, a correção ambiental necessária.

### Código dos dispositivos (MicroPython)

Os ESP32 foram programados em **MicroPython** (arquivos `.py`), e não em Arduino (`.ino`). O código de cada dispositivo fica em:

| Dispositivo | Arquivos |
|---|---|
| ESP32 Monitor | [`esp32-monitor/main.py`](esp32-monitor/main.py), `lcd_api.py`, `i2c_lcd.py` |
| ESP32 Atuador | [`esp32-atuador/main.py`](esp32-atuador/main.py), `lcd_api.py`, `i2c_lcd.py` |

## 🔧 Manual de hardware (montagem)

### Ligações do ESP32 Monitor

| Componente | Pino do componente | ESP32 |
|---|---|---|
| DHT11 / DHT22 | VCC | 3V3 |
| | DATA | GPIO 15 |
| | GND | GND |
| LDR (módulo com saída analógica) | VCC | 3V3 |
| | AO | GPIO 34 (ADC) |
| | GND | GND |
| LED azul | Ânodo (+), em série com resistor de 330 Ω | GPIO 2 |
| | Cátodo (−) | GND |
| Buzzer | + | GPIO 25 (PWM) |
| | − | GND |
| LCD 16x2 I2C | SDA / SCL | GPIO 21 / GPIO 22 |
| | VCC / GND | 5V / GND |

### Ligações do ESP32 Atuador

| Componente | Pino do componente | ESP32 |
|---|---|---|
| LED amarelo (iluminação) | Ânodo (+), em série com resistor de 220 Ω | GPIO 26 (PWM) |
| | Cátodo (−) | GND |
| LED vermelho (atuação ambiental) | Ânodo (+), em série com resistor de 220 Ω | GPIO 27 |
| | Cátodo (−) | GND |
| LCD 16x2 I2C | SDA / SCL | GPIO 21 / GPIO 22 |
| | VCC / GND | 5V / GND |

### Preparar o ESP32 físico

1. Grave o firmware MicroPython no ESP32 (por exemplo, com o Thonny: *Ferramentas → Opções → Interpretador → MicroPython (ESP32) → Instalar ou atualizar o firmware*).
2. No topo do `main.py` do dispositivo, ajuste a configuração:

   ```python
   WIFI_SSID = "nome-da-rede"   # Wokwi: "Wokwi-GUEST"
   WIFI_SENHA = "senha-da-rede" # Wokwi: ""
   MODELO_DHT = "DHT11"         # só no Monitor; Wokwi: "DHT22"
   ```

   Confira também `SERVIDOR` (IP público da AWS).
3. Copie para o ESP32 os arquivos `main.py`, `lcd_api.py` e `i2c_lcd.py` (no Thonny: *Arquivo → Salvar como → Dispositivo MicroPython*).
4. Reinicie o ESP32 e acompanhe o terminal: `Wi-Fi conectado!` e `MQTT conectado!` indicam que está pronto.

**Observações:**

- O LCD é detectado automaticamente nos endereços I2C `0x27` ou `0x3F`. Sem LCD conectado, o ESP32 segue funcionando normalmente.
- O ESP32 usa apenas MQTT (porta 1883). Se a rede bloquear o acesso, use o roteador do celular.
- No Wokwi, uma leitura maior do LDR significa menos luz. No hardware real, confirme o sentido com o módulo utilizado.

## 💡 Controle inteligente da iluminação

O sistema oferece dois modos de operação:

**Automático:** a intensidade do LED é ajustada de acordo com as leituras do sensor LDR.

**Manual:** o usuário define o brilho diretamente pela dashboard.

O atuador confirma o brilho aplicado por MQTT, permitindo sincronizar as informações exibidas na interface e nos dispositivos.

## 🌡️ Atuação ambiental simbólica

O ESP32 Atuador recebe as leituras do monitor e os limites configurados na dashboard. Com isso, identifica qual correção seria necessária:

| Condição | Indicação no LCD |
|---|---|
| Temperatura abaixo / acima da faixa | `AQUECER` / `RESFRIAR` |
| Umidade abaixo / acima da faixa | `UMIDIFICAR` / `DESUMIDIFICAR` |
| Pouca / muita luz (LDR) | `AUMENTAR LUZ` / `DIMINUIR LUZ` |

O LED vermelho pisca enquanto temperatura ou umidade estiverem fora da faixa.

> **A atuação é simbólica:** o sistema **indica** a ação corretiva, mas **não altera fisicamente a temperatura nem a umidade**. A montagem não possui aquecedor, resfriador, umidificador ou desumidificador.

Os limites salvos na dashboard são enviados aos dois ESP32 pelo MQTT e aplicados sem reiniciar. Detalhes em [`docs/ARQUITETURA_E_INTEGRACAO.md`](docs/ARQUITETURA_E_INTEGRACAO.md).

## 🚨 Alertas e monitoramento

O sistema permite configurar limites (triggers) para:

- Temperatura.
- Umidade.
- Luminosidade.

Quando um parâmetro sai da faixa, a dashboard aciona remotamente o ESP32 Monitor: o **LED azul pisca** até o valor voltar ao normal e o **buzzer toca um tom diferente para cada tipo de anomalia** (temperatura 1200 Hz, umidade 1800 Hz, luminosidade 2400 Hz; com várias anomalias, os tons se alternam). Esse acionamento é feito pelo front-end, no botão **"Alertas no ESP monitor"** da visão geral.

Os limites de luminosidade são configurados em ADC (leitura bruta do LDR, 0–4095). Os LCDs e a dashboard exibem a luz como **% relativa** (0% = escuro, 100% = muito claro), calculada a partir do ADC só para apresentação; não é uma medida em lux. Detalhes em [`docs/ARQUITETURA_E_INTEGRACAO.md`](docs/ARQUITETURA_E_INTEGRACAO.md).

O backend também identifica situações em que os dados deixam de ser atualizados.

## 🖥️ Dashboard

A interface web reúne:

- Leituras dos sensores e indicadores de estado dos dispositivos (online/offline).
- **Gráficos dinâmicos do histórico**, consumidos da API **8666 do STH-Comet**: gráfico interativo no navegador (valor de cada ponto ao passar o mouse, atualização automática a cada 15 s) e gráfico gerado no backend com Matplotlib.
- **Cadastro e gerenciamento dos IoT Devices** no IoT Agent (cadastrar, editar e excluir).
- **Ajuste dos triggers** de temperatura, umidade e luminosidade.
- Acionamento dos alertas remotos no ESP32 Monitor.
- Controle manual e automático da iluminação.
- Recursos de administração FIWARE (serviços, entidades, assinaturas e registros).

A dashboard foi desenvolvida com HTML, CSS e JavaScript e utiliza a API FastAPI. Detalhes em [`docs/DASHBOARD.md`](docs/DASHBOARD.md).

## 🧭 Manual de operação

1. **Conectar:** com o backend e a dashboard rodando (veja *Como executar*), abra `http://127.0.0.1:5500/dashboard/`. Em **⚙ Configurar conexão → Verificar serviços**, confira API, FIWARE, MQTT e limites em verde.
2. **Acompanhar o ambiente:** a **Visão geral** mostra temperatura, umidade, luminosidade e o brilho confirmado pelo atuador, atualizados a cada 5 s.
3. **Ajustar os triggers:** em **Limites & alertas**, defina mínimo e máximo de cada sensor e clique em **Salvar limites**. Os novos limites chegam aos ESP32 na hora.
4. **Ativar os alertas remotos:** na **Visão geral**, ligue **"Alertas no ESP monitor"**. Enquanto um parâmetro estiver fora da faixa, o LED azul pisca e o buzzer toca o tom da anomalia; ao voltar ao normal, o alerta para. A automação funciona enquanto a página estiver aberta.
5. **Controlar a iluminação:** em **Controle da iluminação**, escolha **Automático** (brilho pelo LDR) ou **Manual** (defina o brilho e clique em **Aplicar brilho**).
6. **Analisar o histórico:** em **Histórico & gráficos**, escolha o sensor. O gráfico dinâmico mostra cada leitura ao passar o mouse; é possível baixar o gráfico (PNG) e os dados (CSV).
7. **Cadastrar dispositivos:** em **Dispositivos**, clique em **Novo dispositivo**, escolha o perfil (monitor ou atuador) e confirme. Também é possível editar e excluir.

## ⭐ Diferenciais

- **Dois ESP32 com funções complementares:** além do monitor exigido, um **ESP32 Atuador** controla a iluminação por PWM.
- **Iluminação inteligente:** modo automático pelo LDR e modo manual pela dashboard, com **confirmação do brilho realmente aplicado** pelo ESP32.
- **Atuação ambiental simbólica:** o atuador indica `AQUECER`, `RESFRIAR`, `UMIDIFICAR` e `DESUMIDIFICAR` no LCD e pisca um LED vermelho.
- **Triggers sincronizados em tempo real:** limites salvos na dashboard chegam aos ESP32 por MQTT (mensagem retida), sem reiniciar.
- **Displays LCD 16x2** nos dois dispositivos, com telas alternadas e animação de abertura do grupo.
- **Luminosidade em % relativa** nos LCDs e na dashboard, mantendo o ADC internamente.
- **Gráficos dinâmicos** com atualização automática e exportação PNG/CSV.
- **Diagnóstico de serviços** (API, FIWARE, MQTT e limites) em um clique, e status online/offline dos dispositivos.
- **Dashboard responsiva**, utilizável também no celular.

## 🛠️ Tecnologias utilizadas

| Camada | Tecnologias |
|---|---|
| Dispositivos | ESP32, MicroPython, Wokwi |
| Sensores e atuadores | DHT11 / DHT22, LDR, LED PWM, buzzer, LCD I2C |
| Comunicação | MQTT, HTTP, NGSI-v2 |
| Plataforma IoT | FIWARE Orion, IoT Agent UltraLight, STH-Comet |
| Mensageria | Eclipse Mosquitto |
| Banco de dados | MongoDB |
| Backend | Python, FastAPI, Uvicorn, Matplotlib |
| Frontend | HTML, CSS, JavaScript |
| Infraestrutura | AWS EC2, Docker Compose |

## 📁 Estrutura do repositório

```text
vinheria-agnello-iot-cp5/
├── backend/
│   ├── main.py
│   ├── limites.json
│   └── requirements.txt
├── dashboard/
│   ├── index.html
│   ├── app.js
│   ├── core.js
│   ├── styles.css
│   ├── marca.svg
│   ├── taca.png
│   └── *.ttf (fontes do logo)
├── esp32-monitor/
│   ├── main.py
│   ├── diagram.json
│   ├── lcd_api.py
│   ├── i2c_lcd.py
│   └── wokwi-project.txt
├── esp32-atuador/
│   ├── main.py
│   ├── diagram.json
│   ├── lcd_api.py
│   ├── i2c_lcd.py
│   └── wokwi-project.txt
├── infraestrutura/
│   ├── docker-compose.yml
│   └── mosquitto/
│       └── mosquitto.conf
├── docs/
├── requirements.txt
├── .gitignore
└── README.md
```

## 🚀 Como executar (manual de instalação do software)

### 1. Pré-requisitos

- Python e pip.
- Acesso a uma infraestrutura FIWARE com MQTT.
- Navegador web.
- Projetos ESP32 no Wokwi ou ESP32 físicos montados (veja *Manual de hardware*).
- Docker com Docker Compose, caso seja necessário iniciar a infraestrutura.

### 2. Configurar a infraestrutura

O arquivo `infraestrutura/docker-compose.yml` descreve os serviços utilizados no projeto.

Antes de executar a infraestrutura, revise as credenciais de demonstração, as portas expostas e as configurações de rede.

Em ambiente de desenvolvimento, a partir da pasta `infraestrutura`:

```bash
docker compose up -d
```

Este comando cria ou inicia os serviços Docker e deve ser usado somente no ambiente de implantação pretendido.

### 3. Instalar as dependências do backend

Na raiz do repositório:

```bash
python -m venv .venv
```

Ative o ambiente virtual e instale as dependências:

```bash
python -m pip install -r requirements.txt
```

O `requirements.txt` da raiz inclui o `backend/requirements.txt`.

### 4. Configurar a conexão com a AWS

No arquivo `backend/main.py`, confira o endereço definido em `IP_SERVIDOR`.

Configure também `SERVIDOR` nos `main.py` dos ESP32 (Wokwi ou físicos) com o mesmo IP.

O endereço público de uma instância EC2 pode mudar após uma parada e inicialização.

### 5. Iniciar a API

Na pasta `backend`:

```bash
python -m uvicorn main:app
```

API local:

http://127.0.0.1:8000

Documentação interativa:

http://127.0.0.1:8000/docs

### 6. Iniciar a dashboard

Abra um segundo terminal na raiz do repositório:

```bash
python -m http.server 5500
```

Acesse:

http://127.0.0.1:5500/dashboard/

A dashboard precisa conseguir acessar a API FastAPI configurada.

### 7. Iniciar os dispositivos

Abra as simulações no Wokwi e inicie os dois ESP32:

- **Monitor (LDR + DHT22):** https://wokwi.com/projects/477273550482344961
- **Atuador:** https://wokwi.com/projects/477273561317281793

No hardware físico, siga *Preparar o ESP32 físico*.

Confira as configurações de rede e MQTT antes de iniciar.

## 📚 Documentação complementar

| Documento | Conteúdo |
|---|---|
| [Guia de Execução](docs/GUIA_DE_EXECUCAO.md) | Passo a passo para configurar, executar e testar o ambiente. |
| [Arquitetura e Integração](docs/ARQUITETURA_E_INTEGRACAO.md) | Comunicação MQTT, FIWARE, FastAPI e integração dos dispositivos. |
| [Dashboard](docs/DASHBOARD.md) | Funcionalidades, arquivos e checklist da interface. |
| [Status do Projeto](docs/STATUS_DO_PROJETO.md) | Funcionalidades concluídas e validações realizadas. |

### Estado atual

- **Software e simulações Wokwi:** concluídos e validados.
- **Backend e integração FIWARE:** concluídos e testados na AWS.
- **Dashboard:** concluída, com gráficos dinâmicos, cadastro de dispositivos e ajuste de triggers.
- **Hardware físico:** ESP32 Monitor com DHT11, LDR, LED azul e buzzer, apresentado no hands-on.

## 🔒 Observações de segurança

Este repositório documenta um protótipo acadêmico.

As configurações de demonstração, incluindo autenticação simplificada do MongoDB e conexões MQTT anônimas, não são recomendadas para ambientes de produção.

Antes de disponibilizar os serviços publicamente, é necessário revisar autenticação, permissões, proteção de portas, credenciais e conexões seguras.

## 👨‍💻 Desenvolvimento

**Grupo DEBUGGERS — FIAP**

Projeto desenvolvido para a disciplina de Edge Computing, no contexto da Vinheria Agnello.

## 📚 Créditos

A infraestrutura FIWARE foi baseada nos materiais e no repositório disponibilizados pelo professor Cabrini, com adaptações para integração dos dispositivos, do backend e da dashboard desenvolvidos pelo grupo.

---
**Vinheria Agnello | Grupo DEBUGGERS | FIAP**

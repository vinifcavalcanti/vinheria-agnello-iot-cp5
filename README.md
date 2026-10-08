
# 🍷 Vinheria Agnello
### Sistema IoT de Monitoramento Ambiental e Controle Inteligente de Iluminação

**FIAP | Edge Computing | Checkpoint 5**

Desenvolvido pelo **Grupo DEBUGGERS**.

---

## 📖 Sobre o projeto

O projeto Vinheria Agnello apresenta uma solução de Internet das Coisas (IoT) para monitorar as condições ambientais de uma vinheria e controlar sua iluminação de forma inteligente.

A proposta utiliza dois ESP32 simulados no Wokwi, comunicação MQTT, serviços FIWARE hospedados na AWS e uma aplicação web para centralizar o monitoramento e o gerenciamento dos dispositivos.

A solução permite acompanhar temperatura, umidade e luminosidade, consultar dados históricos, configurar limites de alerta e controlar a intensidade da iluminação em tempo real.

## 🎯 Objetivos

- Monitorar temperatura, umidade e luminosidade.
- Automatizar o controle da iluminação conforme a luz ambiente.
- Permitir controle manual do brilho pela dashboard.
- Emitir alertas visuais e sonoros para condições fora dos limites.
- Exibir informações em displays LCD nos dispositivos.
- Registrar e consultar dados por meio da plataforma FIWARE.
- Disponibilizar uma interface web para monitoramento e administração.

## 🏗️ Arquitetura

O sistema possui cinco componentes principais:

1. **ESP32 Monitor:** leitura dos sensores DHT22 e LDR, publicação de dados e emissão de alertas.
2. **ESP32 Atuador:** controle PWM da iluminação e confirmação do estado aplicado.
3. **Infraestrutura FIWARE:** processamento e armazenamento de dados com Orion, IoT Agent, STH-Comet, MongoDB e Mosquitto.
4. **Backend FastAPI:** integração com os serviços FIWARE, consultas, gerenciamento de alertas e comandos de controle.
5. **Dashboard Web:** visualização das informações e interação com o sistema.

### Fluxo simplificado

```text
ESP32 Monitor ── MQTT ── Mosquitto ── IoT Agent ── Orion
      │                                              │
      └── Comandos de brilho ── ESP32 Atuador        │
                                                     │
                                STH-Comet / MongoDB
                                                     │
                                    Backend FastAPI
                                            │
                                     Dashboard Web
```

## 🔌 Hardware simulado

### ESP32 Monitor

- ESP32 com MicroPython.
- Sensor DHT22 para temperatura e umidade.
- Sensor LDR para luminosidade.
- LED azul para alertas.
- Buzzer para avisos sonoros.
- Display LCD 16x2 com comunicação I2C.

O monitor realiza leituras ambientais, publica os dados via MQTT e emite alertas conforme os limites configurados.

### ESP32 Atuador

- ESP32 com MicroPython.
- LED controlado por PWM.
- Resistor de proteção.
- Display LCD 16x2 com comunicação I2C.

O atuador recebe comandos de intensidade luminosa, aplica o brilho solicitado e publica confirmações de estado.

## 💡 Controle inteligente da iluminação

O sistema oferece dois modos de operação:

**Automático:** a intensidade do LED é ajustada de acordo com as leituras do sensor LDR.

**Manual:** o usuário define o brilho diretamente pela dashboard.

O atuador confirma o brilho aplicado por MQTT, permitindo sincronizar as informações exibidas na interface e nos dispositivos.

## 🚨 Alertas e monitoramento

O sistema permite configurar limites para:

- Temperatura.
- Umidade.
- Luminosidade.

Quando uma condição ultrapassa os limites definidos, a aplicação pode registrar alertas e acionar os indicadores visuais e sonoros do monitor.

O backend também identifica situações em que os dados deixam de ser atualizados.

## 🖥️ Dashboard

A interface web reúne:

- Leituras dos sensores.
- Indicadores de estado dos dispositivos.
- Gráficos e histórico de medições.
- Controle manual e automático de iluminação.
- Configuração de limites ambientais.
- Consulta e gerenciamento de alertas.
- Recursos de administração FIWARE.

A dashboard foi desenvolvida com HTML, CSS e JavaScript e utiliza a API FastAPI.

## 🛠️ Tecnologias utilizadas

| Camada | Tecnologias |
|---|---|
| Dispositivos | ESP32, MicroPython, Wokwi |
| Sensores e atuadores | DHT22, LDR, LED PWM, buzzer, LCD I2C |
| Comunicação | MQTT, HTTP, NGSI-v2 |
| Plataforma IoT | FIWARE Orion, IoT Agent UltraLight, STH-Comet |
| Mensageria | Eclipse Mosquitto |
| Banco de dados | MongoDB |
| Backend | Python, FastAPI, Uvicorn |
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
│   └── marca.svg
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
├── .gitignore
└── README.md
```

## 🚀 Como executar

### 1. Pré-requisitos

- Python e pip.
- Acesso a uma infraestrutura FIWARE com MQTT.
- Navegador web.
- Projetos ESP32 no Wokwi.
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
python -m pip install -r backend/requirements.txt
```

### 4. Configurar a conexão com a AWS

No arquivo `backend/main.py`, confira o endereço definido em `IP_SERVIDOR`.

Configure também o endereço do broker MQTT nos projetos Wokwi conforme a infraestrutura utilizada.

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

- **Monitor:** https://wokwi.com/projects/477273550482344961
- **Atuador:** https://wokwi.com/projects/477273561317281793

Confira as configurações de rede e MQTT antes de iniciar as simulações.

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

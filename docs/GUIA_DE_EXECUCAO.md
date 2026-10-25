# Guia de Execução — Vinheria Agnello (CP5)

Este guia explica como **reproduzir o ambiente de software já desenvolvido**. A montagem física (hands-on) é uma etapa separada e ainda depende dos componentes reais.

## 1. Baixar o projeto

```bash
git clone https://github.com/vinifcavalcanti/vinheria-agnello-iot-cp5.git
cd vinheria-agnello-iot-cp5
```

Na raiz estão as pastas `backend/`, `dashboard/`, `esp32-monitor/`, `esp32-atuador/` e `infraestrutura/`.

## 2. Confirmar a AWS/FIWARE

O ambiente utilizado nos testes foi uma instância **AWS EC2 Ubuntu** com Docker, contendo:

| Serviço | Porta no host |
|---|---|
| Orion | 1026 |
| IoT Agent UL | 4041 |
| STH-Comet | 8666 |
| Mosquitto MQTT | 1883 |
| Mosquitto 9001 | Mapeada no Compose; uso efetivo depende da configuração do broker |
| MongoDB histórico | 27017 — evitar exposição pública |
| MongoDB interno | Sem porta publicada |

No terminal da EC2, uma consulta **somente de leitura** para conferir os serviços:

```bash
sudo docker ps -a
```

O Compose documentado fica em `infraestrutura/docker-compose.yml`, com a configuração do broker em `infraestrutura/mosquitto/mosquitto.conf`. **Não execute um novo Compose sobre a instância existente sem conferir o ambiente, os volumes e as credenciais.** Em uma instalação nova, será preciso também configurar/provisionar os recursos FIWARE (entidades, IoT Agent, assinaturas e histórico) usados pelo sistema: iniciar os contêineres, por si só, não cria esses recursos.

## 3. Atualizar o IP público da EC2

O último IPv4 utilizado durante os testes foi **`54.237.148.216`**, mas ele pode mudar quando a instância for parada/iniciada.

Confira e, se necessário, atualize:

1. `backend/main.py`: variável `IP_SERVIDOR`.
2. `esp32-monitor/main.py`: endereço MQTT da AWS.
3. `esp32-atuador/main.py`: endereço MQTT da AWS.
4. Projetos originais no Wokwi: atualize e clique em **Save** em cada um, pois não sincronizam com o GitHub.

## 4. Iniciar o backend FastAPI

É necessário ter Python e pip no computador.

**Windows — PowerShell (na raiz do repositório):**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --port 8000
```

**Linux/macOS (na raiz):**

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r backend/requirements.txt
./.venv/bin/python -m uvicorn main:app --app-dir backend --port 8000
```

Acesse `http://127.0.0.1:8000/` e `http://127.0.0.1:8000/docs`. Para verificar a consulta aos sensores, use `http://127.0.0.1:8000/sensores`.

> **Atenção:** o `backend/main.py` foi testado na porta 8001 usando `--app-dir backend`, e respondeu às consultas do Orion. Caso a porta 8000 já esteja ocupada, use `--port 8001` e ajuste o endereço da API usado pela dashboard, se necessário.

## 5. Iniciar a dashboard

Abra **outro terminal** na raiz do repositório. Com o Python disponível:

```bash
python -m http.server 5500
```

Em alguns ambientes Linux/macOS, use `python3` em vez de `python`.

Abra `http://127.0.0.1:5500/dashboard/`.

Confira em `dashboard/core.js` e `dashboard/app.js` a **URL da API** configurada. A dashboard e o backend precisam estar acessíveis um ao outro. Evite abrir `index.html` diretamente como arquivo local (`file://`).

## 6. Iniciar os ESP32 no Wokwi

- [Monitor — sensores, buzzer, LED de alerta e LCD](https://wokwi.com/projects/477273550482344961)
- [Atuador — brilho PWM, modo e LCD](https://wokwi.com/projects/477273561317281793)

Abra os dois projetos, confira o IP do broker, salve e execute as simulações. Os diretórios locais incluem `main.py`, `diagram.json`, `lcd_api.py` e `i2c_lcd.py` de cada ESP32.

Se um Wokwi ficar aberto em segundo plano e perder a conexão MQTT, confira os logs seriais e tente reiniciar **a simulação**, sem alterar a AWS automaticamente.

## 7. Verificação rápida do sistema

- [ ] Orion responde em `http://IP_DA_AWS:1026/version`.
- [ ] FastAPI responde em `/`.
- [ ] FastAPI responde em `/sensores` com dados do FIWARE.
- [ ] Monitor publica as leituras; LCD apresenta os valores.
- [ ] Atuador recebe comandos MQTT; LED PWM e LCD refletem o estado.
- [ ] Atuador alterna as telas de iluminação, temperatura, umidade e luz, sem `*` no fim da segunda linha (limites da dashboard recebidos).
- [ ] O botão "Verificar serviços" (em Configurar conexão) mostra API, FIWARE, MQTT e limites em verde.
- [ ] Dashboard mostra sensores e permite controle manual/automático.
- [ ] Alarmes e histórico são testados com valores adequados ao ambiente.

Se o Orion responder, mas a API der timeout, **confira primeiro `IP_SERVIDOR` e reinicie o Uvicorn**, antes de alterar contêineres. Consultas diretas ao Orion podem exigir os cabeçalhos `fiware-service: smart` e `fiware-servicepath: /`.

## 8. Testar a atuação ambiental no Wokwi

O DHT22 e o LDR do Wokwi permitem mudar os valores clicando no componente durante a simulação. Com o backend, os dois ESP32 e a dashboard rodando:

1. **Inicialização:** os dois LCDs mostram "GRUPO DEBUGGERS" e "VINHERIA AGNELLO / ESP32 ATUADOR" (ou "ESP32 MONITOR"), cerca de 3 s, e depois `Conectando WiFi`.
2. **Limites:** na dashboard, em *Limites & alertas*, salve temperatura 15–20 °C e umidade 50–80%. A mensagem deve ser "salvos no limites.json e enviados aos ESPs". O `*` some do LCD do Atuador.
3. **Temperatura:** no DHT22 do Monitor, use 25 °C → `RESFRIAR` e LED vermelho piscando; 13 °C → `AQUECER`; 18 °C → `NORMAL` e LED apagado.
4. **Umidade:** 45% → `UMIDIFICAR`; 90% → `DESUMIDIFICAR`; 65% → `NORMAL`.
5. **Ambos fora da faixa:** o LED continua piscando e o LCD mostra as duas ações nas telas alternadas.
6. **Iluminação:** com o LDR no escuro (ADC alto), o brilho vai a 100% e a tela de luz mostra uma % baixa (ex.: `Luz: 2%`) e `AUMENTAR LUZ`; com muita luz (ADC baixo), 0%, `Luz: 99%` e `DIMINUIR LUZ`. O LCD do Monitor mostra a mesma `Luz: X%` e a dashboard exibe o mesmo valor no card de luminosidade.
7. **Modo manual:** aplique 25% pela dashboard. O Atuador mostra `Modo: Manual` / `Brilho: 25%` e ignora o Monitor. Volte ao automático em seguida.
8. **Mudança de limites ao vivo:** com 18 °C, mude a faixa para 20–30 °C. A tela muda para `AQUECER` sem reiniciar o ESP.
9. **Monitor desligado:** pare a simulação do Monitor. Após cerca de 15 s, o Atuador mostra `DADOS ANTIGOS` e apaga o LED vermelho.
10. **Reconexão:** reinicie só o Atuador. Ele deve receber os limites retidos na hora (sem `*`) e voltar a decidir assim que o Monitor publicar.
11. **Dashboard:** o painel "Correções indicadas pelo ESP atuador" mostra "Confirmado pelo ESP" com as mesmas ações do LCD.

## 9. Hands-on físico (pendente)

A simulação está pronta, mas a montagem precisa ser validada com as peças reais. Antes de ligar, compare o esquema `diagram.json` com o hardware, confira os níveis de tensão, resistores, alimentação do LCD e pinos de entrada/saída. Verifique também a rede Wi-Fi real: a rede `Wokwi-GUEST` existe no simulador e **não será utilizada no ESP32 físico**.

## Segurança e origem

A infraestrutura foi baseada em material disponibilizado pelo professor e usa parâmetros adequados apenas a uma demonstração acadêmica. MQTT anônimo, senhas de exemplo e portas publicadas não devem ser replicados num ambiente de produção ou rede pública irrestrita.

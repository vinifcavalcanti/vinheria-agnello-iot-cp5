# Estado do Projeto — Vinheria Agnello (CP5)

**Equipe:** Grupo DEBUGGERS — FIAP | Edge Computing  
**Objetivo deste documento:** transferir o estado atual do trabalho aos integrantes que vão continuar o CP5.

## Visão geral

O **software desenvolvido nesta etapa está concluído e foi validado no ambiente de simulação**: dois ESP32 em MicroPython no Wokwi, backend FastAPI, comunicação MQTT/FIWARE e dashboard web. O repositório foi criado para **compartilhar essa base com o grupo**, não para indicar que toda a entrega acadêmica esteja terminada.

**Hands-on:** o ESP32 Monitor físico usa DHT11, LDR, LED azul e buzzer, com o mesmo `main.py` da simulação (sensor e Wi-Fi configuráveis no topo do arquivo). As instruções de montagem estão no *Manual de hardware* do README.

## Implementado e testado em simulação

| Área | Situação | Observações |
|---|---|---|
| ESP32 Monitor (Wokwi) | Concluído em simulação | DHT22, LDR, LED de alerta, buzzer, LCD I2C, publicação MQTT e comandos automáticos |
| ESP32 Atuador (Wokwi) | Concluído em simulação | LED PWM, modos automático/manual, confirmação de estado e LCD I2C |
| Atuação ambiental simbólica | Implementada; falta validar no Wokwi | LED vermelho no GPIO 27, decisões AQUECER/RESFRIAR/UMIDIFICAR/DESUMIDIFICAR, 4 telas no LCD, limites sincronizados por MQTT (retain). Testada em simulação local; ver o guia de execução, seção 8 |
| Comunicação MQTT | Validada em testes | Comandos de brilho, estados e alertas; ocorreram reconexões intermitentes no Wokwi |
| FIWARE na AWS | Funcionando nos testes realizados | Orion, IoT Agent UL, STH-Comet, Mosquitto e dois MongoDBs em Docker |
| Backend FastAPI | Validado localmente | Inicialização de `backend/main.py`; consultas de sensores ao Orion pelo IP atualizado |
| Dashboard web | Base funcional | Leituras, histórico, alertas, controle de brilho, limites e recursos administrativos FIWARE |
| Repositório GitHub | Publicado | Código compartilhado como base de continuidade |

**Importante:** esses testes comprovam funcionamento nos ambientes usados; **não substituem testes com dispositivos físicos** nem garantem disponibilidade futura da instância AWS.

## Preparação para o hands-on

- [x] Código dos ESP32 preparado para o hardware físico: `MODELO_DHT` (DHT11/DHT22), `WIFI_SSID`/`WIFI_SENHA` e LCD opcional (detecção automática em `0x27`/`0x3F`).
- [x] Manual de hardware com as ligações de cada componente (README).
- [x] Dashboard final integrada: gráficos dinâmicos (STH-Comet :8666), cadastro de dispositivos e ajuste de triggers.
- [x] Simulações Wokwi atualizadas e validadas com a AWS.
- [ ] Montar e gravar o ESP32 físico no laboratório e validar o fluxo ponta a ponta com a AWS.
- [ ] Registrar fotos e vídeo do funcionamento para a entrega.

## Pontos de atenção para quem assumir

1. **Não apagar nem reprovisionar entidades FIWARE sem antes verificar o ambiente.** A infraestrutura contém dados e configurações já usados nos testes.
2. **O IP público da EC2 é dinâmico.** Ao reiniciar a instância, confira o IP no backend e nos dois projetos Wokwi (e nos arquivos locais correspondentes).
3. **Wokwi e GitHub são cópias independentes.** Alterar o código no GitHub não atualiza automaticamente a simulação publicada no Wokwi.
4. **Não executar `docker compose down -v` na infraestrutura existente.** Isso pode remover volumes de dados.
5. A dashboard atual usa uma API local; publicar apenas os arquivos estáticos não torna o backend automaticamente acessível pela internet.
6. As credenciais e permissões presentes no Compose são **de demonstração acadêmica**, não adequadas a um servidor público de produção.

## Ponto de partida

Leia, nesta ordem: `GUIA_DE_EXECUCAO.md`, `ARQUITETURA_E_INTEGRACAO.md` e `DASHBOARD.md`. Para continuar o hands-on, parta dos circuitos `diagram.json` de cada projeto e confira as ligações dos componentes reais antes de energizar.

## Links

- [Repositório-base do grupo](https://github.com/vinifcavalcanti/vinheria-agnello-iot-cp5)
- [ESP32 Monitor no Wokwi](https://wokwi.com/projects/477273550482344961)
- [ESP32 Atuador no Wokwi](https://wokwi.com/projects/477273561317281793)

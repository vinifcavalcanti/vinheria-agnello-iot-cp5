# Estado do Projeto — Vinheria Agnello (CP5)

**Equipe:** Grupo DEBUGGERS — FIAP | Edge Computing  
**Objetivo deste documento:** transferir o estado atual do trabalho aos integrantes que vão continuar o CP5.

## Visão geral

O **software desenvolvido nesta etapa está concluído e foi validado no ambiente de simulação**: dois ESP32 em MicroPython no Wokwi, backend FastAPI, comunicação MQTT/FIWARE e dashboard web. O repositório foi criado para **compartilhar essa base com o grupo**, não para indicar que toda a entrega acadêmica esteja terminada.

**A etapa pendente é o hands-on:** montagem e integração dos componentes físicos, testes em hardware real e evidências da entrega. Outro integrante poderá aprimorar o visual/experiência da dashboard, preservando suas integrações.

## Implementado e testado em simulação

| Área | Situação | Observações |
|---|---|---|
| ESP32 Monitor (Wokwi) | Concluído em simulação | DHT22, LDR, LED de alerta, buzzer, LCD I2C, publicação MQTT e comandos automáticos |
| ESP32 Atuador (Wokwi) | Concluído em simulação | LED PWM, modos automático/manual, confirmação de estado e LCD I2C |
| Comunicação MQTT | Validada em testes | Comandos de brilho, estados e alertas; ocorreram reconexões intermitentes no Wokwi |
| FIWARE na AWS | Funcionando nos testes realizados | Orion, IoT Agent UL, STH-Comet, Mosquitto e dois MongoDBs em Docker |
| Backend FastAPI | Validado localmente | Inicialização de `backend/main.py`; consultas de sensores ao Orion pelo IP atualizado |
| Dashboard web | Base funcional | Leituras, histórico, alertas, controle de brilho, limites e recursos administrativos FIWARE |
| Repositório GitHub | Publicado | Código compartilhado como base de continuidade |

**Importante:** esses testes comprovam funcionamento nos ambientes usados; **não substituem testes com dispositivos físicos** nem garantem disponibilidade futura da instância AWS.

## Pendente para conclusão do CP5

- [ ] Montar fisicamente os circuitos do Monitor e do Atuador com os componentes disponíveis.
- [ ] Confirmar pinagem, alimentação, compatibilidade dos módulos e proteção elétrica no hardware real.
- [ ] Adaptar os códigos MicroPython apenas onde o hardware físico exigir (por exemplo, diferenças de LDR, LCD, Wi-Fi e PWM).
- [ ] Testar comunicação ponta a ponta com os dois ESP32 físicos e a AWS.
- [ ] Validar alertas, comandos de iluminação, LCDs, histórico e dashboard durante o hands-on.
- [ ] Registrar fotos, vídeos, testes e resultados exigidos pelo professor.
- [ ] Integrar eventuais melhorias visuais feitas pelo integrante responsável pela dashboard.
- [ ] Consolidar a entrega final no repositório definido pelo grupo.

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

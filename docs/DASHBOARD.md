# Guia da Dashboard — Vinheria Agnello (CP5)

**Público-alvo:** integrante responsável por melhorar o design e a experiência de uso da dashboard, aproveitando a integração já desenvolvida.

## Situação atual

A dashboard **já funciona em ambiente local**, integrada ao backend FastAPI e aos serviços FIWARE utilizados no projeto. Ela pode receber melhorias visuais e de usabilidade, mas sua reestruturação **não deve eliminar os recursos de controle e monitoramento existentes**.

A montagem física do hands-on ainda está pendente. A dashboard pode ser aprimorada independentemente, utilizando os dados do Wokwi e da AWS durante os testes.

## Arquivos

| Arquivo | Papel principal |
|---|---|
| `dashboard/index.html` | Estrutura da interface |
| `dashboard/styles.css` | Aparência, responsividade e componentes visuais |
| `dashboard/app.js` | Comportamento da aplicação e eventos da interface |
| `dashboard/core.js` | Lógica compartilhada e integração HTTP/API |
| `dashboard/marca.svg` | Identidade visual utilizada pela dashboard |

Antes de mover funções entre `app.js` e `core.js`, verifique suas referências reais no projeto.

## Funcionalidades a preservar

- Leituras atuais de temperatura, umidade e luminosidade.
- Exibição de status dos dispositivos, incluindo a atualização dos dados.
- Gráficos e consultas de histórico via FIWARE/STH-Comet.
- Controle da iluminação em **modo automático** e **modo manual**.
- Envio do brilho desejado e apresentação do **estado confirmado pelo atuador**, não apenas do valor solicitado.
- Configuração de limites ambientais.
- Listagem e gerenciamento de alertas.
- Recursos de administração FIWARE já desenvolvidos (entidades, assinaturas, IoT Agent e demais seções existentes).

## Fluxo técnico

```text
Navegador
   |
   | HTTP (fetch)
   v
FastAPI — backend/main.py
   |                  \
   |                   \ MQTT: comandos e confirmações
   v                    v
Orion / STH-Comet     Mosquitto → ESP32 Atuador
```

A dashboard **não deve presumir** que o ESP32 aplicou um comando só porque a chamada HTTP foi enviada. Sempre que possível, use o retorno de estado real disponível na API.

## Executar para desenvolver

1. Confira o IP público da AWS no `backend/main.py`.
2. Inicie o backend, na raiz do repositório, usando o Python do ambiente virtual:

   ```bash
   python -m uvicorn main:app --app-dir backend --port 8000
   ```

3. Em outro terminal, na raiz do repositório:

   ```bash
   python -m http.server 5500
   ```

4. Acesse `http://127.0.0.1:5500/dashboard/`.
5. Se houver erro de API, confira em `dashboard/core.js` e `dashboard/app.js` a URL/base da API e consulte `http://127.0.0.1:8000/docs`.

> O comando `python` pressupõe um ambiente em que as dependências já estejam instaladas. Para a instalação inicial, siga `GUIA_DE_EXECUCAO.md`.

## Recomendações para quem vai melhorar o design

- Priorize alterações incrementais em layout, CSS, acessibilidade e responsividade.
- Preserve identificadores do HTML que sejam usados por seletores JavaScript.
- Não renomeie rotas, payloads ou campos da API sem coordenar a alteração com o backend.
- Evite misturar simulação de dados fictícios aos dados reais sem identificação clara.
- Mostre estados de carregamento, falha de comunicação e dados desatualizados.
- Teste as telas em computador e celular.
- Se refatorar a interface, faça alterações pequenas e teste leitura, controle manual, controle automático, alarmes e histórico após cada etapa.
- Prefira trabalhar em uma branch própria antes de integrar as mudanças no repositório final do grupo.

## Checklist de regressão

- [ ] Dashboard abre por HTTP local, sem erros de JavaScript no console.
- [ ] Leituras de sensores chegam da API.
- [ ] Status offline/dados desatualizados é exibido corretamente.
- [ ] Histórico e gráficos funcionam com dados disponíveis.
- [ ] Controle manual envia comandos e mostra estado confirmado.
- [ ] Modo automático funciona sem ser sobrescrito pela interface.
- [ ] Alterações de limites continuam sendo persistidas pelo backend.
- [ ] Alertas continuam aparecendo e mudando de estado.
- [ ] Seções administrativas FIWARE continuam operacionais.
- [ ] Interface permanece utilizável em telas menores.

## Publicação na web

O GitHub Pages pode servir **somente a parte estática** da dashboard. Ele **não executa FastAPI** e endereços como `127.0.0.1:8000` são locais ao computador de quem abre a página. Para abrir a dashboard completa em outro computador sem executar o backend localmente, será necessária uma API remotamente acessível, com HTTPS e proteção dos endpoints administrativos. Essa implantação **não foi realizada nesta etapa**.

## Para alterar com segurança

A documentação interativa `http://127.0.0.1:8000/docs` é a referência mais confiável para os endpoints existentes no backend. Sempre compare o comportamento visual com o sistema já funcionando antes de substituir arquivos.

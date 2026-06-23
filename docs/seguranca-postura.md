# Postura de segurança — Compre Barato Alagoas

Este documento descreve o **modelo de ameaça** e as **fronteiras de controle** do
projeto. Serve para revisões de segurança, scanners e quem avalia se o código
aberto é compatível com a operação em produção.

**Resumo:** a API de aplicação é **pública por desenho** (o app Flutter/web é um
cliente não confiável). O código-fonte pode permanecer **open source**. A proteção
não vem de esconder rotas no GitHub; vem de **segredos fora do repositório**,
**admin fechado por padrão**, **limites de abuso**, **minimização de dados (LGPD)**
e **desligar a UI interativa do OpenAPI em produção**.

Documentação relacionada no site estático:

- [Segurança & dados (LGPD)](seguranca-e-dados.html)
- [LGPD · Medição de uso](lgpd-medicao-de-uso.html)
- [Política de privacidade (app)](https://alagoas.precospublicos.ia.br/privacy.html)

---

## 1. O que é público de propósito

| Superfície | Por quê existe | Controle principal |
|------------|----------------|--------------------|
| Código no GitHub (MIT) | Transparência, confiança LGPD, reuso cívico | Segredos **nunca** no git; ver `.gitignore` e `.env.example` |
| `POST /api/v1/search` e rotas de produto | O app precisa chamar o backend | Rate limit diário, validação de entrada, cache, sem PII desnecessária na resposta |
| Site de documentação (`docs.*`) | Explicar produto e privacidade | Conteúdo orientado a usuário/operador; sem credenciais |
| Dados de preço (origem SEFAZ-AL) | Dados públicos de NFC-e | Token SEFAZ só no servidor (painel admin cifrado ou bootstrap no `.env` da VPS) |

**Achado típico de scanner:** “API documentada / endpoints visíveis.”  
**Resposta deste projeto:** o cliente (navegador ou APK) já revela o contrato. Código
aberto e documentação de produto **não** substituem autenticação nem limites; e
**não** são, por si só, vulnerabilidade se os controles abaixo estiverem ativos.

---

## 2. O que *não* é fronteira de segurança

- **Visibilidade do repositório público** — ocultar o código não remove a API em
  `https://alagoas.precospublicos.ia.br`. Quem quiser abusar ainda fala HTTPS com o
  backend.
- **Só confiar em “ninguém sabe a URL do admin”** — o painel usa subdomínio
  separado, mas a API admin exige token; sem token responde **401** (fail-closed).
- **Swagger/ReDoc em produção** — facilita varredura automatizada e não é necessário
  ao app. Por isso fica **desligado em produção** (ver §4).

---

## 3. Superfícies e controles

### 3.1 API de aplicação (usuário)

- Clientes **não autenticados de conta** (sem login/senha); identidade de dispositivo
  é opcional e usada para consentimento/listas na nuvem (LGPD).
- Token de dispositivo: gerado no cliente, **armazenado no servidor só como hash
  com sal** — um dump de Redis não devolve o bearer utilizável.
- Buscas: limite diário configurável (`DAILY_SEARCH_LIMIT`), chaveada de forma a
  evitar abuso trivial.
- Localização: usada na busca; política de **não reter** trajetos como perfil.
- Erros: `X-Request-ID` para correlação em suporte, sem vazar stack ao usuário.

### 3.2 API administrativa (`/admin/api/*`)

- Desligada na prática se `ADMIN_TOKEN` estiver vazio (**401**).
- Comparação de token em **tempo constante** (`hmac.compare_digest`).
- Servida em vhost próprio (`admin.<domínio>`); mesmo backend, origem separada.
- Cofre de segredos (ex.: token SEFAZ): escrita via painel, **Fernet** em repouso no
  Redis; a API de status devolve só *fingerprint*, não o segredo.

### 3.3 Segredos e configuração

| Segredo | Onde vive | Não vive em |
|---------|-----------|-------------|
| `ADMIN_TOKEN` | `.env` só no servidor | git, app cliente, respostas JSON |
| `SECRET_ENCRYPTION_KEY` | `.env` só no servidor | git, backups públicos |
| Token SEFAZ | Preferencialmente painel → Redis cifrado; fallback `SEFAZ_APP_TOKEN` no `.env` da VPS | repositório público |
| `ANTHROPIC_API_KEY` | `.env` da VPS | cliente Flutter, commits |
| Postgres / Redis | rede interna Docker; API publicada só em `127.0.0.1:8000` no host | internet direta |

Material operacional sensível (notas de sessão, guias on-device com paths de máquina,
arte-fonte extra) fica no repositório **privado** do time, não no produto público.

### 3.4 LLM / SEFAZ (amplificação de custo)

- Entrada do usuário tratada como **dados inertes** no prompt (regras de segurança no
  system prompt; fallback determinístico se o modelo falhar ou for desviado).
- Fan-out SEFAZ limitado (`SEFAZ_CONCURRENCY`, páginas, raio/dias dentro do permitido
  pela API pública).
- Cache Redis reduz repetição de consultas iguais.

### 3.5 Frontend estático e app

- Admin e docs de produto são **HTML/JS estáticos** sem renderizar entrada arbitrária
  de usuário no servidor.
- App Links / `assetlinks.json` usam fingerprint de certificado de assinatura (esperado
  em Android); não é credencial de API.

---

## 4. OpenAPI / Swagger em produção

Comportamento do backend (`ENVIRONMENT` + opcional `EXPOSE_API_DOCS`):

| Ambiente | `/docs`, `/redoc`, `/openapi.json` |
|----------|-------------------------------------|
| `development` (padrão local) | **Ligados** — útil para dev e testes |
| `production` (compose de deploy define isso) | **Desligados** (404) |
| Qualquer um + `EXPOSE_API_DOCS=true` | Ligados (escape hatch) |
| Qualquer um + `EXPOSE_API_DOCS=false` | Desligados |

O nginx do app usuário só faz proxy de **`/api` e `/health`** para o FastAPI; não
publica mais `/docs` nem `/openapi.json` na borda.

**Importante:** desligar a UI do OpenAPI **não** “esconde” o contrato do app — o
cliente continua chamando as mesmas rotas. Reduz ruído em pentests automatizados e
evita que a superfície *interativa* de documentação rode em produção sem necessidade.

A visão humana dos endpoints permanece na [documentação do produto](index.html#api)
(site `docs.*`), em linguagem de produto — não como consola de exploração no mesmo
host da API.

---

## 5. Resposta a achados frequentes

| Achado | Severidade que adotamos | Tratamento |
|--------|-------------------------|------------|
| “API pública / documentada” | Informativo se controles §3 ok | Manter open source; citar este doc; garantir §4 em prod |
| OpenAPI/Swagger em produção | Baixa/média higiene | Desligado por padrão em `production` |
| Admin sem autenticação | Crítica se `ADMIN_TOKEN` vazio e rota acessível com dados | Fail-closed; configurar token forte na VPS |
| Segredo no repositório | Crítica | Rotacionar; nunca commitar `.env` |
| Abuso / scraping / custo LLM | Média operacional | Rate limit, cache, mocks em dev, monitorar admin |
| Prompt injection | Média (integridade/custo) | Prompt endurecido + fallback mock + testes dedicados |

---

## 6. O que auditores / scanners devem verificar

Checklist objetivo (além de “tem OpenAPI?”):

1. Em produção com `ENVIRONMENT=production`, `GET /docs` e `GET /openapi.json` → **404**.
2. `GET /admin/api/...` sem token → **401**.
3. Nenhum `.env` real, chave PEM ou token SEFAZ no histórico público relevante.
4. Redis/Postgres não publicados na internet (só rede do compose + proxy local).
5. CORS de produção **não** é `*` se houver credenciais cross-origin sensíveis (ajustar
   `CORS_ORIGINS` no `.env` da VPS).
6. Política de privacidade e minimização alinhadas ao código (hashes, consentimento
   para listas na nuvem).

---

## 7. Open source de propósito

Mantemos o código da aplicação público porque:

1. Os dados de preço já são públicos (SEFAZ-AL); o valor está na **ponte segura** e na
   UX honesta, não num algoritmo secreto de Estado.
2. Alegações de LGPD e “não vendemos sua busca” ficam **auditáveis**.
3. Fechar o GitHub **não fecha** a API HTTPS do app.

O que fica restrito ao time (repositório privado ou só na VPS) são **segredos de
operação**, notas internas e eventuais relatórios informais — não o desenho de
segurança descrito aqui.

---

## 8. Limitações honestas

- Quem tem **root na VPS** pode ler memória de processo e o `.env` no disco; mitigação
  completa exigiria HSM/KMS externo (fora do escopo atual de uma VPS única).
- Rate limit e cache dependem do Redis saudável; sem Redis a API nem sobe (falha
  rápida).
- Este texto **não** substitui pentest formal nem laudo LGPD de DPO externo; é a
  postura do projeto para orientar implementação e revisão.

---

*Última orientação alinhada ao código: docs interativos desligados em produção;
controles em `backend/app/config.py` (`api_docs_enabled`), `backend/app/main.py` e
`deploy/nginx/alagoas.precospublicos.ia.br.conf`.*

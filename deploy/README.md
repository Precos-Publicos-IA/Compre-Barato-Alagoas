# Deploy — Compre Barato Alagoas

Sobe o projeto em um servidor Linux com Docker, atrás de um **nginx + certbot** que já
faça o TLS. Nada específico de um servidor é versionado: host, usuário, chave SSH e
diretório são passados por variáveis de ambiente; segredos ficam em um único `.env`.

## Topologia

```
Internet → nginx do host (TLS, certbot)
            ├── /                → web Flutter estática em <DEPLOY_DIR>/web
            └── /api,/health,... → reverse proxy 127.0.0.1:8000 (Docker)
Docker (compose, deploy/):
   api (FastAPI, 127.0.0.1:8000) · postgres (pgvector) · redis
```

Só a porta da API é publicada, e apenas em `localhost`.

## Configuração

Toda a configuração vive em **um único `.env` na raiz do repositório** (copie de
`.env.example`). Ele alimenta tanto o backend quanto o `docker-compose`. O `.env`
**nunca** é versionado nem enviado pelo deploy — fica somente no servidor.

O destino do deploy é informado por variáveis de ambiente ao rodar `deploy.sh`:

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DEPLOY_HOST` | `usuario@host` do servidor | `deploy@your-server.example.com` |
| `DEPLOY_SSH_KEY` | caminho da chave SSH privada | `~/.ssh/id_ed25519` |
| `DEPLOY_DOMAIN` | domínio público servido pelo nginx | domínio de produção |
| `DEPLOY_DIR` | diretório do app no servidor | `/srv/apps/compre-barato-alagoas` |

## Primeiro deploy

A partir de uma máquina com o repositório e o Flutter instalados:

```bash
# 1) Suba código + builds e crie os containers.
DEPLOY_HOST=usuario@SEU_SERVIDOR \
DEPLOY_SSH_KEY=~/.ssh/sua_chave \
DEPLOY_DIR=/srv/apps/compre-barato-alagoas \
  deploy/deploy.sh

# 2) No servidor, defina os segredos no .env (na raiz de DEPLOY_DIR).
ssh -i ~/.ssh/sua_chave usuario@SEU_SERVIDOR
cd /srv/apps/compre-barato-alagoas
nano .env       # defina POSTGRES_PASSWORD; mantenha USE_MOCK_* = true por enquanto
cd deploy && docker compose --env-file ../.env up -d
curl -s http://127.0.0.1:8000/health    # espera status ok

# 3) Configure o vhost do nginx + TLS (um vhost novo; os demais sites ficam intactos).
sudo cp deploy/nginx/alagoas.precospublicos.ia.br.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/alagoas.precospublicos.ia.br.conf \
           /etc/nginx/sites-enabled/
#   Ajuste o `root` do vhost para <DEPLOY_DIR>/web.
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d SEU_DOMINIO      # emite e instala o certificado

# 4) Teste final.
curl -s https://SEU_DOMINIO/health
```

## CI/CD (deploy automático a cada push na `main`)

O workflow `.github/workflows/deploy.yml` faz deploy automático a cada push na
`main`, mas **só faz o que mudou de verdade** (job `changes` detecta os caminhos):

| Mudou… | O que o pipeline faz |
|--------|----------------------|
| `backend/**` | roda `pytest`, reconstrói a imagem e reinicia o stack |
| `frontend/**` | reconstrói a web Flutter + APK e sincroniza (sem reiniciar a API) |
| `deploy/**`, `.env.example`, o próprio workflow | sincroniza e reinicia o stack com a imagem atual |
| `admin-frontend/**` | só sincroniza o dashboard (sem rebuild/restart) |
| `docs/**` | só sincroniza o site de docs (sem rebuild/restart) |
| só `README.md` / `LICENSE` / `.gitignore` / `shared-assets/**` | **nada** — o pipeline nem inicia |

Detalhes do deploy quando há código:
- a imagem do backend (Dockerfile multi-stage, enxuta) é construída **no runner**,
  nunca no servidor — nenhum cache de build se acumula no host compartilhado;
- envio por SSH: imagem via `docker save | docker load` (sem registry), estáticos via `rsync`;
- antes de tocar no host há uma **checagem de disco** (aborta se houver < ~2 GB livres);
  `deploy/remote-update.sh` sobe o stack, remove imagens antigas **só deste app** e roda health check.
- `workflow_dispatch` (Run workflow) força um deploy completo — útil para redeploy/rollback.

Configure uma vez os *secrets* do repositório (nada específico do host fica versionado):

| Secret | Conteúdo |
|--------|----------|
| `DEPLOY_HOST` | `usuario@host` do servidor |
| `DEPLOY_SSH_KEY` | chave SSH **privada** do deploy (conteúdo do arquivo) |
| `DEPLOY_DIR` | diretório do app no servidor |
| `DEPLOY_DOMAIN` | domínio público (usado no build do Flutter) |

O nginx/TLS do host **não** é tocado pelo pipeline (segue gerido à mão no servidor).
Para rodar manualmente sem push, use **Actions → este workflow → Run workflow**.

## Atualizações manuais (fallback)

`deploy.sh` reconstrói a web + APK, sincroniza backend/deploy/web e recria os
containers **construindo a imagem no próprio servidor**. É o caminho de emergência;
o normal é deixar o CI/CD acima cuidar do deploy. Rode-o com as mesmas variáveis de
ambiente do primeiro deploy.

## O que o CI sincroniza vs. o que fica só no git (#289)

| Mudança no repositório | Efeito em produção |
|------------------------|--------------------|
| `backend/**` | pytest, imagem API, restart compose |
| `frontend/**` | build web+APK, rsync `web/` (+ APK) |
| `admin-frontend/**` | rsync `admin/` |
| `docs/**` | rsync `docs/` (site docs.*) |
| `deploy/**` (compose, nginx **exemplos**, `well-known/`, scripts) | rsync `deploy/` + possível restart; **nginx do host não é recarregado pelo pipeline** — operador copia/ajusta vhosts e `nginx -s reload` |
| `SECURITY.md`, `THIRD_PARTY.md`, `AGENTS.md`, `CHANGELOG.md` na raiz | **não** alteram sozinhos arquivos servidos; `security.txt` vivo vem de `deploy/well-known/security.txt` |
| `README.md` / `LICENSE` | ignorados no trigger do workflow (`paths-ignore`) |

Flags Flutter no build de CI (#292): web e APK usam `--tree-shake-icons`; web usa
`--web-renderer canvaskit` (alinhar com #140 se quiser `html`/`auto` via variável
de repositório no futuro).

Pós-deploy (#293): job `live-verify` roda `e2e/live.js` quando o deploy em `main`
sucede; passo adicional `ops_probes.js` valida `/health` (mocks off em live),
`security.txt` e, se existir, `client-config` (tolerante a 404 até a rota estar
no ar).

## Indo ao ar com dados reais

Edite o `.env` no servidor:

```
USE_MOCK_SEFAZ=false
SEFAZ_APP_TOKEN=<token da SEFAZ>
USE_MOCK_LLM=false
ANTHROPIC_API_KEY=<chave>
```

depois `cd deploy && docker compose --env-file ../.env up -d` para reiniciar a API.
Nenhuma mudança de código é necessária.

## Notas

- O usuário do deploy precisa estar no grupo `docker` para rodar `docker compose` sem
  `sudo`.
- Em host compartilhado, **nunca** use `docker system prune`. Limpe só as próprias
  imagens: `docker image prune -f` / `docker builder prune -f`.

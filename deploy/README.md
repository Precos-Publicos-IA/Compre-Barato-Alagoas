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

## Atualizações

`deploy.sh` reconstrói a web + APK, sincroniza backend/deploy/web e recria os
containers. Rode-o novamente com as mesmas variáveis de ambiente do primeiro deploy.

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

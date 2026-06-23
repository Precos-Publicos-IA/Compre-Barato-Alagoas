# Compre Barato Alagoas

**Compare preços de supermercados, farmácias e lojas em Alagoas e monte a lista de
compras mais barata — usando dados públicos e reais de notas fiscais (NFC-e).**

Aplicativo aberto (Android + web) que ajuda as pessoas de Alagoas, começando por
Maceió, a encontrar onde comprar mais barato. Os preços vêm da **API pública
Economiza Alagoas**, mantida pela Secretaria da Fazenda do Estado de Alagoas
(SEFAZ-AL), e refletem vendas reais coletadas quase em tempo real.

> Projeto **Preços Públicos IA** · Licença MIT · App online em
> https://alagoas.precospublicos.ia.br · Documentação em
> https://docs.alagoas.precospublicos.ia.br

A SEFAZ-AL é, hoje, a única secretaria estadual do país a oferecer esse serviço de
consulta de preços de forma pública e gratuita. Este projeto é uma forma de colocar
esses dados na mão da população, com uma experiência simples e acessível.

## O que o app faz

- Você digita (ou fala) sua lista de compras em linguagem natural — ex.: *"5kg de
  arroz, 1L de leite, sabão em pó"*.
- O app consulta os preços praticados perto de você e calcula o **preço justo por
  unidade** (por kg, por litro, por unidade) para comparar produtos de tamanhos
  diferentes de forma honesta.
- O resultado é uma lista de lojas ordenada da **mais barata** para a mais cara, com
  o quanto você economiza e a data de cada venda.
- A lista pode ser compartilhada por um link curto.

## Como funciona (a parte difícil)

A base de dados da SEFAZ não tem um campo com o **tamanho da embalagem** ("5kg",
"1L"): essa informação só existe no texto livre da descrição do produto. O coração do
projeto é justamente extrair tamanho e unidade desse texto para calcular um
**preço por unidade comparável**. Essa lógica vive em
`backend/app/services/normalization/`.

```
Usuário (Flutter, Android/web)
        │
        ▼
Backend (FastAPI)  ──►  API pública Economiza Alagoas (SEFAZ-AL)
        │
        ├── interpreta a lista (LLM)
        ├── normaliza tamanho/unidade  →  preço justo por kg/L/un
        └── ranqueia as lojas por cesta total
```

O backend funciona como intermediário seguro: é ele quem guarda o token de acesso à
SEFAZ — o token **nunca** vai para o aplicativo do usuário.

## Estrutura do repositório

| Pasta | Descrição |
|-------|-----------|
| `backend/` | API em FastAPI: intermediário seguro, normalização e ranqueamento. |
| `frontend/` | App em Flutter (Android + web): Riverpod, mapa OpenStreetMap, voz. |
| `admin-frontend/` | Painel administrativo estático (métricas de IA/produto + técnico). |
| `docs/` | Documentação estática (pt-BR), publicada em `docs.<domínio>`. |
| `deploy/` | docker-compose + nginx para subir o projeto em um servidor. |
| `shared-assets/` | Arte/logo de origem do app. |

Cada pasta tem o seu próprio README com instruções detalhadas.

## Documentação

A documentação funcional e técnica completa (em pt-BR) fica em
[`docs/`](docs/index.html) e é publicada em
**https://docs.alagoas.precospublicos.ia.br** — visão geral, arquitetura, fluxo de
busca, normalização de preço justo, ranqueamento, privacidade/LGPD, API e uma seção
honesta de limitações conhecidas. É um site estático (HTML/CSS, sem build).

## Rodando localmente

O projeto roda **sem nenhuma infraestrutura externa** em *modo mock* (catálogo
sintético de Maceió, sem necessidade de token da SEFAZ nem de chave de LLM).

**Backend**
```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload      # docs em http://127.0.0.1:8000/docs
```

**Frontend**
```bash
cd frontend
flutter pub get
flutter test
flutter run --dart-define=API_BASE_URL=http://<ip-da-sua-maquina>:8000
```

Toda a configuração é por variáveis de ambiente — copie `.env.example` para `.env` e
ajuste o que precisar.

## Fonte de dados: API Economiza Alagoas (SEFAZ-AL)

Os dados vêm da API pública da SEFAZ-AL. O uso exige um **token de acesso gratuito**,
solicitado diretamente à secretaria.

- **Manual de Orientação do Desenvolvedor:**
  https://gcs.sefaz.al.gov.br/documentos/visualizarDocumento.action?key=ltOvHx2smR4%3D
- **Solicitação de token:** envie nome completo, CPF e nome do projeto para
  `api@sefaz.al.gov.br`.
- **Informações gerais:** `economizaalagoas@sefaz.al.gov.br`

Enquanto o token não está configurado, mantenha `USE_MOCK_SEFAZ=true`. Para ir ao ar
com dados reais, basta preencher o token no `.env` e mudar as flags — **sem alterar
código** (veja [`deploy/README.md`](deploy/README.md)).

## Deploy

O `deploy/` traz um `docker-compose` (API + Postgres + Redis) pensado para rodar atrás
de um nginx com TLS. Toda configuração sensível (token, senhas, domínio) fica em um
único arquivo `.env`, que **nunca** é versionado. Passo a passo em
[`deploy/README.md`](deploy/README.md).

## Licença

[MIT](LICENSE) — © 2026 Preços Públicos IA. Sinta-se livre para usar, estudar e
contribuir.

## Manutenção interna

Notas de sessão, guias on-device, arte-fonte (`.xcf`), relatórios informais de segurança
e outputs de pesquisa de agente ficam no repositório privado
[Compre-Barato-Alagoas-Privado](https://github.com/Precos-Publicos-IA/Compre-Barato-Alagoas-Privado)
(acesso restrito ao time).


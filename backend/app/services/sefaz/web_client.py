"""SEFAZ data via the public Economiza Alagoas *website* (no AppToken).

Used while the official JSON API token is unavailable. The site is slow and
returns multi‑MB HTML for broad terms, so this client is deliberately thrifty:

* one short-lived httpx client + cookie jar **per search** (session is stateful);
* global semaphore to cap concurrent hits on SEFAZ's web tier;
* after the description POST, only open the best GPC category when needed;
* **stream** the category page and stop after ``max_cards`` / ``max_bytes``;
* prefer specific search strings (callers already use LLM ``search_term``).

Maps HTML cards into the same ``PesquisaResponse`` shape as the official API so
normalization/ranking stay unchanged. Store ids are ``web:<caceal>`` (or a
stable hash) because the page rarely exposes CNPJ.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from typing import Iterable

import httpx

from .http_client import SefazApiError
from .models import (
    Endereco,
    Estabelecimento,
    PesquisaResponse,
    Produto,
    Registro,
    Venda,
)

logger = logging.getLogger(__name__)

_DEFAULT_BASE = "https://economizaalagoas.sefaz.al.gov.br"
_UA = (
    "CompreBaratoAlagoas/0.1 (+https://alagoas.precospublicos.ia.br; "
    "public-price research; contact via GitHub Precos-Publicos-IA)"
)

# Shared across instances so concurrent basket items do not stampede the site.
_WEB_SEM: asyncio.Semaphore | None = None
_WEB_SEM_LIMIT = 2

_CARD_SPLIT = re.compile(r'<div class="cartao\b', re.I)
_TITLE = re.compile(
    r'class="cartao_titulo_texto[^"]*"[^>]*>\s*([^<]+?)\s*<', re.I
)
_SHARE = re.compile(
    r"compartilhar\(\s*'((?:\\'|[^'])*)'\s*,\s*'((?:\\'|[^'])*)'\s*,\s*"
    r"'((?:\\'|[^'])*)'\s*,\s*'((?:\\'|[^'])*)'\s*\)",
    re.S,
)
_GTIN = re.compile(r"consultarPorCodigoBarra\(\s*'(\d+)'\s*\)")
_CACEAL = re.compile(r"exibirEstabelecimento\(\s*'(\d+)'\s*\)")
_UNIT = re.compile(
    r'class="valor_unitario"[^>]*>\s*R\$\s*([\d.]+),(\d{2})\s*<', re.I
)
_LAST = re.compile(
    r'class="valor_ultima_venda"[^>]*>\s*R\$\s*([\d.]+),(\d{2})\s*<', re.I
)
_UNIT_LABEL = re.compile(
    r'class="valor_unitario"[\s\S]{0,200}?<span[^>]*>\s*([A-Za-z]{1,6})\s*<',
    re.I,
)
_RELATIVE = re.compile(
    r"H[aá]\s+(\d+)\s+dia",
    re.I,
)
_RELATIVE_HOURS = re.compile(
    r"H[aá]\s+(\d+)\s+hora",
    re.I,
)
_CATEGORY = re.compile(
    r"consultarPorCategoria\((\d+)\);[\s\S]*?"
    r'<span class="mdl-list__item-sub-title">\s*(\d+)\s*produtos\s*</span>',
    re.I,
)
_ADDR_BLOCK = re.compile(
    r'class="cartao_contribuinte_bloco_esquerdo"[^>]*>([\s\S]*?)</div>',
    re.I,
)
_BR_MONEY = re.compile(r"R\$\s*([\d.]+),(\d{2})")


def _web_semaphore(limit: int) -> asyncio.Semaphore:
    global _WEB_SEM, _WEB_SEM_LIMIT
    if _WEB_SEM is None or _WEB_SEM_LIMIT != limit:
        _WEB_SEM = asyncio.Semaphore(max(1, limit))
        _WEB_SEM_LIMIT = max(1, limit)
    return _WEB_SEM


def _unesc(s: str) -> str:
    return unescape(s.replace("\\'", "'").replace("\n", " ")).strip()


def _brl_to_float(whole: str, cents: str) -> float:
    # Brazilian thousands: 1.234,56 → 1234.56
    return float(whole.replace(".", "") + "." + cents)


def _parse_price(text: str) -> float | None:
    m = _BR_MONEY.search(text or "")
    if not m:
        return None
    return _brl_to_float(m.group(1), m.group(2))


def _relative_sale_date(chunk: str) -> str | None:
    """Best-effort ISO date from 'Há N dias…' / 'Há N horas…'."""
    now = datetime.now(timezone.utc)
    m = _RELATIVE.search(chunk)
    if m:
        return (now - timedelta(days=int(m.group(1)))).date().isoformat()
    m = _RELATIVE_HOURS.search(chunk)
    if m:
        return (now - timedelta(hours=int(m.group(1)))).date().isoformat()
    return None


def _store_id(caceal: str | None, store: str, address: str) -> str:
    if caceal:
        return f"web:{caceal}"
    digest = hashlib.sha1(f"{store}|{address}".encode()).hexdigest()[:12]
    return f"web:{digest}"


def _parse_address_block(chunk: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Return (logradouro, numero, bairro, municipio) from the left contributor block."""
    m = _ADDR_BLOCK.search(chunk)
    if not m:
        return None, None, None, None
    raw = re.sub(r"<br\s*/?>", "\n", m.group(1), flags=re.I)
    raw = re.sub(r"<[^>]+>", "", raw)
    lines = [ln.strip(" ,") for ln in raw.splitlines() if ln.strip()]
    # lines: [store_name, street+num, "MACEIO, BAIRRO,", CEP]
    logradouro = lines[1] if len(lines) > 1 else None
    municipio = None
    bairro = None
    if len(lines) > 2:
        parts = [p.strip() for p in lines[2].split(",") if p.strip()]
        if parts:
            municipio = parts[0]
        if len(parts) > 1:
            bairro = parts[1]
    numero = None
    if logradouro and "," in logradouro:
        # "AV FOO, 123" → street / number
        street, _, rest = logradouro.partition(",")
        logradouro = street.strip()
        num = rest.strip().split(",")[0].strip()
        if num:
            numero = num
    return logradouro, numero, bairro, municipio


def parse_categories(html: str) -> list[tuple[int, int]]:
    """Return [(gpc_code, product_count), ...] from a category listing page."""
    out: list[tuple[int, int]] = []
    for m in _CATEGORY.finditer(html):
        out.append((int(m.group(1)), int(m.group(2))))
    return out


def _simplify_term(term: str) -> str:
    """First significant word of a multi-token query (for website retry)."""
    for t in re.split(r"[^a-zA-ZÀ-ú0-9]+", term.strip()):
        if len(t) >= 3 and not _SIZE_TOKEN.match(t.lower().replace(",", ".")):
            if t.lower() not in {"tipo", "para", "com"}:
                return t.lower()
    return term.strip().lower()[:30]


def pick_category(categories: Iterable[tuple[int, int]]) -> int | None:
    """Choose a GPC segment: prefer food (50M) when present, else the largest."""
    cats = list(categories)
    if not cats:
        return None
    by_id = {c: n for c, n in cats if n > 0}
    if not by_id:
        return None
    if 50_000_000 in by_id:
        return 50_000_000
    return max(by_id.items(), key=lambda kv: kv[1])[0]


def parse_cards(html: str, *, max_cards: int | None = None) -> list[Registro]:
    """Parse product cards from Economiza HTML into ``Registro`` rows."""
    parts = _CARD_SPLIT.split(html)
    if len(parts) <= 1:
        return []
    # first split piece is preamble
    rows: list[Registro] = []
    for chunk in parts[1:]:
        if max_cards is not None and len(rows) >= max_cards:
            break
        # Incomplete streamed card (missing closer signals) — skip.
        if "compartilhar(" not in chunk and "valor_ultima_venda" not in chunk:
            continue
        share = _SHARE.search(chunk)
        title_m = _TITLE.search(chunk)
        product = _unesc(share.group(1)) if share else (
            _unesc(title_m.group(1)) if title_m else ""
        )
        if not product:
            continue

        price: float | None = None
        if share:
            price = _parse_price(_unesc(share.group(2)))
            store = _unesc(share.group(3))
            addr_share = _unesc(share.group(4))
        else:
            store = ""
            addr_share = ""
        if price is None:
            m = _LAST.search(chunk) or _UNIT.search(chunk)
            if m:
                price = _brl_to_float(m.group(1), m.group(2))
        if price is None or price <= 0:
            continue

        if not store:
            # fall back to first line of address block
            ab = _ADDR_BLOCK.search(chunk)
            if ab:
                first = re.sub(r"<[^>]+>", "\n", ab.group(1)).strip().splitlines()
                store = first[0].strip() if first else "Loja"
            else:
                store = "Loja"

        gtin_m = _GTIN.search(chunk)
        caceal_m = _CACEAL.search(chunk)
        unit_m = _UNIT_LABEL.search(chunk)
        um = (unit_m.group(1).strip().upper() if unit_m else "UN") or "UN"

        logradouro, numero, bairro, municipio = _parse_address_block(chunk)
        if not bairro and addr_share:
            # "AV X, 1, BAIRRO" last segment often neighborhood
            bits = [b.strip() for b in addr_share.split(",") if b.strip()]
            if len(bits) >= 3:
                bairro = bits[-1]
            if logradouro is None and bits:
                logradouro = bits[0]
            if numero is None and len(bits) >= 2:
                numero = bits[1]

        caceal = caceal_m.group(1) if caceal_m else None
        cnpj = _store_id(caceal, store, addr_share or (logradouro or ""))
        sale_date = _relative_sale_date(chunk)

        rows.append(
            Registro(
                produto=Produto(
                    codigo=gtin_m.group(1) if gtin_m else None,
                    descricao=product,
                    descricao_sefaz=product,
                    gtin=gtin_m.group(1) if gtin_m else None,
                    unidade_medida=um,
                    venda=Venda(
                        data_venda=sale_date,
                        valor_declarado=price,
                        valor_venda=price,
                    ),
                ),
                estabelecimento=Estabelecimento(
                    cnpj=cnpj,
                    razao_social=store,
                    nome_fantasia=store,
                    endereco=Endereco(
                        nome_logradouro=logradouro,
                        numero_imovel=numero,
                        bairro=bairro,
                        municipio=municipio or "Maceió",
                        # Website does not expose coordinates; ranking falls back
                        # to items_found + basket total only.
                        latitude=None,
                        longitude=None,
                    ),
                ),
            )
        )
    return rows


_SIZE_TOKEN = re.compile(r"^(\d+(?:[.,]\d+)?)(kg|g|l|ml|un|und)$", re.I)
# Grocery app: drop pet/animal feed unless the user asked for it.
_PET_NOISE = re.compile(
    r"\b(c[aã]es?|c[aã]o|gatos?|dog|cat|ra[cç][aã]o|pet|filhote|"
    r"canina|felina|animal(?:is)?|cachorro|arrozcao|amigaco|amigao|luppy|"
    r"biluzao|cravil|au\s*au)\b"
    r"|p\s*c[aã]o|para\s+c[aã]o|p\s*anim|agrovan",
    re.I,
)
_PET_QUERY = re.compile(
    r"\b(c[aã]es?|c[aã]o|gato|dog|cat|ra[cç][aã]o|pet|cachorro)\b",
    re.I,
)


def _filter_relevant(rows: list[Registro], term: str) -> list[Registro]:
    """Drop obvious off-topic cards when the site is loose (e.g. 'arroz' → pet food).

    * Word tokens (e.g. ``arroz``, ``leite``) must all appear in the description.
    * Size tokens (``5kg``) use a boundary-aware match so ``5kg`` does not hit ``15kg``.
    * Pet-food noise is stripped unless the query itself is about pets.
    If filtering would wipe everything, keep the original list (better noisy than empty).
    """
    raw = [t for t in re.split(r"[^a-z0-9.,]+", term.lower()) if t]
    words: list[str] = []
    sizes: list[re.Pattern[str]] = []
    for t in raw:
        if t in {"tipo", "para", "com", "de", "do", "da"}:
            continue
        sm = _SIZE_TOKEN.match(t.replace(",", "."))
        if sm:
            num, unit = sm.group(1).replace(",", "."), sm.group(2).lower()
            # allow "5kg", "5 kg", "5,0kg"
            sizes.append(
                re.compile(
                    rf"(?<![\d.]){re.escape(num)}\s*{re.escape(unit)}\b",
                    re.I,
                )
            )
        elif len(t) >= 3:
            words.append(t)
    if not words and not sizes:
        return rows

    want_pet = bool(_PET_QUERY.search(term))

    def ok(desc: str, *, require_size: bool) -> bool:
        d = desc.lower()
        if not want_pet and _PET_NOISE.search(d):
            return False
        if words and not all(w in d for w in words):
            return False
        if require_size and sizes and not any(p.search(d) for p in sizes):
            return False
        return True

    kept = [r for r in rows if ok(r.produto.descricao or "", require_size=bool(sizes))]
    if kept:
        return kept
    # Soften: word tokens only (drop size requirement) before giving up.
    soft = [r for r in rows if ok(r.produto.descricao or "", require_size=False)]
    if soft:
        return soft
    return rows
class WebSefazClient:
    """Scrape economizaalagoas.sefaz.al.gov.br into ``PesquisaResponse``."""

    source_name = "web"
    cache_namespace = "web"

    def __init__(
        self,
        *,
        base_url: str = _DEFAULT_BASE,
        timeout: float = 45.0,
        max_cards: int = 200,
        max_bytes: int = 1_500_000,
        concurrency: int = 2,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._max_cards = max(20, max_cards)
        self._max_bytes = max(100_000, max_bytes)
        self._concurrency = max(1, concurrency)

    async def search_product(
        self,
        *,
        descricao: str | None = None,
        gtin: str | None = None,
        latitude: float,
        longitude: float,
        radius_km: int,
        days: int,
        pagina: int = 1,
        registros_por_pagina: int = 500,
    ) -> PesquisaResponse:
        # Website has no pagination/geo; ignore pagina > 1 and radius/coords.
        if pagina > 1:
            return self._empty_page(pagina=pagina, per_page=registros_por_pagina)

        if bool(descricao) == bool(gtin):
            raise ValueError("provide exactly one of descricao or gtin")
        term = (gtin or descricao or "").strip()
        if len(term) < 3:
            raise SefazApiError("search term too short for Economiza website (min 3 chars)")

        async with _web_semaphore(self._concurrency):
            rows = await self._search_term(term)
            rows = _filter_relevant(rows, term)
            # Specific terms like "arroz 5kg" often return mostly pet food on the
            # website. If too few grocery hits remain, retry the headword alone
            # (unit-price ranking still compares 1kg vs 5kg fairly later).
            if len(rows) < 12:
                simplified = _simplify_term(term)
                if simplified and simplified != term.lower():
                    extra = await self._search_term(simplified)
                    extra = _filter_relevant(extra, simplified)
                    # Prefer original term's word tokens when merging.
                    seen = {
                        (
                            r.produto.descricao,
                            r.estabelecimento.cnpj,
                            r.produto.venda.valor_venda if r.produto.venda else 0,
                        )
                        for r in rows
                    }
                    for r in extra:
                        key = (
                            r.produto.descricao,
                            r.estabelecimento.cnpj,
                            r.produto.venda.valor_venda if r.produto.venda else 0,
                        )
                        if key not in seen:
                            rows.append(r)
                            seen.add(key)

        # Approximate "days" window from relative sale text when present.
        if days and days < 10:
            filtered: list[Registro] = []
            for r in rows:
                dv = r.produto.venda.data_venda if r.produto.venda else None
                if not dv:
                    filtered.append(r)
                    continue
                try:
                    sale = datetime.fromisoformat(dv).replace(tzinfo=timezone.utc)
                except ValueError:
                    filtered.append(r)
                    continue
                if (datetime.now(timezone.utc) - sale).days <= days:
                    filtered.append(r)
            rows = filtered or rows

        # Cap to what the official API would roughly return per page.
        cap = min(self._max_cards, max(1, registros_por_pagina))
        rows = rows[:cap]
        return PesquisaResponse(
            total_registros=len(rows),
            total_paginas=1,
            pagina=1,
            registros_por_pagina=registros_por_pagina,
            registros_pagina=len(rows),
            primeira_pagina=True,
            ultima_pagina=True,
            conteudo=rows,
        )

    async def _search_term(self, term: str) -> list[Registro]:
        timeout = httpx.Timeout(self._timeout, connect=10.0, pool=10.0)
        async with httpx.AsyncClient(
            base_url=self._base,
            headers={
                "User-Agent": _UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
            follow_redirects=True,
            timeout=timeout,
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
        ) as client:
            try:
                await client.get("/")
            except httpx.HTTPError as exc:
                raise SefazApiError(f"Economiza website unreachable: {exc}") from exc

            try:
                r1 = await client.post(
                    "/exibicaoPrecoProduto.htm",
                    data={"textoConsulta": term[:30]},  # site maxlength=30
                    headers={
                        "Origin": self._base,
                        "Referer": self._base + "/",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                r1.raise_for_status()
            except httpx.HTTPError as exc:
                raise SefazApiError(f"Economiza search failed: {exc}") from exc

            html1 = r1.text
            cards = parse_cards(html1, max_cards=self._max_cards)
            if len(cards) >= 5:
                logger.info(
                    "web sefaz: term=%r direct cards=%d bytes=%d",
                    term,
                    len(cards),
                    len(html1),
                )
                return cards

            categories = parse_categories(html1)
            cat = pick_category(categories)
            if cat is None:
                logger.info(
                    "web sefaz: term=%r no cards/categories bytes=%d",
                    term,
                    len(html1),
                )
                return cards

            # When the site reports a small category, pull it all (still byte-capped).
            # Broad categories (thousands of cards) are stream-stopped early — the page
            # is price-sorted ascending, so the head is often junk (candy, pet food).
            # We over-read a bit past max_cards so post-filters still have candidates.
            known = next((n for c, n in categories if c == cat), None)
            card_budget = self._max_cards
            if known is not None and known <= self._max_cards:
                card_budget = known + 5
            elif known is not None and known > self._max_cards:
                # Read 2× so relevance filter can discard off-topic cheap hits.
                card_budget = min(known, self._max_cards * 2)

            html2 = await self._stream_category(
                client, cat, max_cards=card_budget
            )
            cards2 = parse_cards(html2, max_cards=card_budget)
            logger.info(
                "web sefaz: term=%r cat=%s known=%s cards=%d stream_bytes=%d",
                term,
                cat,
                known,
                len(cards2),
                len(html2),
            )
            return cards2 or cards

    async def _stream_category(
        self,
        client: httpx.AsyncClient,
        cat: int,
        *,
        max_cards: int | None = None,
    ) -> str:
        """Download category HTML until we have enough cards or hit max_bytes."""
        limit_cards = max_cards if max_cards is not None else self._max_cards
        url = f"/exibicaoPrecoProduto.htm?codSegmentoGPC={cat}"
        buf: list[str] = []
        total = 0
        card_count = 0
        try:
            async with client.stream(
                "GET",
                url,
                headers={"Referer": self._base + "/exibicaoPrecoProduto.htm"},
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_text():
                    buf.append(chunk)
                    total += len(chunk)
                    card_count += chunk.count('class="cartao')
                    if card_count >= limit_cards or total >= self._max_bytes:
                        # Drop the rest of the response so the server can finish.
                        await resp.aclose()
                        break
        except httpx.HTTPError as exc:
            raise SefazApiError(f"Economiza category fetch failed: {exc}") from exc
        return "".join(buf)
    @staticmethod
    def _empty_page(*, pagina: int, per_page: int) -> PesquisaResponse:
        return PesquisaResponse(
            total_registros=0,
            total_paginas=1,
            pagina=pagina,
            registros_por_pagina=per_page,
            registros_pagina=0,
            primeira_pagina=pagina <= 1,
            ultima_pagina=True,
            conteudo=[],
        )

    async def aclose(self) -> None:  # pragma: no cover - no long-lived resources
        return None

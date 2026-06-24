"""Turn raw SEFAZ rows into normalized, fairly-comparable offers.

The decision tree for the *unit price* (price per kg / L / un):

1. If ``unidadeMedida`` is itself a weight/volume unit (KG, G, L, ML, ...), the product
   is sold loose and ``valorVenda`` is already the price for one of those units — we
   only convert it to the canonical base.
2. Otherwise the price is for a *package*, so we mine the package size from the
   description (``extract_quantity``) and divide.
3. If we can't determine a size, we fall back to price-per-package and flag
   ``quantity_parsed=False`` — this is the signal that value-comparison quality dropped
   for that row.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..sefaz.models import Registro
from .quantity import extract_quantity
from .units import dimension, normalize_unit_token, to_base

_MASS_VOLUME = {"mass", "volume"}

# Upper sanity bound for a single NFC-e line price (R$). Real grocery items sit far
# below this; anything above is bad SEFAZ data and is dropped (#254).
_MAX_PLAUSIBLE_PRICE = 100_000.0


@dataclass(frozen=True)
class NormalizedOffer:
    # product
    description: str
    description_sefaz: str | None
    gtin: str | None
    unidade_medida: str | None
    # pricing
    price: float                # valorVenda (price of the package/last sale)
    unit_price: float           # price per base_unit (the fair-comparison number)
    base_unit: str              # 'kg' | 'L' | 'un'
    quantity: float             # package size in `unit`
    unit: str                   # raw unit the quantity is expressed in
    quantity_parsed: bool       # False => unit_price is per-package fallback
    parse_method: str           # 'unidade_medida' | 'description' | 'fallback'
    parse_confidence: float
    sale_date: str | None
    # store
    cnpj: str
    store_name: str
    latitude: float | None
    longitude: float | None
    bairro: str | None
    address: str | None


def _store_name(reg: Registro) -> str:
    est = reg.estabelecimento
    return est.nome_fantasia or est.razao_social or est.cnpj


def _address(reg: Registro) -> str | None:
    e = reg.estabelecimento.endereco
    if not e:
        return None
    parts = [p for p in (e.nome_logradouro, e.numero_imovel, e.bairro) if p]
    return ", ".join(parts) if parts else None


def normalize_offer(reg: Registro) -> NormalizedOffer | None:
    """Normalize one SEFAZ row, or None if it has no usable price."""
    venda = reg.produto.venda
    if venda is None or venda.valor_venda is None:
        return None
    price = float(venda.valor_venda)
    # Reject implausible prices: a zero/negative row would sort to the top as the
    # "cheapest", and an absurdly large one is clearly bad SEFAZ data (#254).
    if not (0 < price <= _MAX_PLAUSIBLE_PRICE):
        return None
    desc = reg.produto.descricao
    um = reg.produto.unidade_medida

    um_dim = dimension(um) if um else None

    if um_dim in _MASS_VOLUME:
        # Sold by weight/volume: price is per `um`; convert to canonical base.
        conv = to_base(1.0, um)  # type: ignore[arg-type]
        assert conv is not None
        factor, base_unit = conv
        unit_price = price / factor
        quantity, unit = 1.0, normalize_unit_token(um)  # type: ignore[arg-type]
        parsed, method, conf = True, "unidade_medida", 1.0
    else:
        pq = extract_quantity(desc)
        if pq and pq.base_value > 0:
            unit_price = price / pq.base_value
            base_unit = pq.base_unit
            quantity, unit = pq.value, pq.unit
            parsed, method, conf = True, "description", pq.confidence
        else:
            # Last resort: compare per package / per unit.
            unit_price = price
            base_unit = "un"
            quantity, unit = 1.0, normalize_unit_token(um) if um else "un"
            parsed, method, conf = False, "fallback", 0.0

    est = reg.estabelecimento
    endereco = est.endereco
    return NormalizedOffer(
        description=desc,
        description_sefaz=reg.produto.descricao_sefaz or None,
        gtin=reg.produto.gtin,
        unidade_medida=um,
        price=round(price, 2),
        unit_price=round(unit_price, 4),
        base_unit=base_unit,
        quantity=quantity,
        unit=unit,
        quantity_parsed=parsed,
        parse_method=method,
        parse_confidence=conf,
        sale_date=venda.data_venda,
        cnpj=est.cnpj,
        store_name=_store_name(reg),
        latitude=endereco.latitude if endereco else None,
        longitude=endereco.longitude if endereco else None,
        bairro=endereco.bairro if endereco else None,
        address=_address(reg),
    )

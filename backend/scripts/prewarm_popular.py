#!/usr/bin/env python3
"""
Creative scale prep: "Pre-warm popular items" for the RAG layer.

At 5k+ users the top searched items (from analytics) should be pre-populated
into the Requester/Verifier RAG so first-time vague searches for common things
("arroz", "leite") get good rewrites immediately, without waiting for organic
learning. This helps logarithmic cost (popular items hit cache/RAG fast).

Run manually or as a background job. Uses the same Cache RAG methods.
For demo it hardcodes some from the data-patterns report + mock catalog.
In real life it would pull from analytics.items() top_searched.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.cache import Cache
import fakeredis.aioredis


async def prewarm():
    # Isolated fake for demo (in prod would use real redis)
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    cache = Cache(client=fake)
    await cache.ping()

    # From data patterns + common poor-user baskets (audience focused)
    popular_mappings = [
        ("arroz", "arroz branco tipo 1", 15),
        ("arroz", "arroz 5kg", 12),
        ("leite", "leite na caixa integral", 10),
        ("feijao", "feijao cario", 8),
        ("pao", "pao frances", 6),
        ("manteiga", "manteiga com sal", 4),
        ("iogurte", "iogurte natural", 4),
        ("coca", "refrigerante cola", 5),
        ("banana", "banana prata", 4),
    ]

    for user_term, effective, count in popular_mappings:
        await cache.record_successful_mapping(user_term, effective, count)
        print(f"Pre-warmed RAG: '{user_term}' -> '{effective}' (score {count})")

    # Demonstrate the creative similarity
    for vague in ["pao", "arroz 5", "leite 1L", "feijao"]:
        sims = await cache.find_similar_effective_terms(vague, limit=2)
        print(f"  For vague '{vague}' similarity found: {sims}")

    print("\nPre-warm complete. This would be driven by real analytics.top_searched at scale.")
    print("Result: fewer cold SEFAZ calls for the 80/20 common items that poor users buy every week.")


if __name__ == "__main__":
    asyncio.run(prewarm())

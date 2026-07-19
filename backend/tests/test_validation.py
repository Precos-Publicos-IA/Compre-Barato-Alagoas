"""Tests for SEFAZ output validation."""

from __future__ import annotations

import pytest

from app.services.catalog.validation import (
    deterministic_validate,
    build_validation_prompt,
    parse_validation_response,
    analyze_store_coverage,
)


class TestDeterministicValidate:
    def test_valid_descriptions(self):
        result = deterministic_validate(
            product_slug="arroz",
            display_name="Arroz",
            category="staples",
            descriptions=["ARROZ BRANCO 1KG", "ARROZ TIPO 1 CAMIL 5KG"],
            known_negative=["ARROZ P CAES", "ARROZ DOCE"],
        )
        assert result.valid is True

    def test_invalid_all_negative(self):
        result = deterministic_validate(
            product_slug="arroz",
            display_name="Arroz",
            category="staples",
            descriptions=["ARROZ P CAES 1KG", "ARROZ DOCE PUDIM"],
            known_negative=["ARROZ P CAES", "ARROZ DOCE"],
        )
        assert result.valid is False
        assert len(result.rejected_descriptions) == 2

    def test_mixed_descriptions(self):
        result = deterministic_validate(
            product_slug="leite",
            display_name="Leite",
            category="dairy",
            descriptions=[
                "LEITE UHT INTEGRAL 1L",
                "LEITE BETANIA 1L",
                "LEITE CONDENSADO MOCINHA",
            ],
            known_negative=["LEITE CONDENSADO", "CREME DE LEITE"],
        )
        # 1 out of 3 is negative = 33% < 50%, so valid
        assert result.valid is True
        assert "LEITE CONDENSADO MOCINHA" in result.rejected_descriptions

    def test_empty_descriptions(self):
        result = deterministic_validate(
            product_slug="arroz",
            display_name="Arroz",
            category="staples",
            descriptions=[],
            known_negative=["ARROZ P CAES"],
        )
        assert result.valid is True

    def test_no_negative_terms(self):
        result = deterministic_validate(
            product_slug="arroz",
            display_name="Arroz",
            category="staples",
            descriptions=["ARROZ BRANCO 1KG"],
            known_negative=[],
        )
        assert result.valid is True


class TestBuildValidationPrompt:
    def test_prompt_structure(self):
        results = [
            {
                "product_slug": "arroz",
                "display_name": "Arroz",
                "category": "staples",
                "search_terms_used": ["arroz", "arroz tipo 1"],
                "sample_descriptions": ["ARROZ BRANCO 1KG", "ARROZ TIPO 1"],
                "known_positive": ["ARROZ BRANCO 1KG"],
                "known_negative": ["ARROZ DOCE"],
            }
        ]
        prompt = build_validation_prompt(results)
        assert "Arroz" in prompt
        assert "ARROZ BRANCO 1KG" in prompt
        assert "ARROZ DOCE" in prompt


class TestParseValidationResponse:
    def test_parse_json_array(self):
        response = '[{"product_slug": "arroz", "valid": true, "reason": "OK"}]'
        results = parse_validation_response(response)
        assert len(results) == 1
        assert results[0]["valid"] is True

    def test_parse_single_object(self):
        response = '{"product_slug": "arroz", "valid": false, "reason": "wrong"}'
        results = parse_validation_response(response)
        assert len(results) == 1

    def test_parse_markdown_wrapped(self):
        response = '```json\n[{"valid": true}]\n```'
        results = parse_validation_response(response)
        assert len(results) == 1

    def test_parse_invalid(self):
        results = parse_validation_response("not json")
        assert len(results) == 0


class TestStoreCoverage:
    def test_flags_incomplete_coverage(self):
        store_products = {
            "store1": {
                "name": "Store 1",
                "found": ["arroz", "feijao"],
                "missing": ["leite", "cafe", "oleo"],
            }
        }
        flags = analyze_store_coverage(store_products, total_products_requested=5)
        # 2/5 = 40% → between 20% and 80% → should be flagged
        assert len(flags) == 1
        assert flags[0].flag_type == "incomplete_store_coverage"
        assert flags[0].details["coverage_ratio"] == 0.4

    def test_no_flags_full_coverage(self):
        store_products = {
            "store1": {
                "name": "Store 1",
                "found": ["arroz", "feijao", "leite", "cafe", "oleo"],
                "missing": [],
            }
        }
        flags = analyze_store_coverage(store_products, total_products_requested=5)
        assert len(flags) == 0

    def test_no_flags_low_coverage(self):
        store_products = {
            "store1": {
                "name": "Store 1",
                "found": ["arroz"],
                "missing": ["feijao", "leite", "cafe", "oleo"],
            }
        }
        flags = analyze_store_coverage(store_products, total_products_requested=5)
        # 1/5 = 20% → not above threshold
        assert len(flags) == 0

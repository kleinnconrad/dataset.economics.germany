"""Tests of the Gemini annotation with a fake client."""
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any, Callable

import pytest
from google.genai import types

from annotation import (
    BATCH_SIZE,
    AnnotationInput,
    CallBudgetExceededError,
    GeminiAnnotator,
    build_prompt,
    clean_annotation,
    clean_country_codes,
    extraction_hash,
    keep_known,
)
from schema import Sector, ItemAnnotation
from settings import Settings


def label(number: int, **overrides: Any) -> dict[str, Any]:
    """Returns a valid model answer for one item."""
    base = {
        "item_number": number, "is_economic": True, "topic": "Industry and manufacturing",
        "topics_secondary": ["Labour market and wages"], "issue_detail": "Stellenabbau bei Zulieferern",
        "article_type": "News", "sectors": ["Automotive"],
        "companies": [{"name": "Volkswagen", "role": "Subject", "tone": "Negative"},
                      {"name": "Zulieferer GmbH", "role": "Affected", "tone": "Neutral"}],
        "institutions": ["Trade union"], "countries": ["DE"], "states_concerned": ["DE-NI"],
        "event_types": ["Job cuts"], "event_status": "Announced or planned",
        "indicators": [{"indicator": "Employment", "direction": "Falling"}],
        "commodities": [{"commodity": "Steel and iron ore", "price_direction": "Rising"}],
        "shortages": ["Semiconductors and electronics"], "overall_tone": "Negative",
        "economic_outlook": "Deteriorating", "mentions_uncertainty": True, "mentions_recession": False,
        "policy_level": "Not applicable", "government_involved": False, "frame": "Economic consequences",
        "upcoming_events": [], "communication_type": "Not applicable",
    }
    base.update(overrides)
    return base


def response(items: list[dict[str, Any]], finish: Any = types.FinishReason.STOP) -> SimpleNamespace:
    """Builds a fake GenerateContentResponse."""
    return SimpleNamespace(
        text=json.dumps({"items": items}), candidates=[SimpleNamespace(finish_reason=finish)],
        prompt_feedback=None, usage_metadata=None,
    )


class FakeClient:
    """Fake genai client whose responses are produced by a function of the prompt."""

    def __init__(self, answer: Callable[[str], SimpleNamespace]) -> None:
        self.prompts: list[str] = []
        self.models = SimpleNamespace(generate_content=self._generate)
        self._answer = answer

    def _generate(self, model: str, contents: str, config: Any) -> SimpleNamespace:
        self.prompts.append(contents)
        return self._answer(contents)


def items(count: int) -> list[AnnotationInput]:
    return [AnnotationInput(kind="news article", source="News Example (business newspaper)",
                            published="2026-10-26", title=f"Titel {n}", teaser="Teaser") for n in range(count)]


def annotator(answer: Callable[[str], SimpleNamespace], **overrides: Any) -> tuple[GeminiAnnotator, FakeClient]:
    client = FakeClient(answer)
    settings = Settings(**overrides)
    return GeminiAnnotator(settings, client=client, sleep=lambda s: None, clock=lambda: 0.0), client


def test_annotate_aligns_labels_with_items_by_number() -> None:
    def answer(prompt: str) -> SimpleNamespace:
        return response([label(2, topic="Energy"), label(1)])

    ann, _ = annotator(answer)
    labels = ann.annotate(items(2))

    assert labels[0] is not None and labels[0].topic == "Industry and manufacturing"
    assert labels[1] is not None and labels[1].topic == "Energy"


def test_annotate_returns_none_for_items_missing_in_the_response() -> None:
    ann, _ = annotator(lambda prompt: response([label(1)]))
    labels = ann.annotate(items(3))
    assert labels[0] is not None and labels[1] is None and labels[2] is None


def test_unusable_response_is_split_until_single_items() -> None:
    def answer(prompt: str) -> SimpleNamespace:
        count = prompt.count("\nKind:")
        if count > 1:
            return response([], finish=types.FinishReason.MAX_TOKENS)
        return response([label(1)])

    ann, client = annotator(answer)
    labels = ann.annotate(items(4))

    assert all(result is not None for result in labels)
    assert len(client.prompts) == 1 + 2 + 4


def test_call_budget_stops_the_annotation() -> None:
    ann, _ = annotator(lambda prompt: response([label(1)]), max_gemini_calls_per_run=1)
    ann.annotate(items(1))
    with pytest.raises(CallBudgetExceededError):
        ann.annotate(items(1))


def test_call_budget_holds_across_threads() -> None:
    ann, client = annotator(lambda prompt: response([label(1)]), max_gemini_calls_per_run=3)

    def call(_: int) -> bool:
        try:
            ann.annotate(items(1))
        except CallBudgetExceededError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(call, range(8)))

    assert sum(results) == 3
    assert len(client.prompts) == 3 and ann.usage.calls == 3


def test_annotate_rejects_oversized_batches() -> None:
    ann, _ = annotator(lambda prompt: response([]))
    with pytest.raises(ValueError):
        ann.annotate(items(BATCH_SIZE + 1))


def test_keep_known_maps_to_the_vocabulary_and_drops_other_values() -> None:
    assert keep_known(["automotive", "Rockets", "Automotive", " Real  estate "], Sector) == ["Automotive", "Real estate"]


def test_clean_country_codes() -> None:
    assert clean_country_codes(["de", "UK", "EL", "Germany", "DE", "us "]) == ["DE", "GB", "GR", "US"]


def test_clean_annotation_normalizes_lists_and_press_fields() -> None:
    raw = ItemAnnotation.model_validate(label(
        1,
        companies=[{"name": " Volkswagen ", "role": "Subject", "tone": "Negative"},
                   {"name": "volkswagen", "role": "Affected", "tone": "Positive"}],
        topics_secondary=["Industry and manufacturing", "Energy", "energy", "Trade and tariffs", "Taxes"],
        sectors=["Automotive", "Chemicals", "Banking and financial services", "Retail", "Spaceflight"],
        institutions=["European Central Bank", "Bank of Narnia"],
        states_concerned=["DE-BY", "Bayern"],
        event_types=["Job cuts", "Layoffs"],
        indicators=[{"indicator": "Inflation", "direction": "Rising"}, {"indicator": "inflation", "direction": "Falling"},
                    {"indicator": "Vibes", "direction": "Rising"}],
        commodities=[{"commodity": "Copper", "price_direction": "Rising"}, {"commodity": "Unobtainium",
                                                                              "price_direction": "Rising"}],
        shortages=["Skilled workers", "Patience"],
        upcoming_events=[{"event_type": "Central bank decision", "date": "2026-11-05"},
                         {"event_type": "Central bank decision", "date": "next week"},
                         {"event_type": "Central bank decision", "date": "2020-01-01"},
                         {"event_type": "Party", "date": "2026-11-06"}],
        communication_type="Financial results", issue_detail="  Stellenabbau   bei VW ",
    ))

    news = clean_annotation(raw, "news article", "2026-10-26")
    press = clean_annotation(raw, "press release", "2026-10-26")

    assert [c.name for c in news.companies] == ["Volkswagen"] and news.companies[0].tone == "Negative"
    assert news.topics_secondary == ["Energy", "Trade and tariffs"]
    assert news.sectors == ["Automotive", "Chemicals", "Banking and financial services"]
    assert news.institutions == ["European Central Bank"]
    assert news.states_concerned == ["DE-BY"]
    assert news.event_types == ["Job cuts"]
    assert [(i.indicator, i.direction) for i in news.indicators] == [("Inflation", "Rising")]
    assert [c.commodity for c in news.commodities] == ["Copper"]
    assert news.shortages == ["Skilled workers"]
    assert [(e.event_type, e.date) for e in news.upcoming_events] == [("Central bank decision", "2026-11-05")]
    assert news.issue_detail == "Stellenabbau bei VW"
    assert news.communication_type == "Not applicable"
    assert press.communication_type == "Financial results"


def test_build_prompt_numbers_items_and_marks_missing_text() -> None:
    prompt = build_prompt([AnnotationInput(kind="press release", source="BMW Group (company)", published=None,
                                           title="T")])
    assert "Item 1" in prompt and "Kind: press release" in prompt
    assert "Published: (unknown)" in prompt and "Teaser: (none)" in prompt


def test_extraction_hash_changes_with_the_model() -> None:
    assert extraction_hash(Settings()) != extraction_hash(Settings(gemini_model="other-model"))

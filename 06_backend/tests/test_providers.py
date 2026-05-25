from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from pindou.pattern.builder import ColorRef, PatternSheet
from pindou.providers.base import PreviewProvider, PreviewProviderError, PreviewResult, SizePreset, StylePreset
from pindou.providers.chain import PreviewProviderChain
from pindou.providers.fallback_quantize import FallbackProvider
from pindou.providers.xiaochi_gpt import XiaochiGptProvider
from pindou.tasks.reverse_proxy_health_check import ReverseProxyHealthMonitor


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/"
    "l6j3NwAAAABJRU5ErkJggg=="
)


class FakeImages:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, object]] = []

    def edit(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def api_response(image_bytes: bytes = PNG_1X1) -> object:
    return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(image_bytes).decode("ascii"))])


def test_style_and_size_presets_match_frontend_contract() -> None:
    assert {style.value for style in StylePreset} == {
        "q_portrait",
        "q_pet",
        "q_couple",
        "cartoon_fallback",
    }
    assert {size.value for size in SizePreset} == {"60x80", "80x100", "100x120"}


def test_xiaochi_provider_retries_once_with_new_seed_hint() -> None:
    fake_images = FakeImages([RuntimeError("proxy down"), api_response(PNG_1X1)])
    fake_client = SimpleNamespace(images=fake_images)
    provider = XiaochiGptProvider(
        api_key="test-key",
        base_url="https://example.test/v1",
        client=fake_client,
        seed_factory=lambda: 99,
    )

    result = provider.generate(PNG_1X1, StylePreset.Q_PORTRAIT, SizePreset.SMALL_60X80, seed=1)

    assert result.image == PNG_1X1
    assert result.provider_used == "xiaochi_gpt_image_2"
    assert result.fallback_count == 0
    assert len(fake_images.calls) == 2
    assert "Seed hint: 1" in str(fake_images.calls[0]["prompt"])
    assert "Seed hint: 99" in str(fake_images.calls[1]["prompt"])
    assert fake_images.calls[1]["response_format"] == "b64_json"


@dataclass
class StaticProvider(PreviewProvider):
    name: str
    should_fail: bool = False

    def generate(
        self,
        image: bytes,
        style_preset: StylePreset,
        size_preset: SizePreset,
        seed: int | None = None,
    ) -> PreviewResult:
        if self.should_fail:
            raise PreviewProviderError(f"{self.name} failed")
        return PreviewResult.from_image_bytes(
            image,
            target_color_count=8,
            provider_used=self.name,
            fallback_count=0,
            cost_estimate=0.0,
            latency_ms=1,
        )


def test_provider_chain_returns_primary_success_without_fallback_count() -> None:
    chain = PreviewProviderChain(
        providers=[StaticProvider("primary")],
        fallback_provider=StaticProvider("fallback"),
    )

    result = chain.generate(PNG_1X1, StylePreset.Q_PET, SizePreset.MEDIUM_80X100)

    assert result.provider_used == "primary"
    assert result.fallback_count == 0
    assert "fallback_chain_failures" not in result.metadata


def test_provider_chain_uses_backup_after_primary_failure() -> None:
    chain = PreviewProviderChain(
        providers=[StaticProvider("primary", should_fail=True), StaticProvider("backup")],
        fallback_provider=StaticProvider("fallback"),
    )

    result = chain.generate(PNG_1X1, StylePreset.Q_COUPLE, SizePreset.MEDIUM_80X100)

    assert result.provider_used == "backup"
    assert result.fallback_count == 1
    assert result.metadata["fallback_chain_failures"][0]["provider"] == "primary"


class FakePatternBuilder:
    def build(self, **kwargs: object) -> PatternSheet:
        color = ColorRef(
            brand="MARD",
            code="01",
            name_cn="黑色",
            name_en="Black",
            hex="#000000",
            rgb=(0, 0, 0),
            bead_diameter_mm=5.0,
        )
        return PatternSheet(
            grid=[[color]],
            color_counts={"MARD-01": 1},
            bead_total=1,
            coords=[(0, 0, "MARD-01")],
            no_bead_mask=[[False]],
            palette_used=[color],
            estimated_cost_cny=0.01,
            brand="MARD",
            bead_diameter_mm=5.0,
        )


def test_provider_chain_uses_quantize_fallback_after_all_ai_failures() -> None:
    chain = PreviewProviderChain(
        providers=[StaticProvider("primary", should_fail=True), StaticProvider("backup", should_fail=True)],
        fallback_provider=FallbackProvider(pattern_builder=FakePatternBuilder()),
    )

    result = chain.generate(PNG_1X1, StylePreset.CARTOON_FALLBACK, SizePreset.LARGE_100X120)

    assert result.provider_used == "fallback_quantize"
    assert result.fallback_count == 2
    assert result.target_color_count == 1
    assert result.image.startswith(b"\x89PNG")


def test_reverse_proxy_monitor_logs_alert_after_three_failures(caplog: pytest.LogCaptureFixture) -> None:
    def failing_probe(_url: str, _timeout: float) -> bool:
        raise RuntimeError("network down")

    monitor = ReverseProxyHealthMonitor(
        health_url="https://example.test/health",
        interval_seconds=1,
        alert_after_seconds=0,
        probe=failing_probe,
    )

    with caplog.at_level(logging.ERROR):
        asyncio.run(monitor.check_once())
        asyncio.run(monitor.check_once())
        asyncio.run(monitor.check_once())

    assert "ADR-007 alert" in caplog.text

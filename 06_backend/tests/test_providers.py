from __future__ import annotations

import asyncio
import base64
import io
import logging
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from PIL import Image

from pindou.pattern.builder import PatternBuilder
from pindou.providers.base import PreviewProvider, PreviewProviderError, PreviewResult, SizePreset, StylePreset
from pindou.providers.chain import PreviewProviderChain
from pindou.providers.fallback_quantize import FallbackProvider
from pindou.providers.xiaochi_gpt import XiaochiGptProvider
from pindou.tasks.reverse_proxy_health_check import ReverseProxyHealthMonitor


def make_png_1x1() -> bytes:
    output = io.BytesIO()
    Image.new("RGBA", (1, 1), (255, 255, 255, 255)).save(output, format="PNG")
    return output.getvalue()


PNG_1X1 = make_png_1x1()


def white_bg_preview_png() -> bytes:
    output = io.BytesIO()
    image = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
    for x in range(10, 22):
        for y in range(10, 22):
            image.putpixel((x, y), (255, 120, 120, 255))
    image.save(output, format="PNG")
    return output.getvalue()


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
    preset_values = {
        SizePreset.SINGLE_BOARD_26X26.value,
        SizePreset.DOUBLE_BOARD_52X52.value,
        SizePreset.TRIPLE_BOARD_78X78.value,
        SizePreset.FOUR_BOARD_104X104.value,
    }
    assert preset_values == {"26x26", "52x52", "78x78", "104x104"}
    assert SizePreset("45x30").warning is not None


def test_xiaochi_provider_retries_once_with_new_seed_hint() -> None:
    fake_images = FakeImages([RuntimeError("proxy down"), api_response(PNG_1X1)])
    fake_client = SimpleNamespace(images=fake_images)
    provider = XiaochiGptProvider(
        api_key="test-key",
        base_url="https://example.test/v1",
        client=fake_client,
        seed_factory=lambda: 99,
    )

    result = provider.generate(PNG_1X1, StylePreset.Q_PORTRAIT, SizePreset.DOUBLE_BOARD_52X52, seed=1)

    assert result.image == PNG_1X1
    assert result.provider_used == "xiaochi_gpt_image_2"
    assert result.fallback_count == 0
    assert len(fake_images.calls) == 2
    assert "Seed hint: 1" in str(fake_images.calls[0]["prompt"])
    assert "Seed hint: 99" in str(fake_images.calls[1]["prompt"])
    assert fake_images.calls[1]["response_format"] == "b64_json"


def test_xiaochi_provider_uses_silent_subject_detect_minimal_palette_prompt() -> None:
    fake_images = FakeImages([api_response(PNG_1X1)])
    fake_client = SimpleNamespace(images=fake_images)
    provider = XiaochiGptProvider(
        api_key="test-key",
        base_url="https://example.test/v1",
        client=fake_client,
        retry_count=0,
    )

    result = provider.generate(PNG_1X1, StylePreset.Q_PET, SizePreset.DOUBLE_BOARD_52X52, seed=7)
    prompt = str(fake_images.calls[0]["prompt"])

    assert result.target_color_count == 6
    assert "先自动识别画面真实主体" in prompt
    assert "即使与所选风格不符，也以真实主体为准" in prompt
    assert "【静默执行，不向用户提示】" in prompt
    assert "通常 3-6 种" in prompt
    assert "真实主体识别优先，静默纠偏" in prompt
    assert "萌宠提示" in prompt


def test_xiaochi_provider_strips_ai_white_background_to_alpha() -> None:
    fake_images = FakeImages([api_response(white_bg_preview_png())])
    fake_client = SimpleNamespace(images=fake_images)
    provider = XiaochiGptProvider(
        api_key="test-key",
        base_url="https://example.test/v1",
        client=fake_client,
        retry_count=0,
        enable_white_bg_auto_nobead=True,
    )

    result = provider.generate(PNG_1X1, StylePreset.Q_PET, SizePreset.SINGLE_BOARD_26X26)
    image = Image.open(io.BytesIO(result.image)).convert("RGBA")

    assert result.metadata["white_bg_detected"] is True
    assert image.getpixel((0, 0))[3] == 0
    assert image.getpixel((16, 16))[3] == 255


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

    result = chain.generate(PNG_1X1, StylePreset.Q_PET, SizePreset.TRIPLE_BOARD_78X78)

    assert result.provider_used == "primary"
    assert result.fallback_count == 0
    assert "fallback_chain_failures" not in result.metadata


def test_provider_chain_uses_backup_after_primary_failure() -> None:
    chain = PreviewProviderChain(
        providers=[StaticProvider("primary", should_fail=True), StaticProvider("backup")],
        fallback_provider=StaticProvider("fallback"),
    )

    result = chain.generate(PNG_1X1, StylePreset.Q_COUPLE, SizePreset.TRIPLE_BOARD_78X78)

    assert result.provider_used == "backup"
    assert result.fallback_count == 1
    assert result.metadata["fallback_chain_failures"][0]["provider"] == "primary"


def test_provider_chain_uses_quantize_fallback_after_all_ai_failures() -> None:
    chain = PreviewProviderChain(
        providers=[StaticProvider("primary", should_fail=True), StaticProvider("backup", should_fail=True)],
        fallback_provider=FallbackProvider(pattern_builder=PatternBuilder(target_colors=8)),
    )

    result = chain.generate(PNG_1X1, StylePreset.CARTOON_FALLBACK, SizePreset.DOUBLE_BOARD_52X52)

    assert result.provider_used == "fallback_quantize"
    assert result.fallback_count == 2
    assert result.target_color_count >= 1
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

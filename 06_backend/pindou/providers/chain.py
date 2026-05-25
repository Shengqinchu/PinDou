"""Preview provider fallback chain."""

from __future__ import annotations

from dataclasses import replace

from pindou.providers.base import PreviewProvider, PreviewProviderError, PreviewResult, SizePreset, StylePreset


class PreviewProviderChain(PreviewProvider):
    """Try AI providers first, then fall back to script quantization."""

    name = "preview_provider_chain"

    def __init__(
        self,
        *,
        providers: list[PreviewProvider],
        fallback_provider: PreviewProvider,
    ) -> None:
        if not providers:
            raise ValueError("PreviewProviderChain requires at least one primary provider.")
        self.providers = providers
        self.fallback_provider = fallback_provider

    def generate(
        self,
        image: bytes,
        style_preset: StylePreset,
        size_preset: SizePreset,
        seed: int | None = None,
    ) -> PreviewResult:
        failures: list[dict[str, str]] = []

        for provider in self.providers:
            try:
                result = provider.generate(image, style_preset, size_preset, seed)
                return self._with_chain_metadata(result, failures)
            except Exception as exc:  # noqa: BLE001 - fallback chain must catch provider-specific errors.
                failures.append({"provider": provider.name, "error": str(exc)})

        try:
            result = self.fallback_provider.generate(image, style_preset, size_preset, seed)
        except Exception as exc:  # noqa: BLE001 - normalize full chain failure.
            failures.append({"provider": self.fallback_provider.name, "error": str(exc)})
            raise PreviewProviderError("All preview providers failed.") from exc
        return self._with_chain_metadata(result, failures)

    @staticmethod
    def _with_chain_metadata(result: PreviewResult, failures: list[dict[str, str]]) -> PreviewResult:
        if not failures:
            return result
        metadata = {**result.metadata, "fallback_chain_failures": failures}
        return replace(result, fallback_count=result.fallback_count + len(failures), metadata=metadata)

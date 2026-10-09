"""Thin model-client boundary for deterministic development integration.

No provider selection, SDK, prompt policy, tools, or additional retry loop. A future
production client must validate output against an approved tutoring policy before
returning text; text-shape validation alone does not establish semantic safety.
"""

from typing import Protocol

from ai_tutor.processing_service import ProcessingInput
from ai_tutor.worker import ProcessingFailure


class ModelClient(Protocol):
    async def generate(self, request: ProcessingInput) -> str:
        """Return validated text, propagate cancellation, and never retry internally."""
        ...


class ModelProcessor:
    """Adapt one model-client invocation to the existing worker processor boundary."""

    def __init__(self, client: ModelClient):
        self.client = client

    async def __call__(self, request: ProcessingInput) -> str:
        # Worker owns timing, authorization, leases, and the single retry budget.
        response = await self.client.generate(request)
        if not isinstance(response, str) or not response.strip() or "\x00" in response:
            raise ProcessingFailure("MODEL_INVALID_OUTPUT")
        return response  # Preserve valid text exactly; no trimming/coercion.


class FakeModelClient:
    """Explicitly injected synthetic response; never a fallback for a real provider.

    Callers supply reviewed synthetic text. No input capture, database access, network
    access, or automatic configuration. The call counter is local test evidence only.
    """

    def __init__(self, response: str):
        if not isinstance(response, str) or not response.strip() or "\x00" in response:
            raise ValueError("A nonempty synthetic text response is required")
        self._response = response
        self.calls = 0

    async def generate(self, request: ProcessingInput) -> str:
        self.calls += 1
        return self._response

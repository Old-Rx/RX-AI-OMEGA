from dataclasses import dataclass

from .config import Settings
from .models import WorkflowStep
from .providers import GenerationRequest, build_provider


@dataclass
class RuntimeEngine:
    settings: Settings

    def run(self, step: WorkflowStep, context: dict[str, str]) -> str:
        provider = build_provider(step.agent.provider or self.settings.provider, self.settings)
        return provider.generate(
            GenerationRequest(
                instructions=step.agent.instructions,
                prompt=step.prompt,
                context=context,
            )
        )

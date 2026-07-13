"""Concrete active-target transport adapters."""

from ragscanner.targets.generic_rest import (
    DestinationResolver,
    GenericRestResponseMapping,
    GenericRestTargetAdapter,
    GenericRestTargetConfig,
    SystemDestinationResolver,
    render_json_template,
)

__all__ = [
    "DestinationResolver",
    "GenericRestResponseMapping",
    "GenericRestTargetAdapter",
    "GenericRestTargetConfig",
    "SystemDestinationResolver",
    "render_json_template",
]

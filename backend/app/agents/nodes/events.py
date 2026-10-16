from typing import Any

from langgraph.config import get_stream_writer


def emit(event: str, **data: Any) -> None:
    try:
        writer = get_stream_writer()
    except Exception:
        return
    writer({"event": event, "data": data})


def status(stage: str, message: str) -> None:
    emit("status", stage=stage, message=message)

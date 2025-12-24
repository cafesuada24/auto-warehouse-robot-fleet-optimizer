import datetime
import json
import logging
import os
import sys
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Final, override

from .logging_context import get_context

# ---------- JSON formatting ----------

_BUILTIN_RECORD_ATTRS: Final[frozenset[str]] = frozenset(
    {
        # logging.LogRecord core
        'name',
        'msg',
        'args',
        'levelname',
        'levelno',
        'pathname',
        'filename',
        'module',
        'exc_info',
        'exc_text',
        'stack_info',
        'lineno',
        'funcName',
        'created',
        'msecs',
        'relativeCreated',
        'thread',
        'threadName',
        'processName',
        'process',
        # derived/commonly present
        'message',
    },
)


def _json_default(value: object) -> str:
    # Never let logging blow up because something isn't JSON-serializable.
    return repr(value)


class _JsonFormatter(logging.Formatter):
    """Minimal JSON formatter without external dependencies.

    Produces stable keys and supports `extra={...}` fields.
    """

    @override
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            'ts': datetime.datetime.fromtimestamp(
                record.created,
                tz=datetime.UTC,
            ).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'msg': record.getMessage(),
        }

        # Standard useful fields
        if record.exc_info:
            payload['exc_info'] = self.formatException(record.exc_info)

        # Include all non-builtin record attributes (from `extra=...`)
        extras = _extract_extras(record)
        if extras:
            payload.update(extras)

        return json.dumps(payload, ensure_ascii=False, default=_json_default)


def _extract_extras(record: logging.LogRecord) -> dict[str, object]:
    out: dict[str, object] = {}
    for k, v in record.__dict__.items():
        if k not in _BUILTIN_RECORD_ATTRS:
            out[k] = v
    return out


# ---------- Configuration ----------


@dataclass(frozen=True, slots=True)
class LogConfig:
    level: str = 'INFO'
    json: bool = False

    service: str = 'unknown-service'
    version: str = '0.0.0'

    log_dir: Path | None = None
    filename: str = 'app.log'

    rotate_bytes: int = 50 * 1024 * 1024
    backup_count: int = 5


def _config_from_env() -> LogConfig:
    truthy = {'1', 'true', 'yes', 'y', 'on', 't'}
    log_dir = os.getenv('LOG_DIR')
    return LogConfig(
        level=os.getenv('LOG_LEVEL', 'INFO'),
        json=os.getenv('LOG_JSON', '0').strip().lower() in truthy,
        service=os.getenv('SERVICE_NAME', 'unknown-service'),
        version=os.getenv('SERVICE_VERSION', '0.0.0'),
        log_dir=Path(log_dir) if log_dir else None,
        filename=os.getenv('FILENAME', 'app.log'),
        rotate_bytes=int(os.getenv("LOG_ROTATE_BYTES", "52428800")),
        backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
    )


def _parse_level(level: str) -> int:
    name = level.strip().upper()
    value = getattr(logging, name, None)
    return value if isinstance(value, int) else logging.INFO


# ---------- Context adapter ----------


class ContextLogger(logging.LoggerAdapter[logging.Logger]):
    """Attach stable context to every log line.

    Use:
        log = ContextLogger(logging.getLogger("svc"), {"request_id": "..."}).
    """

    @override
    def process(
        self,
        msg: object,
        kwargs: MutableMapping[str, object],
    ) -> tuple[object, MutableMapping[str, object]]:
        extra_obj = kwargs.get('extra')

        base_ctx: dict[str, object] = dict(self.extra) if self.extra else {}

        if extra_obj is None:
            kwargs['extra'] = base_ctx
            return msg, kwargs

        if not isinstance(extra_obj, Mapping):
            raise TypeError(
                f'logging "extra" must be a mapping, got {type(extra_obj).__name__}',
            )

        merged: dict[str, object] = {**base_ctx, **dict(extra_obj)}
        kwargs['extra'] = merged
        return msg, kwargs


def get_logger(name: str, *, ctx: Mapping[str, Any] | None = None) -> ContextLogger:
    """Returns a LoggerAdapter that automatically merges contextual fields."""
    base = logging.getLogger(name)
    return ContextLogger(base, dict(ctx) if ctx else {})


# ---------- LogRecord factory (global/static fields) ----------

_RECORD_FACTORY_INSTALLED: bool = False


def _install_record_factory(static_fields: Mapping[str, object]) -> None:
    global _RECORD_FACTORY_INSTALLED

    if _RECORD_FACTORY_INSTALLED:
        # If already installed, do nothing. (Deterministic + avoids factory stacking.)
        return

    old_factory = logging.getLogRecordFactory()

    def factory(*args: object, **kwargs: object) -> logging.LogRecord:
        record = old_factory(*args, **kwargs)
        for k, v in static_fields.items():
            setattr(record, k, v)

        ctx = get_context()
        for k, v in ctx.items():
            if not hasattr(record, k):
                setattr(record, k, v)
        return record

    logging.setLogRecordFactory(factory)
    _RECORD_FACTORY_INSTALLED = True


# ---------- Setup ----------


def _create_file_handler(cfg: LogConfig, level: int) -> logging.FileHandler:
    assert cfg.log_dir is not None

    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.log_dir / cfg.filename

    handler = RotatingFileHandler(
        filename=path,
        maxBytes=cfg.rotate_bytes,
        backupCount=cfg.backup_count,
        encoding='utf-8',
    )
    handler.setLevel(level)
    return handler


def setup_logging(config: LogConfig | None = None) -> None:
    """Idempotent-ish logger setup."""
    cfg = config or _config_from_env()
    level = _parse_level(cfg.level)

    root = logging.getLogger()
    root.setLevel(level)

    # Replace handlers to avoid duplicate logs in reloads/tests
    for h in root.handlers[:]:
        root.removeHandler(h)

    if cfg.json:
        formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s %(levelname)s %(name)s - %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S%z',
        )

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(formatter)
    root.addHandler(stdout_handler)

    if cfg.log_dir is not None:
        file_hanlder = _create_file_handler(cfg, level)
        file_hanlder.setFormatter(formatter)
        root.addHandler(file_hanlder)

    # Add global context via LogRecord factory so it's always present
    _install_record_factory({'service': cfg.service, 'version': cfg.version})

import contextlib
import json
import logging
from pathlib import Path

import pytest
from awrfo.logging.logger import LogConfig, get_logger, setup_logging


def _flush_logging() -> None:
    """Ensure handlers flush so capsys sees the output."""
    root = logging.getLogger()
    for h in root.handlers[:]:
        with contextlib.suppress(Exception):
            h.flush()


@pytest.fixture(autouse=True)
def clean_root_handlers() -> None:
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)


def _stdout_lines(capsys: pytest.CaptureFixture[str]) -> list[str]:
    out = capsys.readouterr().out
    return [ln for ln in out.splitlines() if ln.strip()]


def test_json_is_printed_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(LogConfig(json=True, service='svc-a', version='1.2.3'))

    log = get_logger('test.json')
    log.info('hello')

    _flush_logging()
    lines = _stdout_lines(capsys)
    assert len(lines) == 1

    payload = json.loads(lines[0])
    assert payload['msg'] == 'hello'
    assert payload['level'] == 'INFO'
    assert payload['logger'] == 'test.json'
    assert payload['service'] == 'svc-a'
    assert payload['version'] == '1.2.3'
    assert 'ts' in payload


def test_json_includes_extra_fields(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(LogConfig(json=True))

    log = get_logger('test.extra')
    log.info('op', extra={'user_id': 42, 'action': 'create'})

    _flush_logging()
    payload = json.loads(_stdout_lines(capsys)[0])
    assert payload['user_id'] == 42
    assert payload['action'] == 'create'


def test_non_serializable_extra_does_not_crash(
    capsys: pytest.CaptureFixture[str],
) -> None:
    setup_logging(LogConfig(json=True))

    class Weird:
        pass

    log = get_logger('test.nonserial')
    log.info('x', extra={'obj': Weird()})

    _flush_logging()
    payload = json.loads(_stdout_lines(capsys)[0])
    assert 'obj' in payload
    assert isinstance(payload['obj'], str)


def test_plain_formatter_prints_text(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(LogConfig(json=False))

    log = get_logger('test.plain')
    log.warning('plain-text')

    _flush_logging()
    line = _stdout_lines(capsys)[0]
    assert 'plain-text' in line
    assert 'WARNING' in line
    assert 'test.plain' in line


def test_log_level_respected(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(LogConfig(level='ERROR', json=True))

    log = get_logger('test.level')
    log.info('nope')
    log.error('yes')

    _flush_logging()
    lines = _stdout_lines(capsys)
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload['msg'] == 'yes'


def test_file_logging_writes_file(tmp_path: Path) -> None:
    log_dir = tmp_path / 'logs'
    setup_logging(LogConfig(json=True, log_dir=log_dir, filename='service.log'))

    log = get_logger('test.file')
    log.info('file-test')
    _flush_logging()

    log_file = log_dir / 'service.log'
    assert log_file.exists()

    content = log_file.read_text(encoding='utf-8').strip().splitlines()
    assert content, 'expected at least one log line in file'

    payload = json.loads(content[-1])
    assert payload['msg'] == 'file-test'
    assert payload['logger'] == 'test.file'


def test_setup_logging_is_idempotent_stdout_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    setup_logging(LogConfig(json=True))
    setup_logging(LogConfig(json=True))

    log = get_logger('test.idempotent')
    log.info('once')

    _flush_logging()
    lines = _stdout_lines(capsys)
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload['msg'] == 'once'

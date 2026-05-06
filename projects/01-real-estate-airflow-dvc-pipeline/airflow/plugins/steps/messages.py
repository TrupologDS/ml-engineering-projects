"""Optional Airflow Telegram callbacks with safe environment-based settings."""

from __future__ import annotations

import logging
import os
from typing import Any

from airflow.providers.telegram.hooks.telegram import TelegramHook

logger = logging.getLogger(__name__)


def _get_setting(name: str) -> str | None:
    # Airflow Variables take precedence so production credentials stay outside files.
    try:
        from airflow.models import Variable

        value = Variable.get(name, default_var=None)
        if value:
            return value
    except Exception:
        logger.debug("Airflow Variable lookup failed for %s", name, exc_info=True)
    return os.getenv(name)


def _send_message(text: str) -> None:
    token = _get_setting("TELEGRAM_BOT_TOKEN")
    chat_id = _get_setting("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        # Missing notification credentials should never fail the data pipeline.
        logger.info("Telegram notification skipped because credentials are not configured.")
        return

    hook = TelegramHook(token=token, chat_id=chat_id)
    hook.send_message({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})


def send_telegram_failure_message(context: dict[str, Any]) -> None:
    dag = context.get("dag")
    dag_id = getattr(dag, "dag_id", str(dag))
    run_id = context.get("run_id", "")
    task_key = context.get("task_instance_key_str", "")
    exc = context.get("exception", "")
    _send_message(
        f"Airflow DAG failed: `{dag_id}`\n"
        f"Run ID: `{run_id}`\n"
        f"Task: `{task_key}`\n"
        f"Error: `{exc}`"
    )


def send_telegram_success_message(context: dict[str, Any]) -> None:
    dag = context.get("dag")
    dag_id = getattr(dag, "dag_id", str(dag))
    run_id = context.get("run_id", "")
    _send_message(f"Airflow DAG completed: `{dag_id}`\nRun ID: `{run_id}`")

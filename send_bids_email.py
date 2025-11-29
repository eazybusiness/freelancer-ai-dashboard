#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import dotenv_values

from email_notifier import EmailSender
from generate_bids import _build_email_bodies, _read_notification_email_from_env_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Send an email summary for existing bids JSON files "
            "(no new AI calls)."
        ),
    )
    parser.add_argument(
        "--input-json",
        required=True,
        help="Path to bids JSON file produced by generate_bids.py.",
    )
    parser.add_argument(
        "--to",
        help=(
            "Recipient email address. If provided, overrides NOTIFICATION_EMAIL "
            "from the environment/.env."
        ),
    )

    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        raise SystemExit(f"Input JSON not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        payload: Dict[str, Any] = json.load(f)

    generated = payload.get("generated_bids") or []
    if not isinstance(generated, list) or not generated:
        print("No generated_bids found in input JSON; nothing to email.")
        return

    # Resolve recipient: CLI --to takes precedence, then environment/.env.
    notification_email = args.to
    if not notification_email:
        # First from environment, then python-dotenv,
        # then a manual parser as a last resort.
        notification_email = os.getenv("NOTIFICATION_EMAIL")
        if not notification_email:
            env_path = Path(__file__).resolve().parent / ".env"
            try:
                env_values = dotenv_values(env_path)
            except Exception:
                env_values = {}
            notification_email = env_values.get("NOTIFICATION_EMAIL")

        if not notification_email:
            notification_email = _read_notification_email_from_env_file()

    if not notification_email:
        print("NOTIFICATION_EMAIL is not set; cannot send email.")
        return

    sender = EmailSender()
    plain_body, html_body = _build_email_bodies(payload)
    subject = f"[Freelance AI] {len(generated)} existing bid draft(s)"

    sender.send_email(
        subject=subject,
        body=plain_body,
        notification_email=notification_email,
        attachment_paths=[str(input_path)],
        html_body=html_body,
    )


if __name__ == "__main__":
    main()

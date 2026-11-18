"""Send one real STK Push to your phone with the configured Daraja credentials.

This is a manual diagnostic tool: it requests an access token, sends a single
STK Push and prints the Daraja response. Nothing is written to the database.

Usage (from the backend/ directory, with .env filled in):

    python scripts/mpesa_sandbox_check.py 254712345678
    python scripts/mpesa_sandbox_check.py 0712345678 1

The phone argument is your own Safaricom number. The amount defaults to KES 1.
Your MPESA_CALLBACK_URL must be reachable from the internet (e.g. ngrok) if you
want to see the callback result – see docs/mpesa-testing.md.
"""

import argparse
import os
import sys

# Allow `python scripts/mpesa_sandbox_check.py` from the backend directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.services import mpesa  # noqa: E402

REQUIRED = (
    "MPESA_CONSUMER_KEY",
    "MPESA_CONSUMER_SECRET",
    "MPESA_PASSKEY",
    "MPESA_CALLBACK_URL",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send one Daraja sandbox STK Push.")
    parser.add_argument("phone", help="Your Safaricom number, e.g. 254712345678")
    parser.add_argument(
        "amount", nargs="?", type=int, default=1, help="Amount in KES (default: 1)"
    )
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        config = app.config

        missing = [
            name
            for name in REQUIRED
            if not config.get(name) or str(config.get(name)).startswith("your-")
        ]
        if missing:
            print("Missing or placeholder settings in .env: " + ", ".join(missing))
            return 1

        if args.amount < 1:
            print("Amount must be at least KES 1.")
            return 1

        try:
            msisdn = mpesa.normalize_msisdn(args.phone)
        except ValueError as exc:
            print(exc)
            return 1

        print(f"Environment: {config.get('MPESA_ENV')}")
        print(f"Shortcode:   {config.get('MPESA_SHORTCODE')}")
        print(f"Callback:    {config.get('MPESA_CALLBACK_URL')}")
        print(f"Phone:       {msisdn}")
        print(f"Amount:      KES {args.amount}")

        try:
            mpesa._get_access_token()
        except Exception as exc:  # network / auth problems
            print(f"Could not get an access token: {exc}")
            return 1
        print("Access token: OK")

        try:
            response = mpesa.stk_push(
                phone=msisdn,
                amount=args.amount,
                account_reference="SANDBOX",
                description="Sandbox test",
            )
        except Exception as exc:
            print(f"STK Push failed: {exc}")
            return 1

        print("\nSTK Push response:")
        for key, value in response.items():
            print(f"  {key}: {value}")

        if response.get("ResponseCode") != "0":
            print("\nDaraja rejected the request – check the error message above.")
            return 1

        print(
            "\nCheck your phone and enter your M-Pesa PIN.\n"
            "Safaricom will POST the result to your callback URL; watch "
            "MPESA_CALLBACK_URL (ngrok) and the donations table."
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

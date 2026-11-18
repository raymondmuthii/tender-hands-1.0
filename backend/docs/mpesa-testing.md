# Testing M-Pesa (Daraja sandbox)

This walks through verifying the STK Push integration end to end against
Safaricom's **sandbox**. Nothing here charges real money.

> **Status:** the code path is unit-tested (`backend/tests/test_mpesa.py`), but
> the live sandbox flow has **not** been verified yet. Treat it as verified only
> once the checklist at the bottom has been completed and you have seen a
> `completed` donation with a real M-Pesa receipt.

---

## 1. Create the Daraja app (you do this once)

1. Sign in at <https://developer.safaricom.co.ke/> with your Safaricom number.
2. Open **My Apps → Add a new app**.
3. Name it (e.g. `Tender Hands`) and tick **Lipa Na M-Pesa Online**. Save.
4. Open the app's **Keys** tab and copy:
   - **Consumer Key** → `MPESA_CONSUMER_KEY`
   - **Consumer Secret** → `MPESA_CONSUMER_SECRET`
5. Open **Simulate → Test Credentials** (or <https://developer.safaricom.co.ke/test_credentials>)
   and copy the **Lipa na M-Pesa Online Passkey** → `MPESA_PASSKEY`.
   The sandbox passkey belongs to the sandbox shortcode **174379**.

Sandbox values (already the defaults in `app/config.py`):

| Setting | Sandbox value |
|---|---|
| Shortcode | `174379` |
| Passkey | from the Test Credentials page |
| Transaction type | `CustomerPayBillOnline` |
| Test phone number | `254708374149` |
| Base URL | `https://sandbox.safaricom.co.ke` |

## 2. Expose your local callback

Safaricom needs a public **HTTPS** URL to POST the payment result to.

```bash
# terminal 1 – Flask
cd backend && .venv\Scripts\activate && flask --app api:app run --debug

# terminal 2 – tunnel to Flask's port
ngrok http 5000
```

Copy the `https://<random>.ngrok-free.app` address ngrok prints and set:

```env
MPESA_CALLBACK_URL=https://<random>.ngrok-free.app/api/mpesa/callback
```

Notes:

- The URL must end in `/api/mpesa/callback` and must be HTTPS.
- Free ngrok URLs change every restart; update `.env` and restart Flask when
  they do.
- `ngrok` itself is a free download from <https://ngrok.com/download>; you need
  a free ngrok account and `ngrok config add-authtoken <token>` once.

## 3. Check the credentials without a phone

```bash
cd backend
.venv\Scripts\activate
python scripts/mpesa_sandbox_check.py 254708374149 1
```

The script requests an access token, sends exactly one STK Push and prints
Daraja's response. It writes nothing to the database. If the token request
fails, the consumer key/secret are wrong; if the push fails, check the
shortcode, passkey and callback URL.

## 4. Run a real sandbox payment

1. Make sure you are logged in as a donor in the frontend and a charity is
   approved (`python seed.py` gives you both).
2. Click **Donate**, enter a phone number you control (or the sandbox test
   number `254708374149`) and an amount of at least KES 10.
3. Approve the prompt on the phone with the M-Pesa PIN.

### What success looks like

Request (`POST /mpesa/stkpush/v1/processrequest`) — handled by
`app/services/mpesa.py`:

- `Timestamp` is `YYYYMMDDHHmmss` in **East Africa Time**, and the `Password` is
  `base64(Shortcode + Passkey + Timestamp)` using that same string.
- `Amount` is a whole number of KES.
- `PartyA` / `PhoneNumber` are `2547XXXXXXXX` (no `+`, no leading zero).
- `AccountReference` ≤ 12 characters, `TransactionDesc` ≤ 13 characters.

Daraja replies with `ResponseCode: "0"` and a `CheckoutRequestID`. That is only
an acknowledgement that the prompt was sent.

Callback (`POST /api/mpesa/callback`) — a successful payload:

```json
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "29115-34620561-1",
      "CheckoutRequestID": "ws_CO_191220191020363925",
      "ResultCode": 0,
      "ResultDesc": "The service request is processed successfully.",
      "CallbackMetadata": {
        "Item": [
          { "Name": "Amount", "Value": 1500 },
          { "Name": "MpesaReceiptNumber", "Value": "QHX4XXXXXX" },
          { "Name": "TransactionDate", "Value": 20261118120530 },
          { "Name": "PhoneNumber", "Value": 254708374149 }
        ]
      }
    }
  }
}
```

In the database (`donations` table) the matching row goes from:

| column | before | after a successful callback |
|---|---|---|
| `status` | `pending` | `completed` |
| `checkout_request_id` | `ws_CO_...` | unchanged |
| `mpesa_receipt` | `NULL` | `QHX4XXXXXX` |

A failed or cancelled payment (`ResultCode` 1032 "Request cancelled by user",
1 "Insufficient funds", 1037 "Timeout"…) sets `status = 'failed'` and leaves
`mpesa_receipt` empty. The app returns HTTP 200 with
`{"ResultCode": 0, "ResultDesc": "Accepted"}` in both cases, which is what
Daraja expects; it retries a few times when the callback does not answer 200.

You can confirm with:

```bash
cd backend && .venv\Scripts\activate
python -c "from app import create_app; from app.models.donation import Donation; app=create_app();
with app.app_context(): print([(d.id, d.status, d.mpesa_receipt, d.checkout_request_id) for d in Donation.query.all()])"
```

(One-liner on PowerShell is awkward — a tiny script or `flask shell` is fine too.)

## 5. Common sandbox errors

| Daraja response | Likely cause |
|---|---|
| `Invalid Access Token` | Consumer key/secret wrong, or the token expired (tokens last ~1 hour; the app requests a fresh one per push) |
| `Invalid Timestamp` / auth failure | Server clock not in EAT – this repo now builds the timestamp in `Africa/Nairobi` time (UTC+3) |
| `Invalid PhoneNumber` | Number not in `2547XXXXXXXX` form – the service normalises `07…`, `+254…` and `254…` |
| `Bad Request - Invalid CallBackURL` | `MPESA_CALLBACK_URL` is not a public HTTPS URL |
| `The transaction is being processed` | The same `CheckoutRequestID` still in flight – wait before retrying |

---

## ✅ Checklist – steps only you can do

Tick these off. Until they are all done and you have seen a `completed`
donation, the live payment flow is **unverified**.

- [ ] Create a Daraja account at <https://developer.safaricom.co.ke/> (Safaricom number required).
- [ ] Create an app with **Lipa Na M-Pesa Online** and copy the Consumer Key and Secret.
- [ ] Copy the sandbox passkey for shortcode `174379` from **Test Credentials**.
- [ ] Put `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_PASSKEY` into `backend/.env`.
- [ ] Start ngrok, put the HTTPS URL + `/api/mpesa/callback` into `MPESA_CALLBACK_URL`, restart Flask.
- [ ] Run `python scripts/mpesa_sandbox_check.py <your phone>` and confirm `Access token: OK` and `ResponseCode: 0`.
- [ ] Approve the STK prompt on your own phone (or the sandbox test number `254708374149`).
- [ ] Confirm in the database that the donation is `completed` with an `mpesa_receipt`.
- [ ] Send me the outcome so the README/status can be updated.

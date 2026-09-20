# Sample Evidence Set — "Operation Phantom Grid" mini-scenario

These 6 files are the exact fixtures your backend's test suite already uses (`backend/tests/fixtures/`) — I ran the full pytest suite against them before packaging (97/97 tests pass, including the end-to-end lifecycle test), so this is a known-good dataset, not a guess.

Drop all 6 into the Evidence Intake dropzone. The filenames are chosen so the frontend's `detectSourceType()` auto-picks the right type — you shouldn't need to manually override any of them.

## The story these files tell

A phishing APK ("fake bank alert") compromises a victim's phone, money is drained through a two-hop mule chain, and cashes out to one syndicate account — all within about 90 minutes on 15 March 2024.

## What links what (use this to verify correlation is actually working)

| Shared identifier | Appears in |
|---|---|
| Phone `+919811122233` | `cdr_delhi_mumbai.csv` (caller) ↔ both Android log files (`phone=`/`subscriber_phone`) |
| IMEI `860123456789012` | `cdr_delhi_mumbai.csv` ↔ both Android log files (`imei=`/`device_imei`) |
| IP `185.220.101.5` | `email_phishing_alert.eml` (Received header) ↔ both Android log files (`assigned_ip` / network telemetry endpoint) |
| Domain `fraud-alert-axis.com` | Both `.eml` files — same operator sent the phishing email *and* coordinated the mule payout |
| UPI handle `cashout_syndicate@paytm` | Appears twice in `bank_upi_transactions.csv` — two different mule accounts converging on one cash-out account |
| Account chain | `VICTIM_ACC_001 → MULE_ACC_101 → MULE_ACC_202 → CASHOUT_ACC_303` — a 3-hop chain completed inside ~45 minutes |

## What to check on each screen

- **Evidence Intake:** all 6 files should show "processed" status, not "failed." One blank row is deliberately included in both the CDR and bank CSVs (malformed-row handling) — it should be silently skipped, not crash the ingestion.
- **Correlation Board:** you should see one connected cluster, not 6 isolated islands — the phone/IMEI/IP links above are what should be pulling everything together. The account chain should visibly fan in toward `CASHOUT_ACC_303`.
- **Risk Desk:** the mule accounts (especially `MULE_ACC_101` and the cash-out account) should score high, with reason codes mentioning multi-hop routing given the tight ~90-minute timestamp window.
- **Brief Viewer:** export should generate without error, custody chain should show as verified (all 6 files were hashed on ingest).

If any of the above doesn't hold — e.g., files show as isolated instead of linked, or nothing gets flagged as high-risk — that's a real bug to chase, not a data problem, since this exact dataset already passes the backend's own correlation and risk tests.

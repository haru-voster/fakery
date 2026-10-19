# BlueRock Group investments – Django backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate && python manage.py createsuperuser
python manage.py runserver
Copy .env.example values into your environment. Without email/SMS keys, emails print to the console and SMS is logged only.
Transactions are entered by staff in /admin/ after a real payment is confirmed.

Public landing page is /, dashboard is /dashboard/. Floating WhatsApp button and chat widget are on every page; chat messages are saved (see Support messages in /admin/) and alert staff by SMS and email via SUPPORT_PHONE / SUPPORT_EMAIL.
Set WHATSAPP_NUMBER to your real WhatsApp number.

Dashboard pages: /dashboard/, /dashboard/settings/, /dashboard/fund/, /dashboard/history/. Fund requests are saved as pending; staff mark them completed in /admin/ after a payment is confirmed. The eye button (bottom-left) lets users change theme and brightness.

Security: hashed passwords (min 10 chars), password reset by email (links expire in 1 hour), login lockout after 5 failed attempts, password re-entry for withdrawals/transfers, KYC required before withdrawing or transferring, email alerts on password change and withdrawal requests. Planned: 2FA (TOTP).
Use a real SMTP provider (EMAIL_HOST etc.) so reset emails are delivered; without it they print to the console.


## Admin payment review

Staff users see an administrator overview at `/dashboard/` with registered accounts, pending deposits, confirmed deposits, and recent payment activity. Use `/admin/` to search users and review transactions. Verify USDT transfers on the relevant blockchain before marking a deposit `completed`; pending deposits do not count toward the customer's balance. The site does not automatically credit guaranteed 10% daily returns. If you offer investment projections, disclose that they are estimates and do not represent guaranteed or withdrawable funds.


## USDT deposits (Ethereum ERC-20)

This project supports automatic verification of customer-submitted Ethereum mainnet USDT transaction hashes. It does not custody or send funds; deposits go directly to the configured receiving wallet. Configure `USDT_ERC20_RECEIVING_ADDRESS`, `ETHEREUM_RPC_URL`, and `USDT_ERC20_CONFIRMATIONS` in the production environment before enabling deposits. The configured address must be an Ethereum address you control, and the RPC URL must be for Ethereum mainnet. Never put a private key or seed phrase in the application.

Run database migrations with `python manage.py migrate`. To retry pending deposits, schedule `python manage.py check_usdt_deposits` every minute using cron or your hosting scheduler. The customer must paste the transaction hash after sending, because a single shared wallet address cannot automatically identify which customer made a transfer without a unique address or transaction hash. The command verifies the official Ethereum mainnet USDT contract, recipient address, exact amount, successful receipt, and required confirmations before crediting the ledger. Test on a staging environment and with a small amount before production.


## Recent interface improvements

- The appearance/visibility control (moon/sun icon) is positioned at the upper-right of the page and offers Auto, Light, Dark, and brightness settings.
- The public market snapshot refreshes every 60 seconds. When the market API is unavailable, the interface switches to explicitly labelled simulated demo values that animate locally; demo prices are not real market quotes.
- The landing page includes responsive stock photography of people talking and collaborating. The images are illustrative and are not customer testimonials.
- Successful registration signs users in and sends them to their dashboard. Signed-in users who open the signup page are redirected to the dashboard.

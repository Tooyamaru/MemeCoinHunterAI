# Security

## Permanent rules

Never commit:

- Private keys
- Wallet seed phrases
- API secrets
- Credentials
- `.env` files containing secrets

Use environment secrets. Documentation may contain secret variable names only, never values.

## Future trading controls

- Any future trading wallet must be isolated from personal or primary holdings.
- Development must not use unrestricted real-money wallet permissions.
- Withdrawal or transfer automation must not be enabled casually.
- Real-money autonomous trading remains disabled until the documented validation gates pass.
- Secrets must not appear in logs, fixtures, screenshots, generated artifacts, or project state.

P00 creates no integrations, wallet, secret configuration, or fund-access code.

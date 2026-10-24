# Hosting Economy Simulator

This runs the whole site (database, website, frontend, asset service) with Docker Compose.
You need a Linux machine (a small VPS is fine: 2 GB RAM, 2 vCPU) with Docker + Docker Compose v2.

## Quick start

```bash
git clone https://github.com/<you>/ecsrev && cd ecsrev
python3 ecs.py            # guided: asks 2 questions, builds, starts, and offers a first signup link
```

`ecs.py` needs only Python 3 and Docker (no pip packages). You can also run the steps separately with
`python3 ecs.py setup` and `python3 ecs.py start`.

Open the address you chose and log in as **ROBLOX** with the owner password. That account is the
site owner and has the admin panel at `/admin`.

### Putting it on the internet with HTTPS

1. Point your domain's DNS A record at the server.
2. `python3 ecs.py setup` and enter `https://your-domain.com` as the address.
3. `python3 ecs.py start --https` (setup already enables this when you give an https:// address). Caddy gets and renews a free certificate automatically (ports 80 and 443 must be open).

Without `--https` the site listens on `127.0.0.1:5000` only. If you already have your own reverse proxy,
proxy to that port. To expose it directly, set `HTTP_BIND=0.0.0.0` in `.env`.

## Adding users

Signup is by invite (the original site's application flow needs real Roblox/social account checks).
Create a one-time signup link:

```bash
python3 ecs.py invite
```

Send the link to the person. Logged-in users can also create invites from `/internal/invite`.

## Everyday commands

| Command | What it does |
|---|---|
| `python3 ecs.py logs [service]` | follow logs (`web`, `frontend`, `db` ...) |
| `python3 ecs.py status` | show containers and check the site responds |
| `python3 ecs.py stop` | stop (data is kept in Docker volumes) |
| `python3 ecs.py update` | `git pull` and rebuild |
| `python3 ecs.py backup` | dump the database to `backup-<date>.sql` |

Data lives in Docker volumes: `ecs_db-data` (database) and `ecs_site-data` (uploads and thumbnails). Back both up.

## What is and is not included

Included: accounts, catalog, avatars/inventory, economy, groups, forums, messages, admin panel, asset uploads.

Not included (they need Windows-only components or extra infrastructure): the avatar/thumbnail **render
service** and the **game servers (RCC)**. Without the render service, new avatar thumbnails are not generated;
without RCC, games cannot be launched.

## Captchas

hCaptcha is off by default (no third-party service needed). To turn it on, create keys at
https://www.hcaptcha.com and put them in `.env` as `HCAPTCHA_SITEKEY` and `HCAPTCHA_SECRET`, then `python3 ecs.py start`.

## Notes

- Never change `POSTGRES_PASSWORD` in `.env` after the first start (the database was created with it).
- The project targets .NET 6, which is end of life; the image runs it on the .NET 8 runtime.
- Changing `OWNER_PASSWORD` in `.env` later does nothing: it is only used when the ROBLOX account is first created.
  Change the password from the site's settings page instead.

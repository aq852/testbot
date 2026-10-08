Exit code: 0
Wall time: 1 seconds
Output:
# TeleVault

TeleVault is a self-hosted Telegram bot for building a private, searchable media library from channels you administer.

## Included in this first release

- Index documents, videos, and audio posted in source channels
- Private search and one-tap file delivery
- Missing-title requests and user profiles
- Admin statistics and reply-based broadcasts
- MongoDB-backed persistence with indexes

## Planned modules

The data model is intentionally small so we can add force-subscription, premium plans, batch links, referrals, clone bot configuration, and a streaming web gateway without rewriting the core.

## Setup

1. Copy `.env.example` to `.env` and fill in your own Telegram and MongoDB credentials.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Start the bot: `python -m app.main`
4. Add the bot as an administrator to each source channel. New media posts will be indexed automatically.

## Safety

Only index and deliver media you are authorized to share. Do not commit `.env`, session files, or tokens.


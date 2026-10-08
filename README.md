Exit code: 0
Wall time: 0.8 seconds
Output:
# TeleVault

TeleVault is a self-hosted Telegram bot for building a private, searchable media library from channels you administer.

## Included in this first release

- Index documents, videos, and audio posted in source channels
- Private search and one-tap file delivery
- Missing-title requests and user profiles
- Admin statistics and reply-based broadcasts
- Source-channel allowlist, force-subscription, bans, and maintenance mode
- 24-hour batch links built from search results
- MongoDB-backed persistence with indexes

## Planned modules

The data model is intentionally small so we can add premium plans, referrals, clone bot configuration, and a streaming web gateway without rewriting the core.

## Setup

1. Copy `.env.example` to `.env` and fill in your own Telegram and MongoDB credentials. Set `SOURCE_CHANNELS` to the IDs of channels the bot may index; leave `FORCE_SUB_CHANNELS` empty until you configure it.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Start the bot: `python -m app.main`
4. Add the bot as an administrator to each source channel. New media posts will be indexed automatically.

## Safety

Only index and deliver media you are authorized to share. Do not commit `.env`, session files, or tokens.


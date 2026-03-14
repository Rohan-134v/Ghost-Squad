# Ghost Squad Bot

Ghost Squad is a Discord bot built for college students who want to stay accountable with LeetCode and stay on top of placement and internship prep. It tracks daily challenge completion, posts AI-generated placement tips, runs a community Q&A system, and comes with a public leaderboard website and a password-protected admin panel.

The bot is live at: https://ghost-squad-0t11.onrender.com

---

## What it does

**LeetCode accountability**
Every day at 9:30 PM IST, the bot checks who has completed the daily LeetCode challenge and calls out anyone who hasn't. Members register their LeetCode username once and the bot handles the rest. A public leaderboard shows everyone's total problems solved, difficulty breakdown, and whether they finished today's challenge.

**Placement and internship feed**
Every morning at 10 AM IST, the bot posts an AI-generated tip covering topics like resume writing, interview prep, DSA topics that actually come up in placements, LinkedIn optimization, and more. Members can also request tips on demand, get mock interview questions for specific roles, and pull up a full 6-month placement prep roadmap.

**Community Q&A**
Members can post questions using `!ask`, and others can reply and mark them solved. There is also a code sharing command that formats code properly in Discord, and a leaderboard of the most helpful members.

**AI tutor**
The bot uses Google Gemini to answer DSA and placement questions. For LeetCode problems it gives hints and logic explanations without spoiling the solution. For general coding questions it can write full code examples.

**Admin panel**
A password-protected web dashboard at `/admin` lets you manage everything without touching the bot. You can force the daily check, post placement tips manually, manage reminders for any user, toggle features on and off, and change the schedule.

---

## Project structure

```
ghost-squad-v2/
    app.py                  main bot file, runs everything
    database.py             JSON-based data layer
    ai_helper.py            Google Gemini integration
    leetcode_buddy.py       LeetCode stats fetcher
    keep_alive.py           keeps the process alive on free hosting
    requirements.txt
    render.yaml             one-click Render deployment config
    .env.example            environment variable template
    cogs/
        user_commands.py    register, leaderboard, stats commands
        help_system.py      Q&A ask/solve/code commands
        placement_feed.py   placement tip, roadmap, mock interview
        reminders.py        reminder logic (admin-controlled)
    web/
        server.py           Flask server for public site and admin panel
    data/                   auto-created at runtime, stores all JSON data
```

---

## Running it locally

**Requirements:** Python 3.10 or higher

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and fill in your values

# Run
python app.py
```

Once running, the public site is at `http://localhost:8080` and the admin panel is at `http://localhost:8080/admin`.

---

## Environment variables

Copy `.env.example` to `.env` and fill these in:

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Your Discord bot token from the Developer Portal |
| `DISCORD_CHANNEL_ID` | The channel ID where the bot listens and posts check reports |
| `PLACEMENT_CHANNEL_ID` | The channel where placement tips get posted (can be the same channel) |
| `GOOGLE_API_KEY` | Your Gemini API key from Google AI Studio |
| `ADMIN_PASSWORD` | Password to access the admin panel at /admin |

To get these:
- Discord token: discord.com/developers/applications, create a bot, copy the token
- Gemini API key: aistudio.google.com, click Get API Key

---

## Deploying on Render

This project includes a `render.yaml` file so Render can pick up the configuration automatically.

1. Push the repo to GitHub
2. Go to render.com, click New, then Web Service
3. Connect your GitHub repository
4. Set the five environment variables in the Render dashboard under Environment
5. Click Deploy

Render will assign a PORT automatically. The bot reads it on startup so no changes are needed. Your site will be live at `https://your-service-name.onrender.com`.

Note: on Render's free tier the service spins down after 15 minutes of inactivity. The `keep_alive.py` module helps with this but for a production deployment consider upgrading to a paid instance.

---

## Discord commands

### LeetCode tracking

| Command | What it does |
|---|---|
| `!register <username>` | Links your LeetCode account to your Discord |
| `!unregister` | Removes your account from the bot |
| `!mystatus` | Shows your personal stats and today's completion |
| `!leaderboard` | Top 10 members sorted by total problems solved |
| `!progress` | Shows everyone's completion status for today |
| `!stats` | Aggregate stats for the whole community |

### Placement and internships

| Command | What it does |
|---|---|
| `!placement` | Generates an AI placement tip on demand |
| `!roadmap` | Posts the full 6-month placement prep plan |
| `!mock <role>` | Generates a mock interview question for a role, e.g. `!mock SDE` |
| `!resume` | Generates a resume writing tip |

### Q&A system

| Command | What it does |
|---|---|
| `!ask <question>` | Posts a question to the channel |
| `!solve <id>` | Marks a question as solved |
| `!code <language> <code>` | Shares code with proper formatting |
| `!questions` | Lists all open questions |
| `!helpers` | Shows the most helpful members |
| `!helpme` | Detailed guide to the Q&A system |

### AI tutor

| Command | What it does |
|---|---|
| `!hint <question>` | Gets a logic hint for a DSA problem, no solution spoilers |

You can also just chat naturally in the bot channel and it will respond.

### Admin only (requires server administrator role in Discord)

| Command | What it does |
|---|---|
| `!force_check` | Runs the daily LeetCode check immediately |
| `!force_placement` | Posts a placement tip to the placement channel immediately |
| `!backup` | Sends all data files as attachments in Discord |

---

## Admin panel

Access it at `your-url/admin` with the password you set in the environment variables.

| Page | What you can do |
|---|---|
| Dashboard | Overview of stats, quick action buttons, recent placement posts |
| Users | View all registered members, remove anyone |
| Reminders | Set reminders for any user by their Discord ID, cancel any reminder |
| Placement | Post AI tips, write and post custom tips, toggle auto-posting, view history |
| Settings | Change the daily check time, placement post time, toggle features, change password |

---

## AI model

The bot uses Google Gemini. The model is set in `ai_helper.py` on the `MODEL_NAME` line. Currently set to `gemini-2.5-flash` which has the best balance of quality and free tier quota (250 requests per day). If you hit rate limits, change it to `gemini-2.5-flash-lite` which allows 1000 requests per day.

Do not use `gemini-2.0-flash` — its free tier quota is effectively zero.

---

## Notes

- All data is stored as JSON files in the `data/` folder which is created automatically on first run. Back these up regularly using `!backup` in Discord or download them from the admin panel.
- The `data/` folder is in `.gitignore` so your user data never gets pushed to GitHub.
- The bot checks LeetCode stats at 9:30 PM IST and posts placement tips at 10:00 AM IST by default. Both times are configurable from the admin panel.

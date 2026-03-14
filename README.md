# 👻 Ghost Squad Bot v2

A Discord bot for placement & DSA accountability, with an AI placement feed and a clean web presence — all on a single Render deployment.

---

## 🌐 Two websites, one server

| URL | Who | What |
|---|---|---|
| `https://your-app.onrender.com/` | **Everyone** | Public leaderboard, stats, latest placement tips |
| `https://your-app.onrender.com/admin` | **Admin only** | Full control panel |

---

## 🚀 Deploy on Render

1. Push repo to GitHub
2. Render → New Web Service → connect repo (auto-detects `render.yaml`)
3. Set env vars in Render Dashboard → Environment:

| Variable | Value |
|---|---|
| `DISCORD_TOKEN` | Bot token |
| `DISCORD_CHANNEL_ID` | Main channel ID |
| `PLACEMENT_CHANNEL_ID` | Placement channel ID |
| `GOOGLE_API_KEY` | Gemini API key |
| `ADMIN_PASSWORD` | Admin password |

---

## 📋 Discord Commands

### LeetCode Tracking
`!register <user>` · `!unregister` · `!mystatus` · `!leaderboard` · `!progress` · `!stats`

### Placement & Internships
`!placement` · `!roadmap` · `!mock <role>` · `!resume`

### Q&A System
`!ask <q>` · `!solve <id>` · `!code <lang> <code>` · `!questions` · `!helpers`

### AI Tutor
`!hint <question>` or just chat naturally in the bot channel

> Reminders are managed from the **admin panel only** — no Discord commands.

---

## 🔒 Admin Panel (`/admin`)

Dashboard · Users · Reminders (view/add/cancel) · Placement Feed · Settings

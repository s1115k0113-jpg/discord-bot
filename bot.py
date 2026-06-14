import discord
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, timedelta

import os
TOKEN = os.getenv("TOKEN")

conn = sqlite3.connect("assignments.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    due_date TEXT NOT NULL,
    author TEXT NOT NULL,
    last_notified_date TEXT
)
""")

conn.commit()

CHANNEL_ID = 1515718663955677345

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

tree = bot.tree

@bot.event
async def on_ready():
    await tree.sync()
    check_deadlines.start()
    print(f"{bot.user} が起動しました")

@tree.command(name="add", description="課題を登録する")
async def add(interaction: discord.Interaction, title: str, due_date: str):

    cursor.execute(
        "INSERT INTO assignments (title, due_date, author) VALUES (?, ?, ?)",
        (title, due_date, str(interaction.user))
    )
    conn.commit()

    await interaction.response.send_message(
        f"課題を登録しました！\n{title}\n締切: {due_date}"
    )

@tree.command(name="list", description="課題一覧")
async def list_assignments(interaction: discord.Interaction):

    cursor.execute("SELECT id, title, due_date FROM assignments")
    rows = cursor.fetchall()

    if not rows:
        await interaction.response.send_message("課題はありません")
        return

    msg = "📚 課題一覧\n\n"

    for r in rows:
        msg += f"ID:{r[0]} | {r[1]} | {r[2]}\n"

    await interaction.response.send_message(msg)

@tree.command(name="delete", description="課題を削除")
async def delete(interaction: discord.Interaction, assignment_id: int):

    cursor.execute(
        "DELETE FROM assignments WHERE id = ?",
        (assignment_id,)
    )
    conn.commit()

    await interaction.response.send_message(
        f"ID {assignment_id} を削除しました"
    )

@tasks.loop(hours=0.25)
async def check_deadlines():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    cursor.execute("SELECT id, title, due_date, last_notified_date FROM assignments")
    rows = cursor.fetchall()

    channel = await bot.fetch_channel(CHANNEL_ID)
    if not channel:
        return

    for row in rows:
        assignment_id, title, due_date, last_notified = row

        try:
            due = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
        except:
            continue

        is_today = now.date() == due.date()
        is_tomorrow = (now.date() + timedelta(days=1)) == due.date()

        if not (is_today or is_tomorrow):
            continue


        if last_notified == today_str:
            continue

        if is_today:
            await channel.send(f"🚨 今日が締切！\n📘 {title}\n📅 {due_date}")
        else:
            await channel.send(f"⚠️ 明日締切！\n📘 {title}\n📅 {due_date}")

        cursor.execute(
            "UPDATE assignments SET last_notified_date = ? WHERE id = ?",
            (today_str, assignment_id)
        )
        conn.commit()

bot.run(TOKEN)
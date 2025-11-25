import os
import json
import discord
from discord.ext import commands
from discord.ui import View, Select

TOKEN = os.getenv("TOKEN")

DATA_FILE = "points.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

DATA = {"users": {}, "role_rewards": {}}

def load_data():
    global DATA
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                DATA = json.load(f)
        except:
            DATA = {"users": {}, "role_rewards": {}}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(DATA, f, indent=4)

load_data()

async def check_roles(member: discord.Member):
    points = DATA["users"].get(str(member.id), 0)
    for role_id, threshold in DATA["role_rewards"].items():
        if points >= threshold:
            role = member.guild.get_role(int(role_id))
            if role and role not in member.roles:
                try:
                    await member.add_roles(role)
                except:
                    pass

class AdminMenu(View):
    def __init__(self):
        super().__init__(timeout=None)
        select = Select(
            placeholder="Выберите действие",
            options=[
                discord.SelectOption(label="Начислить очки", value="add"),
                discord.SelectOption(label="Снять очки", value="remove"),
                discord.SelectOption(label="Установить награду", value="reward"),
                discord.SelectOption(label="Список наград", value="rewards"),
                discord.SelectOption(label="Таблица пользователей", value="top"),
            ]
        )
        select.callback = self.select_action
        self.add_item(select)

    async def select_action(self, interaction: discord.Interaction):
        action = interaction.data["values"][0]
        if action == "add":
            await interaction.response.send_message("Команда: `!add @user amount`", ephemeral=True)
        elif action == "remove":
            await interaction.response.send_message("Команда: `!remove @user amount`", ephemeral=True)
        elif action == "reward":
            await interaction.response.send_message("Команда: `!setreward @role amount`", ephemeral=True)
        elif action == "rewards":
            await interaction.response.send_message("Команда: `!rewards`", ephemeral=True)
        elif action == "top":
            await interaction.response.send_message("Команда: `!top`", ephemeral=True)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def menu(ctx):
    await ctx.send("🛠 Меню администратора:", view=AdminMenu())

@bot.command()
async def help(ctx):
    msg = (
        "🛠 **Команды бота:**\n\n"
        "!add @user <amount> — начислить очки\n"
        "!remove @user <amount> — снять очки\n"
        "!setreward @role <threshold> — установить награду\n"
        "!rewards — список наград\n"
        "!top [True] — таблица пользователей\n"
        "!menu — открыть админ-меню\n"
        "!help — список команд"
    )
    await ctx.send(msg)

@bot.command()
async def add(ctx, member: discord.Member, amount: int):
    uid = str(member.id)
    DATA["users"][uid] = DATA["users"].get(uid, 0) + amount
    save_data()
    await check_roles(member)
    await ctx.send(f"Добавлено {amount} очков пользователю {member.display_name}.")

@bot.command()
async def remove(ctx, member: discord.Member, amount: int):
    uid = str(member.id)
    DATA["users"][uid] = max(0, DATA["users"].get(uid, 0) - amount)
    save_data()
    await ctx.send(f"Снято {amount} очков у пользователя {member.display_name}.")

@bot.command()
async def setreward(ctx, role: discord.Role, threshold: int):
    DATA["role_rewards"][str(role.id)] = threshold
    save_data()
    await ctx.send(f"Роль {role.name} будет выдаваться при {threshold} очках.")

@bot.command()
async def rewards(ctx):
    if not DATA["role_rewards"]:
        return await ctx.send("Награды не настроены.")
    lines = ["🎯 **Список наград:**"]
    for rid, threshold in sorted(DATA["role_rewards"].items(), key=lambda x: x[1]):
        role = ctx.guild.get_role(int(rid))
        name = role.name if role else f"Роль {rid}"
        lines.append(f"• {name}: {threshold} очков")
    await ctx.send("\n".join(lines))

@bot.command()
async def top(ctx, send_dm: bool = False):
    if not DATA["users"]:
        return await ctx.send("Нет данных о пользователях.")
    sorted_users = sorted(DATA["users"].items(), key=lambda x: x[1], reverse=True)
    lines = ["📊 **Топ пользователей:**\n"]
    for uid, points in sorted_users:
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"Пользователь {uid}"
        lines.append(f"• {name}: {points} очков")
    text = "\n".join(lines)
    if send_dm:
        await ctx.author.send(text)
    else:
        await ctx.send(text)

bot.run(TOKEN)



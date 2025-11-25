import os
import json
import nextcord
from nextcord.ext import commands
from nextcord.ui import View, Select

TOKEN = os.getenv("TOKEN")

DATA_FILE = "points.json"
DATA = {"users": {}, "role_rewards": {}}

# ---------------------- ЗАГРУЗКА / СОХРАНЕНИЕ ----------------------

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

# ---------------------- НАСТРОЙКА БОТА ----------------------

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

async def check_roles(member: nextcord.Member):
    points = DATA["users"].get(str(member.id), 0)
    for role_id, threshold in DATA["role_rewards"].items():
        if points >= threshold:
            role = member.guild.get_role(int(role_id))
            if role and role not in member.roles:
                try:
                    await member.add_roles(role)
                except:
                    pass

# ---------------------- МЕНЮ АДМИНА ----------------------

class AdminMenu(View):
    def __init__(self):
        super().__init__(timeout=None)
        select = Select(
            placeholder="Выберите действие",
            options=[
                nextcord.SelectOption(label="Начислить очки", value="add"),
                nextcord.SelectOption(label="Снять очки", value="remove"),
                nextcord.SelectOption(label="Установить награду", value="reward"),
                nextcord.SelectOption(label="Список наград", value="rewards"),
                nextcord.SelectOption(label="Топ пользователей", value="top"),
            ]
        )
        select.callback = self.select_action
        self.add_item(select)

    async def select_action(self, interaction: nextcord.Interaction):
        action = interaction.data["values"][0]
        commands_info = {
            "add": "!add @user amount",
            "remove": "!remove @user amount",
            "reward": "!setreward @role amount",
            "rewards": "!rewards",
            "top": "!top"
        }
        await interaction.response.send_message(f"Команда: `{commands_info[action]}`", ephemeral=True)

# ---------------------- КОМАНДЫ ----------------------

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
        "!top — таблица пользователей\n"
        "!menu — открыть админ-меню\n"
        "!help — список команд"
    )
    await ctx.send(msg)

@bot.command()
async def add(ctx, member: nextcord.Member, amount: int):
    uid = str(member.id)
    DATA["users"][uid] = DATA["users"].get(uid, 0) + amount
    save_data()
    await check_roles(member)
    await ctx.send(f"Добавлено {amount} очков пользователю {member.display_name}.")

@bot.command()
async def remove(ctx, member: nextcord.Member, amount: int):
    uid = str(member.id)
    DATA["users"][uid] = max(0, DATA["users"].get(uid, 0) - amount)
    save_data()
    await ctx.send(f"Снято {amount} очков у пользователя {member.display_name}.")

@bot.command()
async def setreward(ctx, role: nextcord.Role, threshold: int):
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
async def top(ctx):
    if not DATA["users"]:
        return await ctx.send("Нет данных о пользователях.")
    sorted_users = sorted(DATA["users"].items(), key=lambda x: x[1], reverse=True)
    lines = ["📊 **Топ пользователей:**\n"]
    for uid, points in sorted_users:
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"Пользователь {uid}"
        lines.append(f"• {name}: {points} очков")
    await ctx.send("\n".join(lines))


# ---------------------- СТАРТ ----------------------

bot.run(TOKEN)


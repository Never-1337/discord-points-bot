#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord Giveaway Bot with Prefix Commands Only
"""

import os
import json
import time
import uuid
import random
import asyncio
from typing import Dict, List

import discord
# --- Create persistent data directory on Render ---
DATA_DIR = "/opt/render/project/data"
os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, "giveaways.json")
POINTS_FILE = os.path.join(DATA_DIR, "points.json")

# Create files if missing
def ensure_file(path, default_data):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)

ensure_file(DATA_FILE, {})
ensure_file(POINTS_FILE, {})

# Configuration
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("❌ ERROR: Please set TOKEN environment variable")
    print("💡 Command: export TOKEN=your_bot_token_here")
    exit(1)

# Data storage
DATA_FILE = "giveaways.json"
POINTS_FILE = "points.json"
giveaways = {}


# Load data
def load_data():
    global giveaways
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                giveaways = json.load(f)
        else:
            giveaways = {}
    except Exception as e:
        print(f"Error loading data: {e}")
        giveaways = {}


# Save data
def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(giveaways, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")


# Load points data
def load_points():
    try:
        if os.path.exists(POINTS_FILE):
            with open(POINTS_FILE, "r") as f:
                return json.load(f)
        else:
            return {"users": {}, "role_rewards": {}}
    except Exception as e:
        print(f"Error loading points: {e}")
        return {"users": {}, "role_rewards": {}}


# Save points data
def save_points(points_data):
    try:
        with open(POINTS_FILE, "w") as f:
            json.dump(points_data, f, indent=2)
    except Exception as e:
        print(f"Error saving points: {e}")


# Check and update roles based on points
async def update_user_roles(member: discord.Member, new_points: int):
    """Обновить роли пользователя в зависимости от количества артефактов"""
    points_data = load_points()
    role_rewards = points_data.get("role_rewards", {})

    if not role_rewards:
        return

    # Получаем все роли, которые можно выдать
    roles_to_add = []
    for role_id, threshold in role_rewards.items():
        if new_points >= threshold:
            role = member.guild.get_role(int(role_id))
            if role and role not in member.roles:
                roles_to_add.append(role)

    # Выдаем роли
    if roles_to_add:
        try:
            await member.add_roles(
                *roles_to_add,
                reason="Автоматическая выдача ролей за артефакты")
            print(
                f"✅ Выданы роли {[r.name for r in roles_to_add]} пользователю {member.display_name}"
            )
        except Exception as e:
            print(f"❌ Ошибка выдачи ролей: {e}")


# Duration parsing
def parse_duration(duration: str) -> int:
    units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'sec': 1,
        'min': 60,
        'hour': 3600,
        'day': 86400
    }

    duration = duration.lower().strip()
    number = ''
    unit = ''

    for char in duration:
        if char.isdigit():
            number += char
        else:
            unit += char

    if not number or not unit:
        raise ValueError("Invalid duration format")

    number = int(number)
    unit = unit.strip()

    if unit not in units:
        raise ValueError(f"Unknown time unit: {unit}")

    return number * units[unit]


def format_time(seconds: int) -> str:
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]

    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value = seconds // period_seconds
            seconds -= period_value * period_seconds
            result.append(f"{period_value}{period_name}")

    return ' '.join(result) if result else '0s'


# ---------------- Stalker Phrases ----------------
PHRASES_LIGHT = [
    "Говорят, сталкеры нашли странный тайник. Решили не делить — пусть Зона сама выберет победителя. Розыгрыш начался!",
    "На кордоне нашли забытый рюкзак. Внутри что-то ценное… Кто заберёт — решит удача. Время пошло!",
    "С утра мимо пробегал сталкер и обронил что-то увесистое. Раз уж он не вернулся — разыграем среди своих.",
    "Сталкеры передали нам хабар «на честное слово». Ну… посмотрим, кому он достанется.",
    "По Зоне гуляет слух про новую добычу. Решили проверить — запускаем розыгрыш среди своих."
]

PHRASES_MEDIUM = [
    "Бандосы пытались провести свой груз через Зону, но не дошли. Мы забрали трофеи — теперь решим, кому выпадет удача.",
    "Наёмники что-то дорогое уронили во время перестрелки. Мы нашли первыми. Ждите розыгрыша.",
    "Шмонаем заброшенный лагерь — находим хабар. Чтобы не ругаться, запускаем розыгрыш по всем правилам.",
    "Склад долговцев слегка… опустел. Трофей у нас, но кому достанется — решит удача.",
    "Кто-то решил спрятать добычу в аномалии. Мы вытащили. Теперь посмотрим, кому улыбнётся Зона."
]

PHRASES_HARD = [
    "После короткого, но громкого базара пару типов исчезли, а habar остался. Решили не делить — устраиваем розыгрыш.",
    "Группа, что пыталась вынести трофеи с Янтаря, пропала в тумане. Мы нашли только груз. Заберёт его самый везучий…",
    "Вытащили из под обвала контейнер, за который люди друг друга глотки рвали. Теперь решит судьба, кому он достанется.",
    "Кто-то хотел провести через Зоны контрабандный habar. Хотел… А вот приз уже у нас. Запускаем розыгрыш.",
    "После ночи на свалке остались только следы волочения и ящик с ценной шмоткой. Заберёт его тот, кого выберет Зона."
]

WINNER_PHRASES = [
    "Неплохой хабар, {mention}. Видно, Зона сегодня к тебе благосклонна.",
    "Ну ты везучий, {mention}. С таким фартом тебе бы на большой рейд идти.",
    "Зона выбрала тебя, {mention}. Забирай своё, пока никто не передумал.",
    "Ну что, {mention}, видно, масть сегодня лёгла к тебе. Забирай своё — по понятиям положено.",
    "{mention}, сегодня удача шла рядом с тобой. Держи свой трофей, заслужил."
]


def pick_flavor() -> str:
    pool = PHRASES_LIGHT + PHRASES_MEDIUM + PHRASES_HARD
    return random.choice(pool)


# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Добавляем для работы с ролями
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


# Giveaway View
class GiveawayView(View):

    def __init__(self, giveaway_id: str):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

        self.join_btn = Button(label="Участвовать",
                               style=discord.ButtonStyle.primary,
                               custom_id=f"join_{giveaway_id}")
        self.list_btn = Button(label="📜 Участники",
                               style=discord.ButtonStyle.secondary,
                               custom_id=f"list_{giveaway_id}")
        self.luck_btn = Button(label="🎯 Моя удача",
                               style=discord.ButtonStyle.success,
                               custom_id=f"luck_{giveaway_id}")

        self.join_btn.callback = self.join_action
        self.list_btn.callback = self.list_action
        self.luck_btn.callback = self.luck_action

        self.add_item(self.join_btn)
        self.add_item(self.list_btn)
        self.add_item(self.luck_btn)

    async def join_action(self, interaction: discord.Interaction):
        if interaction.user.bot:
            return

        giveaway_id = self.giveaway_id
        user_id = str(interaction.user.id)

        if giveaway_id not in giveaways:
            await interaction.response.send_message("❌ Розыгрыш не найден",
                                                    ephemeral=True)
            return

        giveaway = giveaways[giveaway_id]

        if giveaway.get('ended'):
            await interaction.response.send_message("❌ Розыгрыш завершен",
                                                    ephemeral=True)
            return

        participants = giveaway.get('participants', [])

        if user_id in participants:
            participants.remove(user_id)
            message = "✅ Вы вышли из розыгрыша"
        else:
            participants.append(user_id)
            message = "✅ Вы вступили в розыгрыш"

        giveaway['participants'] = participants
        save_data()

        await interaction.response.send_message(message, ephemeral=True)
        await self.update_giveaway_message(giveaway_id)

    async def list_action(self, interaction: discord.Interaction):
        giveaway_id = self.giveaway_id

        if giveaway_id not in giveaways:
            await interaction.response.send_message("❌ Розыгрыш не найден",
                                                    ephemeral=True)
            return

        giveaway = giveaways[giveaway_id]
        participants = giveaway.get('participants', [])

        if not participants:
            await interaction.response.send_message(
                "👥 Пока никто не участвует", ephemeral=True)
            return

        participant_list = "\n".join(
            [f"<@{uid}>" for uid in participants[:20]])
        if len(participants) > 20:
            participant_list += f"\n... и еще {len(participants) - 20} участников"

        await interaction.response.send_message(
            f"👥 Участников: {len(participants)}\n{participant_list}",
            ephemeral=True)

    async def luck_action(self, interaction: discord.Interaction):
        giveaway_id = self.giveaway_id

        if giveaway_id not in giveaways:
            await interaction.response.send_message("❌ Розыгрыш не найден",
                                                    ephemeral=True)
            return

        giveaway = giveaways[giveaway_id]

        if giveaway.get('ended'):
            await interaction.response.send_message("❌ Розыгрыш завершен",
                                                    ephemeral=True)
            return

        user_id = str(interaction.user.id)
        participants = giveaway.get('participants', [])
        winners_count = giveaway.get('winners', 1)
        end_time = giveaway.get('end_time', 0)

        is_participating = user_id in participants
        total_participants = len(participants)

        if total_participants == 0:
            chance = 0
            chance_text = "0%"
        else:
            chance = (winners_count / total_participants) * 100
            chance_text = f"{chance:.1f}%"

        remaining = max(0, end_time - int(time.time()))
        time_left = format_time(remaining)

        response = (
            f"🎯 **Ваш шанс:** {chance_text}\n"
            f"✅ **Участвуете:** {'Да' if is_participating else 'Нет'}\n"
            f"👥 **Участников:** {total_participants}\n"
            f"🏆 **Победителей:** {winners_count}\n"
            f"⏰ **Осталось:** {time_left}")

        await interaction.response.send_message(response, ephemeral=True)

    async def update_giveaway_message(self, giveaway_id: str):
        if giveaway_id not in giveaways:
            return

        giveaway = giveaways[giveaway_id]
        channel_id = giveaway.get('channel_id')
        message_id = giveaway.get('message_id')

        if not channel_id or not message_id:
            return

        try:
            channel = bot.get_channel(channel_id)
            if not channel:
                return

            message = await channel.fetch_message(message_id)
            remaining = max(0, giveaway['end_time'] - int(time.time()))

            embed = discord.Embed(title="🎉 РОЗЫГРЫШ В ЗОНЕ",
                                  description=giveaway.get('flavor', ''),
                                  color=0x2b5329)

            embed.add_field(name="🏆 Трофей",
                            value=giveaway['prize'],
                            inline=False)
            embed.add_field(name="⏰ Осталось в Зоне",
                            value=format_time(remaining),
                            inline=True)
            embed.add_field(name="👥 Сталкеров",
                            value=str(len(giveaway.get('participants', []))),
                            inline=True)
            embed.add_field(name="🏆 Счастливчиков",
                            value=str(giveaway['winners']),
                            inline=True)
            embed.set_footer(
                text=
                f"ID: {giveaway_id} • Нашел: {giveaway.get('host_name', 'Неизвестный сталкер')}"
            )

            await message.edit(embed=embed, view=GiveawayView(giveaway_id))

        except Exception as e:
            print(f"Error updating message: {e}")


# Giveaway management
async def giveaway_timer(giveaway_id: str):
    while True:
        if giveaway_id not in giveaways:
            break

        giveaway = giveaways[giveaway_id]

        if giveaway.get('ended'):
            break

        remaining = giveaway['end_time'] - time.time()

        if remaining <= 0:
            await end_giveaway(giveaway_id)
            break

        await asyncio.sleep(min(30, remaining))

    print(f"Timer ended for giveaway {giveaway_id}")


async def end_giveaway(giveaway_id: str):
    if giveaway_id not in giveaways:
        return

    giveaway = giveaways[giveaway_id]

    if giveaway.get('ended'):
        return

    giveaway['ended'] = True
    participants = giveaway.get('participants', [])
    winners_count = giveaway['winners']

    # Select winners
    winners = []
    if participants:
        if len(participants) <= winners_count:
            winners = participants
        else:
            winners = random.sample(participants, winners_count)

    # Update message
    await update_ended_message(giveaway_id, winners)

    # Announce winners
    await announce_winners(giveaway_id, winners)

    save_data()
    print(f"Giveaway {giveaway_id} ended with {len(winners)} winners")


async def update_ended_message(giveaway_id: str, winners: List[str]):
    if giveaway_id not in giveaways:
        return

    giveaway = giveaways[giveaway_id]
    channel_id = giveaway.get('channel_id')
    message_id = giveaway.get('message_id')

    if not channel_id or not message_id:
        return

    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            return

        message = await channel.fetch_message(message_id)

        embed = discord.Embed(title="🎉 РОЗЫГРЫШ В ЗОНЕ ЗАВЕРШЕН",
                              description=giveaway.get('flavor', ''),
                              color=0x8B0000)

        embed.add_field(name="🏆 Трофей", value=giveaway['prize'], inline=False)

        if winners:
            winner_mentions = ", ".join([f"<@{uid}>" for uid in winners])
            embed.add_field(name="🏆 Счастливчики",
                            value=winner_mentions,
                            inline=False)
        else:
            embed.add_field(name="🏆 Счастливчики",
                            value="❌ Никто не рискнул",
                            inline=False)

        embed.add_field(name="👥 Сталкеров",
                        value=str(len(giveaway.get('participants', []))),
                        inline=True)
        embed.set_footer(text=f"ID: {giveaway_id} • Зона выбрала")

        await message.edit(embed=embed, view=None)

    except Exception as e:
        print(f"Error updating ended message: {e}")


async def announce_winners(giveaway_id: str, winners: List[str]):
    if giveaway_id not in giveaways:
        return

    giveaway = giveaways[giveaway_id]
    channel_id = giveaway.get('channel_id')

    if not channel_id or not winners:
        return

    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            return

        winner_mentions = ", ".join([f"<@{uid}>" for uid in winners])
        phrase = random.choice(WINNER_PHRASES).format(mention=winner_mentions)

        embed = discord.Embed(
            description=f"🎉 {phrase}\n**Трофей:** {giveaway['prize']}",
            color=0x00ff00)

        await channel.send(embed=embed)

    except Exception as e:
        print(f"Error announcing winners: {e}")


# Points system commands
@bot.command()
async def add(ctx, member: discord.Member, amount: int):
    """Добавить очки пользователю"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ Недостаточно прав, сталкер")
        return

    if amount <= 0:
        await ctx.send("❌ Количество должно быть положительным")
        return

    user_id = str(member.id)
    points_data = load_points()

    points_data.setdefault("users", {})
    points_data["users"][user_id] = points_data["users"].get(user_id,
                                                             0) + amount

    # Сохраняем и обновляем роли
    save_points(points_data)
    await update_user_roles(member, points_data["users"][user_id])

    await ctx.send(f"✅ Добавлено {amount} артефактов сталкеру {member.mention}"
                   )


@bot.command()
async def remove(ctx, member: discord.Member, amount: int):
    """Убрать очки у пользователя"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ Недостаточно прав, сталкер")
        return

    if amount <= 0:
        await ctx.send("❌ Количество должно быть положительным")
        return

    user_id = str(member.id)
    points_data = load_points()

    points_data.setdefault("users", {})
    current = points_data["users"].get(user_id, 0)
    new_points = max(0, current - amount)
    points_data["users"][user_id] = new_points

    # Сохраняем и обновляем роли
    save_points(points_data)
    await update_user_roles(member, new_points)

    await ctx.send(f"✅ Изъято {amount} артефактов у сталкера {member.mention}")


@bot.command()
async def setreward(ctx, role: discord.Role, threshold: int):
    """Установить награду за роль"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ Недостаточно прав, сталкер")
        return

    if threshold <= 0:
        await ctx.send("❌ Порог должен быть положительным")
        return

    points_data = load_points()
    points_data.setdefault("role_rewards", {})
    points_data["role_rewards"][str(role.id)] = threshold

    save_points(points_data)

    await ctx.send(
        f"✅ Роль {role.mention} будет выдаваться при {threshold} артефактах")


@bot.command()
async def rewards(ctx):
    """Показать список наград"""
    points_data = load_points()
    rewards_data = points_data.get("role_rewards", {})

    if not rewards_data:
        await ctx.send("❌ Награды не настроены")
        return

    embed = discord.Embed(title="🎯 Награды в Зоне", color=0x2b5329)

    for role_id, threshold in sorted(rewards_data.items(), key=lambda x: x[1]):
        role = ctx.guild.get_role(int(role_id))
        role_name = role.name if role else f"Роль {role_id}"
        embed.add_field(name=role_name,
                        value=f"{threshold} артефактов",
                        inline=True)

    await ctx.send(embed=embed)


@bot.command()
async def top(ctx):
    """Показать топ пользователей по очкам"""
    points_data = load_points()
    users_data = points_data.get("users", {})

    if not users_data:
        await ctx.send("❌ Нет данных об артефактах")
        return

    # Сортируем по убыванию очков
    sorted_users = sorted(users_data.items(), key=lambda x: x[1],
                          reverse=True)[:10]

    embed = discord.Embed(title="🏆 Топ сталкеров", color=0xffd700)

    for i, (user_id, points) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(int(user_id))
        name = member.display_name if member else f"Сталкер {user_id}"
        embed.add_field(name=f"{i}. {name}",
                        value=f"{points} артефактов",
                        inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def checkroles(ctx):
    """Проверить и обновить роли всех пользователей"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ Недостаточно прав, сталкер")
        return

    points_data = load_points()
    users_data = points_data.get("users", {})

    updated_count = 0
    for user_id, points in users_data.items():
        member = ctx.guild.get_member(int(user_id))
        if member:
            await update_user_roles(member, points)
            updated_count += 1

    await ctx.send(f"✅ Обновлены роли для {updated_count} сталкеров")


# Giveaway commands with prefix
@bot.command()
async def giveaway(ctx, duration: str, winners: int, *, prize: str):
    """Создать розыгрыш: !giveaway 1h 1 Приз"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ Недостаточно прав, сталкер")
        return

    try:
        seconds = parse_duration(duration)
    except ValueError as e:
        await ctx.send(f"❌ Неверная длительность: {e}")
        return

    if winners < 1:
        await ctx.send("❌ Должен быть хотя бы 1 счастливчик")
        return

    if len(prize.strip()) < 2:
        await ctx.send("❌ Трофей слишком скромный")
        return

    giveaway_id = str(uuid.uuid4())[:8]
    end_time = int(time.time()) + seconds
    flavor = pick_flavor()

    giveaway_data = {
        'id': giveaway_id,
        'channel_id': ctx.channel.id,
        'creator_id': str(ctx.author.id),
        'prize': prize,
        'winners': winners,
        'participants': [],
        'end_time': end_time,
        'ended': False,
        'flavor': flavor,
        'host_name': ctx.author.display_name
    }

    # Create embed
    embed = discord.Embed(title="🎉 НАЙДЕН ХАБАР В ЗОНЕ",
                          description=flavor,
                          color=0x2b5329)

    embed.add_field(name="🏆 Трофей", value=prize, inline=False)
    embed.add_field(name="⏰ Время до изъятия",
                    value=format_time(seconds),
                    inline=True)
    embed.add_field(name="👥 Сталкеров", value="0", inline=True)
    embed.add_field(name="🏆 Счастливчиков", value=str(winners), inline=True)
    embed.set_footer(
        text=f"ID: {giveaway_id} • Нашел: {ctx.author.display_name}")

    view = GiveawayView(giveaway_id)

    # Send message
    message = await ctx.send(embed=embed, view=view)

    # Save data
    giveaway_data['message_id'] = message.id
    giveaways[giveaway_id] = giveaway_data
    save_data()

    # Register view and start timer
    bot.add_view(GiveawayView(giveaway_id), message_id=message.id)
    asyncio.create_task(giveaway_timer(giveaway_id))

    # Delete command message
    try:
        await ctx.message.delete()
    except:
        pass


@bot.command()
async def gdelete(ctx, giveaway_id: str):
    """Удалить розыгрыш: !gdelete <id>"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ Недостаточно прав, сталкер")
        return

    if giveaway_id not in giveaways:
        await ctx.send("❌ Розыгрыш не найден")
        return

    giveaway = giveaways[giveaway_id]

    # Try to delete message
    try:
        channel = bot.get_channel(giveaway['channel_id'])
        if channel:
            message = await channel.fetch_message(giveaway['message_id'])
            await message.delete()
    except:
        pass

    # Remove from data
    del giveaways[giveaway_id]
    save_data()

    await ctx.send(f"✅ Хабар `{giveaway_id}` изъят Долгом")

    # Delete command message
    try:
        await ctx.message.delete()
    except:
        pass


@bot.command()
async def greroll(ctx, giveaway_id: str):
    """Перерозыгрыш: !greroll <id>"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ Недостаточно прав, сталкер")
        return

    if giveaway_id not in giveaways:
        await ctx.send("❌ Розыгрыш не найден")
        return

    giveaway = giveaways[giveaway_id]

    if not giveaway.get('ended'):
        await ctx.send("❌ Хабар еще не поделен")
        return

    participants = giveaway.get('participants', [])
    winners_count = giveaway['winners']

    # Select new winners
    winners = []
    if participants:
        if len(participants) <= winners_count:
            winners = participants
        else:
            winners = random.sample(participants, winners_count)

    # Announce new winners
    if winners:
        winner_mentions = ", ".join([f"<@{uid}>" for uid in winners])
        phrase = random.choice(WINNER_PHRASES).format(mention=winner_mentions)
        embed = discord.Embed(
            description=f"🎉 {phrase}\n**Трофей:** {giveaway['prize']}",
            color=0x00ff00)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Не нашлось смельчаков для передела")

    # Delete command message
    try:
        await ctx.message.delete()
    except:
        pass


# Help command
@bot.command()
async def help(ctx):
    """Показать справку по командам"""
    embed = discord.Embed(title="📋 Команды сталкера", color=0x2b5329)

    embed.add_field(
        name="🎉 Команды хабара",
        value=("`!giveaway длительность победители трофей` - Найти хабар\n"
               "`!gdelete id_розыгрыша` - Изъять хабар\n"
               "`!greroll id_розыгрыша` - Передел хабара\n"
               "*(требуются права на управление сообщениями)*"),
        inline=False)

    embed.add_field(
        name="📊 Команды артефактов",
        value=("`!add @user количество` - Выдать артефакты\n"
               "`!remove @user количество` - Изъять артефакты\n"
               "`!setreward @role количество` - Установить награду\n"
               "`!rewards` - Список наград\n"
               "`!top` - Топ сталкеров\n"
               "`!checkroles` - Обновить роли всех сталкеров\n"
               "*(требуются права на управление сообщениями)*"),
        inline=False)

    await ctx.send(embed=embed)


# Bot events
@bot.event
async def on_ready():
    print(f"✅ Бот запущен как {bot.user.name}")

    # Load data
    load_data()

    # Restore active giveaways
    active_count = 0
    current_time = time.time()

    for giveaway_id, giveaway in giveaways.items():
        if not giveaway.get('ended'):
            # Register view
            try:
                bot.add_view(GiveawayView(giveaway_id),
                             message_id=giveaway['message_id'])
            except:
                pass

            # Check if ended
            if giveaway['end_time'] <= current_time:
                asyncio.create_task(end_giveaway(giveaway_id))
            else:
                asyncio.create_task(giveaway_timer(giveaway_id))
                active_count += 1

    print(f"🎯 Восстановлено активных хабаров: {active_count}")


# Run bot
if __name__ == "__main__":
    print("🚀 Запуск бота...")
    print("💡 Убедитесь, что переменная TOKEN установлена!")
    bot.run(TOKEN)




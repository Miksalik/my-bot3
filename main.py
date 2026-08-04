import discord
import os
from discord.ext import commands, tasks
from datetime import datetime, timezone

intents = discord.Intents.default()
intents.members = True
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# НАСТРОЙКА: Вставьте ID вашего текстового канала для уведомлений
LOG_CHANNEL_ID = 1534155761608032336  

# Конфигурация ролей: от самых больших сроков к самым меньшим
ROLES_CONFIG = {
    3650: "10 лет на сервере",          # Ярко-фиолетовый
    3285: "9 лет на сервере",           # Ярко-фиолетовый
    2920: "8 лет на сервере",           # Ярко-фиолетовый
    2555: "7 лет на сервере",           # Золотой
    2190: "6 лет на сервере",           # Золотой
    1825: "5 лет на сервере",           # Золотой
    1460: "4 года на сервере",          # Красный
    1095: "3 года на сервере",          # Красный
    730: "2 года на сервере",           # Оранжевый
    365: "Год на сервере",              # Оранжевый
    180: "Больше 6 месяцев на сервере", # Зеленый
    150: "6 месяцев на сервере",        # Зеленый
    60: "Больше месяца на сервере",     # Синий
    30: "Месяц на сервере",             # Синий
    21: "3 недели на сервере",          # Серый
    14: "2 недели на сервере",          # Серый
    7: "Неделя на сервере"              # Серый
}

# Список всех названий временных ролей, чтобы бот знал, какие именно роли нужно заменять
ALL_TIME_ROLE_NAMES = set(ROLES_CONFIG.values())

# Функция для подбора цвета Embed-сообщения
def get_embed_color(role_name: str) -> int:
    if "лет" in role_name and any(x in role_name for x in ["8", "9", "10"]):
        return 0xca00ff  # Ярко-фиолетовый
    if "лет" in role_name and any(x in role_name for x in ["5", "6", "7"]):
        return 0xe4ae39  # Золотой
    if "года" in role_name or "Год" in role_name:
        return 0xeb4b4b if "3" in role_name or "4" in role_name else 0xff8c00 
    if "месяц" in role_name or "месяцев" in role_name:
        return 0x50c878 if "6" in role_name else 0x5e98d9 
    return 0xb0c3d9  # Серый

async def process_roles_updating(guild: discord.Guild):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    
    for member in guild.members:
        if member.bot:
            continue

        now = datetime.now(timezone.utc)
        if not member.joined_at:
            continue
            
        days_on_server = (now - member.joined_at).days

        # Вычисляем ОДНУ самую высокую роль, которая должна быть у человека по его стажу
        target_role_name = None
        for days_required, role_name in ROLES_CONFIG.items():
            if days_on_server >= days_required:
                target_role_name = role_name
                break 

        if target_role_name:
            target_role = discord.utils.get(guild.roles, name=target_role_name)
            
            # Если нужная роль есть на сервере, но у человека в профиле её ЕЩЕ НЕТ
            if target_role and target_role not in member.roles:
                try:
                    # 1. Находим, какие СТАРЫЕ роли времени сейчас висят на человеке
                    old_time_roles = [r for r in member.roles if r.name in ALL_TIME_ROLE_NAMES and r.name != target_role_name]
                    
                    # 2. Если у него есть старые роли времени, СНИМАЕМ их с профиля
                    if old_time_roles:
                        await member.remove_roles(*old_time_roles)
                    
                    # 3. ВЫДАЕМ новую актуальную роль времени
                    await member.add_roles(target_role)
                    print(f"[ПОВЫШЕНИЕ] Участник {member.name} переведен на роль: {target_role_name}")
                    
                    # 4. Отправляем красивое сообщение в текстовый лог-канал
                    if channel:
                        embed = discord.Embed(
                            title="🎉 Обновление статуса времени!",
                            description=f"Участник {member.mention} перешел на новый этап!",
                            color=get_embed_color(target_role_name),
                            timestamp=datetime.now()
                        )
                        embed.add_field(name="Новая роль в профиле", value=f"**{target_role_name}**", inline=True)
                        embed.add_field(name="Всего дней на сервере", value=f"📜 {days_on_server} дней", inline=True)
                        embed.set_thumbnail(url=member.display_avatar.url)
                        embed.set_footer(text=f"ID: {member.id}")
                        await channel.send(embed=embed)
                        
                except discord.Forbidden:
                    print(f"[ОШИБКА] Не удалось обновить роли для {member.name}. Убедитесь, что роль бота находится ВЫШЕ ролей времени в настройках сервера!")

@bot.event
async def on_ready():
    print(f"Бот {bot.user.name} успешно запущен! Система автозамены ролей в профилях активна.")
    check_server_roles.start()

# Автоматическая проверка всех участников каждые 30 минут
@tasks.loop(minutes=30)
async def check_server_roles():
    for guild in bot.guilds:
        await process_roles_updating(guild)

# Ручная команда для админа, чтобы мгновенно обновить роли всем прямо сейчас
@bot.command(name="sync_roles")
@commands.has_permissions(administrator=True) 
async def sync_roles(ctx):
    await ctx.send("🔄 Запущена ручная замена устаревших ролей у участников. Пожалуйста, подождите...")
    await process_roles_updating(ctx.guild)
    await ctx.send("✅ Проверка завершена! У всех участников теперь только актуальные роли времени.")

@sync_roles.error
async def sync_roles_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас нет прав Администратора для использования этой команды.")
# Проверьте, что выше нет лишних пустых отступов перед декораторами

# Безопасный запуск через переменные окружения Bothost
token = os.getenv("BOT_TOKEN")

if token:
    bot.run(token)
else:
    print("Ошибка: Переменная BOT_TOKEN не настроена в панели Bothost!")

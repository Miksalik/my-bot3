import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
import os

intents = discord.Intents.all()
intents.members = True
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# НАСТРОЙКА: Вставьте сюда ID вашего текстового канала для уведомлений
LOG_CHANNEL_ID = 123456789012345678  

# Полная конфигурация: Дни на сервере -> (Название роли, HEX-цвет)
ROLES_CONFIG = {
    3650: ("10 лет на сервере", 0xca00ff),          # Ярко-фиолетовый
    3285: ("9 лет на сервере", 0xca00ff),           # Ярко-фиолетовый
    2920: ("8 лет на сервере", 0xca00ff),           # Ярко-фиолетовый
    2555: ("7 лет на сервере", 0xe4ae39),           # Золотой
    2190: ("6 лет на сервере", 0xe4ae39),           # Золотой
    1825: ("5 лет на сервере", 0xe4ae39),           # Золотой
    1460: ("4 года на сервере", 0xeb4b4b),          # Красный
    1095: ("3 года на сервере", 0xeb4b4b),          # Красный
    730: ("2 года на сервере", 0xff8c00),           # Оранжевый
    365: ("Год на сервере", 0xff8c00),              # Оранжевый
    180: ("Больше 6 месяцев на сервере", 0x50c878), # Зеленый
    150: ("6 месяцев на сервере", 0x50c878),        # Зеленый
    60: ("Больше месяца на сервере", 0x5e98d9),     # Синий
    30: ("Месяц на сервере", 0x5e98d9),             # Синий
    21: ("3 недели на сервере", 0xb0c3d9),          # Серый
    14: ("2 недели на сервере", 0xb0c3d9),          # Серый
    7: ("Неделя на сервере", 0xb0c3d9)              # Серый
}

# ИСПРАВЛЕНО: Теперь здесь собираются ТОЛЬКО чистые текстовые названия ролей
ALL_TIME_ROLE_NAMES = set(role_data[0] for role_data in ROLES_CONFIG.values())

# Функция, которая САМА создаёт роль на сервере, если её там нет
async def get_or_create_role(guild: discord.Guild, role_name: str, color_hex: int) -> discord.Role:
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        try:
            # Создаём роль с параметром hoist=True (выделение в списке справа)
            role = await guild.create_role(
                name=role_name, 
                color=discord.Color(color_hex),
                hoist=True,  
                reason="Автоматическое создание сетки ролей времени"
            )
            print(f"[СЕРВЕР] Бот успешно создал роль: {role_name}")
        except discord.Forbidden:
            print(f"[ОШИБКА ПРАВ] У бота нет прав на управление ролями для создания {role_name}!")
    return role

async def process_roles_updating(guild: discord.Guild):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    members_count = 0
    
    async for member in guild.fetch_members(limit=None):
        if member.bot:
            continue
            
        members_count += 1
        now = datetime.now(timezone.utc)
        if not member.joined_at:
            continue
            
        days_on_server = (now - member.joined_at).days

        target_role_name = None
        target_color = None
        
        # Определяем нужную роль
        for days_required, (role_name, color_hex) in ROLES_CONFIG.items():
            if days_on_server >= days_required:
                target_role_name = role_name
                target_color = color_hex
                break 

        if target_role_name:
            # Бот проверяет / создаёт нужную роль на сервере
            target_role = await get_or_create_role(guild, target_role_name, target_color)
            
            if target_role and target_role not in member.roles:
                try:
                    # Находим и удаляем старые временные роли из профиля участника
                    old_time_roles = [r for r in member.roles if r.name in ALL_TIME_ROLE_NAMES and r.name != target_role_name]
                    
                    if old_time_roles:
                        await member.remove_roles(*old_time_roles)
                    
                    # Выдаем новую актуальную роль времени
                    await member.add_roles(target_role)
                    print(f"[ВЫДАЧА] Успешно выдана роль {target_role_name} для {member.name}")
                    
                    if channel:
                        embed = discord.Embed(
                            title="🎉 Обновление статуса времени!",
                            description=f"Участник {member.mention} получил новый ранг!",
                            color=discord.Color(target_color),
                            timestamp=datetime.now()
                        )
                        embed.add_field(name="Роль в профиле", value=f"**{target_role_name}**", inline=True)
                        embed.add_field(name="Стаж на сервере", value=f"📜 {days_on_server} дней", inline=True)
                        embed.set_thumbnail(url=member.display_avatar.url)
                        embed.set_footer(text=f"ID: {member.id}")
                        await channel.send(embed=embed)
                        
                except discord.Forbidden:
                    print(f"[КРИТИЧЕСКАЯ ОШИБКА] Перетащите роль бота Wild Time на самый верх списка ролей в Discord!")
                    
    print(f"[ЛОГ] Проверка завершена. Обработано участников: {members_count}")

@bot.event
async def on_ready():
    print(f"Бот {bot.user.name} успешно запущен! Система автосоздания и выдачи активна.")
    check_server_roles.start()

@tasks.loop(minutes=30)
async def check_server_roles():
    for guild in bot.guilds:
        await process_roles_updating(guild)

@bot.command(name="sync_roles")
@commands.has_permissions(administrator=True) 
async def sync_roles(ctx):
    await ctx.send("🔄 Запущена проверка. Бот проверяет участников и создаёт недостающие роли...")
    await process_roles_updating(ctx.guild)
    await ctx.send("✅ Все роли успешно проверены и обновлены!")

@sync_roles.error
async def sync_roles_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас нет прав Администратора для использования этой команды.")

token = os.getenv("BOT_TOKEN")
if token:
    bot.run(token)
else:
    print("Ошибка: Переменная BOT_TOKEN не настроена!")

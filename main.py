import discord
from discord import app_commands
from discord.ext import commands
import os

GUILD_ID = 1443387233062354954

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

config = {
    "admin_roles": [],
    "log_channel": None
}

@bot.event
async def on_ready():
    print("🔄 SINCRONIZANDO COMANDOS...")
    guild = discord.Object(id=GUILD_ID)

    try:
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
        print("✅ COMANDOS ANTIGOS LIMPOS")
    except Exception as e:
        print("⚠ ERRO AO LIMPAR:", e)

    try:
        synced = await bot.tree.sync(guild=guild)
        print(f"✅ COMANDOS REGISTRADOS: {len(synced)}")
    except Exception as e:
        print("❌ ERRO AO REGISTRAR:", e)

    print("✅ BOT ONLINE")


def is_admin(interaction: discord.Interaction):
    return any(role.id in config["admin_roles"] for role in interaction.user.roles)

# CONFIGURAR CARGO ADMIN
@bot.tree.command(name="config-admin", description="Configurar cargo administrador")
@app_commands.check(is_admin)
async def config_admin(interaction: discord.Interaction, cargo: discord.Role):
    config["admin_roles"].append(cargo.id)
    await interaction.response.send_message(f"✅ {cargo.name} agora é cargo administrador.", ephemeral=True)

# CONFIGURAR CANAL LOG
@bot.tree.command(name="config-log", description="Configurar canal de registros PRF")
@app_commands.check(is_admin)
async def config_log(interaction: discord.Interaction, canal: discord.TextChannel):
    config["log_channel"] = canal.id
    await interaction.response.send_message(f"✅ Canal setado: {canal.mention}", ephemeral=True)

# REGISTRAR MEMBRO
@bot.tree.command(name="registrar", description="Registrar membro na PRF")
@app_commands.check(is_admin)
async def registrar(interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):
    await membro.add_roles(cargo)

    msg = f"✅ {membro.mention} registrado como **{cargo.name}**."

    await interaction.response.send_message(msg)

    try:
        await membro.send(f"👮 Você foi registrado na PRF como **{cargo.name}**.")
    except:
        pass

    if config["log_channel"]:
        canal = bot.get_channel(config["log_channel"])
        await canal.send(msg)

# PROMOVER
@bot.tree.command(name="promover", description="Promover membro")
@app_commands.check(is_admin)
async def promover(interaction: discord.Interaction, membro: discord.Member, novo_cargo: discord.Role):
    await membro.add_roles(novo_cargo)

    msg = f"📈 {membro.mention} promovido para **{novo_cargo.name}**."

    await interaction.response.send_message(msg)

    if config["log_channel"]:
        await bot.get_channel(config["log_channel"]).send(msg)

# REBAIXAR
@bot.tree.command(name="rebaixar", description="Rebaixar membro")
@app_commands.check(is_admin)
async def rebaixar(interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):
    await membro.add_roles(cargo)

    msg = f"📉 {membro.mention} rebaixado para **{cargo.name}**."

    await interaction.response.send_message(msg)

    if config["log_channel"]:
        await bot.get_channel(config["log_channel"]).send(msg)

# DEMITIR
@bot.tree.command(name="exonerar", description="Expulsar da PRF")
@app_commands.check(is_admin)
async def exonerar(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    for role in membro.roles:
        if role.name != "@everyone":
            await membro.remove_roles(role)

    msg = f"❌ {membro.mention} foi exonerado.\nMotivo: {motivo}"

    await interaction.response.send_message(msg)

    try:
        await membro.send(f"🚫 Você foi exonerado da PRF.\nMotivo: {motivo}")
    except:
        pass

    if config["log_channel"]:
        await bot.get_channel(config["log_channel"]).send(msg)

# ADVERTÊNCIA
@bot.tree.command(name="punir", description="Aplicar advertência")
@app_commands.check(is_admin)
async def punir(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    msg = f"⚠ {membro.mention} advertido.\nMotivo: {motivo}"

    await interaction.response.send_message(msg)

    try:
        await membro.send(f"⚠ Advertência PRF\nMotivo: {motivo}")
    except:
        pass

    if config["log_channel"]:
        await bot.get_channel(config["log_channel"]).send(msg)


bot.run(os.getenv("DISCORD_TOKEN"))

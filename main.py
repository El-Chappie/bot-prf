import discord
from discord import app_commands
from discord.ext import commands
import os

# ==========================
# CONFIGURAÇÕES
# ==========================
GUILD_ID = 1443387233062354954  # ID DO SEU SERVIDOR

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

config = {
    "admin_roles": [],
    "log_channel": None
}

# ==========================
# EVENT
# ==========================
@bot.event
async def on_ready():
    print("➡ BOT INICIADO")
    guild = discord.Object(id=GUILD_ID)

    print("🔄 APAGANDO COMANDOS...")
    bot.tree.clear_commands(guild=guild)

    print("🔁 RECRIANDO COMANDOS...")
    synced = await bot.tree.sync(guild=guild)

    print(f"✅ COMANDOS REGISTRADOS: {len(synced)}")
    print(f"✅ BOT ONLINE COMO: {bot.user}")

# ==========================
# VERIFICADOR ADMIN
# ==========================
def is_admin(interaction: discord.Interaction):
    return any(role.id in config["admin_roles"] for role in interaction.user.roles)

# ==========================
# CONFIG ADMIN
# ==========================
@bot.tree.command(name="config-admin", description="Define cargo administrador")
async def config_admin(interaction: discord.Interaction, cargo: discord.Role):
    config["admin_roles"].append(cargo.id)
    await interaction.response.send_message(
        f"✅ Cargo {cargo.mention} agora tem permissão administrativa.",
        ephemeral=True
    )

# ==========================
# CONFIG CANAL LOG
# ==========================
@bot.tree.command(name="config-log", description="Define canal de registros PRF")
async def config_log(interaction: discord.Interaction, canal: discord.TextChannel):
    config["log_channel"] = canal.id
    await interaction.response.send_message(
        f"✅ Canal de comunicados definido: {canal.mention}",
        ephemeral=True
    )

# ==========================
# REGISTRAR MEMBRO
# ==========================
@bot.tree.command(name="registrar", description="Registrar membro")
async def registrar(interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):
    if not is_admin(interaction):
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    await membro.add_roles(cargo)

    msg = f"✅ {membro.mention} registrado como **{cargo.name}**"

    await interaction.response.send_message(msg)

    try:
        await membro.send(f"👮 Você foi registrado na PRF como **{cargo.name}**.")
    except:
        pass

    if config["log_channel"]:
        await bot.get_channel(config["log_channel"]).send(msg)

# ==========================
# PROMOVER
# ==========================
@bot.tree.command(name="promover", description="Promover membro")
async def promover(interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):
    if not is_admin(interaction):
        return await interaction.response.send_message("❌ Permissão negada.", ephemeral=True)

    await membro.add_roles(cargo)

    msg = f"📈 {membro.mention} promovido para **{cargo.name}**"

    await interaction.response.send_message(msg)

    if config["log_channel"]:
        await bot.get_channel(config["log_channel"]).send(msg)

# ==========================
# REBAIXAR
# ==========================
@bot.tree.command(name="rebaixar", description="Rebaixar membro")
async def rebaixar(interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):
    if not is_admin(interaction):
        return await interaction.response.send_message("❌ Sem autorização.", ephemeral=True)

    await membro.add_roles(cargo)

    msg = f"📉 {membro.mention} rebaixado para **{cargo.name}**"

    await interaction.response.send_message(msg)

    if config["log_channel"]:
        await bot.get_channel(config["log_channel"]).send(msg)

# ==========================
# EXONERAR
# ==========================
@bot.tree.command(name="exonerar", description="Remover membro da PRF")
async def exonerar(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    if not is_admin(interaction):
        return await interaction.response.send_message("❌ Sem autorização.", ephemeral=True)

    for role in membro.roles:
        if role.name != "@everyone":
            await membro.remove_roles(role)

    msg = f"❌ {membro.mention} exonerado.\nMotivo: {motivo}"

    await interaction.response.send_message(msg)

    try:
        await membro.send(f"🚫 Você foi exonerado da PRF.\nMotivo: {motivo}")
    except:
        pass

    if config["log_channel"]:
        await bot.get_channel(config["log_channel"]).send(msg)

# ==========================
# ADVERTÊNCIA
# ==========================
@bot.tree.command(name="punir", description="Aplicar punição")
async def punir(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    if not is_admin(interaction):
        return await interaction.response.send_message("❌ Sem autorização.", ephemeral=True)

    msg = f"⚠ {membro.mention} advertido.\nMotivo: {motivo}"

    await interaction.response.send_message(msg)

    try:
        await membro.send(f"⚠ Advertência PRF\nMotivo: {motivo}")
    except:
        pass

    if config["log_channel"]:
        await bot.get_channel(c_
        
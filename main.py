import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")
DB = "prf.db"

PATENTES = [
    "Diretor geral","executivo","de operações","de inteligência",
    "superintendente executivo","superintendente regional",
    "delegado geral","executivo","inspetor chefe","inspetor",
    "supervisor","agente 1 classe","agente 2 classe","agente 3 classe","aluno"
]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --------------------------------------------------------

async def iniciar_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS membros(
            id INTEGER PRIMARY KEY,
            nome_rp TEXT,
            patente TEXT,
            status TEXT,
            advertencias INTEGER DEFAULT 0
        )
        """)
        await db.commit()

@bot.event
async def on_ready():
    await iniciar_db()
    await bot.tree.sync()
    print("Bot PRF ONLINE")

# --------------------------------------------------------
# UTILIDADES DE CARGO

async def remover_patentes(member):
    for role in member.roles:
        if role.name in PATENTES or role.name == "civil":
            await member.remove_roles(role)

async def setar_patente(member, cargo_nome):
    role = discord.utils.get(member.guild.roles, name=cargo_nome)
    if not role:
        raise Exception(f"Cargo '{cargo_nome}' não existe.")
    await member.add_roles(role)

# --------------------------------------------------------
# PERMISSÃO HIERÁRQUICA

def patente_index(nome):
    try:
        return PATENTES.index(nome)
    except:
        return 999

async def tem_permissao(member, patente_min):
    for role in member.roles:
        if role.name in PATENTES:
            return patente_index(role.name) <= patente_index(patente_min)
    return member.guild_permissions.administrator

# --------------------------------------------------------
# REGISTRAR

@bot.tree.command()
async def registrar(interaction: discord.Interaction, usuario: discord.Member, nome_rp: str, patente: str):
    if not await tem_permissao(interaction.user, "supervisor"):
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    if patente not in PATENTES:
        return await interaction.response.send_message("❌ Patente inválida.", ephemeral=True)

    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO membros VALUES (?,?,?,?,0)", 
                         (usuario.id, nome_rp, patente, "ativo"))
        await db.commit()

    await remover_patentes(usuario)
    await setar_patente(usuario, patente)

    await usuario.send(f"✅ Você foi registrado na PRF.\nPatente: {patente}")

    await interaction.response.send_message(f"✔ {usuario.mention} registrado como {patente}.")


# --------------------------------------------------------
# PROMOVER

@bot.tree.command()
async def promover(interaction: discord.Interaction, usuario: discord.Member, nova_patente: str):
    if not await tem_permissao(interaction.user, "inspetor"):
        return await interaction.response.send_message("❌ Sem permissão.")

    if nova_patente not in PATENTES:
        return await interaction.response.send_message("Patente inválida.")

    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE membros SET patente=? WHERE id=?", (nova_patente, usuario.id))
        await db.commit()

    await remover_patentes(usuario)
    await setar_patente(usuario, nova_patente)

    await usuario.send(f"📈 Você foi PROMOVIDO para {nova_patente}.")
    await interaction.response.send_message(f"✅ {usuario.mention} promovido.")


# --------------------------------------------------------
# REBAIXAR

@bot.tree.command()
async def rebaixar(interaction: discord.Interaction, usuario: discord.Member, nova_patente: str, motivo: str):
    if not await tem_permissao(interaction.user, "inspetor"):
        return await interaction.response.send_message("Sem permissão.")

    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE membros SET patente=? WHERE id=?", (nova_patente, usuario.id))
        await db.commit()

    await remover_patentes(usuario)
    await setar_patente(usuario, nova_patente)

    await usuario.send(f"📉 Você foi REBAIXADO para {nova_patente}.\nMotivo: {motivo}")
    await interaction.response.send_message("Rebaixamento aplicado.")


# --------------------------------------------------------
# EXONERAR

@bot.tree.command()
async def exonerar(interaction: discord.Interaction, usuario: discord.Member, motivo: str):
    if not await tem_permissao(interaction.user, "inspetor"):
        return await interaction.response.send_message("Sem permissão.")

    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE membros SET status='exonerado' WHERE id=?", (usuario.id,))
        await db.commit()

    await remover_patentes(usuario)
    await setar_patente(usuario, "civil")

    await usuario.send(f"⛔ Você foi EXONERADO da PRF.\nMotivo: {motivo}")
    await interaction.response.send_message("Exoneração concluída.")


# --------------------------------------------------------
# ADVERTIR

@bot.tree.command()
async def advertir(interaction: discord.Interaction, usuario: discord.Member, motivo: str):
    if not await tem_permissao(interaction.user, "supervisor"):
        return await interaction.response.send_message("Sem permissão.")

    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE membros SET advertencias = advertencias + 1 WHERE id=?", (usuario.id,))
        await db.commit()

    await usuario.send(f"⚠️ ADVERTÊNCIA OFICIAL\nMotivo: {motivo}")
    await interaction.response.send_message("Advertência aplicada.")

# --------------------------------------------------------

bot.run(TOKEN)
  

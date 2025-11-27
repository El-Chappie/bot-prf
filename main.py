import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import os, json

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"

# ---------------- CONFIG ----------------
def carregar_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = {
            "admins": [],
            "canal_folha": None
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        return cfg
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

config = carregar_config()

# ---------------- UTILIDADES ----------------
def eh_admin(membro: discord.Member):
    return any(role.id in config.get("admins", []) for role in membro.roles)

def embed_padrao(titulo, descricao, cor=0x1F8B4C):
    e = discord.Embed(title=titulo, description=descricao, color=cor)
    e.set_footer(text="Polícia Rodoviária Federal • Sistema Oficial")
    return e

async def enviar_canal(guild, canal_id, embed):
    if not canal_id:
        return
    canal = guild.get_channel(canal_id)
    if canal:
        await canal.send(embed=embed)

async def enviar_dm(usuario, embed):
    try:
        await usuario.send(embed=embed)
    except:
        pass

# ---------------- EVENTO ----------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ BOT PRF ONLINE — {bot.user}")

# ---------------- CONFIGURAÇÃO ----------------
@bot.tree.command(name="config-admin", description="Define um cargo administrativo")
async def config_admin(interaction: discord.Interaction, cargo: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Apenas administradores do servidor.", ephemeral=True)

    config["admins"].append(cargo.id)
    salvar_config(config)
    await interaction.response.send_message(f"✅ Cargo {cargo.mention} definido como ADMINISTRATIVO.")

@bot.tree.command(name="config-folha", description="Define o canal da folha da PRF")
async def config_folha(interaction: discord.Interaction, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Apenas administradores do servidor.", ephemeral=True)

    config["canal_folha"] = canal.id
    salvar_config(config)
    await interaction.response.send_message(f"✅ Canal da folha definido para {canal.mention}")

# ---------------- INCORPORAÇÃO ----------------
@bot.tree.command(name="incorporar", description="Incorpora um membro à PRF")
@app_commands.describe(membro="Usuário a incorporar", cargo="Cargo da PRF (mention)")
async def incorporar(interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role):

    if not eh_admin(interaction.user):
        return await interaction.response.send_message("❌ Você não possui autorização.", ephemeral=True)

    await membro.add_roles(cargo, reason="Incorporação à PRF")

    texto = (
        f"Fica oficialmente registrada a **INTEGRAÇÃO** do cidadão abaixo aos quadros da Polícia Rodoviária Federal.\n\n"
        f"👤 **Servidor:** {membro.mention}\n"
        f"🎖 **Cargo:** {cargo.mention}\n"
        f"🧑‍⚖️ **Autoridade:** {interaction.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    embed = embed_padrao("📋 TERMO DE INCORPORAÇÃO", texto, 0x2ECC71)

    await interaction.response.send_message("✅ Incorporação registrada com sucesso.", ephemeral=True)
    await enviar_canal(interaction.guild, config.get("canal_folha"), embed)
    await enviar_dm(membro, embed)

# ---------------- EXONERAÇÃO ----------------
@bot.tree.command(name="exonerar", description="Exonera um membro da PRF")
@app_commands.describe(membro="Usuário a exonerar", motivo="Motivo da exoneração")
async def exonerar(interaction: discord.Interaction, membro: discord.Member, motivo: str):

    if not eh_admin(interaction.user):
        return await interaction.response.send_message("❌ Você não possui autorização.", ephemeral=True)

    texto = (
        f"Fica oficialmente registrada a **EXONERAÇÃO** do servidor abaixo dos quadros da Polícia Rodoviária Federal.\n\n"
        f"👤 **Servidor:** {membro.mention}\n"
        f"📄 **Motivo:** {motivo}\n"
        f"🧑‍⚖️ **Autoridade:** {interaction.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    embed = embed_padrao("🚨 TERMO DE EXONERAÇÃO", texto, 0xE74C3C)

    await interaction.response.send_message("✅ Exoneração registrada com sucesso.", ephemeral=True)
    await enviar_canal(interaction.guild, config.get("canal_folha"), embed)
    await enviar_dm(membro, embed)

# ---------------- START ----------------
bot.run(os.getenv("DISCORD_TOKEN"))

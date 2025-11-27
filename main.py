import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import os, json

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"

CARGO_CIVIL_ID = 1443537740821037136
CARGO_PRF_ID = 1443387935700291697

def carregar_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = {"admins": [], "canal_folha": None}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        return cfg
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8"):
        json.dump(cfg, f, indent=4)

config = carregar_config()

def eh_admin(m):
    return any(r.id in config["admins"] for r in m.roles)

def embed_padrao(t, d, c=0x2ecc71):
    e = discord.Embed(title=t, description=d, color=c)
    e.set_footer(text="Polícia Rodoviária Federal • Sistema Oficial")
    return e

async def enviar_canal(g, cid, e):
    if not cid: return
    c = g.get_channel(cid)
    if c: await c.send(embed=e)

async def tentar_dm(u, e):
    try: await u.send(embed=e)
    except: pass

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ BOT PRF ONLINE")

# CONFIGS
@bot.tree.command(name="config-admin")
async def config_admin(i: discord.Interaction, cargo: discord.Role):
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message("❌ Sem permissão.", ephemeral=True)
    if cargo.id not in config["admins"]:
        config["admins"].append(cargo.id)
        salvar_config(config)
    await i.response.send_message(f"✅ {cargo.mention} autorizado.", ephemeral=True)

@bot.tree.command(name="config-folha")
async def config_folha(i: discord.Interaction, canal: discord.TextChannel):
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message("❌ Sem permissão.", ephemeral=True)
    config["canal_folha"] = canal.id
    salvar_config(config)
    await i.response.send_message(f"✅ Canal configurado.", ephemeral=True)

# ✳️ INCORPORAR
@bot.tree.command(name="incorporar", description="Incorporar servidor à PRF")
@app_commands.describe(
    membro="Servidor que será incorporado",
    cargo="Patente ou função a ser atribuída"
)
async def incorporar(i: discord.Interaction, membro: discord.Member, cargo: discord.Role):

    if not eh_admin(i.user):
        return await i.response.send_message("❌ Você não possui autorização.", ephemeral=True)

    prf = i.guild.get_role(CARGO_PRF_ID)
    civil = i.guild.get_role(CARGO_CIVIL_ID)

    if not prf or not civil:
        return await i.response.send_message("❌ Cargo PRF ou CIVIL não localizado.", ephemeral=True)

    # REMOVE CIVIL
    if civil in membro.roles:
        await membro.remove_roles(civil)

    # ADICIONA CARGOS
    await membro.add_roles(prf, cargo)

    # ALTERA NICK
    nome = membro.name
    novo = f"『PRF』{cargo.name}│{nome}"

    try:
        await membro.edit(nick=novo)
    except:
        pass

    texto = (
        f"Foi oficialmente formalizada a **INCORPORAÇÃO** do servidor abaixo.\n\n"
        f"👤 **Servidor:** {membro.mention}\n"
        f"🎖 **Cargo:** {cargo.mention}\n"
        f"🟢 **Status:** PRF Ativo\n"
        f"🧑‍⚖️ **Autoridade:** {i.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("📋 TERMO DE INCORPORAÇÃO", texto)

    await i.response.send_message("✅ Incorporação realizada com sucesso.", ephemeral=True)
    await enviar_canal(i.guild, config["canal_folha"], emb)
    await tentar_dm(membro, emb)

# 🚨 EXONERAR
@bot.tree.command(name="exonerar", description="Exonerar servidor da PRF")
@app_commands.describe(
    membro="Servidor a ser exonerado",
    motivo="Motivo da exoneração"
)
async def exonerar(i: discord.Interaction, membro: discord.Member, motivo: str):

    if not eh_admin(i.user):
        return await i.response.send_message("❌ Você não possui autorização.", ephemeral=True)

    civil = i.guild.get_role(CARGO_CIVIL_ID)
    if not civil:
        return await i.response.send_message("❌ Cargo civil inexistente.", ephemeral=True)

    # REMOVE TODOS
    for r in membro.roles:
        if r != i.guild.default_role:
            await membro.remove_roles(r)

    # ADICIONA CIVIL
    await membro.add_roles(civil)

    # RESET NOME
    try:
        await membro.edit(nick=None)
    except:
        pass

    texto = (
        f"Foi oficialmente executada a **EXONERAÇÃO** do servidor abaixo.\n\n"
        f"👤 **Servidor:** {membro.mention}\n"
        f"📄 **Motivo:** {motivo}\n"
        f"🔴 **Status:** Civil\n"
        f"🧑‍⚖️ **Autoridade:** {i.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("🚨 TERMO DE EXONERAÇÃO", texto, 0xe74c3c)

    await i.response.send_message("✅ Exoneração realizada.", ephemeral=True)
    await enviar_canal(i.guild, config["canal_folha"], emb)
    await tentar_dm(membro, emb)

# START
bot.run(os.getenv("DISCORD_TOKEN"))

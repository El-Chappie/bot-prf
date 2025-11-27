import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import os, json

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"

def carregar_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "admins": [],
            "canal_avisos": None,
            "canal_logs": None
        }
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

config = carregar_config()

# ========= FUNÇÕES =========

def eh_admin(membro: discord.Member):
    return any(role.id in config["admins"] for role in membro.roles)

def embed_padrao(titulo, desc, cor):
    emb = discord.Embed(title=titulo, description=desc, color=cor)
    emb.set_footer(text="PRF • Sistema Oficial")
    return emb

async def enviar_canal(guild, canal_id, embed):
    if canal_id:
        canal = guild.get_channel(canal_id)
        if canal:
            await canal.send(embed=embed)

async def enviar_dm(membro, embed):
    try:
        await membro.send(embed=embed)
    except:
        pass

# ========= EVENT =========

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ BOT PRF CONFIG ON")

# ========= CONFIGURAÇÕES =========

@bot.tree.command(name="config-admin")
@app_commands.describe(cargo="Cargo autorizado")
async def config_admin(inter: discord.Interaction, cargo: discord.Role):

    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Apenas administradores do Discord.", ephemeral=True)
        return

    if cargo.id not in config["admins"]:
        config["admins"].append(cargo.id)
        salvar_config(config)

    await inter.response.send_message(f"✅ Cargo {cargo.mention} agora é ADMINISTRATIVO.")

@bot.tree.command(name="config-avisos")
@app_commands.describe(canal="Canal de avisos")
async def config_avisos(inter: discord.Interaction, canal: discord.TextChannel):

    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Apenas administradores.", ephemeral=True)
        return

    config["canal_avisos"] = canal.id
    salvar_config(config)

    await inter.response.send_message(f"✅ Canal de comunicações definido: {canal.mention}")

@bot.tree.command(name="config-logs")
@app_commands.describe(canal="Canal de logs")
async def config_logs(inter: discord.Interaction, canal: discord.TextChannel):

    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Apenas administradores.", ephemeral=True)
        return

    config["canal_logs"] = canal.id
    salvar_config(config)

    await inter.response.send_message(f"✅ Canal de logs definido: {canal.mention}")

@bot.tree.command(name="config-status")
async def config_status(inter: discord.Interaction):

    admins = []
    for role_id in config["admins"]:
        role = inter.guild.get_role(role_id)
        if role:
            admins.append(role.mention)

    canal_a = f"<#{config['canal_avisos']}>" if config["canal_avisos"] else "❌ Não definido"
    canal_l = f"<#{config['canal_logs']}>" if config["canal_logs"] else "❌ Não definido"

    emb = embed_padrao("⚙️ CONFIGURAÇÃO PRF",
        f"**Cargos Admin:**\n" + "\n".join(admins) +
        f"\n\n📢 **Canal avisos:** {canal_a}"
        f"\n📁 **Canal logs:** {canal_l}",
        0x95A5A6
    )

    await inter.response.send_message(embed=emb, ephemeral=True)

# ========= COMANDOS ADMIN =========

@bot.tree.command(name="registrar")
@app_commands.describe(membro="Usuário", cargo="Cargo")
async def registrar(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role):

    if not eh_admin(inter.user):
        await inter.response.send_message("❌ Você não possui autorização.", ephemeral=True)
        return

    await membro.add_roles(cargo)

    emb = embed_padrao("📋 REGISTRO EFETUADO",
        f"**Membro:** {membro.mention}\n"
        f"**Cargo:** {cargo.mention}\n"
        f"**Autoridade:** {inter.user.mention}",
        0x3498DB
    )

    await inter.response.send_message(embed=emb)
    await enviar_dm(membro, emb)
    await enviar_canal(inter.guild, config["canal_avisos"], emb)
    await enviar_canal(inter.guild, config["canal_logs"], emb)

@bot.tree.command(name="promover")
@app_commands.describe(membro="Membro", cargo="Novo cargo")
async def promover(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role):

    if not eh_admin(inter.user):
        await inter.response.send_message("❌ Sem permissão.", ephemeral=True)
        return

    await membro.add_roles(cargo)

    emb = embed_padrao("📈 PROMOÇÃO",
        f"**Membro:** {membro.mention}\n"
        f"**Novo cargo:** {cargo.mention}\n"
        f"**Autoridade:** {inter.user.mention}",
        0x2ECC71
    )

    await inter.response.send_message(embed=emb)
    await enviar_dm(membro, emb)
    await enviar_canal(inter.guild, config["canal_avisos"], emb)
    await enviar_canal(inter.guild, config["canal_logs"], emb)

@bot.tree.command(name="rebaixar")
@app_commands.describe(membro="Membro", cargo="Novo cargo", motivo="Motivo")
async def rebaixar(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role, motivo: str):

    if not eh_admin(inter.user):
        await inter.response.send_message("❌ Sem permissão.", ephemeral=True)
        return

    await membro.add_roles(cargo)

    emb = embed_padrao("📉 REBAIXAMENTO",
        f"**Membro:** {membro.mention}\n"
        f"**Novo cargo:** {cargo.mention}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}",
        0xE67E22
    )

    await inter.response.send_message(embed=emb)
    await enviar_dm(membro, emb)
    await enviar_canal(inter.guild, config["canal_avisos"], emb)
    await enviar_canal(inter.guild, config["canal_logs"], emb)

@bot.tree.command(name="exonerar")
@app_commands.describe(membro="Membro", motivo="Motivo")
async def exonerar(inter: discord.Interaction, membro: discord.Member, motivo: str):

    if not eh_admin(inter.user):
        await inter.response.send_message("❌ Sem permissão.", ephemeral=True)
        return

    emb = embed_padrao("🚨 EXONERAÇÃO",
        f"**Membro:** {membro.mention}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}",
        0xC0392B
    )

    await inter.response.send_message(embed=emb)
    await enviar_dm(membro, emb)
    await enviar_canal(inter.guild, config["canal_avisos"], emb)
    await enviar_canal(inter.guild, config["canal_logs"], emb)

# ========= INICIAR =========
bot.run(os.getenv("DISCORD_TOKEN"))

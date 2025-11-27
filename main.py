# ========================
# BOT PRF DISCORD RP
# ========================

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import os, json

# ========= CONFIG =========
GUILD_ID = 1443387233062354954  # COLE AQUI O ID REAL DO SERVIDOR

CONFIG_FILE = "config.json"
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ========= HIERARQUIA =========
HIERARQUIA = [
    "DIRETOR GERAL",
    "DIRETOR EXECUTIVO",
    "DIRETOR DE OPERAÇÕES",
    "DIRETOR DE INTELIGÊNCIA",
    "SUPERINTENDENTE EXECUTIVO",
    "SUPERINTENDENTE REGIONAL",
    "DELEGADO GERAL",
    "DELEGADO EXECUTIVO",
    "CHEFE DE SETOR",
    "CHEFE DE NÚCLEO",
    "CHEFE DE EQUIPE",
    "INSPETOR CHEFE",
    "INSPETOR",
    "SUPERVISOR",
    "AGENTE – 1ª CLASSE",
    "AGENTE – 2ª CLASSE",
    "AGENTE – 3ª CLASSE",
    "ALUNO FEDERAL",
    "CIVIL"
]

# ========= CONFIG FILE =========
def carregar_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = {
            "admins": [],
            "canal_avisos": None,
            "canal_logs": None
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=4)
        return cfg
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def salvar_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

config = carregar_config()

# ========= UTIL =========
def eh_admin(membro):
    return any(role.id in config["admins"] for role in membro.roles)

def embed_padrao(titulo, desc, cor):
    emb = discord.Embed(title=titulo, description=desc, color=cor)
    emb.set_footer(text="PRF • Sistema Oficial")
    return emb

async def enviar_dm(user, embed):
    try:
        await user.send(embed=embed)
    except:
        pass

async def enviar_canal(guild, canal_id, embed):
    if canal_id:
        canal = guild.get_channel(canal_id)
        if canal:
            await canal.send(embed=embed)

async def limpar_cargos(membro):
    for role in membro.roles:
        if role.name.upper() in HIERARQUIA:
            await membro.remove_roles(role)

# ========= EVENT =========
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ COMANDOS SINCRONIZADOS: {len(synced)}")
    except Exception as e:
        print(e)
    print("✅ BOT PRF ONLINE")

# ========= CONFIG ADMIN =========
@bot.tree.command(name="config-admin", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(cargo="Cargo administrativo")
async def config_admin(inter, cargo: discord.Role):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Apenas administradores do servidor.", ephemeral=True)
        return
    if cargo.id not in config["admins"]:
        config["admins"].append(cargo.id)
        salvar_config(config)
    await inter.response.send_message(f"✅ {cargo.mention} agora é cargo administrativo.")

# ========= CONFIG CANAIS =========
@bot.tree.command(name="config-avisos", guild=discord.Object(id=GUILD_ID))
async def config_avisos(inter, canal: discord.TextChannel):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Apenas administradores do servidor.", ephemeral=True)
        return
    config["canal_avisos"] = canal.id
    salvar_config(config)
    await inter.response.send_message(f"✅ Canal de avisos: {canal.mention}")

@bot.tree.command(name="config-logs", guild=discord.Object(id=GUILD_ID))
async def config_logs(inter, canal: discord.TextChannel):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Apenas administradores.", ephemeral=True)
        return
    config["canal_logs"] = canal.id
    salvar_config(config)
    await inter.response.send_message(f"✅ Canal de logs: {canal.mention}")

@bot.tree.command(name="config-status", guild=discord.Object(id=GUILD_ID))
async def config_status(inter):
    admins = [inter.guild.get_role(i).mention for i in config["admins"] if inter.guild.get_role(i)]
    ca = f"<#{config['canal_avisos']}>" if config["canal_avisos"] else "❌"
    cl = f"<#{config['canal_logs']}>" if config["canal_logs"] else "❌"

    emb = embed_padrao("⚙️ CONFIGURAÇÕES",
        f"**Admins:** {', '.join(admins) if admins else 'Nenhum'}\n"
        f"**Canal avisos:** {ca}\n"
        f"**Canal logs:** {cl}",
        0x95A5A6
    )
    await inter.response.send_message(embed=emb, ephemeral=True)

# ========= REGISTRO =========
@bot.tree.command(name="registrar", guild=discord.Object(id=GUILD_ID))
async def registrar(inter, membro: discord.Member, cargo: discord.Role):
    if not eh_admin(inter.user):
        await inter.response.send_message("❌ Sem autorização.", ephemeral=True)
        return
    await limpar_cargos(membro)
    await membro.add_roles(cargo)
    emb = embed_padrao("📋 REGISTRO",
        f"{membro.mention} registrado como {cargo.mention}\n"
        f"Autoridade: {inter.user.mention}",
        0x3498DB
    )
    await inter.response.send_message(embed=emb)
    await enviar_dm(membro, emb)
    await enviar_canal(inter.guild, config["canal_avisos"], emb)
    await enviar_canal(inter.guild, config["canal_logs"], emb)

# ========= PROMOÇÃO =========
@bot.tree.command(name="promover", guild=discord.Object(id=GUILD_ID))
async def promover(inter, membro: discord.Member, cargo: discord.Role):
    if not eh_admin(inter.user): return
    await limpar_cargos(membro)
    await membro.add_roles(cargo)
    emb = embed_padrao("📈 PROMOÇÃO",
        f"{membro.mention} promovido a {cargo.mention}",
        0x2ECC71
    )
    await inter.response.send_message(embed=emb)
    await enviar_dm(membro, emb)
    await enviar_canal(inter.guild, config["canal_avisos"], emb)
    await enviar_canal(inter.guild, config["canal_logs"], emb)

# ========= REBAIXAR =========
@bot.tree.command(name="rebaixar", guild=discord.Object(id=GUILD_ID))
async def rebaixar(inter, membro: discord.Member, cargo: discord.Role, motivo: str):
    if not eh_admin(inter.user): return
    await limpar_cargos(membro)
    await membro.add_roles(cargo)
    emb = embed_padrao("📉 REBAIXAMENTO",
        f"{membro.mention} rebaixado para {cargo.mention}\nMotivo: {motivo}",
        0xE67E22
    )
    await inter.response.send_message(embed=emb)
    await enviar_dm(membro, emb)
    await enviar_canal(inter.guild, config["canal_avisos"], emb)
    await enviar_canal(inter.guild, config["canal_logs"], emb)

# ========= ADVERTIR =========
@bot.tree.command(name="advertir", guild=discord.Object(id=GUILD_ID))
async def advertir(inter, membro: discord.Member, motivo: str):
    if not eh_admin(inter.user): return
    emb = embed_padrao("⚠️ ADVERTÊNCIA",
        f"{membro.mention}\nMotivo: {motivo}",
        0xF1C40F
    )
    await inter.response.send_message(embed=emb)
    await enviar_dm(membro, emb)
    await enviar_canal(inter.guild, config["canal_avisos"], emb)
    await enviar_canal(inter.guild, config["canal_logs"], emb)

# ========= EXONERAR =========
@bot.tree.command(name="exonerar", guild=discord.Object(id=GUILD_ID))
async def exonerar(inter, membro: discord.Member, motivo: str):
    if not eh_admin(inter.user): return
    cargo_civil = discord.utils.get(inter.guild.roles, name="CIVIL")
    if not cargo_civil:
        await inter.response.send_message("❌ Cargo CIVIL não existe.", ephemeral=True)
        return

    await limpar_cargos(membro)
    await membro.add_roles(cargo_civil)

    emb = embed_padrao("🚨 EXONERAÇÃO",
        f"{membro.mention} foi exonerado.\nMotivo: {motivo}",
        0xC0392B
    )
    await inter.response.send_message(embed=emb)
    await enviar_dm(membro, emb)
    await enviar_canal(inter.guild, config["canal_avisos"], emb)
    await enviar_canal(inter.guild, config["canal_logs"], emb)

# ========= RUN =========
bot.run(os.getenv("DISCORD_TOKEN"))

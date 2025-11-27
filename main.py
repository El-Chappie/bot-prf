# main.py — BOT PRF FINAL
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import os, json, traceback

# ---------------- CONFIG / INTENTS ----------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"
WARNINGS_FILE = "advertencias.json"

# ---------------- HIERARQUIA ----------------
HIERARQUIA = [
    "DIRETOR GERAL","DIRETOR EXECUTIVO","DIRETOR DE OPERAÇÕES","DIRETOR DE INTELIGÊNCIA",
    "SUPERINTENDENTE EXECUTIVO","SUPERINTENDENTE REGIONAL","DELEGADO GERAL","DELEGADO EXECUTIVO",
    "CHEFE DE SETOR","CHEFE DE NÚCLEO","CHEFE DE EQUIPE","INSPETOR CHEFE","INSPETOR","SUPERVISOR",
    "AGENTE – 1ª CLASSE","AGENTE – 2ª CLASSE","AGENTE – 3ª CLASSE","ALUNO FEDERAL","CIVIL"
]

# ---------------- CONFIG ----------------
def carregar_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = {"admins": [], "canal_avisos": None, "canal_logs": None}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        return cfg
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

config = carregar_config()

# ---------------- ADVERTÊNCIAS ----------------
def carregar_warns():
    if not os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
        return {}
    with open(WARNINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_warns(dados):
    with open(WARNINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4)

def get_warns(uid):
    return carregar_warns().get(str(uid), [])

def add_warn(uid, info):
    data = carregar_warns()
    uid = str(uid)
    data.setdefault(uid, []).append(info)
    salvar_warns(data)

def clear_warns(uid):
    data = carregar_warns()
    data.pop(str(uid), None)
    salvar_warns(data)

# ---------------- UTIL ----------------
def eh_admin(m):
    return any(r.id in config.get("admins", []) for r in m.roles)

def role_is_prf(role):
    return role.name.upper() in [h.upper() for h in HIERARQUIA]

async def remover_cargos_prf(m:
discord.Member):
    prs = [r for r in m.roles if role_is_prf(r)]
    if prs:
        await m.remove_roles(*prs)

async def enviar_canal(g, cid, e):
    if not cid: return
    c = g.get_channel(cid)
    if c: await c.send(embed=e)

async def enviar_dm(m, e):
    try: await m.send(embed=e)
    except: pass

def embed_padrao(t, d, c=0x2F3136):
    e = discord.Embed(title=t, description=d, color=c)
    e.set_footer(text="PRF • Sistema Oficial")
    return e

# ---------------- BOT ----------------
@bot.event
async def on_ready():
    try: await bot.tree.sync()
    except: pass
    print(f"✅ BOT PRF ONLINE — {bot.user}")

# ---------------- CONFIGURAÇÃO ----------------
@bot.tree.command(name="config-admin")
async def cfg_admin(i:discord.Interaction,c:discord.Role):
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    config.setdefault("admins",[]).append(c.id)
    salvar_config(config)
    await i.response.send_message(f"✅ {c.mention} é ADMIN DO SISTEMA.")

@bot.tree.command(name="config-avisos")
async def cfg_av(i:discord.Interaction,c:discord.TextChannel):
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    config["canal_avisos"]=c.id
    salvar_config(config)
    await i.response.send_message(f"✅ Avisos em {c.mention}")

@bot.tree.command(name="config-logs")
async def cfg_log(i:discord.Interaction,c:discord.TextChannel):
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    config["canal_logs"]=c.id
    salvar_config(config)
    await i.response.send_message(f"✅ Logs em {c.mention}")

# ---------------- COMANDOS ----------------
def bloqueado(u):
    return len(get_warns(u.id))>=3

# REGISTRAR
@bot.tree.command(name="registrar")
async def registrar(i, m:discord.Member, r:discord.Role):
    if not eh_admin(i.user): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    if bloqueado(m): return await i.response.send_message("🚫 Exoneração obrigatória (3 advertências).",ephemeral=True)
    await remover_cargos_prf(m); await m.add_roles(r)

    emb = embed_padrao("📋 REGISTRO",
    f"Membro: {m.mention}\nCargo: {r.mention}\nAutoridade: {i.user.mention}",0x3498DB)

    await i.response.send_message(embed=emb)
    await enviar_canal(i.guild,config["canal_avisos"],emb)
    await enviar_canal(i.guild,config["canal_logs"],emb)
    await enviar_dm(m,emb)

# PROMOVER
@bot.tree.command(name="promover")
async def promover(i, m:discord.Member, r:discord.Role):
    if not eh_admin(i.user): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    if bloqueado(m): return await i.response.send_message("🚫 Exoneração obrigatória.",ephemeral=True)
    await remover_cargos_prf(m); await m.add_roles(r)

    emb = embed_padrao("📈 PROMOÇÃO",
    f"Membro: {m.mention}\nCargo: {r.mention}\nAutoridade: {i.user.mention}",0x2ECC71)

    await i.response.send_message(embed=emb)
    await enviar_canal(i.guild,config["canal_avisos"],emb)
    await enviar_canal(i.guild,config["canal_logs"],emb)
    await enviar_dm(m,emb)

# REBAIXAR
@bot.tree.command(name="rebaixar")
async def rebaixar(i, m:discord.Member, r:discord.Role, motivo:str):
    if not eh_admin(i.user): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)
    if bloqueado(m): return await i.response.send_message("🚫 Exoneração obrigatória.",ephemeral=True)
    await remover_cargos_prf(m); await m.add_roles(r)

    emb = embed_padrao("📉 REBAIXAMENTO",
    f"Membro: {m.mention}\nCargo: {r.mention}\nMotivo: {motivo}",0xE67E22)

    await i.response.send_message(embed=emb)
    await enviar_canal(i.guild,config["canal_avisos"],emb)
    await enviar_canal(i.guild,config["canal_logs"],emb)
    await enviar_dm(m,emb)

# ADVERTIR
@bot.tree.command(name="advertir")
async def advertir(i, m:discord.Member, motivo:str):
    if not eh_admin(i.user): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)

    add_warn(m.id,{"motivo":motivo,"autor":i.user.id,
    "data":datetime.now().strftime("%d/%m/%Y %H:%M")})

    total = len(get_warns(m.id))

    emb = embed_padrao("⚠ ADVERTÊNCIA",
    f"Membro: {m.mention}\nMotivo: {motivo}\nAdvertência: {total}/3",0xF1C40F)

    await i.response.send_message(embed=emb)
    await enviar_canal(i.guild,config["canal_avisos"],emb)
    await enviar_canal(i.guild,config["canal_logs"],emb)
    await enviar_dm(m,emb)

    # EXONERA AUTOMÁTICO
    if total>=3:
        civil = discord.utils.get(i.guild.roles,name="CIVIL")
        await remover_cargos_prf(m); await m.add_roles(civil)
        clear_warns(m.id)

        emb2 = embed_padrao("🚨 EXONERAÇÃO AUTOMÁTICA",
        f"Membro: {m.mention}\nMotivo: Excesso de advertências",0xE74C3C)

        await enviar_canal(i.guild,config["canal_avisos"],emb2)
        await enviar_canal(i.guild,config["canal_logs"],emb2)
        await enviar_dm(m,emb2)

# EXONERAR MANUAL
@bot.tree.command(name="exonerar")
async def exonerar(i, m:discord.Member, motivo:str):
    if not eh_admin(i.user): return await i.response.send_message("❌ Sem permissão.",ephemeral=True)

    civil = discord.utils.get(i.guild.roles,name="CIVIL")
    await remover_cargos_prf(m); await m.add_roles(civil)
    clear_warns(m.id)

    emb = embed_padrao("🚨 EXONERAÇÃO",
    f"Membro: {m.mention}\nMotivo: {motivo}",0xC0392B)

    await i.response.send_message(embed=emb)
    await enviar_canal(i.guild,config["canal_avisos"],emb)
    await enviar_canal(i.guild,config["canal_logs"],emb)
    await enviar_dm(m,emb)

# ---------------- START ----------------
bot.run(os.getenv("DISCORD_TOKEN"))

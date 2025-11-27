# main.py — BOT PRF (Comandos oficiais e sistema administrativo completo)
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import json, os, traceback

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

from edital import Edital
bot.add_cog(Edital(bot))

ARQ_CONFIG = "config.json"
ARQ_ADV = "advertencias.json"

CARGO_CIVIL_ID = 1443537740821037136
CARGO_PRF_ID = 1443387935700291697

def carregar(arq, padrao):
    if not os.path.exists(arq):
        with open(arq, "w", encoding="utf-8") as f:
            json.dump(padrao, f, indent=4)
        return padrao
    with open(arq, "r", encoding="utf-8") as f:
        return json.load(f)

config = carregar(ARQ_CONFIG, {"admins": [], "canal_folha": None, "canal_logs": None})
advertencias = carregar(ARQ_ADV, {})

def salvar_config():
    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def salvar_adv():
    with open(ARQ_ADV, "w", encoding="utf-8") as f:
        json.dump(advertencias, f, indent=4)

def eh_admin(membro):
    return any(r.id in config["admins"] for r in membro.roles)

def embed_padrao(t, d, c=0x2F3136):
    e = discord.Embed(title=t, description=d, color=c)
    e.set_footer(text="PRF • Sistema Oficial")
    return e

async def enviar(guild, canal_id, embed):
    if canal_id:
        canal = guild.get_channel(canal_id)
        if canal:
            await canal.send(embed=embed)

async def dm_safe(user, embed):
    try:
        await user.send(embed=embed)
    except:
        pass

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ BOT ONLINE — {bot.user}")

# =========================
# CONFIGURAÇÕES
# =========================
@bot.tree.command(name="config-admin")
async def config_admin(i: discord.Interaction, cargo: discord.Role):
    if not i.user.guild_permissions.administrator:
        return await i.response.send_message("❌ Apenas administradores.", ephemeral=True)
    config["admins"].append(cargo.id)
    salvar_config()
    await i.response.send_message("✅ Cargo definido como ADMIN.", ephemeral=True)

@bot.tree.command(name="config-folha")
async def config_folha(i: discord.Interaction, canal: discord.TextChannel):
    config["canal_folha"] = canal.id
    salvar_config()
    await i.response.send_message("✅ Canal da folha definido.", ephemeral=True)

@bot.tree.command(name="config-logs")
async def config_logs(i: discord.Interaction, canal: discord.TextChannel):
    config["canal_logs"] = canal.id
    salvar_config()
    await i.response.send_message("✅ Canal de logs definido.", ephemeral=True)

# =========================
# INCORPORAÇÃO
# /incorporar @user @role cargo nome
# =========================
@bot.tree.command(name="incorporar")
async def incorporar(i: discord.Interaction, membro: discord.Member, role: discord.Role, cargo: str, nome: str):
    if not eh_admin(i.user):
        return await i.response.send_message("❌ Sem permissão.", ephemeral=True)

    guild = i.guild
    prf = guild.get_role(CARGO_PRF_ID)

    for r in membro.roles:
        if r != guild.default_role:
            await membro.remove_roles(r)

    await membro.add_roles(prf, role)
    await membro.edit(nick=f"『PRF』{cargo}│{nome}")

    texto = f"""A PRF torna pública a INCORPORAÇÃO:

👮 Servidor: {membro.mention}
🏅 Cargo: {cargo}
🆔 Role: {role.mention}
📌 Situação: EFETIVO
🧑‍⚖️ Autoridade: {i.user.mention}
📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"""

    emb = embed_padrao("📋 TERMO DE INCORPORAÇÃO", texto, 0x3498DB)

    await i.response.send_message("✅ Incorporação realizada.", ephemeral=True)
    await enviar(guild, config["canal_folha"], emb)
    await enviar(guild, config["canal_logs"], emb)
    await dm_safe(membro, emb)

# =========================
# PROMOVER
# =========================
@bot.tree.command(name="promover")
async def promover(i: discord.Interaction, membro: discord.Member, role: discord.Role, cargo: str):
    if not eh_admin(i.user):
        return await i.response.send_message("❌ Sem permissão.", ephemeral=True)

    for r in membro.roles:
        if r.id != CARGO_PRF_ID and r != i.guild.default_role:
            await membro.remove_roles(r)

    await membro.add_roles(role)
    await membro.edit(nick=f"『PRF』{cargo}│{membro.display_name}")

    texto = f"""ATO DE PROMOÇÃO:

👮 Servidor: {membro.mention}
🏅 Novo cargo: {cargo}
🆔 Role: {role.mention}
🧑‍⚖️ Autoridade: {i.user.mention}
📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"""

    emb = embed_padrao("📈 PROMOÇÃO", texto, 0x2ECC71)

    await i.response.send_message("✅ Promoção efetuada.", ephemeral=True)
    await enviar(i.guild, config["canal_folha"], emb)
    await enviar(i.guild, config["canal_logs"], emb)
    await dm_safe(membro, emb)

# =========================
# REBAIXAR
# =========================
@bot.tree.command(name="rebaixar")
async def rebaixar(i: discord.Interaction, membro: discord.Member, role: discord.Role, cargo: str, motivo: str):
    if not eh_admin(i.user):
        return await i.response.send_message("❌ Sem permissão.", ephemeral=True)

    for r in membro.roles:
        if r.id != CARGO_PRF_ID and r != i.guild.default_role:
            await membro.remove_roles(r)

    await membro.add_roles(role)
    await membro.edit(nick=f"『PRF』{cargo}│{membro.display_name}")

    emb = embed_padrao("📉 REBAIXAMENTO",
        f"""Servidor: {membro.mention}
Novo cargo: {cargo}
Motivo: {motivo}
Autoridade: {i.user.mention}
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}""",
        0xE67E22)

    await i.response.send_message("✅ Rebaixamento registrado.", ephemeral=True)
    await enviar(i.guild, config["canal_folha"], emb)
    await enviar(i.guild, config["canal_logs"], emb)

# =========================
# ADVERTIR
# =========================
@bot.tree.command(name="advertir")
async def advertir(i: discord.Interaction, membro: discord.Member, motivo: str):
    uid = str(membro.id)
    lista = advertencias.get(uid, [])
    lista.append(motivo)
    advertencias[uid] = lista
    salvar_adv()

    if len(lista) >= 3:
        await exonerar(i, membro, "3 advertências acumuladas.")
        advertencias.pop(uid)
        salvar_adv()
        return

    emb = embed_padrao("⚠️ ADVERTÊNCIA",
        f"""Servidor: {membro.mention}
Advertência Nº {len(lista)}
Motivo: {motivo}
Autoridade: {i.user.mention}""",0xF1C40F)

    await i.response.send_message("✅ Advertência aplicada.", ephemeral=True)
    await enviar(i.guild, config["canal_logs"], emb)
    await dm_safe(membro, emb)

# =========================
# EXONERAR
# =========================
@bot.tree.command(name="exonerar")
async def exonerar(i: discord.Interaction, membro: discord.Member, motivo: str):
    civil = i.guild.get_role(CARGO_CIVIL_ID)

    for r in membro.roles:
        if r != i.guild.default_role:
            await membro.remove_roles(r)

    await membro.add_roles(civil)
    await membro.edit(nick=None)

    emb = embed_padrao("🚨 EXONERAÇÃO",
        f"""Servidor: {membro.mention}
Motivo: {motivo}
Autoridade: {i.user.mention}""",0xC0392B)

    await i.response.send_message("✅ Exoneração realizada.", ephemeral=True)
    await enviar(i.guild, config["canal_folha"], emb)
    await enviar(i.guild, config["canal_logs"], emb)
    await dm_safe(membro, emb)

bot.run(os.getenv("DISCORD_TOKEN"))

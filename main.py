# main.py — BOT PRF FINAL PROFISSIONAL
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import os, json

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

ARQ_CONFIG = "config.json"
ARQ_ADV = "advertencias.json"

CARGO_CIVIL_ID = 1443537740821037136
CARGO_PRF_ID = 1443387935700291697


# ---------------- ARQUIVOS ----------------
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


# ---------------- UTIL ----------------
def eh_admin(m):
    return any(r.id in config["admins"] for r in m.roles)

def embed_padrao(titulo, texto, cor):
    e = discord.Embed(title=titulo, description=texto, color=cor)
    e.set_footer(text="PRF • Sistema Oficial")
    return e

async def enviar(guild, canal_id, embed):
    canal = guild.get_channel(canal_id)
    if canal:
        await canal.send(embed=embed)

async def dm(user, embed):
    try:
        await user.send(embed=embed)
    except:
        pass


# ---------------- READY ----------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ BOT PRF ONLINE")


# ---------------- CONFIG ----------------
@bot.tree.command(name="config-admin")
async def config_admin(inter: discord.Interaction, cargo: discord.Role):
    if not inter.user.guild_permissions.administrator:
        return await inter.response.send_message("❌ Apenas administradores.", ephemeral=True)
    if cargo.id not in config["admins"]:
        config["admins"].append(cargo.id)
        salvar_config()
    await inter.response.send_message("✅ Cargo administrativo setado.", ephemeral=True)

@bot.tree.command(name="config-folha")
async def config_folha(inter: discord.Interaction, canal: discord.TextChannel):
    if not inter.user.guild_permissions.administrator:
        return await inter.response.send_message("❌ Apenas administradores.", ephemeral=True)
    config["canal_folha"] = canal.id
    salvar_config()
    await inter.response.send_message("✅ Canal da folha definido.", ephemeral=True)

@bot.tree.command(name="config-logs")
async def config_logs(inter: discord.Interaction, canal: discord.TextChannel):
    if not inter.user.guild_permissions.administrator:
        return await inter.response.send_message("❌ Apenas administradores.", ephemeral=True)
    config["canal_logs"] = canal.id
    salvar_config()
    await inter.response.send_message("✅ Canal de logs definido.", ephemeral=True)


# ---------------- INCORPORAR ----------------
@bot.tree.command(name="incorporar")
async def incorporar(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role, nome_cargo: str):

    if not eh_admin(inter.user):
        return await inter.response.send_message("❌ Sem permissão.", ephemeral=True)

    guild = inter.guild
    prf = guild.get_role(CARGO_PRF_ID)

    for r in membro.roles:
        if r != guild.default_role:
            await membro.remove_roles(r)

    await membro.add_roles(prf, cargo)

    try:
        await membro.edit(nick=f"『PRF』{nome_cargo}│{membro.name}")
    except:
        pass

    texto = (
        "A Polícia Rodoviária Federal torna pública a seguinte INCORPORAÇÃO:\n\n"
        f"👮 **Servidor:** {membro.mention}\n"
        f"🏅 **Cargo:** {nome_cargo}\n"
        f"📌 **Situação:** EFETIVO ATIVO\n"
        f"🧑‍⚖️ **Autoridade:** {inter.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("📋 TERMO OFICIAL DE INCORPORAÇÃO", texto, 0x3498DB)
    await inter.response.send_message("✅ Incorporação realizada.", ephemeral=True)
    await enviar(guild, config["canal_folha"], emb)
    await enviar(guild, config["canal_logs"], emb)
    await dm(membro, emb)


# ---------------- PROMOVER ----------------
@bot.tree.command(name="promover")
async def promover(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role, nome_cargo: str):

    if not eh_admin(inter.user):
        return await inter.response.send_message("❌ Sem permissão.", ephemeral=True)

    for r in membro.roles:
        if r.id != CARGO_PRF_ID:
            await membro.remove_roles(r)

    await membro.add_roles(cargo)

    try:
        await membro.edit(nick=f"『PRF』{nome_cargo}│{membro.name}")
    except:
        pass

    texto = (
        "A Direção da PRF resolve PROMOVER o servidor abaixo:\n\n"
        f"👮 **Servidor:** {membro.mention}\n"
        f"🏅 **Novo Cargo:** {nome_cargo}\n"
        f"🧑‍⚖️ **Autoridade:** {inter.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("📈 ATO DE PROMOÇÃO", texto, 0x2ECC71)
    await inter.response.send_message("✅ Promoção anotada.", ephemeral=True)
    await enviar(inter.guild, config["canal_folha"], emb)
    await dm(membro, emb)


# ---------------- REBAIXAR ----------------
@bot.tree.command(name="rebaixar")
async def rebaixar(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role, nome_cargo: str, motivo: str):

    if not eh_admin(inter.user):
        return await inter.response.send_message("❌ Sem permissão.", ephemeral=True)

    for r in membro.roles:
        if r.id != CARGO_PRF_ID:
            await membro.remove_roles(r)

    await membro.add_roles(cargo)

    try:
        await membro.edit(nick=f"『PRF』{nome_cargo}│{membro.name}")
    except:
        pass

    texto = (
        "A Direção da PRF resolve REBAIXAR o servidor abaixo:\n\n"
        f"👮 **Servidor:** {membro.mention}\n"
        f"🏅 **Novo Cargo:** {nome_cargo}\n"
        f"📄 **Justificativa:** {motivo}\n"
        f"🧑‍⚖️ **Autoridade:** {inter.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("📉 ATO DE REBAIXAMENTO", texto, 0xE67E22)
    await inter.response.send_message("✅ Rebaixamento registrado.", ephemeral=True)
    await enviar(inter.guild, config["canal_folha"], emb)
    await dm(membro, emb)


# ---------------- ADVERTÊNCIA ----------------
@bot.tree.command(name="advertir")
async def advertir(inter: discord.Interaction, membro: discord.Member, motivo: str):

    if not eh_admin(inter.user):
        return await inter.response.send_message("❌ Sem permissão.", ephemeral=True)

    lista = advertencias.get(str(membro.id), [])
    lista.append({"motivo": motivo, "data": datetime.now().strftime("%d/%m/%Y %H:%M")})
    advertencias[str(membro.id)] = lista
    salvar_adv()

    if len(lista) >= 3:
        await exonerar(inter, membro, "Excesso de advertências")
        return

    texto = (
        "A Direção da PRF aplica ADVERTÊNCIA DISCIPLINAR:\n\n"
        f"👮 **Servidor:** {membro.mention}\n"
        f"⚠️ **Advertência Nº:** {len(lista)}\n"
        f"📄 **Motivo:** {motivo}\n"
        f"🧑‍⚖️ **Autoridade:** {inter.user.mention}"
    )

    emb = embed_padrao("⚠️ ADVERTÊNCIA DISCIPLINAR", texto, 0xF1C40F)
    await inter.response.send_message("✅ Advertência aplicada.", ephemeral=True)
    await enviar(inter.guild, config["canal_folha"], emb)
    await dm(membro, emb)


# ---------------- EXONERAR ----------------
@bot.tree.command(name="exonerar")
async def exonerar(inter: discord.Interaction, membro: discord.Member, motivo: str):

    if not eh_admin(inter.user):
        return await inter.response.send_message("❌ Sem permissão.", ephemeral=True)

    civil = inter.guild.get_role(CARGO_CIVIL_ID)

    for r in membro.roles:
        if r != inter.guild.default_role:
            await membro.remove_roles(r)

    await membro.add_roles(civil)

    # Remove nickname
    try:
        await membro.edit(nick=None)
    except:
        pass

    # Zera advertências
    advertencias.pop(str(membro.id), None)
    salvar_adv()

    texto = (
        "A Polícia Rodoviária Federal resolve EXONERAR:\n\n"
        f"👤 **Servidor:** {membro.mention}\n"
        f"📄 **Motivo:** {motivo}\n"
        f"🧑‍⚖️ **Autoridade:** {inter.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("🚨 ATO DE EXONERAÇÃO", texto, 0xC0392B)
    await inter.response.send_message("✅ Exoneração concluída.", ephemeral=True)
    await enviar(inter.guild, config["canal_folha"], emb)
    await dm(membro, emb)


# ---------------- TOKEN ----------------
bot.run(os.getenv("DISCORD_TOKEN"))

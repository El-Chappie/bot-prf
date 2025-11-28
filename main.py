import discord
from discord.ext import commands
from datetime import datetime
import json, os
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Config e outros comandos do seu main.py aqui (sem bot.add_cog(Edital(bot)))

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

# Seus comandos via @bot.tree.command (config-admin, incorporar, promover, etc) aqui
# ... [copie exatamente seus comandos aqui sem alterações] ...

# **IMPORTANTE: NÃO CHAME bot.add_cog(Edital(bot)) AQUI!**

# INÍCIO DO GERENCIAMENTO ASSÍNCRONO PARA CARREGAR EXTENSÕES

async def main():
    async with bot:
        await bot.load_extension("edital")  # Carrega o cog edital.py
        await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())

import discord
from discord.ext import commands
from discord import app_commands
import os, json, traceback
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

print("⏳ INICIANDO BOT...")

# ==========================
# CARREGAR EDITAL (FORÇADO)
# ==========================
COG_PATH = "edital.py"

def carregar_edital():
    if not os.path.exists(COG_PATH):
        print("❌ ERRO CRÍTICO: edital.py NÃO EXISTE.")
        quit()

    try:
        from edital import Edital
        bot.add_cog(Edital(bot))
        print("✅ EDITAL CARREGADO COM SUCESSO.")
    except Exception as e:
        print("❌ ERRO AO CARREGAR edital.py:")
        traceback.print_exc()



@bot.event
async def on_ready():
    try:
        await carregar_edital()
    except:
        pass

    try:
        synced = await bot.tree.sync()
        print(f"✅ SLASH SYNC: {len(synced)} comandos.")
    except Exception as e:
        print("❌ ERRO AO SYNCAR SLASH:")
        traceback.print_exc()

    print(f"🤖 ONLINE COMO {bot.user}")

# ==========================
# RESTANTE DO BOT NORMAL
# ==========================
def carregar(arq, padrao):
    if not os.path.exists(arq):
        with open(arq, "w", encoding="utf-8") as f:
            json.dump(padrao, f)
        return padrao
    with open(arq, "r", encoding="utf-8") as f:
        return json.load(f)

config = carregar("config.json", {"admins": [], "canal_folha": None, "canal_logs": None})
advertencias = carregar("advertencias.json", {})

def salvar_config():
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def salvar_adv():
    with open("advertencias.json", "w", encoding="utf-8") as f:
        json.dump(advertencias, f, indent=4)

def eh_admin(m):
    return any(r.id in config["admins"] for r in m.roles)

# ✅ teste visual
@bot.tree.command(name="ping")
async def ping(i: discord.Interaction):
    await i.response.send_message("🏓 PONG",ephemeral=True)


bot.run(os.getenv("DISCORD_TOKEN"))

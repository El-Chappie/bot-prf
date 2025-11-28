import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import traceback
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

ARQ_CONFIG = "config.json"
ARQ_ADV = "advertencias.json"

def carregar(arq, padrao):
    if not os.path.exists(arq):
        with open(arq, "w", encoding="utf-8") as f:
            json.dump(padrao, f, indent=4, ensure_ascii=False)
        return padrao
    with open(arq, "r", encoding="utf-8") as f:
        return json.load(f)

config = carregar(ARQ_CONFIG, {"admins": [], "canal_folha": None, "canal_logs": None})
advertencias = carregar(ARQ_ADV, {})

def salvar_config():
    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def salvar_adv():
    with open(ARQ_ADV, "w", encoding="utf-8") as f:
        json.dump(advertencias, f, indent=4, ensure_ascii=False)

def eh_admin(membro):
    return any(r.id in config["admins"] for r in membro.roles)

# Função para carregar o cog Edital com tratamento de erro
def carregar_edital():
    try:
        from edital import Edital
    except ModuleNotFoundError:
        print("❌ Arquivo edital.py não encontrado. O bot NÃO vai carregar o Edital.")
        return False
    except Exception:
        print("❌ Erro ao importar edital.py:")
        traceback.print_exc()
        return False

    try:
        bot.add_cog(Edital(bot))
        print("✅ Cog Edital carregado com sucesso.")
        return True
    except Exception:
        print("❌ Erro ao adicionar cog Edital:")
        traceback.print_exc()
        return False

@bot.event
async def on_ready():
    print(f"🤖 Bot logado como {bot.user} (ID: {bot.user.id})")
    sucesso = carregar_edital()

    # Sincronizar comandos slash globalmente (pode demorar até 1 hora para aparecer em todos servidores)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Comandos slash sincronizados: {len(synced)}")
    except Exception:
        print("❌ Erro ao sincronizar comandos slash:")
        traceback.print_exc()

    if not sucesso:
        print("⚠️ ATENÇÃO: Cog Edital NÃO foi carregado!")

# Comando de teste para garantir que o bot está rodando
@bot.tree.command(name="ping", description="Responde pong para testar o bot.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)

# Aqui você deve adicionar os outros comandos do seu main.py, como incorporar, promover, etc.
# Exemplo para comando com app_commands:

@bot.tree.command(name="config-admin", description="Configura um cargo como admin")
@app_commands.describe(cargo="Cargo a ser configurado como admin")
async def config_admin(interaction: discord.Interaction, cargo: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Apenas administradores podem usar.", ephemeral=True)
        return
    if cargo.id not in config["admins"]:
        config["admins"].append(cargo.id)
        salvar_config()
    await interaction.response.send_message(f"✅ Cargo {cargo.name} configurado como admin.", ephemeral=True)

# Roda o bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Variável DISCORD_TOKEN não encontrada no ambiente.")
        exit(1)
    bot.run(token)

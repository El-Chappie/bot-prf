import discord
from discord.ext import commands
from datetime import datetime
import json, os
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# =============================
# CONFIGURAÇÕES
# =============================

ARQ_CONFIG = "config.json"
ARQ_ADV = "advertencias.json"

CARGO_CIVIL_ID = 1443537740821037136
CARGO_PRF_ID = 1443387935700291697


# =============================
# FUNÇÕES UTILITÁRIAS
# =============================

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


# =============================
# EVENTOS
# =============================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ BOT ONLINE — {bot.user}")


# =============================
# COMANDOS ADMINISTRATIVOS
# =============================

@bot.tree.command(name="addadmin", description="Adicionar administrador do sistema")
async def addadmin(interaction: discord.Interaction, membro: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    if membro.id not in config["admins"]:
        config["admins"].append(membro.id)
        salvar_config()
        await interaction.response.send_message(f"✅ {membro.mention} agora é admin.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Usuário já é admin.", ephemeral=True)


@bot.tree.command(name="setcanallogs", description="Definir canal de logs do sistema")
async def setlog(interaction: discord.Interaction, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    config["canal_logs"] = canal.id
    salvar_config()
    await interaction.response.send_message("✅ Canal de logs definido.", ephemeral=True)


@bot.tree.command(name="setcanalfolha", description="Canal da folha de oficiais")
async def setfolha(interaction: discord.Interaction, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    config["canal_folha"] = canal.id
    salvar_config()
    await interaction.response.send_message("✅ Canal da folha definido.", ephemeral=True)


# =============================
# SISTEMA DE PROMOÇÕES
# =============================

@bot.tree.command(name="promover", description="Promover policial")
async def promover(interaction: discord.Interaction, membro: discord.Member, nova_patente: str):

    if not eh_admin(interaction.user):
        return await interaction.response.send_message("❌ Acesso negado.", ephemeral=True)

    embed = embed_padrao(
        "📜 ATO ADMINISTRATIVO DE PROMOÇÃO",
        f"A Superintendência da Polícia Rodoviária Federal comunica que o(a) servidor(a) "
        f"{membro.mention} foi oficialmente promovido(a).\n\n"
        f"🎖 Nova patente: **{nova_patente}**\n"
        f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        0x16a34a
    )

    await enviar(interaction.guild, config.get("canal_folha"), embed)
    await interaction.response.send_message("✅ Promoção registrada oficialmente.", ephemeral=True)

# =============================
# SISTEMA DE REGISTRO
# =============================

@bot.tree.command(name="registrar", description="Registrar um novo policial")
async def registrar(interaction: discord.Interaction, membro: discord.Member, patente: str):

    if not eh_admin(interaction.user):
        return await interaction.response.send_message("❌ Acesso negado.", ephemeral=True)

    cargo_prf = interaction.guild.get_role(CARGO_PRF_ID)
    cargo_civil = interaction.guild.get_role(CARGO_CIVIL_ID)

    if not cargo_prf:
        return await interaction.response.send_message("❌ Cargo PRF não encontrado.", ephemeral=True)

    await membro.add_roles(cargo_prf)
    if cargo_civil:
        await membro.remove_roles(cargo_civil)

    embed = embed_padrao(
        "📑 REGISTRO OFICIAL",
        f"A Superintendência da Polícia Rodoviária Federal informa que o(a) cidadão(ã) {membro.mention} "
        f"foi oficialmente incorporado(a) ao efetivo da PRF.\n\n"
        f"📛 Patente inicial: **{patente}**\n"
        f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        0x2563eb
    )

    await enviar(interaction.guild, config.get("canal_folha"), embed)
    await interaction.response.send_message("✅ Registro efetuado com êxito.", ephemeral=True)

# =============================
# SISTEMA DE EXONERACAO
# =============================

@bot.tree.command(name="exonerar", description="Exonerar policial da PRF")
async def exonerar(interaction: discord.Interaction, membro: discord.Member, motivo: str):

    if not eh_admin(interaction.user):
        return await interaction.response.send_message("❌ Acesso negado.", ephemeral=True)

    cargo_prf = interaction.guild.get_role(CARGO_PRF_ID)
    cargo_civil = interaction.guild.get_role(CARGO_CIVIL_ID)

    if cargo_prf:
        await membro.remove_roles(cargo_prf)
    if cargo_civil:
        await membro.add_roles(cargo_civil)

    embed = embed_padrao(
        "📕 ATO DE EXONERAÇÃO",
        f"A Superintendência da Polícia Rodoviária Federal comunica que o(a) servidor(a) "
        f"{membro.mention} foi oficialmente exonerado(a) da corporação.\n\n"
        f"📄 Motivo: {motivo}\n"
        f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        0xdc2626
    )

    await enviar(interaction.guild, config.get("canal_folha"), embed)
    await interaction.response.send_message("✅ Exoneração registrada oficialmente.", ephemeral=True)

# =============================
# SISTEMA DE REBAIXAMENTO
# =============================

@bot.tree.command(name="rebaixar", description="Rebaixar policial")
async def rebaixar(interaction: discord.Interaction, membro: discord.Member, nova_patente: str, motivo: str):

    if not eh_admin(interaction.user):
        return await interaction.response.send_message("❌ Acesso negado.", ephemeral=True)

    embed = embed_padrao(
        "📉 ATO ADMINISTRATIVO DE REBAIXAMENTO",
        f"A Superintendência da Polícia Rodoviária Federal informa que o(a) servidor(a) "
        f"{membro.mention} teve sua patente revista por decisão administrativa.\n\n"
        f"🎖 Nova patente: **{nova_patente}**\n"
        f"📄 Motivo: {motivo}\n"
        f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        0xf59e0b
    )

    await enviar(interaction.guild, config.get("canal_folha"), embed)
    await interaction.response.send_message("✅ Rebaixamento registrado oficialmente.", ephemeral=True)



# =============================
# SISTEMA DE ADVERTÊNCIAS
# =============================

@bot.tree.command(name="advertir", description="Registrar advertência administrativa")
async def advertir(interaction: discord.Interaction, membro: discord.Member, motivo: str):

    if not eh_admin(interaction.user):
        return await interaction.response.send_message("❌ Acesso negado.", ephemeral=True)

    uid = str(membro.id)

    if uid not in advertencias:
        advertencias[uid] = []

    registro = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "motivo": motivo,
        "aplicador": interaction.user.name
    }

    advertencias[uid].append(registro)
    salvar_adv()

    total = len(advertencias[uid])

    embed = embed_padrao(
        "📄 REGISTRO OFICIAL DE ADVERTÊNCIA",
        f"A Superintendência da Polícia Rodoviária Federal informa que o(a) servidor(a) {membro.mention} "
        f"recebeu uma advertência administrativa interna, conforme os termos a seguir:\n\n"
        f"📌 Fundamentação: {motivo}\n"
        f"👮 Aplicador: {interaction.user.name}\n"
        f"📅 Data: {registro['data']}\n"
        f"📂 Total de advertências: {total}",
        0xf97316
    )

    await enviar(interaction.guild, config.get("canal_logs"), embed)
    await interaction.response.send_message("✅ Advertência registrada com sucesso.", ephemeral=True)



@bot.tree.command(name="veradv", description="Consultar histórico disciplinar de um servidor")
async def veradv(interaction: discord.Interaction, membro: discord.Member):

    if not eh_admin(interaction.user):
        return await interaction.response.send_message("❌ Acesso negado.", ephemeral=True)

    uid = str(membro.id)

    if uid not in advertencias or not advertencias[uid]:
        return await interaction.response.send_message("✅ Nenhuma advertência registrada.", ephemeral=True)

    texto = ""
    for i, adv in enumerate(advertencias[uid], 1):
        texto += (
            f"#{i}\n"
            f"📅 Data: {adv['data']}\n"
            f"📄 Motivo: {adv['motivo']}\n"
            f"👮 Aplicador: {adv['aplicador']}\n\n"
        )

    embed = embed_padrao(
        "📂 HISTÓRICO DISCIPLINAR",
        f"Servidor: {membro.mention}\n\n{texto}",
        0x9333ea
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)



# =============================
# INICIALIZAÇÃO EM MODO SEGURO
# =============================

async def main():
    async with bot:
        await bot.load_extension("edital")  # CARREGA edital.py
        await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())

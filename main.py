import discord
from discord.ext import commands
from datetime import datetime
import json, os, asyncio

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
# FUNÇÕES DE ARQUIVO
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

def eh_admin(usuario):
    return usuario.id in config["admins"] or usuario.guild_permissions.administrator

def embed_padrao(titulo, texto, cor=0x1f2937):
    e = discord.Embed(title=titulo, description=texto, color=cor)
    e.set_footer(text="Polícia Rodoviária Federal • Sistema Oficial")
    return e

async def enviar(guild, canal_id, embed):
    if canal_id:
        canal = guild.get_channel(canal_id)
        if canal:
            await canal.send(embed=embed)

# =============================
# INICIALIZAÇÃO
# =============================

@bot.event
async def on_ready():
    if bot.application.owner and bot.application.owner.id not in config["admins"]:
        config["admins"].append(bot.application.owner.id)
        salvar_config()

    await bot.tree.sync()
    print(f"✅ BOT PRF ONLINE — {bot.user}")

# =============================
# ADMINISTRAÇÃO
# =============================

@bot.tree.command(name="addadmin", description="Adicionar administrador ao sistema PRF")
async def addadmin(interaction: discord.Interaction, usuario: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Apenas administradores do servidor podem executar este comando.", ephemeral=True)

    if usuario.id not in config["admins"]:
        config["admins"].append(usuario.id)
        salvar_config()
        await interaction.response.send_message(f"O servidor **{usuario}** foi oficialmente autorizado como administrador do sistema PRF.", ephemeral=True)
    else:
        await interaction.response.send_message("Este servidor já possui autorização administrativa.", ephemeral=True)


@bot.tree.command(name="setcanalfolha", description="Definir canal da folha oficial da PRF")
async def setfolha(interaction: discord.Interaction, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Permissão negada.", ephemeral=True)

    config["canal_folha"] = canal.id
    salvar_config()
    await interaction.response.send_message(f"O canal {canal.mention} foi oficialmente definido como folha administrativa.", ephemeral=True)


@bot.tree.command(name="setcanallogs", description="Definir canal de logs administrativos")
async def setlogs(interaction: discord.Interaction, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Permissão negada.", ephemeral=True)

    config["canal_logs"] = canal.id
    salvar_config()
    await interaction.response.send_message(f"O canal {canal.mention} foi definido como central de registros internos.", ephemeral=True)

# =============================
# REGISTRO
# =============================

@bot.tree.command(name="registrar", description="Registrar novo policial PRF")
async def registrar(interaction: discord.Interaction, usuario: discord.Member, cargo: discord.Role, nick: str):
    if not eh_admin(interaction.user):
        return await interaction.response.send_message("Acesso administrativo não autorizado.", ephemeral=True)

    cargo_prf = interaction.guild.get_role(CARGO_PRF_ID)
    cargo_civil = interaction.guild.get_role(CARGO_CIVIL_ID)

    nome = f"『PRF』{cargo.name}│{nick}"

    try:
        await usuario.edit(nick=nome)
    except:
        pass

    if cargo_prf:
        await usuario.add_roles(cargo_prf)
    await usuario.add_roles(cargo)

    if cargo_civil:
        await usuario.remove_roles(cargo_civil)

    embed = embed_padrao(
        "📑 ATO OFICIAL DE INCORPORAÇÃO",
        f"A Superintendência da Polícia Rodoviária Federal comunica que o(a) cidadão(ã) {usuario.mention} "
        f"foi oficialmente incorporado(a) ao efetivo da corporação.\n\n"
        f"🎖 Cargo: {cargo.mention}\n"
        f"🪪 Nome de serviço: {nome}\n"
        f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        0x2563eb
    )

    await enviar(interaction.guild, config["canal_folha"], embed)
    await interaction.response.send_message("Registro efetuado com êxito.", ephemeral=True)

# =============================
# PROMOÇÃO
# =============================

@bot.tree.command(name="promover", description="Promover policial PRF")
async def promover(interaction: discord.Interaction, usuario: discord.Member, cargo: discord.Role):
    if not eh_admin(interaction.user):
        return await interaction.response.send_message("Acesso negado.", ephemeral=True)

    await usuario.add_roles(cargo)

    embed = embed_padrao(
        "📜 ATO DE PROMOÇÃO",
        f"O servidor {usuario.mention} foi oficialmente promovido para o cargo {cargo.mention}.\n\n"
        f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        0x16a34a
    )

    await enviar(interaction.guild, config["canal_folha"], embed)
    await interaction.response.send_message("Promoção registrada oficialmente.", ephemeral=True)

# =============================
# REBAIXAMENTO
# =============================

@bot.tree.command(name="rebaixar", description="Rebaixar policial PRF")
async def rebaixar(interaction: discord.Interaction, usuario: discord.Member, cargo_antigo: discord.Role, cargo_novo: discord.Role, motivo: str):
    if not eh_admin(interaction.user):
        return await interaction.response.send_message("Acesso negado.", ephemeral=True)

    await usuario.remove_roles(cargo_antigo)
    await usuario.add_roles(cargo_novo)

    embed = embed_padrao(
        "📉 ATO ADMINISTRATIVO DE REBAIXAMENTO",
        f"O servidor {usuario.mention} teve seu cargo alterado oficialmente.\n\n"
        f"🔻 Cargo anterior: {cargo_antigo.mention}\n"
        f"🔺 Cargo atual: {cargo_novo.mention}\n"
        f"📄 Fundamentação administrativa: {motivo}\n"
        f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        0xf59e0b
    )

    await enviar(interaction.guild, config["canal_folha"], embed)
    await interaction.response.send_message("Rebaixamento registrado oficialmente.", ephemeral=True)

# =============================
# EXONERAÇÃO
# =============================

@bot.tree.command(name="exonerar", description="Exonerar policial PRF")
async def exonerar(interaction: discord.Interaction, usuario: discord.Member, motivo: str):
    if not eh_admin(interaction.user):
        return await interaction.response.send_message("Acesso negado.", ephemeral=True)

    cargo_prf = interaction.guild.get_role(CARGO_PRF_ID)
    cargo_civil = interaction.guild.get_role(CARGO_CIVIL_ID)

    if cargo_prf:
        await usuario.remove_roles(cargo_prf)
    if cargo_civil:
        await usuario.add_roles(cargo_civil)

    embed = embed_padrao(
        "📕 ATO FORMAL DE EXONERAÇÃO",
        f"O servidor {usuario.mention} foi oficialmente desligado da Polícia Rodoviária Federal.\n\n"
        f"📄 Motivação administrativa: {motivo}\n"
        f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        0xc81e1e
    )

    await enviar(interaction.guild, config["canal_folha"], embed)
    await interaction.response.send_message("Exoneração processada oficialmente.", ephemeral=True)

# =============================
# ADVERTÊNCIA
# =============================

@bot.tree.command(name="advertir", description="Aplicar advertência administrativa")
async def advertir(interaction: discord.Interaction, usuario: discord.Member, fundamento: str):
    if not eh_admin(interaction.user):
        return await interaction.response.send_message("Acesso administrativo não autorizado.", ephemeral=True)

    uid = str(usuario.id)

    if uid not in advertencias:
        advertencias[uid] = []

    registro = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "fundamento": fundamento,
        "responsavel": interaction.user.name
    }

    advertencias[uid].append(registro)
    salvar_adv()

    embed = embed_padrao(
        "📄 REGISTRO DISCIPLINAR",
        f"O servidor {usuario.mention} recebeu advertência administrativa formal.\n\n"
        f"📜 Fundamentação legal: {fundamento}\n"
        f"👮 Autoridade responsável: {interaction.user.name}\n"
        f"📅 Data: {registro['data']}\n"
        f"📂 Ocorrências registradas: {len(advertencias[uid])}",
        0xf97316
    )

    await enviar(interaction.guild, config["canal_logs"], embed)
    await interaction.response.send_message("Advertência aplicada com sucesso.", ephemeral=True)

# =============================
# CONSULTA DE ADVERTÊNCIAS
# =============================

@bot.tree.command(name="veradv", description="Consultar ficha disciplinar")
async def veradv(interaction: discord.Interaction, usuario: discord.Member):
    if not eh_admin(interaction.user):
        return await interaction.response.send_message("Acesso restrito.", ephemeral=True)

    uid = str(usuario.id)

    if uid not in advertencias:
        return await interaction.response.send_message("Não há registros disciplinares para este servidor.", ephemeral=True)

    texto = ""
    for i, adv in enumerate(advertencias[uid], 1):
        texto += (
            f"#{i}\n"
            f"📅 Data: {adv['data']}\n"
            f"📜 Fundamentação: {adv['fundamento']}\n"
            f"👮 Responsável: {adv['responsavel']}\n\n"
        )

    embed = embed_padrao("📂 FICHA ADMINISTRATIVA", f"Servidor: {usuario.mention}\n\n{texto}", 0x9333ea)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# =============================
# INICIALIZAÇÃO
# =============================

async def main():
    async with bot: 
        await bot.load_extension("edital") # CARREGA edital.py 
        await bot.start(os.getenv("DISCORD_TOKEN")) 
asyncio.run(main())

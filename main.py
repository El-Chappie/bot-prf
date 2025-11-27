import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = "COLOQUE_SEU_TOKEN_AQUI"

# HIERARQUIA OFICIAL PRF
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

def get_cargo(membro):
    for role in membro.roles:
        if role.name in HIERARQUIA:
            return role.name
    return "CIVIL"

def pode_promover(autor, alvo):
    return HIERARQUIA.index(get_cargo(autor)) < HIERARQUIA.index(get_cargo(alvo))

async def setar_cargo(membro, novo_cargo):
    for role in membro.roles:
        if role.name in HIERARQUIA:
            await membro.remove_roles(role)

    role = discord.utils.get(membro.guild.roles, name=novo_cargo)
    if role:
        await membro.add_roles(role)

def embed_padrao(titulo, desc, cor=0x0C7BDC):
    emb = discord.Embed(title=titulo, description=desc, color=cor)
    emb.set_footer(text="Polícia Rodoviária Federal • Sistema Oficial")
    return emb

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ BOT PRF ONLINE")

# REGISTRAR
@bot.tree.command(name="registrar")
@app_commands.describe(membro="Usuário a registrar")
async def registrar(inter: discord.Interaction, membro: discord.Member):
    await setar_cargo(membro, "ALUNO FEDERAL")
    emb = embed_padrao("📋 REGISTRO EFETUADO", f"{membro.mention} agora é **ALUNO FEDERAL**.")
    await inter.response.send_message(embed=emb)

# PROMOVER
@bot.tree.command(name="promover")
@app_commands.describe(membro="Usuário", cargo="Novo cargo")
async def promover(inter: discord.Interaction, membro: discord.Member, cargo: str):
    cargo = cargo.upper()

    if cargo not in HIERARQUIA:
        await inter.response.send_message("❌ Cargo inválido.")
        return

    if not pode_promover(inter.user, membro):
        await inter.response.send_message("❌ Você não pode promover alguém de patente igual ou superior.")
        return

    await setar_cargo(membro, cargo)

    emb = embed_padrao(
        "📈 PROMOÇÃO NA PRF",
        f"**Membro:** {membro.mention}\n"
        f"**Novo cargo:** {cargo}\n"
        f"**Autoridade:** {inter.user.mention}\n"
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    await inter.response.send_message(embed=emb)

# REBAIXAR
@bot.tree.command(name="rebaixar")
@app_commands.describe(membro="Usuário", cargo="Novo cargo", motivo="Motivo")
async def rebaixar(inter: discord.Interaction, membro: discord.Member, cargo: str, motivo: str):
    cargo = cargo.upper()

    await setar_cargo(membro, cargo)

    emb = embed_padrao(
        "📉 REBAIXAMENTO",
        f"**Membro:** {membro.mention}\n"
        f"**Novo cargo:** {cargo}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}",
        cor=0xE67E22
    )
    await inter.response.send_message(embed=emb)

# ADVERTIR
@bot.tree.command(name="advertir")
@app_commands.describe(membro="Usuário", motivo="Motivo")
async def advertir(inter: discord.Interaction, membro: discord.Member, motivo: str):
    emb = embed_padrao(
        "⚠ ADVERTÊNCIA DISCIPLINAR",
        f"**Membro:** {membro.mention}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}",
        cor=0xF1C40F
    )
    await inter.response.send_message(embed=emb)

# EXONERAR
@bot.tree.command(name="exonerar")
@app_commands.describe(membro="Usuário", motivo="Motivo")
async def exonerar(inter: discord.Interaction, membro: discord.Member, motivo: str):
    await setar_cargo(membro, "CIVIL")

    emb = embed_padrao(
        "🚨 EXONERAÇÃO",
        f"**Membro:** {membro.mention}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}",
        cor=0xC0392B
    )
    await inter.response.send_message(embed=emb)

bot.run(TOKEN)

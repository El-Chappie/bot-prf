import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# === CARGOS AUTORIZADOS (NOME EXATO COMO NO DISCORD) ===
AUTORIDADES = [
    "DIRETOR GERAL",
    "DIRETOR EXECUTIVO",
    "DIRETOR DE OPERAÇÕES",
    "DIRETOR DE INTELIGÊNCIA",
    "SUPERINTENDENTE EXECUTIVO",
    "SUPERINTENDENTE REGIONAL",
    "DELEGADO GERAL",
    "DELEGADO EXECUTIVO"
]

# === TODOS OS CARGOS DA PRF (INCLUINDO CIVIL) ===
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

def eh_autoridade(membro: discord.Member):
    return any(role.name.upper() in AUTORIDADES for role in membro.roles)

def cargo_prf(membro: discord.Member):
    for role in membro.roles:
        if role.name in HIERARQUIA:
            return role
    return None

async def setar_cargo(membro: discord.Member, novo_cargo: discord.Role):
    # Remove cargos PRF antigos
    for role in membro.roles:
        if role.name in HIERARQUIA:
            await membro.remove_roles(role)

    # Adiciona novo cargo
    await membro.add_roles(novo_cargo)

def embed_padrao(titulo, desc, cor):
    emb = discord.Embed(title=titulo, description=desc, color=cor)
    emb.set_footer(text="POLÍCIA RODOVIÁRIA FEDERAL • SISTEMA OFICIAL")
    return emb

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ BOT PRF ONLINE")

# ========= REGISTRO =========
@bot.tree.command(name="registrar", description="Registrar membro na corporação")
@app_commands.describe(membro="Usuário", cargo="Cargo do servidor")
async def registrar(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role):

    if not eh_autoridade(inter.user):
        await inter.response.send_message("❌ Você não tem autorização para registrar.", ephemeral=True)
        return

    if cargo.name not in HIERARQUIA:
        await inter.response.send_message("❌ Este cargo não é da PRF.", ephemeral=True)
        return

    await setar_cargo(membro, cargo)

    emb = embed_padrao("📋 REGISTRO EFETUADO",
        f"**Membro:** {membro.mention}\n"
        f"**Cargo atribuído:** {cargo.mention}\n"
        f"**Registrado por:** {inter.user.mention}\n"
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        0x3498DB
    )

    await inter.response.send_message(embed=emb)

# ========= PROMOVER =========
@bot.tree.command(name="promover", description="Promover membro")
@app_commands.describe(membro="Usuário", cargo="Novo cargo")
async def promover(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role):

    if not eh_autoridade(inter.user):
        await inter.response.send_message("❌ Você não tem autorização para promover.", ephemeral=True)
        return

    if cargo.name not in HIERARQUIA:
        await inter.response.send_message("❌ Cargo inválido.", ephemeral=True)
        return

    await setar_cargo(membro, cargo)

    emb = embed_padrao("📈 PROMOÇÃO",
        f"**Membro:** {membro.mention}\n"
        f"**Novo cargo:** {cargo.mention}\n"
        f"**Autoridade:** {inter.user.mention}\n"
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        0x2ECC71
    )

    await inter.response.send_message(embed=emb)

# ========= REBAIXAR =========
@bot.tree.command(name="rebaixar", description="Rebaixar membro")
@app_commands.describe(membro="Usuário", cargo="Novo cargo", motivo="Motivo")
async def rebaixar(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role, motivo: str):

    if not eh_autoridade(inter.user):
        await inter.response.send_message("❌ Você não tem autorização para rebaixar.", ephemeral=True)
        return

    await setar_cargo(membro, cargo)

    emb = embed_padrao("📉 REBAIXAMENTO",
        f"**Membro:** {membro.mention}\n"
        f"**Novo cargo:** {cargo.mention}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}",
        0xE67E22
    )

    await inter.response.send_message(embed=emb)

# ========= ADVERTÊNCIA =========
@bot.tree.command(name="advertir", description="Advertir membro")
@app_commands.describe(membro="Usuário", motivo="Motivo")
async def advertir(inter: discord.Interaction, membro: discord.Member, motivo: str):

    if not eh_autoridade(inter.user):
        await inter.response.send_message("❌ Você não tem autorização.", ephemeral=True)
        return

    emb = embed_padrao("⚠ ADVERTÊNCIA DISCIPLINAR",
        f"**Membro:** {membro.mention}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}",
        0xF1C40F
    )

    await inter.response.send_message(embed=emb)

# ========= EXONERAR =========
@bot.tree.command(name="exonerar", description="Exonerar membro")
@app_commands.describe(membro="Usuário", motivo="Motivo")
async def exonerar(inter: discord.Interaction, membro: discord.Member, motivo: str):

    if not eh_autoridade(inter.user):
        await inter.response.send_message("❌ Você não tem autorização para exonerar.", ephemeral=True)
        return

    cargo_civil = discord.utils.get(membro.guild.roles, name="CIVIL")
    if not cargo_civil:
        await inter.response.send_message("❌ Cargo CIVIL não existe.", ephemeral=True)
        return

    await setar_cargo(membro, cargo_civil)

    emb = embed_padrao("🚨 EXONERAÇÃO",
        f"**Membro:** {membro.mention}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}",
        0xC0392B
    )

    await inter.response.send_message(embed=emb)

# ========= INICIALIZA =========
import os
bot.run(os.getenv("DISCORD_TOKEN"))

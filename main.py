# main.py — BOT PRF (incorporar @user @role cargo nome) - com verificação EFETIVO
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import os, json, traceback

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

edital_cog = EditalCog(bot)
bot.add_cog(edital_cog)

# Depois configure com seus IDs reais
edital_cog.configurar(
    diretor_roles=[1443387926196260965],
    canal_logs_id=1443619642496258260,
    canal_anuncios_id=1443388062171271339
)

ARQ_CONFIG = "config.json"
ARQ_ADV = "advertencias.json"

# IDs fixos (já fornecidos)
CARGO_CIVIL_ID = 1443537740821037136
CARGO_PRF_ID = 1443387935700291697

# ----------------------------------------
# Helpers para arquivos
# ----------------------------------------
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

# ----------------------------------------
# Utilitários
# ----------------------------------------
def eh_admin(membro: discord.Member) -> bool:
    return any(r.id in config.get("admins", []) for r in membro.roles)

def embed_padrao(titulo: str, texto: str, cor: int = 0x2F3136) -> discord.Embed:
    emb = discord.Embed(title=titulo, description=texto, color=cor)
    emb.set_footer(text="PRF • Sistema Oficial")
    return emb

async def enviar(guild: discord.Guild, canal_id: int, embed: discord.Embed):
    if not canal_id:
        return
    canal = guild.get_channel(canal_id)
    if canal:
        await canal.send(embed=embed)
    else:
        # tenta buscar por API se não estiver em cache
        try:
            canal = await bot.fetch_channel(canal_id)
            if canal:
                await canal.send(embed=embed)
        except Exception:
            print("Erro ao enviar embed: canal não encontrado / sem permissão")

async def dm_safe(user: discord.Member, embed: discord.Embed):
    try:
        await user.send(embed=embed)
    except Exception:
        pass

# ----------------------------------------
# Ready
# ----------------------------------------
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception:
        pass
    print(f"✅ BOT PRF ONLINE — {bot.user}")

# ----------------------------------------
# Config commands
# ----------------------------------------
@bot.tree.command(name="config-admin", description="Define cargo administrativo (menção)")
async def config_admin(inter: discord.Interaction, cargo: discord.Role):
    if not inter.user.guild_permissions.administrator:
        return await inter.response.send_message("❌ Apenas administradores do servidor.", ephemeral=True)
    if cargo.id not in config["admins"]:
        config["admins"].append(cargo.id)
        salvar_config()
    await inter.response.send_message(f"✅ Cargo {cargo.mention} adicionado como ADMIN do sistema.", ephemeral=True)

@bot.tree.command(name="config-folha", description="Define o canal da folha da PRF")
async def config_folha(inter: discord.Interaction, canal: discord.TextChannel):
    if not inter.user.guild_permissions.administrator:
        return await inter.response.send_message("❌ Apenas administradores.", ephemeral=True)
    config["canal_folha"] = canal.id
    salvar_config()
    await inter.response.send_message(f"✅ Canal da folha definido: {canal.mention}", ephemeral=True)

@bot.tree.command(name="config-logs", description="Define o canal de logs da PRF")
async def config_logs(inter: discord.Interaction, canal: discord.TextChannel):
    if not inter.user.guild_permissions.administrator:
        return await inter.response.send_message("❌ Apenas administradores.", ephemeral=True)
    config["canal_logs"] = canal.id
    salvar_config()
    await inter.response.send_message(f"✅ Canal de logs definido: {canal.mention}", ephemeral=True)

# ----------------------------------------
# INCORPORAR — formato exigido:
# /incorporar @user @role cargo nome
# ----------------------------------------
@bot.tree.command(name="incorporar", description="Incorporar servidor à PRF — /incorporar @user @role cargo nome")
@app_commands.describe(
    membro="Usuário a ser incorporado (menção)",
    role="Role a ser aplicado (menção)",
    cargo_text="Nome do cargo (texto para nickname)",
    nome="Nome funcional a aplicar no nickname"
)
async def incorporar(inter: discord.Interaction, membro: discord.Member, role: discord.Role, cargo_text: str, nome: str):
    if not eh_admin(inter.user):
        return await inter.response.send_message("❌ Você não possui autorização.", ephemeral=True)

    guild = inter.guild
    prf_role = guild.get_role(CARGO_PRF_ID)
    civil_role = guild.get_role(CARGO_CIVIL_ID)

    if not prf_role:
        return await inter.response.send_message("❌ Cargo PRF EFETIVO não encontrado no servidor.", ephemeral=True)

    # Remove todos os cargos (exceto @everyone)
    try:
        remove_list = [r for r in membro.roles if r != guild.default_role]
        if remove_list:
            await membro.remove_roles(*remove_list, reason=f"Incorporação por {inter.user}")
    except Exception:
        print("⚠️ Falha ao remover roles antes de incorporar:", traceback.format_exc())

    # Adiciona PRF EFETIVO + role mencionado
    try:
        await membro.add_roles(prf_role, role, reason=f"Incorporação por {inter.user}")
    except Exception:
        return await inter.response.send_message("❌ Erro ao aplicar cargos. Verifique permissões do bot (Manage Roles & posição do cargo).", ephemeral=True)

    # Monta nick no padrão: 『PRF』Cargo│Nome
    novo_nick = f"『PRF』{cargo_text}│{nome}"
    try:
        await membro.edit(nick=novo_nick, reason="Incorporação PRF")
    except Exception:
        # não falhar o comando se não puder renomear (permissão/cargo acima)
        print("⚠️ Falha ao editar nick:", traceback.format_exc())

    # Mensagem formal
    texto = (
        "A Polícia Rodoviária Federal torna pública a seguinte INCORPORAÇÃO:\n\n"
        f"👮 **Servidor:** {membro.mention}\n"
        f"🏅 **Cargo funcional:** {cargo_text}\n"
        f"🆔 **Role aplicado:** {role.mention}\n"
        f"📌 **Situação:** EFETIVO ATIVO\n"
        f"🧑‍⚖️ **Autoridade:** {inter.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("📋 TERMO OFICIAL DE INCORPORAÇÃO", texto, 0x3498DB)

    await inter.response.send_message("✅ Incorporação realizada com sucesso.", ephemeral=True)
    await enviar(guild, config.get("canal_folha"), emb)
    await enviar(guild, config.get("canal_logs"), emb)
    await dm_safe(membro, emb)

# ----------------------------------------
# PROMOVER — exige @role + cargo_text (para nick)
# /promover @user @role cargo_text
# ----------------------------------------
@bot.tree.command(name="promover", description="Promover servidor — /promover @user @role cargo_text")
@app_commands.describe(
    membro="Usuário a promover (menção)",
    role="Role a aplicar (menção)",
    cargo_text="Nome do cargo (texto para nickname)"
)
async def promover(inter: discord.Interaction, membro: discord.Member, role: discord.Role, cargo_text: str):
    if not eh_admin(inter.user):
        return await inter.response.send_message("❌ Sem permissão.", ephemeral=True)

    guild = inter.guild
    prf_role = guild.get_role(CARGO_PRF_ID)

    # Verifica se é servidor registrado (possui PRF EFETIVO)
    if not prf_role or prf_role not in membro.roles:
        return await inter.response.send_message("❌ Usuário não é um servidor registrado (não possui cargo EFETIVO).", ephemeral=True)

    # Remove roles PRF (mantém apenas efetivo se quiser), aqui removemos todos exceto default and prf
    try:
        remove_list = [r for r in membro.roles if r != guild.default_role and r.id != CARGO_PRF_ID]
        if remove_list:
            await membro.remove_roles(*remove_list, reason=f"Promoção por {inter.user}")
    except Exception:
        print("⚠️ Falha ao remover roles antes da promoção:", traceback.format_exc())

    try:
        await membro.add_roles(role, reason=f"Promoção por {inter.user}")
    except Exception:
        return await inter.response.send_message("❌ Erro ao aplicar cargo de promoção. Verifique permissões.", ephemeral=True)

    # Atualiza nick
    novo_nick = f"『PRF』{cargo_text}│{membro.display_name}"
    try:
        await membro.edit(nick=novo_nick, reason="Promoção PRF")
    except Exception:
        print("⚠️ Falha ao editar nick na promoção:", traceback.format_exc())

    texto = (
        "A Direção da PRF resolve PROMOVER o servidor abaixo:\n\n"
        f"👮 **Servidor:** {membro.mention}\n"
        f"🏅 **Novo cargo:** {cargo_text}\n"
        f"🆔 **Role aplicado:** {role.mention}\n"
        f"🧑‍⚖️ **Autoridade:** {inter.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("📈 ATO DE PROMOÇÃO", texto, 0x2ECC71)
    await inter.response.send_message("✅ Promoção registrada.", ephemeral=True)
    await enviar(guild, config.get("canal_folha"), emb)
    await enviar(guild, config.get("canal_logs"), emb)
    await dm_safe(membro, emb)

# ----------------------------------------
# REBAIXAR — exige @role + cargo_text + motivo
# /rebaixar @user @role cargo_text motivo
# ----------------------------------------
@bot.tree.command(name="rebaixar", description="Rebaixar servidor — /rebaixar @user @role cargo_text motivo")
@app_commands.describe(
    membro="Usuário a rebaixar (menção)",
    role="Role a aplicar (menção)",
    cargo_text="Novo nome do cargo (texto para nickname)",
    motivo="Motivo do rebaixamento"
)
async def rebaixar(inter: discord.Interaction, membro: discord.Member, role: discord.Role, cargo_text: str, motivo: str):
    if not eh_admin(inter.user):
        return await inter.response.send_message("❌ Sem permissão.", ephemeral=True)

    guild = inter.guild
    prf_role = guild.get_role(CARGO_PRF_ID)

    # Verifica se é servidor registrado (possui PRF EFETIVO)
    if not prf_role or prf_role not in membro.roles:
        return await inter.response.send_message("❌ Usuário não é um servidor registrado (não possui cargo EFETIVO).", ephemeral=True)

    try:
        remove_list = [r for r in membro.roles if r != guild.default_role and r.id != CARGO_PRF_ID]
        if remove_list:
            await membro.remove_roles(*remove_list, reason=f"Rebaixamento por {inter.user}")
    except Exception:
        print("⚠️ Falha ao remover roles antes do rebaixamento:", traceback.format_exc())

    try:
        await membro.add_roles(role, reason=f"Rebaixamento por {inter.user}")
    except Exception:
        return await inter.response.send_message("❌ Erro ao aplicar cargo de rebaixamento. Verifique permissões.", ephemeral=True)

    novo_nick = f"『PRF』{cargo_text}│{membro.display_name}"
    try:
        await membro.edit(nick=novo_nick, reason="Rebaixamento PRF")
    except Exception:
        print("⚠️ Falha ao editar nick no rebaixamento:", traceback.format_exc())

    texto = (
        "A Direção da PRF resolve REBAIXAR o servidor abaixo:\n\n"
        f"👮 **Servidor:** {membro.mention}\n"
        f"🏅 **Novo cargo:** {cargo_text}\n"
        f"📄 **Motivo:** {motivo}\n"
        f"🧑‍⚖️ **Autoridade:** {inter.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("📉 ATO DE REBAIXAMENTO", texto, 0xE67E22)
    await inter.response.send_message("✅ Rebaixamento registrado.", ephemeral=True)
    await enviar(guild, config.get("canal_folha"), emb)
    await enviar(guild, config.get("canal_logs"), emb)
    await dm_safe(membro, emb)

# ----------------------------------------
# ADVERTIR — registra e exonerar automaticamente na 3ª
# /advertir @user motivo
# ----------------------------------------
@bot.tree.command(name="advertir", description="Advertir servidor — 3 advertências = exoneração automática")
@app_commands.describe(
    membro="Usuário a advertir (menção)",
    motivo="Motivo da advertência"
)
async def advertir(inter: discord.Interaction, membro: discord.Member, motivo: str):
    if not eh_admin(inter.user):
        return await inter.response.send_message("❌ Sem permissão.", ephemeral=True)

    guild = inter.guild
    prf_role = guild.get_role(CARGO_PRF_ID)

    # Verifica se é servidor registrado (possui PRF EFETIVO)
    if not prf_role or prf_role not in membro.roles:
        return await inter.response.send_message("❌ Usuário não é um servidor registrado (não possui cargo EFETIVO).", ephemeral=True)

    uid = str(membro.id)
    lista = advertencias.get(uid, [])
    lista.append({"motivo": motivo, "autor": inter.user.id, "data": datetime.now().strftime("%d/%m/%Y %H:%M")})
    advertencias[uid] = lista
    salvar_adv()

    # Se chegou a 3, exonerar automaticamente
    if len(lista) >= 3:
        # chama a função interna de exoneração (mesma lógica)
        motivo_ex = "Excesso de advertências (3/3)"
        # zera advertências
        advertencias.pop(uid, None)
        salvar_adv()
        # executa exoneração
        await exonerar(inter, membro, motivo_ex)
        return

    texto = (
        "A Direção da PRF aplica ADVERTÊNCIA DISCIPLINAR:\n\n"
        f"👮 **Servidor:** {membro.mention}\n"
        f"⚠️ **Advertência Nº:** {len(lista)}\n"
        f"📄 **Motivo:** {motivo}\n"
        f"🧑‍⚖️ **Autoridade:** {inter.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("⚠️ ADVERTÊNCIA DISCIPLINAR", texto, 0xF1C40F)
    await inter.response.send_message("✅ Advertência registrada.", ephemeral=True)
    await enviar(inter.guild, config.get("canal_folha"), emb)
    await enviar(inter.guild, config.get("canal_logs"), emb)
    await dm_safe(membro, emb)

# ----------------------------------------
# EXONERAR — remove todos os cargos, adiciona CIVIL e remove nickname
# /exonerar @user motivo
# ----------------------------------------
@bot.tree.command(name="exonerar", description="Exonerar servidor da PRF — remove cargos e reseta nick")
@app_commands.describe(
    membro="Usuário a exonerar (menção)",
    motivo="Motivo da exoneração"
)
async def exonerar(inter: discord.Interaction, membro: discord.Member, motivo: str):
    if not eh_admin(inter.user):
        return await inter.response.send_message("❌ Sem permissão.", ephemeral=True)

    guild = inter.guild
    prf_role = guild.get_role(CARGO_PRF_ID)

    # Verifica se é servidor registrado (possui PRF EFETIVO)
    if not prf_role or prf_role not in membro.roles:
        return await inter.response.send_message("❌ Usuário não é um servidor registrado (não possui cargo EFETIVO).", ephemeral=True)

    civil_role = guild.get_role(CARGO_CIVIL_ID)
    if not civil_role:
        return await inter.response.send_message("❌ Role CIVIL não encontrado no servidor.", ephemeral=True)

    try:
        remove_list = [r for r in membro.roles if r != guild.default_role]
        if remove_list:
            await membro.remove_roles(*remove_list, reason=f"Exoneração por {inter.user}")
    except Exception:
        print("⚠️ Falha ao remover roles na exoneração:", traceback.format_exc())

    try:
        await membro.add_roles(civil_role, reason=f"Exoneração por {inter.user}")
    except Exception:
        return await inter.response.send_message("❌ Erro ao adicionar cargo CIVIL. Verifique permissões.", ephemeral=True)

    # Remove nickname (reseta para padrão)
    try:
        await membro.edit(nick=None, reason="Exoneração PRF")
    except Exception:
        print("⚠️ Falha ao remover nickname:", traceback.format_exc())

    # Limpa advertências
    advertencias.pop(str(membro.id), None)
    salvar_adv()

    texto = (
        "A Polícia Rodoviária Federal resolve EXONERAR o servidor abaixo:\n\n"
        f"👤 **Servidor:** {membro.mention}\n"
        f"📄 **Motivo:** {motivo}\n"
        f"🧑‍⚖️ **Autoridade:** {inter.user.mention}\n"
        f"📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    emb = embed_padrao("🚨 ATO DE EXONERAÇÃO", texto, 0xC0392B)
    await inter.response.send_message("✅ Exoneração executada.", ephemeral=True)
    await enviar(guild, config.get("canal_folha"), emb)
    await enviar(guild, config.get("canal_logs"), emb)
    await dm_safe(membro, emb)

# ----------------------------------------
# RODA O BOT
# ----------------------------------------
bot.run(os.getenv("DISCORD_TOKEN"))



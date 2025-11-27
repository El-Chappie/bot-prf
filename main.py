# main.py — Bot PRF completo e configurável
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import os, json, traceback

# ---------------- CONFIG / INTENTS ----------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

CONFIG_FILE = "config.json"

# ---------------- HIERARQUIA (NOMES EXATOS DOS ROLES NO SERVIDOR) ----------------
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

# ---------------- ARMAZENAR/RECUPERAR CONFIG ----------------
def carregar_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = {"admins": [], "canal_avisos": None, "canal_logs": None}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        return cfg
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

config = carregar_config()

# ---------------- UTILITÁRIOS ----------------
def eh_admin(membro: discord.Member) -> bool:
    """verifica se o membro tem algum role ID configurado como admin"""
    try:
        for r in membro.roles:
            if r.id in config.get("admins", []):
                return True
        return False
    except Exception:
        return False

def role_is_prf(role: discord.Role) -> bool:
    """verifica se o nome do role faz parte da hierarquia PRF"""
    return role.name.upper() in [h.upper() for h in HIERARQUIA]

async def remover_cargos_prf(membro: discord.Member):
    """remove todos os cargos da hierarquia que o membro possua"""
    try:
        to_remove = [r for r in membro.roles if role_is_prf(r)]
        if to_remove:
            await membro.remove_roles(*to_remove, reason="Atualização de cargo PRF pelo bot")
    except Exception:
        # não falhar a execução do comando se remoção falhar
        print(f"Erro ao remover cargos PRF de {membro.id}:\n{traceback.format_exc()}")

async def enviar_canal_guild(guild: discord.Guild, canal_id: int, embed: discord.Embed):
    if not canal_id:
        return
    try:
        canal = guild.get_channel(canal_id)
        if canal and isinstance(canal, discord.TextChannel):
            await canal.send(embed=embed)
    except Exception:
        print(f"Erro ao enviar embed para canal {canal_id}:\n{traceback.format_exc()}")

async def enviar_dm(usuario: discord.Member, embed: discord.Embed):
    try:
        await usuario.send(embed=embed)
    except Exception:
        # DM pode falhar se usuário bloqueou DM
        pass

def embed_padrao(titulo: str, descricao: str, cor: int = 0x2F3136) -> discord.Embed:
    emb = discord.Embed(title=titulo, description=descricao, color=cor)
    emb.set_footer(text="PRF • Sistema Oficial")
    return emb

# ---------------- EVENTOS ----------------
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception:
        pass
    print(f"✅ BOT PRF ONLINE — {bot.user} ({bot.user.id})")

# ---------------- COMANDOS DE CONFIG ----------------
@bot.tree.command(name="config-admin", description="Configura um cargo (mention) como cargo administrativo")
@app_commands.describe(cargo="Role do servidor a marcar como administrador do sistema (mention)")
async def config_admin(inter: discord.Interaction, cargo: discord.Role):
    # Somente admins do Discord (Guild Administrators) podem setar isso
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Apenas administradores do servidor podem usar este comando.", ephemeral=True)
        return

    if cargo.id in config.get("admins", []):
        await inter.response.send_message(f"⚠️ O cargo {cargo.mention} já está configurado como administrativo.", ephemeral=True)
        return

    config.setdefault("admins", []).append(cargo.id)
    salvar_config(config)
    await inter.response.send_message(f"✅ Cargo {cargo.mention} registrado como cargo ADMINISTRATIVO.")

@bot.tree.command(name="config-avisos", description="Define o canal de comunicações para enviar avisos (mention do canal)")
@app_commands.describe(canal="Canal de texto onde serão postados avisos públicos (mention)")
async def config_avisos(inter: discord.Interaction, canal: discord.TextChannel):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Apenas administradores do servidor podem usar este comando.", ephemeral=True)
        return
    config["canal_avisos"] = canal.id
    salvar_config(config)
    await inter.response.send_message(f"✅ Canal de comunicações definido para {canal.mention}.")

@bot.tree.command(name="config-logs", description="Define o canal de logs (mention do canal)")
@app_commands.describe(canal="Canal de texto para logs internos")
async def config_logs(inter: discord.Interaction, canal: discord.TextChannel):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("❌ Apenas administradores do servidor podem usar este comando.", ephemeral=True)
        return
    config["canal_logs"] = canal.id
    salvar_config(config)
    await inter.response.send_message(f"✅ Canal de logs definido para {canal.mention}.")

@bot.tree.command(name="config-status", description="Mostra o status atual das configurações")
async def config_status(inter: discord.Interaction):
    admins = []
    for role_id in config.get("admins", []):
        r = inter.guild.get_role(role_id)
        if r:
            admins.append(r.mention)
    canal_avisos = f"<#{config['canal_avisos']}>" if config.get("canal_avisos") else "❌ Não definido"
    canal_logs = f"<#{config['canal_logs']}>" if config.get("canal_logs") else "❌ Não definido"
    texto = f"**Cargos administrativos:**\n{', '.join(admins) if admins else '❌ Nenhum setado'}\n\n" \
            f"**Canal de avisos:** {canal_avisos}\n**Canal de logs:** {canal_logs}"
    emb = embed_padrao("⚙️ CONFIGURAÇÃO ATUAL", texto, 0x95A5A6)
    await inter.response.send_message(embed=emb, ephemeral=True)

# ---------------- COMANDOS ADMINISTRATIVOS (USAM ROLES MENCIONADOS) ----------------
@bot.tree.command(name="registrar", description="Registrar membro na corporação (atribui cargo PRF)")
@app_commands.describe(membro="Usuário a registrar", cargo="Role do servidor a atribuir (mention)")
async def registrar(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role):
    # autorização via roles configuradas em /config-admin
    if not eh_admin(inter.user):
        await inter.response.send_message("❌ Você não tem autorização para executar este comando.", ephemeral=True)
        return

    if not role_is_prf(cargo):
        await inter.response.send_message("❌ O cargo informado não pertence à hierarquia PRF.", ephemeral=True)
        return

    # remove cargos PRF antigos e seta o novo
    await remover_cargos_prf(membro)
    try:
        await membro.add_roles(cargo, reason=f"Registro feito por {inter.user}")
    except Exception as e:
        await inter.response.send_message("❌ Erro ao atribuir cargo. Verifique permissões do bot.", ephemeral=True)
        print(traceback.format_exc())
        return

    # preparar embed
    desc = (
        f"**Membro:** {membro.mention}\n"
        f"**Cargo atribuído:** {cargo.mention}\n"
        f"**Registrado por:** {inter.user.mention}\n"
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    emb = embed_padrao("📋 REGISTRO EFETUADO", desc, 0x3498DB)

    # respostas: interação, canal avisos, canal logs, DM
    await inter.response.send_message(embed=emb)
    await enviar_canal_guild(inter.guild, config.get("canal_avisos"), emb)
    await enviar_canal_guild(inter.guild, config.get("canal_logs"), emb)
    await enviar_dm(membro, emb)

@bot.tree.command(name="promover", description="Promover membro (atribui cargo superior)")
@app_commands.describe(membro="Usuário a promover", cargo="Role do servidor a atribuir (mention)")
async def promover(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role):
    if not eh_admin(inter.user):
        await inter.response.send_message("❌ Você não tem autorização para executar este comando.", ephemeral=True)
        return

    if not role_is_prf(cargo):
        await inter.response.send_message("❌ O cargo informado não pertence à hierarquia PRF.", ephemeral=True)
        return

    # remove cargos PRF antigos e seta o novo
    await remover_cargos_prf(membro)
    try:
        await membro.add_roles(cargo, reason=f"Promoção feita por {inter.user}")
    except Exception:
        await inter.response.send_message("❌ Erro ao atribuir cargo. Verifique permissões do bot.", ephemeral=True)
        print(traceback.format_exc())
        return

    desc = (
        f"**Membro:** {membro.mention}\n"
        f"**Novo cargo:** {cargo.mention}\n"
        f"**Autoridade:** {inter.user.mention}\n"
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    emb = embed_padrao("📈 PROMOÇÃO", desc, 0x2ECC71)

    await inter.response.send_message(embed=emb)
    await enviar_canal_guild(inter.guild, config.get("canal_avisos"), emb)
    await enviar_canal_guild(inter.guild, config.get("canal_logs"), emb)
    await enviar_dm(membro, emb)

@bot.tree.command(name="rebaixar", description="Rebaixar membro (atribui cargo inferior)")
@app_commands.describe(membro="Usuário a rebaixar", cargo="Role do servidor a atribuir (mention)", motivo="Motivo do rebaixamento")
async def rebaixar(inter: discord.Interaction, membro: discord.Member, cargo: discord.Role, motivo: str):
    if not eh_admin(inter.user):
        await inter.response.send_message("❌ Você não tem autorização para executar este comando.", ephemeral=True)
        return

    if not role_is_prf(cargo):
        await inter.response.send_message("❌ O cargo informado não pertence à hierarquia PRF.", ephemeral=True)
        return

    await remover_cargos_prf(membro)
    try:
        await membro.add_roles(cargo, reason=f"Rebaixamento feito por {inter.user}")
    except Exception:
        await inter.response.send_message("❌ Erro ao atribuir cargo. Verifique permissões do bot.", ephemeral=True)
        print(traceback.format_exc())
        return

    desc = (
        f"**Membro:** {membro.mention}\n"
        f"**Novo cargo:** {cargo.mention}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}\n"
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    emb = embed_padrao("📉 REBAIXAMENTO", desc, 0xE67E22)

    await inter.response.send_message(embed=emb)
    await enviar_canal_guild(inter.guild, config.get("canal_avisos"), emb)
    await enviar_canal_guild(inter.guild, config.get("canal_logs"), emb)
    await enviar_dm(membro, emb)

@bot.tree.command(name="advertir", description="Aplicar advertência a um membro")
@app_commands.describe(membro="Usuário a advertir", motivo="Motivo")
async def advertir(inter: discord.Interaction, membro: discord.Member, motivo: str):
    if not eh_admin(inter.user):
        await inter.response.send_message("❌ Você não tem autorização para executar este comando.", ephemeral=True)
        return

    desc = (
        f"**Membro:** {membro.mention}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}\n"
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    emb = embed_padrao("⚠ ADVERTÊNCIA DISCIPLINAR", desc, 0xF1C40F)

    await inter.response.send_message(embed=emb)
    await enviar_canal_guild(inter.guild, config.get("canal_avisos"), emb)
    await enviar_canal_guild(inter.guild, config.get("canal_logs"), emb)
    await enviar_dm(membro, emb)

@bot.tree.command(name="exonerar", description="Exonerar membro (remove dos quadros da PRF e seta CIVIL)")
@app_commands.describe(membro="Usuário a exonerar", motivo="Motivo")
async def exonerar(inter: discord.Interaction, membro: discord.Member, motivo: str):
    if not eh_admin(inter.user):
        await inter.response.send_message("❌ Você não tem autorização para executar este comando.", ephemeral=True)
        return

    # procura cargo CIVIL
    cargo_civil = discord.utils.get(inter.guild.roles, name="CIVIL")
    if not cargo_civil:
        await inter.response.send_message("❌ Cargo 'CIVIL' não existe no servidor. Crie o role com esse nome.", ephemeral=True)
        return

    await remover_cargos_prf(membro)
    try:
        await membro.add_roles(cargo_civil, reason=f"Exoneração feita por {inter.user}")
    except Exception:
        await inter.response.send_message("❌ Erro ao atribuir cargo CIVIL. Verifique permissões do bot.", ephemeral=True)
        print(traceback.format_exc())
        return

    desc = (
        f"**Membro:** {membro.mention}\n"
        f"**Motivo:** {motivo}\n"
        f"**Autoridade:** {inter.user.mention}\n"
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    emb = embed_padrao("🚨 EXONERAÇÃO", desc, 0xC0392B)

    await inter.response.send_message(embed=emb)
    await enviar_canal_guild(inter.guild, config.get("canal_avisos"), emb)
    await enviar_canal_guild(inter.guild, config.get("canal_logs"), emb)
    await enviar_dm(membro, emb)

# ---------------- ERROR HANDLER PARA COMANDOS ----------------
@bot.event
async def on_app_command_error(inter: discord.Interaction, error):
    # resposta amigável no discord e print no log
    try:
        await inter.response.send_message("❌ Ocorreu um erro ao processar o comando.", ephemeral=True)
    except Exception:
        pass
    print("Erro em comando:", traceback.format_exc())

# ---------------- RODAR ----------------
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("ERRO: defina a variável de ambiente DISCORD_TOKEN")
    else:
        bot.run(token)

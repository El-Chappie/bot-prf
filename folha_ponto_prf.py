# folha_ponto_prf.py
# Sistema completo de Folha de Ponto PRF (painel, apreensões, multas, antifraude, relatórios)
# Salve como: folha_ponto_prf.py
# Carregar no main: await bot.load_extension("folha_ponto_prf")

import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import json, os, csv, io, random, asyncio

# -----------------------------
# CONFIGURAÇÃO (ajuste IDs conforme seu servidor)
# -----------------------------
ARQ_PONTO = "ponto_prf.json"
CANAL_PAINEL_ID = None      # ID do canal onde será postado o painel (opcional)
CALL_PERMITIDA = None       # ID da voice channel exigida (opcional)
ROLE_OBRIGATORIA = None     # ID de role que deve estar presente para usar painel (opcional)
TEMPO_MINIMO_DIARIO = 4 * 3600  # 4 horas (em segundos)
ANTIFRAUDE_INTERVAL_MIN = 5     # minutos entre checagens aleatórias
ANTIFRAUDE_PROB = 0.12          # probabilidade de checagem por usuário em cada ciclo

# -----------------------------
# ARQUIVOS / DADOS
# -----------------------------
if os.path.exists(ARQ_PONTO):
    with open(ARQ_PONTO, "r", encoding="utf-8") as f:
        dados = json.load(f)
else:
    dados = {"ponto": {}, "apreensoes": {}, "multas": {}, "logs": []}
    # estrutura:
    # dados["ponto"][uid][YYYY-MM-DD] = {"turnos": [{"entrada": ts, "saida": ts_or_none}, ...]}
    # dados["apreensoes"][uid] = [ {id, data, hora, descricao, tipo, drogas, veiculos, valor, registrado_por}, ... ]
    # dados["multas"][uid] = [ {id, data, valor, motivo, registrado_por}, ... ]
    # dados["logs"] = [ {ts, tipo, usuario, autor, detalhes}, ... ]

def salvar():
    with open(ARQ_PONTO, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# -----------------------------
# UTILITÁRIOS
# -----------------------------
def now_ts():
    return int(datetime.utcnow().timestamp())

def hoje_str():
    return datetime.utcnow().strftime("%Y-%m-%d")

def hora_str(ts=None):
    if ts is None:
        ts = now_ts()
    return datetime.utcfromtimestamp(ts).strftime("%H:%M:%S")

def tempo_seg_str(seg):
    h = int(seg // 3600)
    m = int((seg % 3600) // 60)
    s = int(seg % 60)
    return f"{h:02}:{m:02}:{s:02}"

def logar(tipo, usuario_id, autor_id, detalhes=""):
    entrada = {"ts": now_ts(), "tipo": tipo, "usuario": usuario_id, "autor": autor_id, "detalhes": detalhes}
    dados.setdefault("logs", []).append(entrada)
    salvar()

def assegura_usuario(uid):
    if uid not in dados["ponto"]:
        dados["ponto"][uid] = {}

def uid_of(user):
    return str(user.id)

def total_horas_no_dia(uid, dia):
    total = 0
    entry = dados["ponto"].get(uid, {}).get(dia)
    if not entry:
        return 0
    for t in entry.get("turnos", []):
        if t.get("saida"):
            total += (t["saida"] - t["entrada"])
    return total

def esta_em_servico(uid):
    entry = dados["ponto"].get(uid, {}).get(hoje_str())
    if not entry or not entry.get("turnos"):
        return False
    last = entry["turnos"][-1]
    return last.get("saida") is None

def gerar_id(prefix):
    return f"{prefix}-{int(datetime.utcnow().timestamp())}-{random.randint(100,999)}"

# -----------------------------
# VIEW (Painel com botões)
# -----------------------------
class PainelView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def checar_permissoes_entrada(self, interaction: discord.Interaction):
        # check voice channel requirement
        if CALL_PERMITIDA:
            if not interaction.user.voice or interaction.user.voice.channel.id != CALL_PERMITIDA:
                return False, "Você precisa estar na call oficial para iniciar/encerrar serviço."
        # check role requirement
        if ROLE_OBRIGATORIA:
            role = discord.Object(id=ROLE_OBRIGATORIA)
            if role.id not in [r.id for r in interaction.user.roles]:
                return False, "Você não possui a role necessária para operar o painel de ponto."
        return True, None

    @discord.ui.button(label="✅ Entrar em serviço", style=discord.ButtonStyle.success, custom_id="ponto:entrar")
    async def entrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok, msg = await self.checar_permissoes_entrada(interaction)
        if not ok:
            return await interaction.response.send_message(msg, ephemeral=True)

        uid = uid_of(interaction.user)
        dia = hoje_str()
        assegura_usuario(uid)
        userdata = dados["ponto"][uid].setdefault(dia, {"turnos": []})

        # permite múltiplos turnos — verifica se já está em serviço
        if userdata["turnos"] and userdata["turnos"][-1].get("saida") is None:
            return await interaction.response.send_message("Você já está em serviço.", ephemeral=True)

        userdata["turnos"].append({"entrada": now_ts(), "saida": None})
        salvar()
        logar("entrada", uid, uid, f"entrada via botão")
        await interaction.response.send_message("🟢 Entrada registrada com sucesso.", ephemeral=True)

    @discord.ui.button(label="⛔ Sair de serviço", style=discord.ButtonStyle.danger, custom_id="ponto:sair")
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = uid_of(interaction.user)
        dia = hoje_str()
        if uid not in dados["ponto"] or dia not in dados["ponto"][uid]:
            return await interaction.response.send_message("Nenhum registro de entrada encontrado hoje.", ephemeral=True)

        turnos = dados["ponto"][uid][dia]["turnos"]
        if not turnos or turnos[-1].get("saida") is not None:
            return await interaction.response.send_message("Você não está em serviço.", ephemeral=True)

        turnos[-1]["saida"] = now_ts()
        salvar()
        logar("saida", uid, uid, "saida via botão")

        total_seg = total_horas_no_dia(uid, dia)
        situ = "✅ REGULAR" if total_seg >= TEMPO_MINIMO_DIARIO else "❌ NEGATIVADO"
        await interaction.response.send_message(
            f"🔴 Saída registrada. Total acumulado hoje: `{tempo_seg_str(total_seg)}` — Situação: {situ}",
            ephemeral=True
        )

    @discord.ui.button(label="📄 Minha folha", style=discord.ButtonStyle.secondary, custom_id="ponto:minhafolha")
    async def myfolha(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = uid_of(interaction.user)
        texto = ""
        total_geral = 0
        if uid in dados["ponto"]:
            for dia, info in sorted(dados["ponto"][uid].items(), reverse=True):
                total = 0
                linhas = []
                for t in info.get("turnos", []):
                    ent = hora_str(t["entrada"])
                    sai = hora_str(t["saida"]) if t.get("saida") else "⏳"
                    linhas.append(f"{ent} → {sai}")
                    if t.get("saida"):
                        total += (t["saida"] - t["entrada"])
                total_geral += total
                texto += f"**{dia}** — {tempo_seg_str(total)}\n" + "\n".join(f"  • {l}" for l in linhas) + "\n\n"
        else:
            texto = "Nenhum registro encontrado."
        embed = discord.Embed(title="📋 Minha Folha de Ponto", description=texto[:3500], color=0x2563eb)
        embed.add_field(name="Horas acumuladas (total histórico)", value=tempo_seg_str(total_geral))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🚨 Reportar apreensão / multa", style=discord.ButtonStyle.primary, custom_id="ponto:reportar")
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        # abre instruções para reportar via slash commands (para evitar modals complexos)
        txt = (
            "Para registrar apreensão utilize o comando:\n"
            "`/registrarapreensao usuario:@alvo descricao:\"descrição\" tipo:\"droga/veiculo/arma\" drogas:\"lista\" veiculos:\"placa,modelo\" valor:123`\n\n"
            "Para registrar multa utilize:\n"
            "`/registrarmulta usuario:@alvo valor:100 motivo:\"motivo\"`"
        )
        await interaction.response.send_message(txt, ephemeral=True)

# -----------------------------
# COG PRINCIPAL: comandos administrativos e gestão
# -----------------------------
class FolhaPontoPRF(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.antifraude_loop.start()

    def cog_unload(self):
        self.antifraude_loop.cancel()

    # -------------------------
    # Antifraude: checagens aleatórias em membros atualmente em serviço
    # -------------------------
    @tasks.loop(minutes=ANTIFRAUDE_INTERVAL_MIN)
    async def antifraude_loop(self):
        try:
            for uid, dias in dados["ponto"].items():
                # escolhe aleatoriamente alguns usuários para checar
                if random.random() > ANTIFRAUDE_PROB:
                    continue
                # pega último dia registrado (melhorar no futuro)
                dia = hoje_str()
                if dia not in dias:
                    continue
                turnos = dias[dia].get("turnos", [])
                if not turnos or turnos[-1].get("saida") is not None:
                    continue
                # usuário em serviço -> checar presença em voice
                user_obj = None
                for g in self.bot.guilds:
                    m = g.get_member(int(uid))
                    if m:
                        user_obj = m
                        break
                if not user_obj:
                    # usuário não encontrado no cache -> logar para auditoria
                    logar("antifraude_missing_user", uid, "system", "usuário não encontrado em guilds no momento da checagem")
                    continue
                # se CALL_PERMITIDA definida, checar se está na call
                if CALL_PERMITIDA and (not user_obj.voice or user_obj.voice.channel.id != CALL_PERMITIDA):
                    # marca tentativa suspeita
                    logar("antifraude_failed_call", uid, "system", "usuário em serviço mas não na call obrigatória")
                    # notificar administradores via DM (opcional) - aqui apenas log
                # checagem de presença (online status)
                if user_obj.status == discord.Status.offline:
                    logar("antifraude_offline", uid, "system", "usuário em serviço com status offline")
                # futuro: checagens adicionais de IP, guild voice timestamp via API externa (não implementada)
        except Exception as e:
            print("Erro em antifraude_loop:", e)

    # -------------------------
    # Painel: publica o embed + botões no canal atual (admin only)
    # -------------------------
    @app_commands.command(name="painelponto", description="Publicar painel de ponto com botões (Admin)")
    async def painelponto(self, interaction: discord.Interaction):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        embed = discord.Embed(
            title="🕘 PAINEL DE FOLHA DE PONTO — PRF",
            description=(
                "Use os botões abaixo para iniciar/encerrar expediente ou para abrir sua folha.\n\n"
                f"Jornada mínima diária: **{TEMPO_MINIMO_DIARIO//3600} horas**.\n"
                "Atenção: sistema com auditoria automática e controles antifraude."
            ),
            color=0x0ea5e9
        )
        view = PainelView(self.bot)
        # envia no canal do comando
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Painel publicado.", ephemeral=True)

    # -------------------------
    # Ver folha de um servidor (admin)
    # -------------------------
    @app_commands.command(name="verfolha", description="Ver folha de ponto de um servidor (Admin)")
    async def verfolha(self, interaction: discord.Interaction, usuario: discord.Member):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        uid = uid_of(usuario)
        if uid not in dados["ponto"]:
            return await interaction.response.send_message("Servidor sem registros.", ephemeral=True)

        texto = ""
        for dia, info in sorted(dados["ponto"][uid].items(), reverse=True):
            total = 0
            linhas = []
            for t in info.get("turnos", []):
                ent = hora_str(t["entrada"])
                sai = hora_str(t["saida"]) if t.get("saida") else "⏳"
                linhas.append(f"{ent} → {sai}")
                if t.get("saida"):
                    total += (t["saida"] - t["entrada"])
            texto += f"**{dia}** — {tempo_seg_str(total)}\n" + "\n".join(f"  • {l}" for l in linhas) + "\n\n"

        embed = discord.Embed(title=f"📊 FOLHA — {usuario}", description=texto[:3500], color=0x2563eb)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------
    # Registrar apreensão (admin/director)
    # -------------------------
    @app_commands.command(name="registrarapreensao", description="Registrar apreensão (Admin)")
    async def registrarapreensao(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        descricao: str,
        tipo: str,           # e.g. "drogas", "veículo", "arma", "outro"
        drogas: str = "",    # lista descrita
        veiculos: str = "",  # placa/modelo
        valor: float = 0.0
    ):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        uid = uid_of(usuario)
        assegura_usuario(uid)
        entry = {
            "id": gerar_id("AP"),
            "data": hoje_str(),
            "hora": hora_str(None),
            "descricao": descricao,
            "tipo": tipo,
            "drogas": drogas,
            "veiculos": veiculos,
            "valor": float(valor),
            "registrado_por": uid_of(interaction.user)
        }
        dados.setdefault("apreensoes", {}).setdefault(uid, []).append(entry)
        salvar()
        logar("apreensao", uid, uid_of(interaction.user), f"{tipo} / {descricao}")
        embed = discord.Embed(
            title="📦 Registro de Apreensão",
            description=(
                f"Servidor: {usuario.mention}\n"
                f"Tipo: {tipo}\n"
                f"Descrição: {descricao}\n"
                f"Drogas: {drogas or '—'}\n"
                f"Veículos: {veiculos or '—'}\n"
                f"Valor estimado: R$ {valor:.2f}\n"
                f"Registrado por: {interaction.user.mention}\n"
                f"ID: {entry['id']}"
            ),
            color=0x9f1239
        )
        await enviar_para_folha(interaction.guild, embed)
        await interaction.response.send_message("Apreensão registrada com sucesso.", ephemeral=True)

    # -------------------------
    # Registrar multa (admin/director)
    # -------------------------
    @app_commands.command(name="registrarmulta", description="Registrar multa administrativa (Admin)")
    async def registrarmulta(self, interaction: discord.Interaction, usuario: discord.Member, valor: float, motivo: str):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        uid = uid_of(usuario)
        entry = {
            "id": gerar_id("MU"),
            "data": hoje_str(),
            "hora": hora_str(None),
            "valor": float(valor),
            "motivo": motivo,
            "registrado_por": uid_of(interaction.user)
        }
        dados.setdefault("multas", {}).setdefault(uid, []).append(entry)
        salvar()
        logar("multa", uid, uid_of(interaction.user), motivo)

        embed = discord.Embed(
            title="💸 Registro de Multa",
            description=(
                f"Servidor: {usuario.mention}\n"
                f"Valor: R$ {valor:.2f}\n"
                f"Motivo: {motivo}\n"
                f"Registrado por: {interaction.user.mention}\n"
                f"ID: {entry['id']}"
            ),
            color=0xda8b00
        )
        await enviar_para_folha(interaction.guild, embed)
        await interaction.response.send_message("Multa registrada com sucesso.", ephemeral=True)

    # -------------------------
    # Ver apreensões (admin)
    # -------------------------
    @app_commands.command(name="verapreensoes", description="Ver apreensões de um servidor (Admin)")
    async def verapreensoes(self, interaction: discord.Interaction, usuario: discord.Member):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        uid = uid_of(usuario)
        arr = dados.get("apreensoes", {}).get(uid, [])
        if not arr:
            return await interaction.response.send_message("Nenhuma apreensão registrada para este servidor.", ephemeral=True)

        texto = ""
        for a in arr:
            texto += f"• [{a['id']}] {a['data']} {a['hora']} — {a['tipo']} — {a['descricao']} (R$ {a['valor']:.2f})\n"

        embed = discord.Embed(title=f"📦 Apreensões — {usuario}", description=texto[:3500], color=0x9f1239)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------
    # Ver multas (admin)
    # -------------------------
    @app_commands.command(name="vermultas", description="Ver multas de um servidor (Admin)")
    async def vermultas(self, interaction: discord.Interaction, usuario: discord.Member):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        uid = uid_of(usuario)
        arr = dados.get("multas", {}).get(uid, [])
        if not arr:
            return await interaction.response.send_message("Nenhuma multa registrada para este servidor.", ephemeral=True)

        texto = ""
        total = 0.0
        for m in arr:
            texto += f"• [{m['id']}] {m['data']} {m['hora']} — R$ {m['valor']:.2f} — {m['motivo']}\n"
            total += m['valor']

        embed = discord.Embed(title=f"💸 Multas — {usuario}", description=texto[:3500], color=0xda8b00)
        embed.add_field(name="Total aplicado", value=f"R$ {total:.2f}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------
    # Remover registro (admin) — uso cuidadoso
    # -------------------------
    @app_commands.command(name="removerregistro", description="Remover registro de apreensão/multa/ponto (Admin)")
    async def removerregistro(self, interaction: discord.Interaction, tipo: str, usuario: discord.Member, registro_id: str):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)
        uid = uid_of(usuario)
        if tipo.lower() == "apreensao":
            arr = dados.get("apreensoes", {}).get(uid, [])
            novo = [a for a in arr if a["id"] != registro_id]
            dados["apreensoes"][uid] = novo
            salvar()
            logar("remover_apreensao", uid, uid_of(interaction.user), registro_id)
            return await interaction.response.send_message("Registro de apreensão removido (se existia).", ephemeral=True)
        if tipo.lower() == "multa":
            arr = dados.get("multas", {}).get(uid, [])
            novo = [m for m in arr if m["id"] != registro_id]
            dados["multas"][uid] = novo
            salvar()
            logar("remover_multa", uid, uid_of(interaction.user), registro_id)
            return await interaction.response.send_message("Registro de multa removido (se existia).", ephemeral=True)
        return await interaction.response.send_message("Tipo inválido. Use 'apreensao' ou 'multa'.", ephemeral=True)

    # -------------------------
    # Exportar folha (CSV) — admin
    # -------------------------
    @app_commands.command(name="exportarfolha", description="Exportar folha de um servidor em CSV (Admin)")
    async def exportarfolha(self, interaction: discord.Interaction, usuario: discord.Member):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        uid = uid_of(usuario)
        if uid not in dados["ponto"]:
            return await interaction.response.send_message("Servidor sem registros.", ephemeral=True)

        # cria CSV em memória
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["data", "entrada", "saida", "duracao_segundos"])
        for dia, info in sorted(dados["ponto"][uid].items()):
            for t in info.get("turnos", []):
                entrada = datetime.utcfromtimestamp(t["entrada"]).isoformat() if t.get("entrada") else ""
                saida = datetime.utcfromtimestamp(t["saida"]).isoformat() if t.get("saida") else ""
                dur = (t["saida"] - t["entrada"]) if t.get("saida") else ""
                writer.writerow([dia, entrada, saida, dur])
        output.seek(0)
        file = discord.File(fp=io.BytesIO(output.getvalue().encode("utf-8")), filename=f"folha_{usuario.id}.csv")
        await interaction.response.send_message("Exportando folha...", file=file, ephemeral=True)

    # -------------------------
    # Visualizar logs de auditoria (admin)
    # -------------------------
    @app_commands.command(name="verlogs", description="Ver logs de auditoria (Admin)")
    async def verlogs(self, interaction: discord.Interaction, limit: int = 30):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)
        texto = ""
        for l in list(dados.get("logs", []))[-limit:]:
            ts = datetime.utcfromtimestamp(l["ts"]).strftime("%Y-%m-%d %H:%M:%S")
            texto += f"{ts} | {l['tipo']} | user:{l['usuario']} | autor:{l['autor']} | {l.get('detalhes','')}\n"
        if not texto:
            texto = "Sem logs."
        embed = discord.Embed(title="📝 Logs de Auditoria", description=texto[:3500], color=0x64748b)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# -----------------------------
# Função Helper: enviar embed para canal da folha (se configurado)
# -----------------------------
async def enviar_para_folha(guild: discord.Guild, embed: discord.Embed):
    # envia para canal configurado CANAL_PAINEL_ID se informado; caso contrário envia para o primeiro canal de texto disponível
    canal = None
    if CANAL_PAINEL_ID:
        canal = guild.get_channel(CANAL_PAINEL_ID)
    if not canal:
        for c in guild.text_channels:
            if c.permissions_for(guild.me).send_messages:
                canal = c
                break
    if canal:
        try:
            await canal.send(embed=embed)
        except:
            pass

# -----------------------------
# Helper: checar admin (usa seu código global)
# -----------------------------
# Reutiliza a função eh_admin do seu main; caso não esteja disponível no escopo do módulo, faz fallback simples.
try:
    from __main__ import eh_admin as eh_admin_main
    def eh_admin(user):
        try:
            return eh_admin_main(user)
        except:
            return user.guild_permissions.administrator
except Exception:
    def eh_admin(user):
        return user.guild_permissions.administrator

# -----------------------------
# SETUP
# -----------------------------
async def setup(bot):
    await bot.add_cog(FolhaPontoPRF(bot))

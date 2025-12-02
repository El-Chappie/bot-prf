# folha_ponto_prf.py
# Sistema de Folha de Ponto PRF — SQLite, painel, apreensões, multas, antifraude, relatórios
# Carregar: await bot.load_extension("folha_ponto_prf")

import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
import sqlite3
import io
import csv
import random

# -----------------------------
# CONFIGURAÇÃO (ajuste IDs conforme seu servidor)
# -----------------------------
DB_FILE = "folha_ponto_prf.db"
CANAL_PAINEL_ID = 1445156201347420211      # ID do canal onde será postado o painel (opcional)
CALL_PERMITIDA = None       # ID da voice channel exigida (opcional)
ROLE_OBRIGATORIA = 1443387935700291697     # ID de role que deve estar presente para usar painel (opcional)
TEMPO_MINIMO_DIARIO = 4 * 3600  # 4 horas (em segundos)
ANTIFRAUDE_INTERVAL_MIN = 5     # minutos entre checagens aleatórias
ANTIFRAUDE_PROB = 0.12          # probabilidade de checagem por usuário em cada ciclo

# -----------------------------
# BANCO DE DADOS (SQLite)
# -----------------------------
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()

# Cria tabelas se não existirem
cur.execute("""
CREATE TABLE IF NOT EXISTS pontos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    dia TEXT NOT NULL
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ponto_id INTEGER NOT NULL,
    entrada INTEGER NOT NULL,
    saida INTEGER,
    canal_voz INTEGER,
    FOREIGN KEY(ponto_id) REFERENCES pontos(id) ON DELETE CASCADE
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS apreensoes (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    data TEXT,
    hora TEXT,
    descricao TEXT,
    tipo TEXT,
    drogas TEXT,
    veiculos TEXT,
    valor REAL,
    registrado_por INTEGER
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS multas (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    data TEXT,
    hora TEXT,
    valor REAL,
    motivo TEXT,
    registrado_por INTEGER
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS canais_permitidos (
    canal_id INTEGER PRIMARY KEY
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER,
    tipo TEXT,
    usuario INTEGER,
    autor INTEGER,
    detalhes TEXT
);
""")
conn.commit()

# -----------------------------
# HELPERS (DB operations)
# -----------------------------
def ts_now():
    return int(datetime.utcnow().timestamp())

def hoje_str():
    return datetime.utcnow().strftime("%Y-%m-%d")

def hora_str(ts=None):
    if ts is None:
        ts = ts_now()
    return datetime.utcfromtimestamp(int(ts)).strftime("%H:%M:%S")

def tempo_seg_str(seg):
    h = int(seg // 3600)
    m = int((seg % 3600) // 60)
    s = int(seg % 60)
    return f"{h:02}:{m:02}:{s:02}"

def log_db(tipo, usuario_id, autor_id, detalhes=""):
    cur.execute("INSERT INTO logs (ts, tipo, usuario, autor, detalhes) VALUES (?, ?, ?, ?, ?)",
                (ts_now(), tipo, usuario_id, autor_id, detalhes))
    conn.commit()

def ponto_id_para_dia(user_id, dia):
    cur.execute("SELECT id FROM pontos WHERE user_id = ? AND dia = ?", (user_id, dia))
    r = cur.fetchone()
    return r[0] if r else None

def criar_ponto_dia(user_id, dia):
    cur.execute("INSERT INTO pontos (user_id, dia) VALUES (?, ?)", (user_id, dia))
    conn.commit()
    return cur.lastrowid

def abrir_turno(user_id, canal_voz=None):
    dia = hoje_str()
    pid = ponto_id_para_dia(user_id, dia)
    if pid is None:
        pid = criar_ponto_dia(user_id, dia)
    # verifica se já existe turno aberto
    cur.execute("""
        SELECT t.id FROM turnos t
        JOIN pontos p ON t.ponto_id = p.id
        WHERE p.user_id = ? AND p.dia = ? AND t.saida IS NULL
    """, (user_id, dia))
    if cur.fetchone():
        return None  # já aberto
    agora = ts_now()
    cur.execute("INSERT INTO turnos (ponto_id, entrada, saida, canal_voz) VALUES (?, ?, NULL, ?)",
                (pid, agora, canal_voz))
    conn.commit()
    log_db("entrada", user_id, user_id, "entrada via painel")
    return cur.lastrowid

def fechar_turno_aberto(user_id):
    dia = hoje_str()
    cur.execute("""
        SELECT t.id FROM turnos t
        JOIN pontos p ON t.ponto_id = p.id
        WHERE p.user_id = ? AND p.dia = ? AND t.saida IS NULL
        ORDER BY t.entrada DESC LIMIT 1
    """, (user_id, dia))
    r = cur.fetchone()
    if not r:
        return False
    turno_id = r[0]
    agora = ts_now()
    cur.execute("UPDATE turnos SET saida = ? WHERE id = ?", (agora, turno_id))
    conn.commit()
    log_db("saida", user_id, user_id, "saida via painel")
    return True

def turno_aberto_existe(user_id):
    dia = hoje_str()
    cur.execute("""
        SELECT 1 FROM turnos t
        JOIN pontos p ON t.ponto_id = p.id
        WHERE p.user_id = ? AND p.dia = ? AND t.saida IS NULL
    """, (user_id, dia))
    return cur.fetchone() is not None

def obter_turnos_do_dia(user_id, dia=None):
    if dia is None:
        dia = hoje_str()
    cur.execute("""
        SELECT t.entrada, t.saida FROM turnos t
        JOIN pontos p ON t.ponto_id = p.id
        WHERE p.user_id = ? AND p.dia = ?
        ORDER BY t.entrada ASC
    """, (user_id, dia))
    return cur.fetchall()  # lista de tuplas (entrada, saida)

def total_segundos_dia(user_id, dia=None):
    total = 0
    for ent, sai in obter_turnos_do_dia(user_id, dia):
        if ent:
            if sai:
                total += (int(sai) - int(ent))
            else:
                total += (ts_now() - int(ent))
    return total

def adicionar_apreensao(user_id, descricao, tipo, drogas, veiculos, valor, registrado_por):
    aid = gerar_id("AP")
    cur.execute("""
        INSERT INTO apreensoes (id, user_id, data, hora, descricao, tipo, drogas, veiculos, valor, registrado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (aid, user_id, hoje_str(), hora_str(None), descricao, tipo, drogas, veiculos, float(valor), registrado_por))
    conn.commit()
    log_db("apreensao", user_id, registrado_por, f"{tipo} / {descricao}")
    return aid

def obter_apreensoes(user_id):
    cur.execute("SELECT id, data, hora, descricao, tipo, drogas, veiculos, valor, registrado_por FROM apreensoes WHERE user_id = ? ORDER BY data DESC, hora DESC", (user_id,))
    return cur.fetchall()

def adicionar_multa(user_id, valor, motivo, registrado_por):
    mid = gerar_id("MU")
    cur.execute("""
        INSERT INTO multas (id, user_id, data, hora, valor, motivo, registrado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (mid, user_id, hoje_str(), hora_str(None), float(valor), motivo, registrado_por))
    conn.commit()
    log_db("multa", user_id, registrado_por, motivo)
    return mid

def obter_multas(user_id):
    cur.execute("SELECT id, data, hora, valor, motivo, registrado_por FROM multas WHERE user_id = ? ORDER BY data DESC, hora DESC", (user_id,))
    return cur.fetchall()

def adicionar_canal_permitido(canal_id):
    cur.execute("INSERT OR IGNORE INTO canais_permitidos (canal_id) VALUES (?)", (canal_id,))
    conn.commit()

def remover_canal_permitido(canal_id):
    cur.execute("DELETE FROM canais_permitidos WHERE canal_id = ?", (canal_id,))
    conn.commit()

def canal_autorizado(canal_id):
    cur.execute("SELECT 1 FROM canais_permitidos WHERE canal_id = ?", (canal_id,))
    return cur.fetchone() is not None

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
        # checa se precisa estar em uma call específica
        if CALL_PERMITIDA:
            if not interaction.user.voice or interaction.user.voice.channel.id != CALL_PERMITIDA:
                return False, "Você precisa estar na call oficial para iniciar/encerrar serviço."
        # checa se precisa ter role específica
        if ROLE_OBRIGATORIA:
            if ROLE_OBRIGATORIA not in [r.id for r in interaction.user.roles]:
                return False, "Você não possui a role necessária para operar o painel de ponto."
        return True, None

    @discord.ui.button(label="✅ Entrar em serviço", style=discord.ButtonStyle.success, custom_id="ponto:entrar")
    async def entrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ok, msg = await self.checar_permissoes_entrada(interaction)
        if not ok:
            return await interaction.response.send_message(msg, ephemeral=True)

        user_id = interaction.user.id
        canal_voz = interaction.user.voice.channel.id if interaction.user.voice and interaction.user.voice.channel else None

        if turno_aberto_existe(user_id):
            return await interaction.response.send_message("Você já está em serviço.", ephemeral=True)

        tid = abrir_turno(user_id, canal_voz)
        if not tid:
            return await interaction.response.send_message("Não foi possível iniciar o turno (verifique permissões).", ephemeral=True)

        await interaction.response.send_message("🟢 Entrada registrada com sucesso.", ephemeral=True)

    @discord.ui.button(label="⛔ Sair de serviço", style=discord.ButtonStyle.danger, custom_id="ponto:sair")
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        if not turno_aberto_existe(user_id):
            return await interaction.response.send_message("Você não está em serviço.", ephemeral=True)

        ok = fechar_turno_aberto(user_id)
        if not ok:
            return await interaction.response.send_message("Falha ao registrar saída.", ephemeral=True)

        total_seg = total_segundos_dia(user_id)
        situ = "✅ REGULAR" if total_seg >= TEMPO_MINIMO_DIARIO else "❌ NEGATIVADO"
        await interaction.response.send_message(f"🔴 Saída registrada. Total acumulado hoje: `{tempo_seg_str(total_seg)}` — Situação: {situ}", ephemeral=True)

    @discord.ui.button(label="📄 Minha folha", style=discord.ButtonStyle.secondary, custom_id="ponto:minhafolha")
    async def myfolha(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        # monta texto com últimos dias (limit)
        cur.execute("SELECT dia FROM pontos WHERE user_id = ? ORDER BY dia DESC LIMIT 10", (user_id,))
        dias = [r[0] for r in cur.fetchall()]
        if not dias:
            return await interaction.response.send_message("Nenhum registro encontrado.", ephemeral=True)

        texto = ""
        total_geral = 0
        for dia in dias:
            turnos = obter_turnos_do_dia(user_id, dia)
            total = 0
            lines = []
            for ent, sai in turnos:
                ent_s = hora_str(ent)
                sai_s = hora_str(sai) if sai else "⏳"
                lines.append(f"{ent_s} → {sai_s}")
                if sai:
                    total += (int(sai) - int(ent))
            total_geral += total
            texto += f"**{dia}** — {tempo_seg_str(total)}\n" + "\n".join(f"  • {l}" for l in lines) + "\n\n"

        embed = discord.Embed(title="📋 Minha Folha de Ponto (últimos dias)", description=texto[:3500], color=0x2563eb)
        embed.add_field(name="Horas acumuladas (total dos dias listados)", value=tempo_seg_str(total_geral))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🚨 Reportar apreensão / multa", style=discord.ButtonStyle.primary, custom_id="ponto:reportar")
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        txt = (
            "Para registrar apreensão utilize o comando:\n"
            "`/registrarapreensao usuario:@alvo descricao:\"descrição\" tipo:\"droga/veiculo/arma\" drogas:\"lista\" veiculos:\"placa,modelo\" valor:123`\n\n"
            "Para registrar multa utilize:\n"
            "`/registrarmulta usuario:@alvo valor:100 motivo:\"motivo\"`"
        )
        await interaction.response.send_message(txt, ephemeral=True)

# -----------------------------
# COG PRINCIPAL
# -----------------------------
class FolhaPontoPRF(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.antifraude_loop.start()

    def cog_unload(self):
        self.antifraude_loop.cancel()

    # Antifraude: checagens aleatórias
    @tasks.loop(minutes=ANTIFRAUDE_INTERVAL_MIN)
    async def antifraude_loop(self):
        try:
            # pega todos usuários com turno aberto hoje
            dia = hoje_str()
            cur.execute("""
                SELECT p.user_id FROM pontos p
                JOIN turnos t ON t.ponto_id = p.id
                WHERE p.dia = ? AND t.saida IS NULL
                GROUP BY p.user_id
            """, (dia,))
            rows = cur.fetchall()
            for r in rows:
                if random.random() > ANTIFRAUDE_PROB:
                    continue
                uid = r[0]
                user_obj = None
                for g in self.bot.guilds:
                    m = g.get_member(int(uid))
                    if m:
                        user_obj = m
                        break
                if not user_obj:
                    log_db("antifraude_missing_user", uid, 0, "usuário não encontrado nas guilds")
                    continue
                # se CALL_PERMITIDA definida, checar se está na call
                if CALL_PERMITIDA and (not user_obj.voice or user_obj.voice.channel.id != CALL_PERMITIDA):
                    log_db("antifraude_failed_call", uid, 0, "usuário em serviço mas não na call obrigatória")
                    # opcional: notificar diretores (não implementado automaticamente)
                if user_obj.status == discord.Status.offline:
                    log_db("antifraude_offline", uid, 0, "usuário em serviço com status offline")
        except Exception as e:
            print("Erro em antifraude_loop:", e)

    # Painel: publica o embed + botões no canal atual (admin only)
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
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Painel publicado.", ephemeral=True)

    # Ver folha de um servidor (admin)
    @app_commands.command(name="verfolha", description="Ver folha de ponto de um servidor (Admin)")
    async def verfolha(self, interaction: discord.Interaction, usuario: discord.Member):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        uid = usuario.id
        cur.execute("SELECT dia FROM pontos WHERE user_id = ? ORDER BY dia DESC", (uid,))
        dias = [r[0] for r in cur.fetchall()]
        if not dias:
            return await interaction.response.send_message("Servidor sem registros.", ephemeral=True)

        texto = ""
        for dia in dias:
            turnos = obter_turnos_do_dia(uid, dia)
            total = 0
            linhas = []
            for ent, sai in turnos:
                ent_s = hora_str(ent)
                sai_s = hora_str(sai) if sai else "⏳"
                linhas.append(f"{ent_s} → {sai_s}")
                if sai:
                    total += (int(sai) - int(ent))
            texto += f"**{dia}** — {tempo_seg_str(total)}\n" + "\n".join(f"  • {l}" for l in linhas) + "\n\n"

        embed = discord.Embed(title=f"📊 FOLHA — {usuario}", description=texto[:3500], color=0x2563eb)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Registrar apreensão (admin)
    @app_commands.command(name="registrarapreensao", description="Registrar apreensão (Admin)")
    async def registrarapreensao(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        descricao: str,
        tipo: str,
        drogas: str = "",
        veiculos: str = "",
        valor: float = 0.0
    ):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        aid = adicionar_apreensao(usuario.id, descricao, tipo, drogas, veiculos, valor, interaction.user.id)

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
                f"ID: {aid}"
            ),
            color=0x9f1239
        )
        await enviar_para_folha(interaction.guild, embed)
        await interaction.response.send_message("Apreensão registrada com sucesso.", ephemeral=True)

    # Registrar multa (admin)
    @app_commands.command(name="registrarmulta", description="Registrar multa administrativa (Admin)")
    async def registrarmulta(self, interaction: discord.Interaction, usuario: discord.Member, valor: float, motivo: str):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        mid = adicionar_multa(usuario.id, valor, motivo, interaction.user.id)

        embed = discord.Embed(
            title="💸 Registro de Multa",
            description=(
                f"Servidor: {usuario.mention}\n"
                f"Valor: R$ {valor:.2f}\n"
                f"Motivo: {motivo}\n"
                f"Registrado por: {interaction.user.mention}\n"
                f"ID: {mid}"
            ),
            color=0xda8b00
        )
        await enviar_para_folha(interaction.guild, embed)
        await interaction.response.send_message("Multa registrada com sucesso.", ephemeral=True)

    # Ver apreensões (admin)
    @app_commands.command(name="verapreensoes", description="Ver apreensões de um servidor (Admin)")
    async def verapreensoes(self, interaction: discord.Interaction, usuario: discord.Member):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        arr = obter_apreensoes(usuario.id)
        if not arr:
            return await interaction.response.send_message("Nenhuma apreensão registrada para este servidor.", ephemeral=True)

        texto = ""
        for a in arr:
            texto += f"• [{a[0]}] {a[1]} {a[2]} — {a[4]} — {a[3]} (R$ {a[7]:.2f})\n"

        embed = discord.Embed(title=f"📦 Apreensões — {usuario}", description=texto[:3500], color=0x9f1239)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Ver multas (admin)
    @app_commands.command(name="vermultas", description="Ver multas de um servidor (Admin)")
    async def vermultas(self, interaction: discord.Interaction, usuario: discord.Member):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        arr = obter_multas(usuario.id)
        if not arr:
            return await interaction.response.send_message("Nenhuma multa registrada para este servidor.", ephemeral=True)

        texto = ""
        total = 0.0
        for m in arr:
            texto += f"• [{m[0]}] {m[1]} {m[2]} — R$ {m[3]:.2f} — {m[4]}\n"
            total += m[3]

        embed = discord.Embed(title=f"💸 Multas — {usuario}", description=texto[:3500], color=0xda8b00)
        embed.add_field(name="Total aplicado", value=f"R$ {total:.2f}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Remover registro (admin)
    @app_commands.command(name="removerregistro", description="Remover registro de apreensão/multa/ponto (Admin)")
    async def removerregistro(self, interaction: discord.Interaction, tipo: str, usuario: discord.Member, registro_id: str):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)
        uid = usuario.id
        if tipo.lower() == "apreensao":
            cur.execute("DELETE FROM apreensoes WHERE id = ? AND user_id = ?", (registro_id, uid))
            conn.commit()
            log_db("remover_apreensao", uid, interaction.user.id, registro_id)
            return await interaction.response.send_message("Registro de apreensão removido (se existia).", ephemeral=True)
        if tipo.lower() == "multa":
            cur.execute("DELETE FROM multas WHERE id = ? AND user_id = ?", (registro_id, uid))
            conn.commit()
            log_db("remover_multa", uid, interaction.user.id, registro_id)
            return await interaction.response.send_message("Registro de multa removido (se existia).", ephemeral=True)
        return await interaction.response.send_message("Tipo inválido. Use 'apreensao' ou 'multa'.", ephemeral=True)

    # Exportar folha (CSV)
    @app_commands.command(name="exportarfolha", description="Exportar folha de um servidor em CSV (Admin)")
    async def exportarfolha(self, interaction: discord.Interaction, usuario: discord.Member):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)

        # monta CSV com todos os turnos do usuário
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["data", "entrada_iso", "saida_iso", "duracao_segundos"])
        cur.execute("""
            SELECT p.dia, t.entrada, t.saida FROM turnos t
            JOIN pontos p ON t.ponto_id = p.id
            WHERE p.user_id = ?
            ORDER BY p.dia ASC, t.entrada ASC
        """, (usuario.id,))
        for dia, ent, sai in cur.fetchall():
            entrada_iso = datetime.utcfromtimestamp(int(ent)).isoformat() if ent else ""
            saida_iso = datetime.utcfromtimestamp(int(sai)).isoformat() if sai else ""
            dur = int(sai) - int(ent) if sai else ""
            writer.writerow([dia, entrada_iso, saida_iso, dur])
        output.seek(0)
        file = discord.File(fp=io.BytesIO(output.getvalue().encode("utf-8")), filename=f"folha_{usuario.id}.csv")
        await interaction.response.send_message("Exportando folha...", file=file, ephemeral=True)

    # Ver logs (admin)
    @app_commands.command(name="verlogs", description="Ver logs de auditoria (Admin)")
    async def verlogs(self, interaction: discord.Interaction, limit: int = 30):
        if not eh_admin(interaction.user):
            return await interaction.response.send_message("Acesso negado.", ephemeral=True)
        cur.execute("SELECT ts, tipo, usuario, autor, detalhes FROM logs ORDER BY ts DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        texto = ""
        for ts, tipo, usuario, autor, detalhes in rows:
            ts_s = datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
            texto += f"{ts_s} | {tipo} | u:{usuario} | autor:{autor} | {detalhes}\n"
        if not texto:
            texto = "Sem logs."
        embed = discord.Embed(title="📝 Logs de Auditoria", description=texto[:3500], color=0x64748b)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# -----------------------------
# Função Helper: enviar embed para canal da folha (se configurado)
# -----------------------------
async def enviar_para_folha(guild: discord.Guild, embed: discord.Embed):
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
        except Exception:
            pass

# -----------------------------
# Reuso da função eh_admin do main, com fallback
# -----------------------------
try:
    from __main__ import eh_admin as eh_admin_main
    def eh_admin(user):
        try:
            return eh_admin_main(user)
        except Exception:
            return user.guild_permissions.administrator
except Exception:
    def eh_admin(user):
        return user.guild_permissions.administrator

# -----------------------------
# SETUP
# -----------------------------
async def setup(bot):
    bot.add_view(PainelView(bot))
    await bot.add_cog(FolhaPontoPRF(bot))

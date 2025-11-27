# edital.py — Cog do Edital com hybrid commands (prefix e slash)
import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta

ARQ_PROVA = "edital_prova_data.json"

# Config defaults (você irá configurar via setprovaresult / setprovaresultlog)
DIRETOR_ROLE_IDS = []    # lista a ser preenchida caso queira checar cargos de diretor
CANAL_RESULT_ID = None   # canal público de resultados
CANAL_LOG_ID = None      # canal privado de logs para diretores

COOLDOWN_SEGUNDOS = 3600
NUM_PERGUNTAS = 10
MIN_PONTOS = 6

# banco simples de perguntas (adicione as suas)
PERGUNTAS = [
    {"pergunta": "Qual é a capital do Brasil?", "alternativas": ["Rio", "Brasília", "São Paulo", "Salvador"], "correta": 1},
    {"pergunta": "Maior planeta?", "alternativas": ["Terra", "Marte", "Júpiter", "Saturno"], "correta": 2},
    {"pergunta": "Fórmula da água?", "alternativas": ["H2O", "CO2", "O2", "NaCl"], "correta": 0}
    # ... acrescente perguntas até ter pelo menos NUM_PERGUNTAS + reservas ...
]

def carregar():
    if not os.path.exists(ARQ_PROVA):
        return {"tentativas": {}, "provas": {}}
    with open(ARQ_PROVA, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar(dados):
    with open(ARQ_PROVA, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

class Edital(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dados = carregar()   # estrutura: {"tentativas": {uid: iso}, "provas": {uid: {...}}}
        self.result_channel = CANAL_RESULT_ID
        self.log_channel = CANAL_LOG_ID
        # iniciar tarefa de limpeza
        self._limpar.start()

    def cog_unload(self):
        self._limpar.cancel()

    # -------------------------
    # comandos híbridos (funcionam como / e !)
    # -------------------------
    @commands.hybrid_command(name="setprovaresult", description="Define canal público de resultado (diretor/admin)")
    @commands.has_permissions(administrator=True)
    async def setprovaresult(self, ctx: commands.Context, canal: discord.TextChannel):
        """Define o canal público onde resultados serão anunciados."""
        self.result_channel = canal.id
        await ctx.reply(f"✅ Canal de resultados definido: {canal.mention}", ephemeral=True)

    @commands.hybrid_command(name="setprovaresultlog", description="Define canal de logs da prova (diretores/admin)")
    @commands.has_permissions(administrator=True)
    async def setprovaresultlog(self, ctx: commands.Context, canal: discord.TextChannel):
        """Define o canal onde o log completo das provas será enviado."""
        self.log_channel = canal.id
        await ctx.reply(f"✅ Canal de logs definido: {canal.mention}", ephemeral=True)

    @commands.hybrid_command(name="enviarprova", description="Envia a prova por DM para o usuário (diretor) — /enviarprova @user")
    async def enviarprova(self, ctx: commands.Context, usuario: discord.Member):
        # opcional: checar se quem chamou tem cargo de diretor; por enquanto checamos permissão administrativa
        if not (ctx.author.guild_permissions.administrator or any(r.id in DIRETOR_ROLE_IDS for r in ctx.author.roles)):
            await ctx.reply("❌ Você não tem permissão para iniciar provas.", ephemeral=True)
            return

        uid = str(usuario.id)
        agora = datetime.utcnow()

        # cooldown
        ultima = self.dados["tentativas"].get(uid)
        if ultima:
            dt = datetime.fromisoformat(ultima)
            diff = agora - dt
            if diff.total_seconds() < COOLDOWN_SEGUNDOS:
                resta = int((COOLDOWN_SEGUNDOS - diff.total_seconds()) // 60)
                await ctx.reply(f"⏳ O usuário só poderá tentar novamente daqui ~{resta} minutos.", ephemeral=True)
                return

        if len(PERGUNTAS) < NUM_PERGUNTAS:
            await ctx.reply("❌ Não há perguntas suficientes cadastradas.", ephemeral=True)
            return

        # criar prova com perguntas aleatórias + embaralhar alternativas
        idxs = random.sample(range(len(PERGUNTAS)), NUM_PERGUNTAS)
        questoes = []
        for i in idxs:
            p = PERGUNTAS[i]
            alts = p["alternativas"].copy()
            random.shuffle(alts)
            # recalcula índice correto após shuffle
            correta_valor = p["alternativas"][p["correta"]]
            nova_correta = alts.index(correta_valor)
            questoes.append({"pergunta": p["pergunta"], "alternativas": alts, "correta": nova_correta})

        # salva estado
        self.dados["provas"][uid] = {
            "questoes": questoes,
            "respostas": [],
            "indice": 0,
            "inicio": agora.isoformat()
        }
        self.dados["tentativas"][uid] = (agora + timedelta(seconds=COOLDOWN_SEGUNDOS)).isoformat()
        salvar(self.dados)

        # envia DM com instruções e primeira pergunta
        try:
            await usuario.send(embed=discord.Embed(
                title="📄 Prova do Edital",
                description=f"Você recebeu uma prova com {NUM_PERGUNTAS} questões. Responda por DM enviando A/B/C/D. Boa sorte!",
                color=0x3498DB
            ))
            await self._enviar_pergunta_dm(usuario)
            await ctx.reply(f"✅ Prova enviada para {usuario.mention}.", ephemeral=True)
        except Exception:
            await ctx.reply("❌ Não foi possível enviar DM ao usuário (provavelmente DMs fechadas).", ephemeral=True)

    # -------------------------
    # envio de pergunta por DM
    # -------------------------
    async def _enviar_pergunta_dm(self, usuario: discord.Member):
        uid = str(usuario.id)
        prova = self.dados["provas"].get(uid)
        if not prova:
            return
        i = prova["indice"]
        q = prova["questoes"][i]
        letras = ["A", "B", "C", "D"]
        texto = ""
        for j, alt in enumerate(q["alternativas"]):
            texto += f"\n**{letras[j]}** — {alt}"
        emb = discord.Embed(title=f"Questão {i+1}/{NUM_PERGUNTAS}", description=q["pergunta"] + "\n\n" + texto, color=0x2F3136)
        emb.set_footer(text="Responda por DM enviando A, B, C ou D.")
        await usuario.send(embed=emb)

    # -------------------------
    # listener para respostas por DM
    # -------------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        # ignorar bots
        if message.author.bot:
            return
        # considerar apenas DMs
        if not isinstance(message.channel, discord.DMChannel):
            return
        uid = str(message.author.id)
        if uid not in self.dados["provas"]:
            return  # nada a fazer

        texto = message.content.strip().upper()
        if texto not in ("A", "B", "C", "D"):
            await message.channel.send(embed=discord.Embed(title="Resposta inválida", description="Responda apenas A, B, C ou D.", color=0xE74C3C))
            return

        prova = self.dados["provas"][uid]
        escolha = ["A", "B", "C", "D"].index(texto)
        prova["respostas"].append(escolha)
        prova["indice"] += 1
        salvar(self.dados)

        # se ainda há perguntas, envia próxima
        if prova["indice"] < NUM_PERGUNTAS:
            await message.channel.send(embed=discord.Embed(description=f"Resposta registrada: **{texto}** — Enviando próxima...", color=0x2ECC71))
            await self._enviar_pergunta_dm(message.author)
            return

        # finaliza prova
        await message.channel.send(embed=discord.Embed(description="Todas as respostas recebidas. Aguarde o resultado.", color=0x3498DB))
        await self._finalizar_prova(message.author)

    # -------------------------
    # finalizar e enviar logs/resultados
    # -------------------------
    async def _finalizar_prova(self, usuario: discord.Member):
        uid = str(usuario.id)
        prova = self.dados["provas"].get(uid)
        if not prova:
            return

        respostas = prova["respostas"]
        questoes = prova["questoes"]
        pontos = 0
        letras = ["A", "B", "C", "D"]
        detalhes = ""
        for i, q in enumerate(questoes):
            user_r = respostas[i] if i < len(respostas) else None
            correta = q["correta"]
            if user_r is not None and user_r == correta:
                pontos += 1
            user_letra = letras[user_r] if user_r is not None else "Nenhuma"
            detalhes += f"**Q{i+1}**: {q['pergunta']}\nResposta: {user_letra} | Correta: {letras[correta]}\n\n"

        aprovado = pontos >= MIN_PONTOS
        status_text = "✅ APROVADO" if aprovado else "❌ REPROVADO"

        emb_user = discord.Embed(title="📊 Resultado da Prova", description=f"Você obteve **{pontos}/{NUM_PERGUNTAS}** — {status_text}", color=0x2ECC71 if aprovado else 0xE74C3C)
        await usuario.send(embed=emb_user)

        # anuncia no canal público (se configurado)
        if self.result_channel:
            ch = self.bot.get_channel(self.result_channel)
            if ch:
                emb_pub = discord.Embed(title="Resultado da Prova", description=f"{usuario.mention} obteve **{pontos}/{NUM_PERGUNTAS}** — {status_text}", color=0x2ECC71 if aprovado else 0xE74C3C)
                await ch.send(embed=emb_pub)

        # envia log completo (se configurado)
        if self.log_channel:
            chlog = self.bot.get_channel(self.log_channel)
            if chlog:
                emb_log = discord.Embed(title=f"Log prova — {usuario}", description=f"Pontuação: {pontos}/{NUM_PERGUNTAS}\n\n{detalhes}", color=0x95A5A6, timestamp=datetime.utcnow())
                await chlog.send(embed=emb_log)

        # remove prova do estado
        self.dados["provas"].pop(uid, None)
        salvar(self.dados)

    # -------------------------
    # limpeza periódica de dados antigos
    # -------------------------
    @tasks.loop(hours=24)
    async def _limpar(self):
        agora = datetime.utcnow()
        alterou = False
        # remove provas com > 7 dias
        for uid, prov in list(self.dados["provas"].items()):
            try:
                inicio = datetime.fromisoformat(prov.get("inicio"))
                if agora - inicio > timedelta(days=7):
                    self.dados["provas"].pop(uid, None)
                    alterou = True
            except Exception:
                continue
        # remove tentativas com > 30 dias
        for uid, tent in list(self.dados["tentativas"].items()):
            try:
                dt = datetime.fromisoformat(tent)
                if agora - dt > timedelta(days=30):
                    self.dados["tentativas"].pop(uid, None)
                    alterou = True
            except Exception:
                continue
        if alterou:
            salvar(self.dados)

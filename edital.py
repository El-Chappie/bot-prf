# edital.py
import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta

ARQ_PROVA = "edital_prova_data.json"

DIRETOR_ROLE_IDS = []
CANAL_RESULT_ID = None
CANAL_LOG_ID = None

COOLDOWN_SEGUNDOS = 3600
NUM_PERGUNTAS = 10
MIN_PONTOS = 6

PERGUNTAS = [
    {"pergunta": "Capital do Brasil?", "alternativas": ["Rio", "Brasília", "São Paulo", "Recife"], "correta": 1},
    {"pergunta": "Maior planeta?", "alternativas": ["Terra", "Marte", "Júpiter", "Saturno"], "correta": 2},
    {"pergunta": "Fórmula da água?", "alternativas": ["H2O", "CO2", "O2", "NaCl"], "correta": 0},
    {"pergunta": "Ano do descobrimento do Brasil?", "alternativas": ["1498", "1500", "1510", "1600"], "correta": 1},
    {"pergunta": "Criador do Python?", "alternativas": ["Linus", "Bill", "Guido", "Mark"], "correta": 2},
    {"pergunta": "Primeiro presidente do Brasil?", "alternativas": ["Getúlio", "Deodoro", "Lula", "Sarney"], "correta": 1},
    {"pergunta": "Base da programação?", "alternativas": ["Lógica", "HTML", "CSS", "SQL"], "correta": 0},
    {"pergunta": "Maior oceano?", "alternativas": ["Atlântico", "Indico", "Pacífico", "Ártico"], "correta": 2},
    {"pergunta": "Sistema do Discord?", "alternativas": ["Slack", "Teams", "Guilds", "Servers"], "correta": 3},
    {"pergunta": "Python é?", "alternativas": ["Compilado", "Interpretado", "Binário", "Assembly"], "correta": 1},
    {"pergunta": "RAM significa?", "alternativas": ["Read", "Random", "Run", "Rapid"], "correta": 1}
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
        self.dados = carregar()
        self.result_channel = CANAL_RESULT_ID
        self.log_channel = CANAL_LOG_ID
        self._limpar.start()

    def cog_unload(self):
        self._limpar.cancel()

    @commands.hybrid_command(name="setprovaresult")
    @commands.has_permissions(administrator=True)
    async def setprovaresult(self, ctx, canal: discord.TextChannel):
        self.result_channel = canal.id
        await ctx.reply(embed=discord.Embed(
            title="✅ Configurado",
            description=f"Canal de resultados definido: {canal.mention}",
            color=0x2ecc71
        ), ephemeral=True)

    @commands.hybrid_command(name="setprovaresultlog")
    @commands.has_permissions(administrator=True)
    async def setprovaresultlog(self, ctx, canal: discord.TextChannel):
        self.log_channel = canal.id
        await ctx.reply(embed=discord.Embed(
            title="✅ Configurado",
            description=f"Canal de logs definido: {canal.mention}",
            color=0x2ecc71
        ), ephemeral=True)

    @commands.hybrid_command(name="enviarprova")
    async def enviarprova(self, ctx, usuario: discord.Member):

        if not (ctx.author.guild_permissions.administrator or any(r.id in DIRETOR_ROLE_IDS for r in ctx.author.roles)):
            await ctx.reply(embed=discord.Embed(title="❌ Sem permissão", description="Acesso restrito.", color=0xe74c3c), ephemeral=True)
            return

        uid = str(usuario.id)
        agora = datetime.utcnow()

        if uid in self.dados["tentativas"]:
            await ctx.reply(embed=discord.Embed(title="⏳ Bloqueado", description="Usuário em cooldown.", color=0xf1c40f), ephemeral=True)
            return

        perguntas = random.sample(PERGUNTAS, NUM_PERGUNTAS)
        questoes = []

        for p in perguntas:
            alts = p["alternativas"].copy()
            random.shuffle(alts)
            correta = alts.index(p["alternativas"][p["correta"]])
            questoes.append({"pergunta": p["pergunta"], "alternativas": alts, "correta": correta})

        self.dados["provas"][uid] = {"questoes": questoes, "respostas": [], "indice": 0, "inicio": agora.isoformat()}
        self.dados["tentativas"][uid] = agora.isoformat()
        salvar(self.dados)

        try:
            await usuario.send(embed=discord.Embed(title="📄 Prova", description="Responda A / B / C / D", color=0x3498db))
            await self._enviar_pergunta(usuario)
            await ctx.reply(embed=discord.Embed(description="✅ Prova enviada", color=0x2ecc71), ephemeral=True)
        except:
            await ctx.reply(embed=discord.Embed(description="❌ DM fechada", color=0xe74c3c), ephemeral=True)

    async def _enviar_pergunta(self, user):
        uid = str(user.id)
        p = self.dados["provas"][uid]
        q = p["questoes"][p["indice"]]
        letras = ["A", "B", "C", "D"]
        texto = "\n".join(f"**{letras[i]}** — {alt}" for i, alt in enumerate(q["alternativas"]))

        embed = discord.Embed(title=f"Questão {p['indice']+1}/{NUM_PERGUNTAS}", description=q["pergunta"] + "\n\n" + texto, color=0x95a5a6)
        await user.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot or not isinstance(msg.channel, discord.DMChannel):
            return
        uid = str(msg.author.id)
        if uid not in self.dados["provas"]:
            return

        r = msg.content.upper()
        if r not in ("A", "B", "C", "D"):
            await msg.channel.send(embed=discord.Embed(description="❌ Envie apenas A/B/C/D", color=0xe74c3c))
            return

        prova = self.dados["provas"][uid]
        prova["respostas"].append(["A","B","C","D"].index(r))
        prova["indice"] += 1
        salvar(self.dados)

        if prova["indice"] < NUM_PERGUNTAS:
            await self._enviar_pergunta(msg.author)
        else:
            await self._finalizar(msg.author)

    async def _finalizar(self, user):
        uid = str(user.id)
        prova = self.dados["provas"][uid]
        pontos = sum(1 for i,q in enumerate(prova["questoes"]) if prova["respostas"][i] == q["correta"])
        aprovado = pontos >= MIN_PONTOS
        status = "✅ APROVADO" if aprovado else "❌ REPROVADO"

        await user.send(embed=discord.Embed(title="Resultado", description=f"{pontos}/{NUM_PERGUNTAS}\n{status}", color=0x2ecc71 if aprovado else 0xe74c3c))

        if self.result_channel:
            c = self.bot.get_channel(self.result_channel)
            if c:
                await c.send(embed=discord.Embed(description=f"{user.mention} — {status}", color=0x2ecc71 if aprovado else 0xe74c3c))

        if self.log_channel:
            c = self.bot.get_channel(self.log_channel)
            if c:
                await c.send(embed=discord.Embed(title=f"Log {user}", description=f"Pontuação: {pontos}", color=0x7f8c8d))

        self.dados["provas"].pop(uid)
        salvar(self.dados)

    @tasks.loop(hours=24)
    async def _limpar(self):
        agora = datetime.utcnow()
        for k,v in list(self.dados["tentativas"].items()):
            dt = datetime.fromisoformat(v)
            if agora - dt > timedelta(days=1):
                self.dados["tentativas"].pop(k)
        salvar(self.dados)


async def setup(bot):
    await bot.add_cog(Edital(bot))
    print("✅ Edital carregado corretamente")

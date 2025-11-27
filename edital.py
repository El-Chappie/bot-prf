import discord
from discord.ext import commands
import random
import json
import os
from datetime import datetime, timedelta

DATA = "edital.json"

PERGUNTAS = [
    {
        "q": "Qual o número da polícia no Brasil?",
        "a": ["190", "191", "188", "193"],
        "c": 0
    },
    {
        "q": "O que é hierarquia?",
        "a": ["Desorganização", "Cadeia de comando", "Bagunça", "Desrespeito"],
        "c": 1
    },
    {
        "q": "Qual o dever de um policial?",
        "a": ["Ignorar crimes", "Servir à sociedade", "Desobedecer leis", "Ser violento"],
        "c": 1
    },
    # adicione mais perguntas...
]

COOLDOWN = 3600
NUMERO_QUESTOES = 10
NOTA_CORTE = 7

def load():
    if not os.path.exists(DATA):
        return {}
    return json.load(open(DATA, "r", encoding="utf8"))

def save(d):
    json.dump(d, open(DATA, "w", encoding="utf8"), indent=4, ensure_ascii=False)

def embed(t, d, c=0x2f3136):
    return discord.Embed(title=t, description=d, color=c)

class Edital(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.provas = load()
        self.log = None
        self.result = None

    # ---------------------
    # CONFIG
    # ---------------------

    @commands.command()
    async def setprovaresult(self, ctx, canal: discord.TextChannel):
        self.result = canal.id
        await ctx.send(embed=embed("✅ Resultado definido", canal.mention))

    @commands.command()
    async def setprovaresultlog(self, ctx, canal: discord.TextChannel):
        self.log = canal.id
        await ctx.send(embed=embed("✅ Log definido", canal.mention))

    # ---------------------
    # ENVIAR PROVA
    # ---------------------

    @commands.command(name="enviarprova")
    async def enviar_prova(self, ctx, usuario: discord.Member):

        uid = str(usuario.id)
        agora = datetime.utcnow()

        if uid in self.provas and "cooldown" in self.provas[uid]:
            libera = datetime.fromisoformat(self.provas[uid]["cooldown"])
            if agora < libera:
                resto = int((libera - agora).total_seconds() / 60)
                await ctx.send(embed=embed("⏳ Bloqueado", f"{usuario.mention} poderá tentar novamente em {resto} minutos."))
                return

        questoes = random.sample(PERGUNTAS, NUMERO_QUESTOES)

        # embaralha alternativas sem repetir
        for q in questoes:
            ordem = q["a"].copy()
            random.shuffle(ordem)
            correta = ordem.index(q["a"][q["c"]])
            q["a"] = ordem
            q["c"] = correta

        self.provas[uid] = {
            "iniciado": datetime.utcnow().isoformat(),
            "cooldown": (agora + timedelta(seconds=COOLDOWN)).isoformat(),
            "p": questoes,
            "r": [],
            "i": 0
        }

        save(self.provas)

        try:
            await usuario.send(embed=embed("📄 PROVA INICIADA", "Responda digitando **A, B, C ou D**.\nVocê está sendo monitorado."))
            await self.enviar_pergunta(usuario)
            await ctx.send(embed=embed("✅ Prova enviada", usuario.mention))
        except:
            await ctx.send(embed=embed("❌ Erro", "O usuário está com DM fechada."))

    # ---------------------
    # PERGUNTA
    # ---------------------

    async def enviar_pergunta(self, user):
        uid = str(user.id)
        prova = self.provas.get(uid)

        i = prova["i"]
        q = prova["p"][i]

        texto = ""
        letras = ["A", "B", "C", "D"]
        for n, alt in enumerate(q["a"]):
            texto += f"\n**{letras[n]}** - {alt}"

        e = embed(f"Questão {i+1}/{NUMERO_QUESTOES}", q["q"] + texto)
        await user.send(embed=e)

    # ---------------------
    # RESPOSTA
    # ---------------------

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot or not isinstance(msg.channel, discord.DMChannel):
            return

        uid = str(msg.author.id)
        if uid not in self.provas:
            return

        prova = self.provas[uid]
        resp = msg.content.upper().strip()

        if resp not in ["A", "B", "C", "D"]:
            await msg.channel.send(embed=embed("❌ Inválido", "Digite A, B, C ou D"))
            return

        prova["r"].append(["A","B","C","D"].index(resp))
        prova["i"] += 1
        save(self.provas)

        if prova["i"] >= NUMERO_QUESTOES:
            await self.finalizar(msg.author)
        else:
            await self.enviar_pergunta(msg.author)

    # ---------------------
    # FINALIZAR
    # ---------------------

    async def finalizar(self, user):
        uid = str(user.id)
        prova = self.provas[uid]

        pontos = 0

        for i, q in enumerate(prova["p"]):
            if prova["r"][i] == q["c"]:
                pontos += 1

        status = "✅ APROVADO" if pontos >= NOTA_CORTE else "❌ REPROVADO"

        res = self.bot.get_channel(self.result)
        log = self.bot.get_channel(self.log)

        e = embed("📊 RESULTADO", f"{user.mention}\n\nNota: {pontos}/{NUMERO_QUESTOES}\n{status}")

        await user.send(embed=e)
        if res: await res.send(embed=e)

        if log:
            full = ""
            for i, q in enumerate(prova["p"]):
                user_r = ["A","B","C","D"][prova["r"][i]]
                cor_r = ["A","B","C","D"][q["c"]]
                full += f"\n**Q{i+1}** {q['q']}\nResposta: {user_r} | Correta: {cor_r}\n"

            await log.send(embed=embed("🧾 LOG COMPLETO", full))

        del self.provas[uid]
        save(self.provas)

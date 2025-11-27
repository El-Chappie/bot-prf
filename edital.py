# edital.py — Sistema de Edital PRF (Corrigido e Estável)
import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta

ARQ_PROVA = "edital_prova_data.json"

# Canais (serão configurados por comando)
CANAL_RESULT_ID = None
CANAL_LOG_ID = None

COOLDOWN_SEGUNDOS = 3600
NUM_PERGUNTAS = 10
MIN_PONTOS = 6

# Banco de perguntas (adicione mais)
PERGUNTAS = [
    {"pergunta": "Qual é a capital do Brasil?", "alternativas": ["Rio", "Brasília", "São Paulo", "Salvador"], "correta": 1},
    {"pergunta": "Maior planeta do sistema solar?", "alternativas": ["Terra", "Marte", "Júpiter", "Saturno"], "correta": 2},
    {"pergunta": "Fórmula da água?", "alternativas": ["H2O", "CO2", "O2", "NaCl"], "correta": 0},
    {"pergunta": "Cor da farda oficial da PRF?", "alternativas": ["Azul", "Preta", "Cinza", "Verde"], "correta": 1},
    {"pergunta": "Sigla PRF significa?", "alternativas": ["Polícia Rodoviária Federal","Polícia Regional Federal","Patrulha Rodoviária Fixa","Polícia Federal Rodoviária"], "correta": 0},
    {"pergunta": "Cargo mais alto da PRF?", "alternativas": ["Diretor-Geral","Supervisor","Inspetor","Delegado"], "correta": 0},
    {"pergunta": "Função principal da PRF?", "alternativas": ["Investigar crimes","Patrulhar rodovias","Policiamento aéreo","Polícia civil"], "correta": 1},
    {"pergunta": "O que é hierarquia?", "alternativas": ["Ordem","Respeito","Classificação por cargo","Educação"], "correta": 2},
    {"pergunta": "Quem comanda uma operação?", "alternativas": ["Civil","Inspetor","Diretor ou Delegado","Aluno"], "correta": 2},
    {"pergunta": "Símbolo da PRF?", "alternativas": ["Águia","Onça","Leão","Lobo"], "correta": 0},
    # reservas
    {"pergunta": "Tempo máximo de prova?", "alternativas": ["30 min","60 min","Livre","10 min"], "correta": 1},
    {"pergunta": "Reprovação ocorre com?", "alternativas": ["5 erros","4 erros","6 acertos mínimos","Livre"], "correta": 2}
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

    async def cog_load(self):
        self._limpar.start()

    def cog_unload(self):
        self._limpar.cancel()

    # ---------------- CONFIGURAÇÃO ----------------
    @commands.hybrid_command(name="setprovaresult", description="Define canal público de resultado")
    @commands.has_permissions(administrator=True)
    async def setprovaresult(self, ctx, canal: discord.TextChannel):
        self.result_channel = canal.id
        await ctx.reply(f"✅ Canal público definido: {canal.mention}", ephemeral=True)

    @commands.hybrid_command(name="setprovaresultlog", description="Define canal privado de logs")
    @commands.has_permissions(administrator=True)
    async def setprovaresultlog(self, ctx, canal: discord.TextChannel):
        self.log_channel = canal.id
        await ctx.reply(f"✅ Canal de logs definido: {canal.mention}", ephemeral=True)

    # ---------------- INICIAR PROVA ----------------
    @commands.hybrid_command(name="enviarprova", description="Enviar prova a um usuário")
    @commands.has_permissions(administrator=True)
    async def enviarprova(self, ctx, usuario: discord.Member):
        uid = str(usuario.id)
        agora = datetime.utcnow()

        ultima = self.dados["tentativas"].get(uid)
        if ultima:
            diff = agora - datetime.fromisoformat(ultima)
            if diff.total_seconds() < COOLDOWN_SEGUNDOS:
                restante = int((COOLDOWN_SEGUNDOS - diff.total_seconds()) // 60)
                return await ctx.reply(f"⏳ Tente novamente em {restante} minutos.", ephemeral=True)

        if len(PERGUNTAS) < NUM_PERGUNTAS:
            return await ctx.reply("❌ Perguntas insuficientes.", ephemeral=True)

        perguntas = random.sample(PERGUNTAS, NUM_PERGUNTAS)
        questoes = []

        for p in perguntas:
            alts = p["alternativas"].copy()
            random.shuffle(alts)
            correta = alts.index(p["alternativas"][p["correta"]])
            questoes.append({"pergunta": p["pergunta"], "alternativas": alts, "correta": correta})

        self.dados["provas"][uid] = {
            "questoes": questoes,
            "respostas": [],
            "indice": 0,
            "inicio": agora.isoformat()
        }

        self.dados["tentativas"][uid] = agora.isoformat()
        salvar(self.dados)

        try:
            await usuario.send(embed=discord.Embed(
                title="📑 Prova PRF",
                description="Responda A, B, C ou D em cada pergunta.",
                color=0x3498DB
            ))
            await self._enviar_pergunta(usuario)
            await ctx.reply("✅ Prova enviada.", ephemeral=True)
        except:
            await ctx.reply("❌ Usuário com DM fechada.", ephemeral=True)

    async def _enviar_pergunta(self, usuario):
        prova = self.dados["provas"].get(str(usuario.id))
        i = prova["indice"]
        q = prova["questoes"][i]
        letras = ["A","B","C","D"]

        texto = "\n".join([f"**{letras[n]}** — {alt}" for n, alt in enumerate(q["alternativas"])])
        emb = discord.Embed(title=f"Questão {i+1}/{NUM_PERGUNTAS}", description=f"{q['pergunta']}\n\n{texto}", color=0x2F3136)
        await usuario.send(embed=emb)

    # ---------------- RESPOSTAS ----------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not isinstance(message.channel, discord.DMChannel):
            return

        uid = str(message.author.id)
        if uid not in self.dados["provas"]:
            return

        resposta = message.content.strip().upper()
        if resposta not in ("A","B","C","D"):
            return await message.channel.send("Responda apenas A, B, C ou D.")

        prova = self.dados["provas"][uid]
        prova["respostas"].append(["A","B","C","D"].index(resposta))
        prova["indice"] += 1
        salvar(self.dados)

        if prova["indice"] < NUM_PERGUNTAS:
            await self._enviar_pergunta(message.author)
        else:
            await self._finalizar_prova(message.author)

    async def _finalizar_prova(self, usuario):
        uid = str(usuario.id)
        prova = self.dados["provas"][uid]

        pontos = 0
        letras = ["A","B","C","D"]
        detalhes = ""

        for i,q in enumerate(prova["questoes"]):
            user = prova["respostas"][i]
            if user == q["correta"]:
                pontos += 1
            detalhes += f"Q{i+1}: {letras[user]} | Correta: {letras[q['correta']]}\n"

        status = "✅ APROVADO" if pontos >= MIN_PONTOS else "❌ REPROVADO"

        await usuario.send(embed=discord.Embed(
            title="Resultado da Prova",
            description=f"{pontos}/{NUM_PERGUNTAS} — {status}",
            color=0x2ECC71 if pontos>=MIN_PONTOS else 0xE74C3C
        ))

        if self.result_channel:
            ch = self.bot.get_channel(self.result_channel)
            if ch:
                await ch.send(embed=discord.Embed(
                    title="Resultado Oficial",
                    description=f"{usuario.mention} — {pontos}/{NUM_PERGUNTAS} — {status}",
                    color=0x2ECC71 if pontos>=MIN_PONTOS else 0xE74C3C
                ))

        if self.log_channel:
            log = self.bot.get_channel(self.log_channel)
            if log:
                await log.send(embed=discord.Embed(
                    title=f"LOG — {usuario}",
                    description=detalhes,
                    color=0x95A5A6
                ))

        self.dados["provas"].pop(uid)
        salvar(self.dados)

    # ---------------- LIMPEZA ----------------
    @tasks.loop(hours=24)
    async def _limpar(self):
        agora = datetime.utcnow()
        alterou = False

        for uid, t in list(self.dados["tentativas"].items()):
            if agora - datetime.fromisoformat(t) > timedelta(days=30):
                del self.dados["tentativas"][uid]
                alterou = True

        if alterou:
            salvar(self.dados)

import discord
from discord.ext import commands, tasks
import json, os, random, asyncio
from datetime import datetime, timedelta

ARQ_PROVA = "edital_prova_data.json"

# ========= CONFIGURAÇÃO ========= #
DIRETOR_ROLE_IDS = []   # IDs dos diretores
CATEGORIA_PROVAS_ID = None  # ID da categoria "PROVAS PRF"
CANAL_RESULTADOS_ID = None  # Canal público de resultados

TEMPO_LIMITE = 600  # 10 minutos
NUM_PERGUNTAS = 10
MIN_PONTOS = 6
COOLDOWN_SEGUNDOS = 3600

# ========= PERGUNTAS ========= #
PERGUNTAS = [
    {"pergunta": "Capital do Brasil?", "alternativas": ["Rio", "Brasília", "São Paulo", "Recife"], "correta": 1},
    {"pergunta": "Maior planeta?", "alternativas": ["Terra", "Marte", "Júpiter", "Saturno"], "correta": 2},
    {"pergunta": "Fórmula da água?", "alternativas": ["H2O", "CO2", "O2", "NaCl"], "correta": 0},
    {"pergunta": "Criador do Python?", "alternativas": ["Linus", "Bill", "Guido", "Mark"], "correta": 2},
    {"pergunta": "Primeiro presidente do Brasil?", "alternativas": ["Getúlio", "Deodoro", "Lula", "Sarney"], "correta": 1},
    {"pergunta": "Maior oceano?", "alternativas": ["Atlântico", "Índico", "Pacífico", "Ártico"], "correta": 2},
    {"pergunta": "Python é?", "alternativas": ["Compilado", "Interpretado", "Binário", "Assembly"], "correta": 1},
]

# ================= FUNÇÕES ================= #
def carregar():
    if not os.path.exists(ARQ_PROVA):
        return {"tentativas": {}, "provas": {}}
    with open(ARQ_PROVA, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar(d):
    with open(ARQ_PROVA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=4)

# ================= COG ================= #
class Edital(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dados = carregar()
        self._limpar.start()

    # ========= CONFIG ========= #
    @commands.hybrid_command(name="setcanalresultado")
    @commands.has_permissions(administrator=True)
    async def setcanalresultado(self, ctx, canal: discord.TextChannel):
        global CANAL_RESULTADOS_ID
        CANAL_RESULTADOS_ID = canal.id
        await ctx.reply("✅ Canal de resultados definido.", ephemeral=True)

    @commands.hybrid_command(name="setcategoriaprovas")
    @commands.has_permissions(administrator=True)
    async def setcategoriaprovas(self, ctx, categoria: discord.CategoryChannel):
        global CATEGORIA_PROVAS_ID
        CATEGORIA_PROVAS_ID = categoria.id
        await ctx.reply("✅ Categoria das provas definida.", ephemeral=True)

    # ========= EMBED INICIAL ========= #
    @commands.hybrid_command(name="iniciarprova")
    async def iniciarprova(self, ctx):
        if not (ctx.author.guild_permissions.administrator or any(r.id in DIRETOR_ROLE_IDS for r in ctx.author.roles)):
            return await ctx.reply("❌ Sem permissão.", ephemeral=True)

        embed = discord.Embed(
            title="📄 EDITAL PRF - PROVA OFICIAL",
            description=(
                "Clique no botão abaixo para iniciar a prova.\n\n"
                "📌 **Regras:**\n"
                "• Tempo limite: 10 minutos\n"
                "• 10 questões\n"
                "• Nota mínima: 6\n"
                "• Fraudes = eliminação\n\n"
                "⚠️ Ao iniciar você concorda com o edital."
            ),
            color=0x1F3A8A
        )

        await ctx.send(embed=embed, view=BotaoIniciar(self))

    # ========= ENVIO PERGUNTA ========= #
    async def enviar_questao(self, user, canal):
        prova = self.dados["provas"][str(user.id)]
        q = prova["questoes"][prova["indice"]]

        letras = ["A", "B", "C", "D"]
        campo = "\n".join([f"**{letras[i]}** — {a}" for i, a in enumerate(q["alternativas"])])

        embed = discord.Embed(
            title=f"Questão {prova['indice']+1}/{NUM_PERGUNTAS}",
            description=f"**{q['pergunta']}**",
            color=0x374151
        )
        embed.add_field(name="Alternativas", value=campo, inline=False)
        embed.set_footer(text="PRF - Sistema de Avaliação Oficial")

        await canal.send(user.mention, embed=embed, view=RespostaView(self, user, canal))

    # ========= FINALIZAR ========= #
    async def finalizar(self, user, canal, tempo=False):
        prova = self.dados["provas"].pop(str(user.id))
        salvar(self.dados)

        pontos = sum(1 for i,q in enumerate(prova["questoes"]) if prova["respostas"][i] == q["correta"])
        aprovado = pontos >= MIN_PONTOS

        titulo = "✅ APROVADO" if aprovado else "❌ REPROVADO"
        cor = 0x16a34a if aprovado else 0xdc2626

        embed = discord.Embed(title="📊 RESULTADO FINAL", color=cor)
        embed.add_field(name="Candidato", value=user.mention, inline=False)
        embed.add_field(name="Pontuação", value=f"{pontos}/{NUM_PERGUNTAS}", inline=False)
        embed.add_field(name="Situação", value=titulo, inline=False)

        if tempo:
            embed.add_field(name="Motivo", value="Tempo esgotado", inline=False)

        embed.set_footer(text="PRF • Resultado Oficial")

        await canal.send(embed=embed)

        if CANAL_RESULTADOS_ID:
            c = self.bot.get_channel(CANAL_RESULTADOS_ID)
            if c:
                await c.send(embed=embed)

        await asyncio.sleep(20)
        await canal.delete()

    # ========= LIMPEZA ========= #
    @tasks.loop(hours=1)
    async def _limpar(self):
        agora = datetime.utcnow()
        for uid in list(self.dados["provas"]):
            inicio = datetime.fromisoformat(self.dados["provas"][uid]["inicio"])
            if (agora - inicio).total_seconds() >= TEMPO_LIMITE:
                try:
                    canal = self.bot.get_channel(self.dados["provas"][uid]["canal"])
                    if canal:
                        user = await self.bot.fetch_user(int(uid))
                        await self.finalizar(user, canal, tempo=True)
                except:
                    pass

# ================= BOTAO DE INICIO ================= #
class BotaoIniciar(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="✅ INICIAR PROVA", style=discord.ButtonStyle.success)
    async def iniciar(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        agora = datetime.utcnow()

        if uid in self.cog.dados["tentativas"]:
            dt = datetime.fromisoformat(self.cog.dados["tentativas"][uid])
            if (agora - dt).total_seconds() < COOLDOWN_SEGUNDOS:
                return await interaction.response.send_message("⏳ Você está em cooldown.", ephemeral=True)

        guild = interaction.guild
        categoria = guild.get_channel(CATEGORIA_PROVAS_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
        }

        for rid in DIRETOR_ROLE_IDS:
            r = guild.get_role(rid)
            if r:
                overwrites[r] = discord.PermissionOverwrite(read_messages=True)

        canal = await guild.create_text_channel(
            name=f"prova-{interaction.user.name}",
            category=categoria,
            overwrites=overwrites
        )

        perguntas = random.sample(PERGUNTAS, NUM_PERGUNTAS)
        questoes = []

        for p in perguntas:
            alts = p["alternativas"].copy()
            random.shuffle(alts)
            correta = alts.index(p["alternativas"][p["correta"]])
            questoes.append({"pergunta": p["pergunta"], "alternativas": alts, "correta": correta})

        self.cog.dados["provas"][uid] = {
            "questoes": questoes,
            "indice": 0,
            "respostas": [],
            "inicio": agora.isoformat(),
            "canal": canal.id
        }

        self.cog.dados["tentativas"][uid] = agora.isoformat()
        salvar(self.cog.dados)

        await interaction.response.send_message(f"✅ Prova iniciada: {canal.mention}", ephemeral=True)
        await self.cog.enviar_questao(interaction.user, canal)

# ================= BOTÕES DE RESPOSTA ================= #
class RespostaView(discord.ui.View):
    def __init__(self, cog, user, canal):
        super().__init__(timeout=None)
        self.cog = cog
        self.user = user
        self.canal = canal

    async def responder(self, interaction, n):
        prova = self.cog.dados["provas"].get(str(self.user.id))
        if not prova:
            return

        prova["respostas"].append(n)
        prova["indice"] += 1
        salvar(self.cog.dados)

        await interaction.message.delete()

        if prova["indice"] < NUM_PERGUNTAS:
            await self.cog.enviar_questao(self.user, self.canal)
        else:
            await self.cog.finalizar(self.user, self.canal)

    @discord.ui.button(label="A", style=discord.ButtonStyle.secondary)
    async def a(self, i, _): await self.responder(i, 0)

    @discord.ui.button(label="B", style=discord.ButtonStyle.secondary)
    async def b(self, i, _): await self.responder(i, 1)

    @discord.ui.button(label="C", style=discord.ButtonStyle.secondary)
    async def c(self, i, _): await self.responder(i, 2)

    @discord.ui.button(label="D", style=discord.ButtonStyle.secondary)
    async def d(self, i, _): await self.responder(i, 3)

# ========= SETUP ========= #
async def setup(bot):
    await bot.add_cog(Edital(bot))
    print("✅ Edital carregado corretamente")

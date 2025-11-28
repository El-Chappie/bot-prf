import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta

ARQ_PROVA = "edital_prova_data.json"

DIRETOR_ROLE_IDS = [1443387915689398395, 1443387916633247766]  # IDs dos cargos diretores, configure no seu main antes de carregar o cog
CANAL_RESULT_ID = 1443620398016237589
CANAL_LOG_ID = 1443620192914640907

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


class ProvaView(discord.ui.View):
    def __init__(self, bot, canal, user, cog):
        super().__init__(timeout=600)  # 10 minutos timeout
        self.bot = bot
        self.channel = canal
        self.user = user
        self.cog = cog
        self.dados = cog.dados
        self.letras = ["A", "B", "C", "D"]

        self.indice = 0
        self.questoes = random.sample(PERGUNTAS, NUM_PERGUNTAS)
        self.questoes_formatadas = []
        for p in self.questoes:
            alts = p["alternativas"].copy()
            random.shuffle(alts)
            correta = alts.index(p["alternativas"][p["correta"]])
            self.questoes_formatadas.append({"pergunta": p["pergunta"], "alternativas": alts, "correta": correta})

        self.respostas = []

        # Criar botões dinamicamente
        for i, letra in enumerate(self.letras):
            self.add_item(RespostaButton(letra, i, self))

    async def start(self):
        # Salvar prova no cog.dados para poder gerenciar estado
        self.dados["provas"][str(self.user.id)] = {
            "questoes": self.questoes_formatadas,
            "respostas": [],
            "indice": 0,
            "inicio": datetime.utcnow().isoformat()
        }
        salvar(self.dados)
        await self.enviar_pergunta()

    async def enviar_pergunta(self):
        indice = self.dados["provas"][str(self.user.id)]["indice"]
        q = self.questoes_formatadas[indice]
        texto = "\n".join(f"**{self.letras[i]}** — {alt}" for i, alt in enumerate(q["alternativas"]))
        embed = discord.Embed(
            title=f"Questão {indice+1}/{NUM_PERGUNTAS}",
            description=f"{q['pergunta']}\n\n{texto}",
            color=0x3498db
        )
        await self.channel.send(embed=embed, view=self)

    async def processar_resposta(self, letra_idx):
        dados_prova = self.dados["provas"][str(self.user.id)]
        dados_prova["respostas"].append(letra_idx)
        dados_prova["indice"] += 1
        salvar(self.dados)

        if dados_prova["indice"] < NUM_PERGUNTAS:
            await self.enviar_pergunta()
        else:
            await self.finalizar()

    async def finalizar(self):
        dados_prova = self.dados["provas"].pop(str(self.user.id))
        salvar(self.dados)

        pontos = sum(
            1 for i, q in enumerate(dados_prova["questoes"]) if dados_prova["respostas"][i] == q["correta"]
        )
        aprovado = pontos >= MIN_PONTOS
        status = "✅ APROVADO" if aprovado else "❌ REPROVADO"
        embed = discord.Embed(
            title="Resultado da Prova",
            description=f"{self.user.mention} fez a prova\nPontuação: {pontos}/{NUM_PERGUNTAS}\n{status}",
            color=0x2ecc71 if aprovado else 0xe74c3c
        )
        await self.channel.send(embed=embed)

        # Enviar no canal de resultados, se configurado
        if self.cog.result_channel:
            c = self.bot.get_channel(self.cog.result_channel)
            if c:
                await c.send(embed=embed)

        # Enviar no canal de logs, se configurado
        if self.cog.log_channel:
            c = self.bot.get_channel(self.cog.log_channel)
            if c:
                await c.send(embed=discord.Embed(title=f"Log {self.user}", description=f"Pontuação: {pontos}", color=0x7f8c8d))

        # Deletar canal privado de prova
        try:
            await self.channel.delete(reason="Prova finalizada")
        except:
            pass


class RespostaButton(discord.ui.Button):
    def __init__(self, letra, indice, view):
        super().__init__(label=letra, style=discord.ButtonStyle.primary)
        self.letra_idx = indice
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user.id:
            await interaction.response.send_message("Essa prova não é para você.", ephemeral=True)
            return

        await interaction.response.defer()
        await self.view.processar_resposta(self.letra_idx)
        await interaction.followup.send(f"Resposta {self.label} registrada.", ephemeral=True)


class IniciarProvaButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(label="Iniciar Prova", style=discord.ButtonStyle.success)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild

        if not guild:
            await interaction.response.send_message("Este comando só pode ser usado dentro do servidor.", ephemeral=True)
            return

        # Verifica se o usuário já está fazendo a prova
        if user.id in self.cog.provas_ativas:
            await interaction.response.send_message("Você já está fazendo uma prova.", ephemeral=True)
            return

        # Defer para evitar timeout
        await interaction.response.defer(ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role_id in DIRETOR_ROLE_IDS:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        categoria = None
        if hasattr(self.cog, "categoria_provas_id") and self.cog.categoria_provas_id:
            categoria = guild.get_channel(self.cog.categoria_provas_id)

        nome_canal = f"prova-{user.name}".lower().replace(" ", "-")[:90]

        channel = await guild.create_text_channel(nome_canal, overwrites=overwrites, category=categoria, reason="Canal privado para prova")

        voz_canal = None
        try:
            if user.voice and user.voice.channel:
                overwrites_voice = {
                    guild.default_role: discord.PermissionOverwrite(connect=False),
                    user: discord.PermissionOverwrite(connect=True, speak=True)
                }
                for role_id in DIRETOR_ROLE_IDS:
                    role = guild.get_role(role_id)
                    if role:
                        overwrites_voice[role] = discord.PermissionOverwrite(connect=True, speak=True)

                voz_canal = await guild.create_voice_channel(f"Prova VC - {user.name}", overwrites=overwrites_voice, category=categoria, reason="Canal de voz privado para prova")
                await user.move_to(voz_canal)
        except Exception as e:
            print(f"Erro ao mover usuário para canal de voz: {e}")

        prova_view = ProvaView(self.cog.bot, channel, user, self.cog)
        self.cog.provas_ativas[user.id] = prova_view
        await prova_view.start()

        await interaction.followup.send(
            f"Canal privado criado: {channel.mention}" + (f" e canal de voz criado: {voz_canal.mention}" if voz_canal else ""),
            ephemeral=True
        )


class Edital(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dados = carregar()
        self.result_channel = CANAL_RESULT_ID
        self.log_channel = CANAL_LOG_ID
        self.categoria_provas_id = None  # Id da categoria para os canais de prova (pode setar via comando)
        self.provas_ativas = {}  # user_id: ProvaView instance
        self._limpar.start()

    def cog_unload(self):
        self._limpar.cancel()

    @commands.hybrid_command(name="setcanalresult")
    @commands.has_permissions(administrator=True)
    async def setcanalresult(self, ctx, canal: discord.TextChannel):
        self.result_channel = canal.id
        await ctx.reply(embed=discord.Embed(
            title="✅ Configurado",
            description=f"Canal de resultados definido: {canal.mention}",
            color=0x2ecc71
        ), ephemeral=True)

    @commands.hybrid_command(name="setcategorianoticias")
    @commands.has_permissions(administrator=True)
    async def setcategorianoticias(self, ctx, categoria: discord.CategoryChannel):
        self.categoria_provas_id = categoria.id
        await ctx.reply(embed=discord.Embed(
            title="✅ Configurado",
            description=f"Categoria para canais de prova definida: {categoria.name}",
            color=0x2ecc71
        ), ephemeral=True)

    @commands.hybrid_command(name="enviarprova")
    @commands.has_any_role(*DIRETOR_ROLE_IDS)
    async def enviarprova(self, ctx):
        embed = discord.Embed(
            title="📋 Prova PRF",
            description=(
                "Você pode iniciar a prova clicando no botão abaixo.\n"
                "A prova terá 10 perguntas e você terá 10 minutos para responder.\n"
                "Se não terminar no tempo, será reprovado automaticamente.\n"
                "Ao iniciar, será criado um canal privado para a prova com você, os diretores e o bot."
            ),
            color=0x3498db
        )
        view = discord.ui.View()
        view.add_item(IniciarProvaButton(self))
        await ctx.send(embed=embed, view=view)

    @tasks.loop(hours=24)
    async def _limpar(self):
        agora = datetime.utcnow()
        for k, v in list(self.dados["tentativas"].items()):
            dt = datetime.fromisoformat(v)
            if agora - dt > timedelta(days=1):
                self.dados["tentativas"].pop(k)
        salvar(self.dados)

import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
import random
from datetime import datetime, timedelta

ARQ_PROVA = "edital_prova_data.json"

DIRETOR_ROLE_IDS = []  # IDs dos cargos de diretor para permissões
CANAL_CONTROLE_ID = None  # Canal onde serão postadas as provas com botões para controle
CANAL_RESULT_ID = None
CANAL_LOG_ID = None

NUM_PERGUNTAS = 10
MIN_PONTOS = 6
TEMPO_LIMITE = 600  # 10 minutos em segundos

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
        return {}
    with open(ARQ_PROVA, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar(dados):
    with open(ARQ_PROVA, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


class ProvaView(discord.ui.View):
    def __init__(self, bot, user_id, prova_data, cog):
        super().__init__(timeout=600)  # 10 minutos timeout
        self.bot = bot
        self.user_id = user_id
        self.prova_data = prova_data
        self.cog = cog
        self.current_index = 0
        self.message = None  # Mensagem onde a prova está sendo feita

        # Criar botões de alternativas (A,B,C,D)
        for i, letra in enumerate(["A", "B", "C", "D"]):
            self.add_item(RespostaBotao(letra, i, self))

    async def start(self, ctx):
        # Envia a embed da primeira pergunta com os botões
        embed = self.criar_embed()
        self.message = await ctx.send(embed=embed, view=self)

        # Começa a contagem do timeout da prova
        self.bot.loop.create_task(self.timeout_task())

    def criar_embed(self):
        pergunta = self.prova_data["questoes"][self.current_index]
        descricao = pergunta["pergunta"] + "\n\n"
        for idx, alt in enumerate(pergunta["alternativas"]):
            descricao += f"**{['A','B','C','D'][idx]}** — {alt}\n"
        embed = discord.Embed(
            title=f"Questão {self.current_index + 1}/{NUM_PERGUNTAS}",
            description=descricao,
            color=discord.Color.blurple()
        )
        return embed

    async def timeout_task(self):
        await asyncio.sleep(TEMPO_LIMITE)
        if not self.is_finished():
            await self.terminar_prova(timeout=True)

    def is_finished(self):
        return self.current_index >= NUM_PERGUNTAS

    async def terminar_prova(self, timeout=False):
        # Desabilita botões e mostra resultado
        self.disable_all_items()
        await self.message.edit(view=self)

        uid = str(self.user_id)
        respostas = self.prova_data["respostas"]
        questoes = self.prova_data["questoes"]

        pontos = sum(1 for i,q in enumerate(questoes) if i < len(respostas) and respostas[i] == q["correta"])
        aprovado = pontos >= MIN_PONTOS
        status = "✅ APROVADO" if aprovado else "❌ REPROVADO"

        resultado_desc = f"{pontos}/{NUM_PERGUNTAS}\n{status}"
        if timeout:
            resultado_desc += "\n\n⏰ Tempo esgotado. Prova encerrada."

        try:
            user = await self.bot.fetch_user(self.user_id)
            await user.send(embed=discord.Embed(title="Resultado da Prova", description=resultado_desc,
                                                color=discord.Color.green() if aprovado else discord.Color.red()))
        except:
            pass  # Usuário bloqueou DM?

        canal_result = self.cog.bot.get_channel(CANAL_RESULT_ID)
        if canal_result:
            await canal_result.send(embed=discord.Embed(description=f"<@{self.user_id}> — {status}",
                                                        color=discord.Color.green() if aprovado else discord.Color.red()))

        canal_log = self.cog.bot.get_channel(CANAL_LOG_ID)
        if canal_log:
            await canal_log.send(embed=discord.Embed(title=f"Log Prova <@{self.user_id}>", description=f"Pontuação: {pontos}",
                                                     color=discord.Color.greyple()))

        # Remove a prova da lista ativa
        self.cog.provas_ativas.pop(uid, None)


class RespostaBotao(discord.ui.Button):
    def __init__(self, label, index, view):
        super().__init__(style=discord.ButtonStyle.primary, label=label, custom_id=f"resposta_{index}")
        self.view = view
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            await interaction.response.send_message("Essa prova não é para você!", ephemeral=True)
            return

        # Registra resposta
        self.view.prova_data["respostas"].append(self.index)
        self.view.current_index += 1

        if self.view.current_index >= NUM_PERGUNTAS:
            # Prova finalizada
            await interaction.response.defer()
            await self.view.terminar_prova()
        else:
            # Atualiza embed para próxima pergunta
            embed = self.view.criar_embed()
            await interaction.response.edit_message(embed=embed, view=self.view)


class CancelarProvaButton(discord.ui.Button):
    def __init__(self, cog, user_id):
        super().__init__(label="Cancelar Prova", style=discord.ButtonStyle.danger)
        self.cog = cog
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        # Apenas diretor pode cancelar
        if not any(r.id in DIRETOR_ROLE_IDS for r in interaction.user.roles):
            await interaction.response.send_message("❌ Apenas diretores podem cancelar.", ephemeral=True)
            return

        # Cancela a prova
        uid = str(self.user_id)
        prova = self.cog.provas_ativas.get(uid)
        if not prova:
            await interaction.response.send_message("Prova já finalizada ou não encontrada.", ephemeral=True)
            return

        # Remove prova ativa
        self.cog.provas_ativas.pop(uid)
        # Desabilita o botão
        self.disabled = True
        await interaction.message.edit(view=self.view)
        await interaction.response.send_message(f"Prova do <@{self.user_id}> cancelada.", ephemeral=False)

        # Informa usuário
        try:
            user = await self.cog.bot.fetch_user(self.user_id)
            await user.send(embed=discord.Embed(title="Prova Cancelada", description="Sua prova foi cancelada pelo diretor.",
                                                color=discord.Color.red()))
        except:
            pass


class Edital(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.provas_ativas = {}  # { user_id : ProvaView }
        self.dados = carregar()

    @commands.hybrid_command(name="setcanalcontrole")
    @commands.has_permissions(administrator=True)
    async def set_canal_controle(self, ctx, canal: discord.TextChannel):
        global CANAL_CONTROLE_ID
        CANAL_CONTROLE_ID = canal.id
        await ctx.reply(f"Canal de controle definido: {canal.mention}", ephemeral=True)

    @commands.hybrid_command(name="setcanalresult")
    @commands.has_permissions(administrator=True)
    async def set_canal_result(self, ctx, canal: discord.TextChannel):
        global CANAL_RESULT_ID
        CANAL_RESULT_ID = canal.id
        await ctx.reply(f"Canal de resultados definido: {canal.mention}", ephemeral=True)

    @commands.hybrid_command(name="setcanallog")
    @commands.has_permissions(administrator=True)
    async def set_canal_log(self, ctx, canal: discord.TextChannel):
        global CANAL_LOG_ID
        CANAL_LOG_ID = canal.id
        await ctx.reply(f"Canal de logs definido: {canal.mention}", ephemeral=True)

    @commands.hybrid_command(name="iniciarprova")
    async def iniciar_prova(self, ctx, membro: discord.Member):
        # Permissão: diretor ou admin
        if not (ctx.author.guild_permissions.administrator or any(r.id in DIRETOR_ROLE_IDS for r in ctx.author.roles)):
            await ctx.reply("❌ Sem permissão.", ephemeral=True)
            return

        uid = str(membro.id)
        if uid in self.provas_ativas:
            await ctx.reply("❌ Este membro já está realizando a prova.", ephemeral=True)
            return

        # Seleciona perguntas randomizadas
        perguntas = random.sample(PERGUNTAS, NUM_PERGUNTAS)
        questoes = []
        for p in perguntas:
            alts = p["alternativas"].copy()
            random.shuffle(alts)
            correta = alts.index(p["alternativas"][p["correta"]])
            questoes.append({"pergunta": p["pergunta"], "alternativas": alts, "correta": correta})

        prova_data = {
            "questoes": questoes,
            "respostas": []
        }

        view = ProvaView(self.bot, membro.id, prova_data, self)
        self.provas_ativas[uid] = view

        # Envia embed no canal controle com botão de cancelar para os diretores
        canal_controle = self.bot.get_channel(CANAL_CONTROLE_ID)
        if canal_controle:
            embed = discord.Embed(
                title="📄 Prova iniciada",
                description=f"Prova iniciada para {membro.mention}.\n10 minutos para completar.\nDiretores podem cancelar abaixo.",
                color=discord.Color.blue()
            )
            view_cancel = discord.ui.View()
            view_cancel.add_item(CancelarProvaButton(self, membro.id))
            await canal_controle.send(embed=embed, view=view_cancel)

        await ctx.reply(f"Prova iniciada para {membro.mention}. Instruções enviadas no canal.", ephemeral=True)

        # Envia prova para o canal atual (ou privado), o ideal é criar um canal privado ou categoria para isso
        await view.start(ctx)

async def setup(bot):
    await bot.add_cog(Edital(bot))
    print("✅ Edital interativo carregado")

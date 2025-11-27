# edital.py

import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta

ARQ_PROVA = "edital_prova_data.json"

# CONFIGURAÇÕES DEFAULT - Você deve alterar ou usar o método configurar() para setar
DIRETOR_ROLE_IDS = []  # Exemplo: [1443387935700291697]
CANAL_LOGS_ID = None
CANAL_ANUNCIOS_ID = None

COOLDOWN_SEGUNDOS = 3600
MIN_PONTUACAO = 6
NUM_PERGUNTAS_PROVA = 10

PERGUNTAS = [
    {
        "pergunta": "Qual é a capital do Brasil?",
        "alternativas": ["Rio de Janeiro", "Brasília", "São Paulo", "Salvador"],
        "correta": 1
    },
    {
        "pergunta": "Qual o maior planeta do sistema solar?",
        "alternativas": ["Terra", "Marte", "Júpiter", "Saturno"],
        "correta": 2
    },
    {
        "pergunta": "Quem descobriu a América?",
        "alternativas": ["Cristóvão Colombo", "Vasco da Gama", "Pedro Álvares Cabral", "Fernão de Magalhães"],
        "correta": 0
    },
    {
        "pergunta": "Qual o elemento químico com símbolo 'O'?",
        "alternativas": ["Ouro", "Oxigênio", "Prata", "Hélio"],
        "correta": 1
    },
    {
        "pergunta": "Qual a fórmula da água?",
        "alternativas": ["H2O", "CO2", "NaCl", "O2"],
        "correta": 0
    },
    {
        "pergunta": "Em que ano ocorreu a Revolução Francesa?",
        "alternativas": ["1789", "1776", "1812", "1804"],
        "correta": 0
    },
    {
        "pergunta": "Qual é a moeda oficial do Japão?",
        "alternativas": ["Yen", "Won", "Dólar", "Euro"],
        "correta": 0
    },
    {
        "pergunta": "Quem pintou a Mona Lisa?",
        "alternativas": ["Leonardo da Vinci", "Michelangelo", "Raphael", "Donatello"],
        "correta": 0
    },
    {
        "pergunta": "Qual é o maior oceano do mundo?",
        "alternativas": ["Atlântico", "Índico", "Pacífico", "Ártico"],
        "correta": 2
    },
    {
        "pergunta": "Qual a linguagem de programação usada para bots Discord na maioria dos exemplos?",
        "alternativas": ["Python", "Java", "C#", "Ruby"],
        "correta": 0
    },
    # Perguntas reserva extras para embaralhar
    {
        "pergunta": "Quem foi o primeiro presidente dos Estados Unidos?",
        "alternativas": ["Abraham Lincoln", "George Washington", "Thomas Jefferson", "John Adams"],
        "correta": 1
    },
    {
        "pergunta": "Qual país é conhecido como a terra do sol nascente?",
        "alternativas": ["China", "Japão", "Coreia do Sul", "Tailândia"],
        "correta": 1
    },
    {
        "pergunta": "Qual a capital da França?",
        "alternativas": ["Lyon", "Paris", "Marselha", "Nice"],
        "correta": 1
    },
]

def salvar_dados(dados):
    with open(ARQ_PROVA, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_dados():
    if not os.path.exists(ARQ_PROVA):
        return {"tentativas": {}, "provas": {}}
    with open(ARQ_PROVA, "r", encoding="utf-8") as f:
        return json.load(f)

class EditalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dados = carregar_dados()
        self.limpar_dados_antigos.start()

    def cog_unload(self):
        self.limpar_dados_antigos.cancel()

    # Configurar IDs após criar o cog
    def configurar(self, diretor_roles: list, canal_logs_id: int, canal_anuncios_id: int):
        global DIRETOR_ROLE_IDS, CANAL_LOGS_ID, CANAL_ANUNCIOS_ID
        DIRETOR_ROLE_IDS = diretor_roles
        CANAL_LOGS_ID = canal_logs_id
        CANAL_ANUNCIOS_ID = canal_anuncios_id

    def eh_diretor(self, member: discord.Member):
        return any(role.id in DIRETOR_ROLE_IDS for role in member.roles)

    @commands.hybrid_command(name="enviarprova", description="Envia embed de explicação da prova (só diretores)")
    async def enviarprova(self, ctx: commands.Context):
        if not self.eh_diretor(ctx.author):
            return await ctx.send("❌ Apenas diretores podem usar este comando.", ephemeral=True)

        embed = discord.Embed(
            title="📝 Prova do Edital",
            description=(
                "Você está prestes a iniciar a prova com **10 questões** de múltipla escolha.\n"
                "Cada questão possui 4 alternativas, e apenas uma correta.\n"
                f"Para ser aprovado, é necessário acertar no mínimo {MIN_PONTUACAO} questões.\n\n"
                "Clique no botão abaixo para iniciar a prova.\n"
                "Você poderá tentar novamente somente após 1 hora da última tentativa."
            ),
            color=0x3498DB
        )
        embed.set_footer(text="Sistema de Prova • Polícia Rodoviária Federal")

        class BotaoIniciar(discord.ui.View):
            def __init__(self, cog, autor):
                super().__init__(timeout=None)
                self.cog = cog
                self.autor = autor
                self.iniciado = False  # Previne múltiplos cliques

            @discord.ui.button(label="Iniciar Prova", style=discord.ButtonStyle.green, custom_id="botao_iniciar_prova")
            async def iniciar(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != self.autor:
                    return await interaction.response.send_message("❌ Apenas quem clicou pode usar este botão.", ephemeral=True)

                if self.iniciado:
                    return await interaction.response.send_message("⏳ Prova já iniciada.", ephemeral=True)
                self.iniciado = True

                await self.cog.iniciar_prova(interaction.user, interaction)
                self.clear_items()
                await interaction.message.edit(view=self)

        view = BotaoIniciar(self, ctx.author)
        await ctx.send(embed=embed, view=view)

    async def iniciar_prova(self, user: discord.Member, interaction: discord.Interaction):
        now = datetime.utcnow()
        uid = str(user.id)

        ult_tentativa = self.dados["tentativas"].get(uid)
        if ult_tentativa:
            dt_ultima = datetime.fromisoformat(ult_tentativa)
            diff = now - dt_ultima
            if diff.total_seconds() < COOLDOWN_SEGUNDOS:
                seg_rest = int(COOLDOWN_SEGUNDOS - diff.total_seconds())
                return await interaction.response.send_message(
                    f"⏳ Você só poderá tentar novamente daqui {seg_rest} segundos (~{seg_rest//60} minutos).",
                    ephemeral=True
                )

        perguntas_disponiveis = list(range(len(PERGUNTAS)))
        if len(perguntas_disponiveis) < NUM_PERGUNTAS_PROVA:
            return await interaction.response.send_message(
                "❌ Não há perguntas suficientes cadastradas para montar a prova.",
                ephemeral=True
            )

        questoes_selecionadas = random.sample(perguntas_disponiveis, NUM_PERGUNTAS_PROVA)

        prova = []
        for idx in questoes_selecionadas:
            p = PERGUNTAS[idx]
            alt = p["alternativas"].copy()
            random.shuffle(alt)
            correta_original = p["correta"]  # corrigido aqui
            nova_correta = alt.index(p["alternativas"][correta_original])
            prova.append({
                "pergunta": p["pergunta"],
                "alternativas": alt,
                "correta": nova_correta
            })

        guild = user.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }
        canal = await guild.create_text_channel(
            name=f"prova-{user.name}".lower(),
            overwrites=overwrites,
            reason="Canal privado para prova edital"
        )

        self.dados["provas"][uid] = {
            "canal_id": canal.id,
            "data_inicio": now.isoformat(),
            "respostas": [None]*NUM_PERGUNTAS_PROVA,
            "indice_atual": 0,
            "questoes": prova
        }
        self.dados["tentativas"][uid] = now.isoformat()
        salvar_dados(self.dados)

        await interaction.response.send_message(
            f"✅ Canal privado criado: {canal.mention}. Por favor, responda as perguntas por lá.",
            ephemeral=True
        )
        await self.enviar_pergunta(user, canal)

    async def enviar_pergunta(self, user: discord.Member, canal: discord.TextChannel):
        uid = str(user.id)
        prova = self.dados["provas"].get(uid)
        if not prova:
            await canal.send("❌ Nenhuma prova encontrada para você.")
            return

        indice = prova["indice_atual"]
        if indice >= NUM_PERGUNTAS_PROVA:
            await canal.send("❌ Todas as perguntas já foram respondidas.")
            return

        questao = prova["questoes"][indice]
        embed = discord.Embed(
            title=f"Questão {indice+1} de {NUM_PERGUNTAS_PROVA}",
            description=questao["pergunta"],
            color=0x3498DB
        )
        letras = ["A", "B", "C", "D"]
        texto_alts = ""
        for i, alt in enumerate(questao["alternativas"]):
            texto_alts += f"**{letras[i]}** - {alt}\n"
        embed.add_field(name="Alternativas", value=texto_alts, inline=False)
        embed.set_footer(text="Responda clicando no botão correspondente.")

        class ResponderView(discord.ui.View):
            def __init__(self, cog, user):
                super().__init__(timeout=None)
                self.cog = cog
                self.user = user
                self.respondido = False  # evita múltiplas respostas

            @discord.ui.button(label="A", style=discord.ButtonStyle.secondary, custom_id="resp_A")
            async def resp_a(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.processar_resposta(interaction, 0)

            @discord.ui.button(label="B", style=discord.ButtonStyle.secondary, custom_id="resp_B")
            async def resp_b(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.processar_resposta(interaction, 1)

            @discord.ui.button(label="C", style=discord.ButtonStyle.secondary, custom_id="resp_C")
            async def resp_c(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.processar_resposta(interaction, 2)

            @discord.ui.button(label="D", style=discord.ButtonStyle.secondary, custom_id="resp_D")
            async def resp_d(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.processar_resposta(interaction, 3)

            async def processar_resposta(self, interaction: discord.Interaction, escolha: int):
                if interaction.user != self.user:
                    return await interaction.response.send_message("❌ Este botão não é para você.", ephemeral=True)
                if self.respondido:
                    return await interaction.response.send_message("⏳ Você já respondeu esta questão.", ephemeral=True)
                self.respondido = True

                uid = str(self.user.id)
                prova = self.cog.dados["provas"].get(uid)
                if not prova:
                    return await interaction.response.send_message("❌ Prova não encontrada.", ephemeral=True)

                indice = prova["indice_atual"]
                if indice >= NUM_PERGUNTAS_PROVA:
                    return await interaction.response.send_message("❌ Você já terminou a prova.", ephemeral=True)

                prova["respostas"][indice] = escolha
                prova["indice_atual"] += 1
                salvar_dados(self.cog.dados)

                await interaction.response.send_message(f"✅ Resposta registrada: {['A','B','C','D'][escolha]}", ephemeral=True)

                if prova["indice_atual"] >= NUM_PERGUNTAS_PROVA:
                    await self.cog.finalizar_prova(self.user)
                else:
                    canal = self.user.guild.get_channel(prova["canal_id"])
                    if canal:
                        await self.cog.enviar_pergunta(self.user, canal)

                self.clear_items()
                await interaction.message.edit(view=self)

        view = ResponderView(self, user)
        await canal.send(embed=embed, view=view)

    async def finalizar_prova(self, user: discord.Member):
        uid = str(user.id)
        prova = self.dados["provas"].get(uid)
        if not prova:
            return
        respostas = prova["respostas"]
        questoes = prova["questoes"]

        pontos = 0
        for i, resp in enumerate(respostas):
            if resp is not None and resp == questoes[i]["correta"]:
                pontos += 1

        aprovado = pontos >= MIN_PONTUACAO

        guild = user.guild
        canal_logs = guild.get_channel(CANAL_LOGS_ID) if CANAL_LOGS_ID else None
        canal_anuncios = guild.get_channel(CANAL_ANUNCIOS_ID) if CANAL_ANUNCIOS_ID else None

        texto_respostas = ""
        letras = ["A", "B", "C", "D"]
        for i, (resp, questao) in enumerate(zip(respostas, questoes)):
            resp_letra = letras[resp] if resp is not None else "Nenhuma"
            correta_letra = letras[questao["correta"]]
            texto_respostas += f"**Q{i+1}**: {questao['pergunta']}\n"
            texto_respostas += f"Resposta do usuário: {resp_letra}\n"
            texto_respostas += f"Resposta correta: {correta_letra}\n\n"

        embed_log = discord.Embed(
            title=f"Prova finalizada - {user}",
            description=f"Pontuação: {pontos}/{NUM_PERGUNTAS_PROVA} - {'APROVADO' if aprovado else 'REPROVADO'}\n\n{texto_respostas}",
            color=0x2ECC71 if aprovado else 0xE74C3C,
            timestamp=datetime.utcnow()
        )
        embed_log.set_footer(text="Sistema de Prova • Polícia Rodoviária Federal")

        if canal_logs:
            try:
                await canal_logs.send(embed=embed_log)
            except Exception:
                pass

        if canal_anuncios:
            emb_anuncio = discord.Embed(
                title="Resultado da Prova",
                description=f"O usuário {user.mention} foi **{'APROVADO' if aprovado else 'REPROVADO'}** na prova do edital.",
                color=0x2ECC71 if aprovado else 0xE74C3C,
                timestamp=datetime.utcnow()
            )
            emb_anuncio.set_footer(text="Sistema de Prova • Polícia Rodoviária Federal")
            try:
                await canal_anuncios.send(embed=emb_anuncio)
            except Exception:
                pass

        canal = guild.get_channel(prova["canal_id"])
        if canal:
            try:
                await canal.delete(reason="Prova finalizada e canal privado removido.")
            except Exception:
                pass

        self.dados["provas"].pop(uid, None)
        salvar_dados(self.dados)

    @tasks.loop(hours=24)
    async def limpar_dados_antigos(self):
        # Limpa dados de provas finalizadas com mais de 7 dias
        agora = datetime.utcnow()
        alterado = False

        for uid, prova in list(self.dados["provas"].items()):
            try:
                data_inicio = datetime.fromisoformat(prova.get("data_inicio"))
            except Exception:
                continue
            if (agora - data_inicio) > timedelta(days=7):
                self.dados["provas"].pop(uid, None)
                alterado = True

        for uid, tentativa in list(self.dados["tentativas"].items()):
            try:
                data_tentativa = datetime.fromisoformat(tentativa)
            except Exception:
                continue
            if (agora - data_tentativa) > timedelta(days=30):
                self.dados["tentativas"].pop(uid, None)
                alterado = True

        if alterado:
            salvar_dados(self.dados)

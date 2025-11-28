import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta

ARQ_PROVA = "edital_prova_data.json"

DIRETOR_ROLE_IDS = [1443387915689398395, 1443387916633247766]  # IDs dos cargos de diretor para liberar acesso ao botão
CANAL_RESULT_ID = 1443620398016237589  # Canal para anunciar resultado

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
        self._limpar.start()

    def cog_unload(self):
        self._limpar.cancel()

    @commands.hybrid_command(name="setcanalresultado", description="Define canal público de resultados")
    @commands.has_permissions(administrator=True)
    async def setcanalresultado(self, ctx, canal: discord.TextChannel):
        self.result_channel = canal.id
        await ctx.reply(f"✅ Canal de resultados definido: {canal.mention}", ephemeral=True)

    @commands.hybrid_command(name="iniciarprova", description="Envia embed com botão para iniciar prova (diretores)")
    @commands.has_any_role(*DIRETOR_ROLE_IDS)
    async def iniciarprova(self, ctx):
        embed = discord.Embed(
            title="📋 Prova do Edital",
            description=(
                "Clique no botão abaixo para iniciar sua prova.\n"
                "Você terá 10 minutos para completá-la.\n"
                "Boa sorte!"
            ),
            color=0x3498DB
        )
        view = self.BotaoIniciarProva(self)
        await ctx.send(embed=embed, view=view)

    class BotaoIniciarProva(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="Iniciar Prova", style=discord.ButtonStyle.primary)
        async def iniciar_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            uid = str(interaction.user.id)
            # Verifica cooldown
            agora = datetime.utcnow()
            tentativas = self.cog.dados.get("tentativas", {})
            if uid in tentativas:
                dt = datetime.fromisoformat(tentativas[uid])
                diff = (agora - dt).total_seconds()
                if diff < COOLDOWN_SEGUNDOS:
                    await interaction.response.send_message(f"⏳ Você está em cooldown. Tente novamente mais tarde.", ephemeral=True)
                    return

            # Cria canal privado para o usuário e os diretores
            guild = interaction.guild
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            # Permissão para diretores
            for role_id in DIRETOR_ROLE_IDS:
                role = guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            canal = await guild.create_text_channel(
                name=f"prova-{interaction.user.name}",
                overwrites=overwrites,
                topic=f"Prova do edital para {interaction.user}",
                reason="Canal privado de prova"
            )

            # Salva estado da prova
            perguntas = random.sample(PERGUNTAS, NUM_PERGUNTAS)
            questoes = []
            for p in perguntas:
                alts = p["alternativas"].copy()
                random.shuffle(alts)
                correta = alts.index(p["alternativas"][p["correta"]])
                questoes.append({"pergunta": p["pergunta"], "alternativas": alts, "correta": correta})

            self.cog.dados["provas"][uid] = {
                "questoes": questoes,
                "respostas": [],
                "indice": 0,
                "inicio": agora.isoformat(),
                "canal": canal.id
            }
            self.cog.dados["tentativas"][uid] = agora.isoformat()
            salvar(self.cog.dados)

            await interaction.response.send_message(f"✅ Canal criado: {canal.mention}. Prova iniciada!", ephemeral=True)

            # Envia primeira questão
            await self.cog.enviar_questao(interaction.user, canal)

    async def enviar_questao(self, user, canal):
        uid = str(user.id)
        prova = self.dados["provas"].get(uid)
        if not prova:
            return

        indice = prova["indice"]
        if indice >= NUM_PERGUNTAS:
            await self.finalizar_prova(user, canal)
            return

        questao = prova["questoes"][indice]

        embed = discord.Embed(
            title=f"Questão {indice+1}/{NUM_PERGUNTAS}",
            description=questao["pergunta"],
            color=0x95a5a6
        )

        view = self.RespostaView(self, user, canal)

        letras = ["A", "B", "C", "D"]
        texto = ""
        for i, alt in enumerate(questao["alternativas"]):
            texto += f"**{letras[i]}** — {alt}\n"
        embed.add_field(name="Alternativas", value=texto, inline=False)

        await canal.send(f"{user.mention}", embed=embed, view=view)

    class RespostaView(discord.ui.View):
        def __init__(self, cog, user, canal):
            super().__init__(timeout=600)  # 10 minutos timeout
            self.cog = cog
            self.user = user
            self.canal = canal

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user != self.user:
                await interaction.response.send_message("❌ Esta prova não é para você.", ephemeral=True)
                return False
            return True

        @discord.ui.button(label="A", style=discord.ButtonStyle.secondary)
        async def botao_a(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.responder(interaction, 0)

        @discord.ui.button(label="B", style=discord.ButtonStyle.secondary)
        async def botao_b(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.responder(interaction, 1)

        @discord.ui.button(label="C", style=discord.ButtonStyle.secondary)
        async def botao_c(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.responder(interaction, 2)

        @discord.ui.button(label="D", style=discord.ButtonStyle.secondary)
        async def botao_d(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.responder(interaction, 3)

        async def responder(self, interaction: discord.Interaction, resposta: int):
            uid = str(self.user.id)
            prova = self.cog.dados["provas"].get(uid)
            if not prova:
                await interaction.response.send_message("❌ Prova não encontrada ou expirada.", ephemeral=True)
                return

            prova["respostas"].append(resposta)
            prova["indice"] += 1
            salvar(self.cog.dados)

            # Apaga a mensagem anterior para evitar spam
            await interaction.message.delete()

            canal = self.canal
            # Se ainda tem questões, envia próxima
            if prova["indice"] < NUM_PERGUNTAS:
                await self.cog.enviar_questao(self.user, canal)
            else:
                await self.cog.finalizar_prova(self.user, canal)

            await interaction.response.send_message(f"Resposta {['A','B','C','D'][resposta]} registrada.", ephemeral=True)

    async def finalizar_prova(self, user, canal):
        uid = str(user.id)
        prova = self.dados["provas"].pop(uid, None)
        if not prova:
            return

        pontos = sum(1 for i, q in enumerate(prova["questoes"]) if prova["respostas"][i] == q["correta"])
        aprovado = pontos >= MIN_PONTOS
        status = "✅ APROVADO" if aprovado else "❌ REPROVADO"

        embed = discord.Embed(
            title="Resultado da Prova",
            description=f"{user.mention} obteve {pontos}/{NUM_PERGUNTAS} — {status}",
            color=0x2ecc71 if aprovado else 0xe74c3c
        )

        if self.result_channel:
            ch = self.bot.get_channel(self.result_channel)
            if ch:
                await ch.send(embed=embed)

        await canal.send(embed=embed)

        # Remove canal da prova após 1 minuto
        await asyncio.sleep(60)
        try:
            await canal.delete(reason="Encerramento da prova")
        except:
            pass

    @tasks.loop(hours=24)
    async def _limpar(self):
        agora = datetime.utcnow()
        alterou = False
        for uid, prov in list(self.dados["provas"].items()):
            try:
                inicio = datetime.fromisoformat(prov.get("inicio"))
                if agora - inicio > timedelta(days=7):
                    self.dados["provas"].pop(uid, None)
                    alterou = True
            except Exception:
                continue
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

async def setup(bot):
    await bot.add_cog(Edital(bot))

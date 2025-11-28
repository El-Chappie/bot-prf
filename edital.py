import discord
from discord.ext import commands, tasks
import asyncio
import random
from datetime import datetime, timedelta

# CONFIGURAÇÕES - ajuste esses valores
DIRETOR_ROLE_IDS = [1443387915689398395, 1443387916633247766]  # IDs dos cargos de diretor
CATEGORIA_PROVAS_ID = 1443387998153605262  # ID da categoria para canais de prova (ou None)
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

class ProvaView(discord.ui.View):
    def __init__(self, bot, channel, user, cog):
        super().__init__(timeout=TEMPO_LIMITE)
        self.bot = bot
        self.channel = channel
        self.user = user
        self.cog = cog
        self.current_index = 0
        self.prova_data = self.criar_prova()
        self.message = None

        for i, letra in enumerate(["A", "B", "C", "D"]):
            self.add_item(RespostaBotao(letra, i, self))

    def criar_prova(self):
        perguntas = random.sample(PERGUNTAS, NUM_PERGUNTAS)
        questoes = []
        for p in perguntas:
            alts = p["alternativas"].copy()
            random.shuffle(alts)
            correta = alts.index(p["alternativas"][p["correta"]])
            questoes.append({"pergunta": p["pergunta"], "alternativas": alts, "correta": correta})
        return {
            "questoes": questoes,
            "respostas": []
        }

    def criar_embed(self):
        p = self.prova_data["questoes"][self.current_index]
        descricao = p["pergunta"] + "\n\n"
        for idx, alt in enumerate(p["alternativas"]):
            descricao += f"**{['A','B','C','D'][idx]}** — {alt}\n"
        embed = discord.Embed(
            title=f"Questão {self.current_index +1}/{NUM_PERGUNTAS}",
            description=descricao,
            color=discord.Color.blue()
        )
        embed.set_footer(text="Você tem 10 minutos para concluir a prova.")
        return embed

    async def start(self):
        embed = self.criar_embed()
        self.message = await self.channel.send(content=self.user.mention, embed=embed, view=self)
        self.bot.loop.create_task(self.timeout_task())

    async def timeout_task(self):
        await asyncio.sleep(TEMPO_LIMITE)
        if not self.is_finished():
            await self.encerrar_prova(timeout=True)

    def is_finished(self):
        return self.current_index >= NUM_PERGUNTAS

    async def encerrar_prova(self, timeout=False):
        self.disable_all_items()
        await self.message.edit(view=self)

        respostas = self.prova_data["respostas"]
        questoes = self.prova_data["questoes"]
        pontos = sum(1 for i,q in enumerate(questoes) if i < len(respostas) and respostas[i] == q["correta"])
        aprovado = pontos >= MIN_PONTOS
        status = "✅ APROVADO" if aprovado else "❌ REPROVADO"

        desc = f"Resultado final: {pontos}/{NUM_PERGUNTAS}\n{status}"
        if timeout:
            desc += "\n\n⏰ Tempo esgotado. Prova finalizada automaticamente."

        await self.channel.send(f"{self.user.mention} terminou a prova.\n{desc}")

        # Notifica DM
        try:
            await self.user.send(embed=discord.Embed(title="Resultado da Prova", description=desc, color=discord.Color.green() if aprovado else discord.Color.red()))
        except:
            pass

        # Envia resultado no canal configurado
        canal_resultados = self.cog.canal_resultados_id
        if canal_resultados:
            canal = self.cog.bot.get_channel(canal_resultados)
            if canal:
                embed_result = discord.Embed(
                    title=f"Resultado da prova - {self.user}",
                    description=f"Pontuação: {pontos}/{NUM_PERGUNTAS}\nStatus: {status}",
                    color=discord.Color.green() if aprovado else discord.Color.red()
                )
                await canal.send(embed=embed_result)

        # Log no canal de logs, se configurado
        canal_log = self.cog.canal_log_id
        if canal_log:
            canal_l = self.cog.bot.get_channel(canal_log)
            if canal_l:
                await canal_l.send(embed=discord.Embed(title=f"Log Prova {self.user}", description=f"Pontuação: {pontos}\nStatus: {status}", color=discord.Color.greyple()))

        # Fecha o canal privado após 1 min
        await asyncio.sleep(60)
        try:
            await self.channel.delete(reason="Prova finalizada")
        except:
            pass

        # Remove da lista ativa
        self.cog.provas_ativas.pop(self.user.id, None)


class RespostaBotao(discord.ui.Button):
    def __init__(self, label, index, view):
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.index = index
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view.user:
            await interaction.response.send_message("Essa prova não é para você.", ephemeral=True)
            return

        self.view.prova_data["respostas"].append(self.index)
        self.view.current_index += 1

        if self.view.current_index >= NUM_PERGUNTAS:
            await interaction.response.defer()
            await self.view.encerrar_prova()
        else:
            embed = self.view.criar_embed()
            await interaction.response.edit_message(embed=embed, view=self.view)


class IniciarProvaButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(label="Iniciar Prova", style=discord.ButtonStyle.success)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user

        if not interaction.guild:
            await interaction.response.send_message("Este comando só pode ser usado dentro do servidor.", ephemeral=True)
            return

        if user.id in self.cog.provas_ativas:
            await interaction.response.send_message("Você já está fazendo uma prova.", ephemeral=True)
            return

        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role_id in DIRETOR_ROLE_IDS:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        category = guild.get_channel(self.cog.categoria_provas_id) if self.cog.categoria_provas_id else None
        nome_canal = f"prova-{user.name}".lower().replace(" ", "-")[:90]

        channel = await guild.create_text_channel(nome_canal, overwrites=overwrites, category=category, reason="Canal privado para prova")

        # MOVE usuário para canal de voz com o mesmo nome (se quiser, pode descomentar abaixo)
        # Se o usuário estiver em canal de voz, tenta mover ele para um canal de voz privado para prova (criado aqui)
        # Para isso, precisa criar canal de voz também. Comente se não quiser.

        voz_canal = None
        try:
            if user.voice and user.voice.channel:
                # Criar canal de voz privado
                overwrites_voice = {
                    guild.default_role: discord.PermissionOverwrite(connect=False),
                    user: discord.PermissionOverwrite(connect=True, speak=True)
                }
                # Permitir diretores no canal de voz
                for role_id in DIRETOR_ROLE_IDS:
                    role = guild.get_role(role_id)
                    if role:
                        overwrites_voice[role] = discord.PermissionOverwrite(connect=True, speak=True)

                voz_canal = await guild.create_voice_channel(f"Prova VC - {user.name}", overwrites=overwrites_voice, category=category, reason="Canal de voz privado para prova")
                await user.move_to(voz_canal)
        except Exception as e:
            print(f"Erro ao mover usuário para canal de voz: {e}")

        prova_view = ProvaView(self.cog.bot, channel, user, self.cog)
        self.cog.provas_ativas[user.id] = prova_view
        await prova_view.start()

        await interaction.response.send_message(f"Canal privado criado: {channel.mention}" + (f" e canal de voz criado: {voz_canal.mention}" if voz_canal else ""), ephemeral=True)


class Edital(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.provas_ativas = {}  # user_id : ProvaView
        self.categoria_provas_id = CATEGORIA_PROVAS_ID
        self.canal_log_id = None
        self.canal_resultados_id = None

    @commands.hybrid_command(name="setcanallog")
    @commands.has_permissions(administrator=True)
    async def set_canal_log(self, ctx, canal: discord.TextChannel):
        self.canal_log_id = canal.id
        await ctx.reply(f"Canal de logs definido: {canal.mention}", ephemeral=True)

    @commands.hybrid_command(name="setcanalresultado")
    @commands.has_permissions(administrator=True)
    async def set_canal_resultado(self, ctx, canal: discord.TextChannel):
        self.canal_resultados_id = canal.id
        await ctx.reply(f"Canal de resultados definido: {canal.mention}", ephemeral=True)

    @commands.hybrid_command(name="lniclarprova")
    @commands.has_any_role(*DIRETOR_ROLE_IDS)
    async def lniciar_prova(self, ctx, canal: discord.TextChannel = None):
        canal = canal or ctx.channel

        embed = discord.Embed(
            title="📄 Prova Oficial da PRF",
            description=(
                "Para iniciar a prova, clique no botão abaixo. Você terá **10 minutos** para responder todas as perguntas.\n\n"
                "**IMPORTANTE:** A prova será realizada em canal privado acessível apenas a você, aos diretores e ao bot."
            ),
            color=discord.Color.green()
        )
        view = discord.ui.View()
        view.add_item(IniciarProvaButton(self))
        await canal.send(embed=embed, view=view)
        await ctx.reply(f"Embed com o botão enviada em {canal.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Edital(bot))
    print("✅ Edital pronto para uso")

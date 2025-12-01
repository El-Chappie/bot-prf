# edital.py — SISTEMA DEFINITIVO DA PROVA PRF

import discord, json, os, random, asyncio
from discord.ext import commands, tasks
from datetime import datetime

ARQ = "edital_prova_data.json"

DIRETOR_ROLE_IDS = [1443387926196260965]
CATEGORIA_PROVAS = 1443387998153605262
CANAL_RESULTADOS = 1443620398016237589

TEMPO = 600
PERGUNTAS_QTD = 10
MINIMA = 6
COOLDOWN = 3600

PERGUNTAS = [
{"pergunta": "A PRF é vinculada a qual ministério?", "alts": ["Defesa", "Justiça", "Infraestrutura", "Segurança Pública"], "c": 1},
{"pergunta": "O policial pode agir fora de serviço quando:", "alts": ["Nunca","Somente com ordem","Em flagrante delito","Somente fardado"], "c": 2},
{"pergunta": "Constitui abuso de autoridade:", "alts": ["Fazer abordagem","Dar voz de prisão legal","Agir sem amparo legal","Executar fiscalização"], "c": 2},
{"pergunta": "Prender alguém sem motivo legal gera:", "alts": ["Advertência","Promoção","Responsabilidade administrativa e penal","Somente processo civil"], "c": 2},
{"pergunta": "Crime de corrupção passiva ocorre quando o agente:", "alts": ["Oferece vantagem","Exige ou aceita vantagem","Ameaça","Facilita"], "c": 1},
{"pergunta": "Sequência: 3, 6, 12, 24, ?", "alts": ["36","42","48","60"], "c": 2},
{"pergunta": "Se todo agente é servidor e nenhum servidor é civil, então:", "alts": ["Todo agente é civil","Nenhum agente é civil","Algum agente é civil","Todo civil é agente"], "c": 1},
{"pergunta": "Hierarquia significa:", "alts": ["Autoridade absoluta","Respeito às graduações","Abuso de poder","Poder político"], "c": 1},
{"pergunta": "Ordem manifestamente ilegal deve ser:", "alts": ["Cumprida","Ignorada sem aviso","Comunicada aos superiores","Guardada em sigilo"], "c": 2},
{"pergunta": "Em viatura, você presencia colega receber suborno. O que fazer?", "alts": ["Aceitar também","Ignorar","Documentar e denunciar","Ameaçar o colega"], "c": 2}
]


def load():
    if not os.path.exists(ARQ):
        return {"provas": {}, "cooldown": {}, "bloqueado": False}
    with open(ARQ,"r",encoding="utf8") as f:
        return json.load(f)

def save(d):
    with open(ARQ,"w",encoding="utf8") as f:
        json.dump(d,f,ensure_ascii=False,indent=4)


class Edital(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.data = load()
        self.timer.start()

    # ✅ AUTO REPROVAÇÃO AO SAIR DO SERVIDOR
    @commands.Cog.listener()
    async def on_member_remove(self, member):

        uid = str(member.id)
        if uid not in self.data["provas"]:
            return

        prova = self.data["provas"][uid]
        canal = self.bot.get_channel(prova["canal"])

        emb = discord.Embed(title="🚨 PROVA CANCELADA.", color=0xef4444)
        emb.description = f"{member.mention} saiu do servidor durante a prova.\n❌ **REPROVADO AUTOMATICAMENTE**"

        if canal:
            await canal.send(embed=emb)
            await asyncio.sleep(10)
            await canal.delete()

        self.data["provas"].pop(uid)
        save(self.data)

        ch = self.bot.get_channel(CANAL_RESULTADOS)
        if ch:
            await ch.send(embed=emb)

    # -------- CONTROLE DIRETOR -------- #

    @commands.hybrid_command(name="bloquearprovas")
    async def bloquear(self, ctx):
        if not any(r.id in DIRETOR_ROLE_IDS for r in ctx.author.roles):
            return await ctx.reply("❌ Apenas diretores.", ephemeral=True)
        self.data["bloqueado"] = True
        save(self.data)
        await ctx.reply("🚫 Provas bloqueadas.", ephemeral=True)


    @commands.hybrid_command(name="liberarprovas")
    async def liberar(self, ctx):
        if not any(r.id in DIRETOR_ROLE_IDS for r in ctx.author.roles):
            return await ctx.reply("❌ Apenas diretores.", ephemeral=True)
        self.data["bloqueado"] = False
        save(self.data)
        await ctx.reply("✅ Provas liberadas.", ephemeral=True)


    # -------- CONFIG -------- #

    @commands.hybrid_command(name="setarmarcacategoria")
    async def setcat(self, ctx, categoria: discord.CategoryChannel):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.reply("❌ Sem permissão.", ephemeral=True)
        global CATEGORIA_PROVAS
        CATEGORIA_PROVAS = categoria.id
        await ctx.reply("✅ Categoria definida.", ephemeral=True)


    @commands.hybrid_command(name="setarresultado")
    async def setres(self, ctx, canal: discord.TextChannel):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.reply("❌ Sem permissão.", ephemeral=True)
        global CANAL_RESULTADOS
        CANAL_RESULTADOS = canal.id
        await ctx.reply("✅ Canal de resultados definido.", ephemeral=True)

    # -------- PUBLICAR EDITAL -------- #

    @commands.hybrid_command(name="publicarprova")
    async def publicar(self, ctx):

        if not any(r.id in DIRETOR_ROLE_IDS for r in ctx.author.roles):
            return await ctx.reply("❌ Apenas diretores.", ephemeral=True)

        embed = discord.Embed(
            title="📘 EDITAL OFICIAL PRF",
            description="Clique abaixo para iniciar a prova.\n⏱️ 10 minutos\n📝 10 questões\n✅ Apenas uma tentativa",
            color=0x0b5ed7
        )

        await ctx.send(embed=embed, view=BotaoIniciar(self))

    # -------- PROVA -------- #

    async def iniciar_prova(self, user, guild):

        if self.data.get("bloqueado"):
            return None, "🚫 As provas estão temporariamente bloqueadas."

        uid = str(user.id)

        # 🔒 Prova dupla
        if uid in self.data["provas"]:
            return None, "⚠️ Você já tem uma prova em andamento."

        now = datetime.utcnow()

        # Cooldown
        if uid in self.data["cooldown"]:
            dt = datetime.fromisoformat(self.data["cooldown"][uid])
            if (now-dt).total_seconds() < COOLDOWN:
                return None, "⏳ Aguarde para tentar novamente."

        categoria = guild.get_channel(CATEGORIA_PROVAS)

        canal = await guild.create_text_channel(
            f"📄-prova-{user.name}",
            category=categoria,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True),
                **{guild.get_role(r): discord.PermissionOverwrite(view_channel=True) for r in DIRETOR_ROLE_IDS}
            }
        )

        questoes = random.sample(PERGUNTAS, PERGUNTAS_QTD)

        prova = []

        for q in questoes:
            alts = q["alts"].copy()
            random.shuffle(alts)
            correta = alts.index(q["alts"][q["c"]])
            prova.append({"p": q["pergunta"], "a": alts, "c": correta})

        self.data["provas"][uid] = {
            "inicio": now.isoformat(),
            "canal": canal.id,
            "i": 0,
            "r": [],
            "q": prova,
            "alerta": False
        }

        self.data["cooldown"][uid] = now.isoformat()
        save(self.data)

        return canal, None

    async def enviar(self, user, canal):

        prova = self.data["provas"].get(str(user.id))
        if not prova:
            return

        q = prova["q"][prova["i"]]

        embed = discord.Embed(
            title=f"Questão {prova['i']+1}/{PERGUNTAS_QTD}",
            description=q["p"],
            color=0x1f2937
        )

        for i,a in enumerate(q["a"]):
            embed.add_field(name=chr(65+i), value=a, inline=False)

        await canal.send(user.mention, embed=embed, view=ResView(self, user, canal))

    async def finalizar(self, user, canal, timeout=False):

        uid = str(user.id)

        if uid not in self.data["provas"]:
            return

        prova = self.data["provas"].pop(uid)
        save(self.data)

        pontos = sum(1 for i,q in enumerate(prova["q"]) if i < len(prova["r"]) and prova["r"][i] == q["c"])
        aprovado = pontos >= MINIMA

        emb = discord.Embed(
            title="📊 RESULTADO FINAL",
            color=0x22c55e if aprovado and not timeout else 0xef4444
        )

        emb.add_field(name="Candidato", value=user.mention)
        emb.add_field(name="Pontuação", value=f"{pontos}/{PERGUNTAS_QTD}")
        emb.add_field(name="Status", value="✅ APROVADO" if aprovado and not timeout else "❌ REPROVADO")

        if timeout:
            emb.add_field(name="Motivo", value="⏱️ TEMPO DE PROVA ESGOTADO.")

        try:
            if canal:
                await canal.send(embed=emb)
        except:
            pass

        try:
            ch = self.bot.get_channel(CANAL_RESULTADOS)
            if ch:
                await ch.send(embed=emb)
        except:
            pass

        if canal:
            await asyncio.sleep(15)
            try:
                await canal.delete()
            except:
                pass


    # -------- TIMER -------- #

    @tasks.loop(seconds=10)
    async def timer(self):

        now = datetime.utcnow()

        for uid,d in list(self.data["provas"].items()):
            start = datetime.fromisoformat(d["inicio"])
            elapsed = (now-start).total_seconds()

            canal = self.bot.get_channel(d["canal"])

            try:
                user = await self.bot.fetch_user(int(uid))
            except:
                continue

            # ⏱️ TimeOut
            if elapsed >= TEMPO:
                await self.finalizar(user, canal, True)
                continue

            # ⚠️ Aviso
            if TEMPO-elapsed <= 60 and not d["alerta"]:
                d["alerta"] = True
                save(self.data)
                if canal:
                    await canal.send("⏰ **ATENÇÃO! FALTA 1 MINUTO PARA O ENCERRAMENTO DA PROVA!**")


# -------- BOTÃO -------- #

class BotaoIniciar(discord.ui.View):

    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="✅ INICIAR PROVA", style=discord.ButtonStyle.success)
    async def start(self, i, _):

        canal, erro = await self.cog.iniciar_prova(i.user, i.guild)

        if erro:
            return await i.response.send_message(erro, ephemeral=True)

        await i.response.send_message(f"✅ Prova iniciada!\n👉 {canal.mention}", ephemeral=True)
        await self.cog.enviar(i.user, canal)


# -------- RESPOSTAS -------- #

class ResView(discord.ui.View):

    def __init__(self, cog, user, canal):
        super().__init__(timeout=None)
        self.cog = cog
        self.u = user
        self.c = canal

    async def marcar(self, i, n):

        prova = self.cog.data["provas"].get(str(self.u.id))
        if not prova:
            return

        prova["r"].append(n)
        prova["i"] += 1
        save(self.cog.data)

        try:
            await i.message.delete()
        except:
            pass

        if prova["i"] < PERGUNTAS_QTD:
            await self.cog.enviar(self.u, self.c)
        else:
            await self.cog.finalizar(self.u, self.c)


    @discord.ui.button(label="A", style=discord.ButtonStyle.secondary)
    async def a(self, i, _): await self.marcar(i,0)

    @discord.ui.button(label="B", style=discord.ButtonStyle.secondary)
    async def b(self, i, _): await self.marcar(i,1)

    @discord.ui.button(label="C", style=discord.ButtonStyle.secondary)
    async def c(self, i, _): await self.marcar(i,2)

    @discord.ui.button(label="D", style=discord.ButtonStyle.secondary)
    async def d(self, i, _): await self.marcar(i,3)


async def setup(bot):
    await bot.add_cog(Edital(bot))

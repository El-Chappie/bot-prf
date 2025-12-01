# edital.py — SISTEMA DEFINITIVO DA PROVA PRF

import discord, json, os, random, asyncio
from discord.ext import commands, tasks
from datetime import datetime, timedelta

ARQ = "edital_prova_data.json"

DIRETOR_ROLE_IDS = [1443387926196260965]
CATEGORIA_PROVAS = 1443387998153605262
CANAL_RESULTADOS = 1443620398016237589

TEMPO = 600
PERGUNTAS_QTD = 10
MINIMA = 6
COOLDOWN = 3600

PERGUNTAS = [
    {"pergunta": "Capital do Brasil?", "alts": ["Rio", "Brasília", "Recife", "São Paulo"], "c": 1},
    {"pergunta": "Maior planeta?", "alts": ["Terra", "Marte", "Júpiter", "Saturno"], "c": 2},
    {"pergunta": "Criador do Python?", "alts": ["Linus", "Bill", "Guido", "Mark"], "c": 2},
    {"pergunta": "Python é?", "alts": ["Compilado", "Interpretado", "Binário", "Assembly"], "c": 1},
    {"pergunta": "Maior oceano?", "alts": ["Atlântico", "Índico", "Pacífico", "Ártico"], "c": 2},
    {"pergunta": "Sistema do Discord?", "alts": ["Canais", "Servidores", "Salas", "Guilds"], "c": 1},
    {"pergunta": "1 byte possui?", "alts": ["4 bits", "8 bits", "16 bits", "32 bits"], "c": 1},
    {"pergunta": "Ano da independência?", "alts": ["1808", "1889", "1822", "1500"], "c": 2},
    {"pergunta": "Quem proclamou a república?", "alts": ["Deodoro", "Getúlio", "Lula", "D. Pedro"], "c": 0},
    {"pergunta": "PRF é?", "alts": ["Exército", "Polícia Federal", "Polícia Rodoviária Federal", "PM"], "c": 2}
]

def load():
    if not os.path.exists(ARQ):
        return {"provas": {}, "cooldown": {}, "bloqueado": False}
    with open(ARQ, "r", encoding="utf8") as f:
        return json.load(f)

def save(d):
    with open(ARQ, "w", encoding="utf8") as f:
        json.dump(d, f, ensure_ascii=False, indent=4)

class Edital(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load()
        self.timer.start()

    # -------- CONTROLE DIRETOR -------- #

    @commands.hybrid_command(name="bloquearprovas")
    @commands.has_permissions(administrator=True)
    async def bloquear(self, ctx):
        if not any(r.id in DIRETOR_ROLE_IDS for r in ctx.author.roles):
            return await ctx.reply("❌ Apenas diretores.", ephemeral=True)
        self.data["bloqueado"] = True
        save(self.data)
        await ctx.reply("🚫 Provas bloqueadas.", ephemeral=True)

    @commands.hybrid_command(name="liberarprovas")
    @commands.has_permissions(administrator=True)
    async def liberar(self, ctx):
        if not any(r.id in DIRETOR_ROLE_IDS for r in ctx.author.roles):
            return await ctx.reply("❌ Apenas diretores.", ephemeral=True)
        self.data["bloqueado"] = False
        save(self.data)
        await ctx.reply("✅ Provas liberadas.", ephemeral=True)

    # -------- CONFIG -------- #

    @commands.hybrid_command(name="setarmarcacategoria")
    @commands.has_permissions(administrator=True)
    async def setcat(self, ctx, categoria: discord.CategoryChannel):
        global CATEGORIA_PROVAS
        CATEGORIA_PROVAS = categoria.id
        await ctx.reply("✅ Categoria definida.", ephemeral=True)

    @commands.hybrid_command(name="setarresultado")
    @commands.has_permissions(administrator=True)
    async def setres(self, ctx, canal: discord.TextChannel):
        global CANAL_RESULTADOS
        CANAL_RESULTADOS = canal.id
        await ctx.reply("✅ Canal de resultados definido.", ephemeral=True)

    # -------- PUBLICAR EDITAL -------- #

    @commands.hybrid_command(name="publicarprova")
    async def publicar(self, ctx):
        if not any(r.id in DIRETOR_ROLE_IDS for r in ctx.author.roles):
            return await ctx.reply("❌ Apenas diretores.", ephemeral=True)

        embed = discord.Embed(
            title="📘 PROVA OFICIAL PRF",
            description="Clique abaixo para iniciar a prova.\n⏱️ 10 minutos\n📝 10 perguntas\n✅ Apenas uma tentativa",
            color=0x0b5ed7
        )

        await ctx.send(embed=embed, view=BotaoIniciar(self))

    # -------- PROVA -------- #

    async def iniciar_prova(self, user, guild):

        if self.data.get("bloqueado"):
            return None, "🚫 As provas estão temporariamente bloqueadas."

        uid = str(user.id)
        now = datetime.utcnow()

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
        prova = self.data["provas"][str(user.id)]
        q = prova["q"][prova["i"]]

        embed = discord.Embed(title=f"Questão {prova['i']+1}/10", description=q["p"], color=0x1f2937)
        for i,a in enumerate(q["a"]):
            embed.add_field(name=chr(65+i), value=a, inline=False)

        await canal.send(user.mention, embed=embed, view=ResView(self, user, canal))

    async def finalizar(self, user, canal, timeout=False):
        prova = self.data["provas"].pop(str(user.id))
        save(self.data)

        pontos = sum(1 for i,q in enumerate(prova["q"]) if prova["r"][i] == q["c"])
        aprovado = pontos >= MINIMA

        emb = discord.Embed(title="📊 RESULTADO FINAL",
                            color=0x22c55e if aprovado else 0xef4444)
        emb.add_field(name="Candidato", value=user.mention)
        emb.add_field(name="Pontuação", value=f"{pontos}/10")
        emb.add_field(name="Status", value="✅ APROVADO" if aprovado else "❌ REPROVADO")

        if timeout:
            emb.add_field(name="Motivo", value="⏱️ TEMPO ESGOTADO")

        await canal.send(embed=emb)

        if CANAL_RESULTADOS:
            ch = self.bot.get_channel(CANAL_RESULTADOS)
            if ch: await ch.send(embed=emb)

        await asyncio.sleep(20)
        await canal.delete()

    # -------- TIMER -------- #

    @tasks.loop(seconds=10)
    async def timer(self):
        now = datetime.utcnow()
        for uid,d in list(self.data["provas"].items()):
            start = datetime.fromisoformat(d["inicio"])
            elapsed = (now-start).total_seconds()

            canal = self.bot.get_channel(d["canal"])
            user = await self.bot.fetch_user(int(uid))

            if elapsed >= TEMPO:
                await self.finalizar(user, canal, True)

            if TEMPO-elapsed <= 60 and not d["alerta"]:
                d["alerta"] = True
                save(self.data)
                if canal:
                    await canal.send("⏰ **ATENÇÃO! FALTA 1 MINUTO!**")

# -------- BOTÃO -------- #

class BotaoIniciar(discord.ui.View):
    def __init__(self, cog): super().__init__(timeout=None); self.cog = cog

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
        super().__init__(timeout=None); self.cog=cog; self.u=user; self.c=canal

    async def marcar(self, i, n):
        prova = self.cog.data["provas"].get(str(self.u.id))
        if not prova: return

        prova["r"].append(n)
        prova["i"] += 1
        save(self.cog.data)

        await i.message.delete()

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

import discord
import os
import threading
import asyncio
from fastapi import FastAPI
from fastapi.responses import FileResponse

TOKEN = os.getenv("TOKEN")
IGNORAR_CATEGORIAS = [
    "╭╼ 🌐Uploader Mode",
    "╭╼ 👥Chat",
    "╭╼ 💎ADM chat",
    "╭╼ 📫Welcome",
    "⭒⇆◁ ❚❚ ▷↻ ⭒ 🔊 ▂▃▅▉ 100%⭒",
]

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

client = discord.Client(intents=intents)
app = FastAPI()


def limpar_nome(nome):
    return nome.replace("/", "-").replace("\\", "-").replace(":", "-")


@client.event
async def on_ready():
    print(f"✅ Bot logado como {client.user}")

    links_por_categoria = {}

    for guild in client.guilds:
        for canal in guild.text_channels:
            if canal.category is None or canal.category.name in IGNORAR_CATEGORIAS:
                continue

            try:
                links_salvos = set()
                async for mensagem in canal.history(limit=None, oldest_first=True):
                    for anexo in mensagem.attachments:
                        links_salvos.add(anexo.url)
                if links_salvos:
                    categoria_nome = canal.category.name
                    canal_nome = canal.name
                    if categoria_nome not in links_por_categoria:
                        links_por_categoria[categoria_nome] = []
                    links_por_categoria[categoria_nome].append(
                        (canal.position, canal_nome, sorted(links_salvos))
                    )
            except Exception as e:
                print(f"⚠️ Erro no canal {canal.name}: {e}")

    # Ordena as categorias e canais conforme a ordem do servidor
    links_por_canal = []
    for guild in client.guilds:
        for categoria in guild.categories:
            if categoria.name in IGNORAR_CATEGORIAS:
                continue
            if categoria.name in links_por_categoria:
                canais = sorted(links_por_categoria[categoria.name], key=lambda x: x[0])
                for _, canal_nome, links in canais:
                    links_por_canal.append(f"# {categoria.name} / {canal_nome}\n")
                    for link in links:
                        links_por_canal.append(link + "\n")
                    links_por_canal.append("\n")  # Espaço extra entre canais

    with open("links_dos_arquivos.txt", "w", encoding="utf-8") as f:
        f.writelines(links_por_canal)

    print("✅ Coleta de links concluída!")
    await client.close()


@app.get("/links")
def get_links():
    if os.path.exists("links_dos_arquivos.txt"):
        return FileResponse("links_dos_arquivos.txt", media_type="text/plain")
    return {"erro": "Arquivo não encontrado"}


def start_bot():
    asyncio.run(client.start(TOKEN))


@app.on_event("startup")
def on_startup():
    threading.Thread(target=start_bot, daemon=True).start()

import discord
import os
import threading
import asyncio
import requests
import time
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def limpar_nome(nome):
    return nome.replace("/", "-").replace("\\", "-").replace(":", "-")


async def coletar_links():
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
                    links_por_canal.append("\n")

    with open("links_dos_arquivos.txt", "w", encoding="utf-8") as f:
        f.writelines(links_por_canal)

    print("✅ Coleta de links concluída!")


@client.event
async def on_ready():
    print(f"✅ Bot logado como {client.user}")
    await coletar_links()


@app.get("/links")
def get_links():
    if os.path.exists("links_dos_arquivos.txt"):
        return FileResponse("links_dos_arquivos.txt", media_type="text/plain")
    return {"erro": "Arquivo não encontrado"}


@app.get("/atualizar_links")
def atualizar_links():
    if not client.is_ready():
        return {"erro": "Bot do Discord ainda não está pronto"}

    async def executar():
        await coletar_links()

    asyncio.run_coroutine_threadsafe(executar(), client.loop)
    return {"status": "Coleta de links em andamento"}


def baixar_txt_url(url, nome_saida):
    resposta = requests.get(url)
    resposta.raise_for_status()
    with open(nome_saida, "wb") as f:
        f.write(resposta.content)


def gerar_html_audios(input_txt, output_txt):
    html_output = [
        "<script>\n"
        "function toggleAlbum(id) {\n"
        "  const div = document.getElementById(id);\n"
        "  div.style.display = div.style.display === 'none' ? 'block' : 'none';\n"
        "}\n"
        "</script>\n\n"
    ]
    artista_album = None
    album_id = 1

    with open(input_txt, "r", encoding="utf-8") as file:
        linhas = [linha.strip() for linha in file if linha.strip()]

    faixa_num = 1
    for linha in linhas:
        if linha.startswith("#"):
            if artista_album is not None:
                html_output.append("</div>\n\n")
            artista_album = linha[1:].strip()
            div_id = f"album{album_id}"
            html_output.append(
                f"<button onclick=\"toggleAlbum('{div_id}')\">Mostrar/Ocultar {artista_album}</button><br>\n"
                f'<div id="{div_id}" style="display:none;">\n'
                f"<h2>{artista_album}</h2>\n"
            )
            album_id += 1
            faixa_num = 1
        else:
            link = linha
            if "/" in link:
                nome_com_extensao = link.split("/")[-1]
                if "." in nome_com_extensao:
                    nome_arquivo = nome_com_extensao.rsplit(".", 1)[0]
                else:
                    nome_arquivo = nome_com_extensao
            else:
                nome_arquivo = f"Faixa {faixa_num}"

            bloco_html = f"""<p>{nome_arquivo}</p>
<audio controls preload="none">
    <source src="{link}" type="audio/ogg; codecs=opus">
</audio>\n"""
            html_output.append(bloco_html)
            faixa_num += 1

    if artista_album is not None:
        html_output.append("</div>\n")

    with open(output_txt, "w", encoding="utf-8") as file:
        file.writelines(html_output)


@app.get("/gerar_html")
def gerar_html():
    output_txt = "saida.txt"

    if os.path.exists(output_txt):
        return FileResponse(output_txt, filename="saida.txt", media_type="text/plain")
    else:
        return {"erro": "Nenhum HTML gerado ainda. Use /atualizar_links primeiro."}


def start_bot():
    asyncio.run(client.start(TOKEN))


@app.on_event("startup")
def on_startup():
    threading.Thread(target=start_bot, daemon=True).start()

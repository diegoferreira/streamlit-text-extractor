import json
import re
import streamlit as st
import trafilatura
import requests
from requests.exceptions import RequestException

st.set_page_config(page_title="Trafilatura Content Extractor", layout="wide")

st.title("🔗 Extrator de Título e Texto via Trafilatura")
st.markdown(
    "Cole a URL de qualquer página pública. O app fará o download, limpará o HTML e mostrará **Título** e **Texto** prontos para copiar."
)

# ----------------------------
# Network helpers
# ----------------------------

def fetch_url_raw(url: str) -> str | None:
    """Download HTML (unicode str) usando Trafilatura e fallback requests."""
    html = trafilatura.fetch_url(url)
    if html:
        return html

    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
            timeout=20,
        )
        if resp.ok:
            resp.encoding = resp.apparent_encoding
            return resp.text
    except RequestException:
        pass
    return None


def maybe_amp_url(url: str) -> str:
    if url.rstrip("/").endswith("/amp"):
        return url
    if url.endswith("/"):
        return url + "amp"
    return url + "/amp"

# ----------------------------
# Next.js specific helpers
# ----------------------------

def def extract_from_next_data(html: str) -> str | None:
    """Tenta extrair o texto a partir do script JSON `__NEXT_DATA__`.

    • Usa regex que captura tanto aspas simples quanto duplas.
    • Se houver múltiplos scripts, pega o **último** (costuma trazer o payload completo).
    """
    # 1) Captura todos os blocos JSON de __NEXT_DATA__
    scripts = re.findall(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    if not scripts:
        return None

    # O último tende a conter o artigo completo
    for raw_json in reversed(scripts):
        try:
            data = json.loads(raw_json)
        except Exception:
            continue

        # Caminhos possíveis: pageProps.post.content ou pageProps.data.post.content
        post_obj = (
            data.get("props", {})
            .get("pageProps", {})
        )
        if not post_obj:
            continue

        # Algumas páginas aninham em "data":{...}
        post_obj = post_obj.get("post") or post_obj.get("data", {}).get("post")
        if not post_obj or not isinstance(post_obj, dict):
            continue

        content_html = post_obj.get("content")
        if content_html and isinstance(content_html, str):
            txt = trafilatura.html2txt(content_html)
            if txt and len(txt.split()) > 50:
                return txt.strip()

    return None
    try:
        data = json.loads(m.group(1))
        # Caminho comum: data['props']['pageProps']['post']['content']
        content_html = (
            data
            .get("props", {})
            .get("pageProps", {})
            .get("post", {})
            .get("content")
        )
        if content_html and isinstance(content_html, str):
            txt = trafilatura.html2txt(content_html)
            if txt and len(txt.split()) > 50:
                return txt.strip()
    except Exception:
        pass
    return None

# ----------------------------
# Extraction logic
# ----------------------------

def extract_text(html: str) -> str | None:
    """Extrai texto limpo usando cascata de técnicas."""
    # 0) Next.js hydration data
    txt = extract_from_next_data(html)
    if txt:
        return txt

    # 1) Precisão
    txt = trafilatura.extract(html, include_formatting=False, include_links=False, favor_recall=False)
    if txt and len(txt.split()) > 50:
        return txt.strip()

    # 2) Recall
    txt = trafilatura.extract(html, include_formatting=False, include_links=False, favor_recall=True)
    if txt and len(txt.split()) > 50:
        return txt.strip()

    # 3) Readability‑lxml → html2txt
    try:
        from readability import Document
        main_html = Document(html).summary(html_partial=True)
        txt = trafilatura.html2txt(main_html)
        if txt and len(txt.split()) > 50:
            return txt.strip()
    except Exception:
        pass

    # 4) html2txt puro
    try:
        txt = trafilatura.html2txt(html)
        if txt and len(txt.split()) > 50:
            return txt.strip()
    except Exception:
        pass

    # 5) BeautifulSoup fallback
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        txt = soup.get_text("\n", strip=True)
        if txt and len(txt.split()) > 50:
            return txt
    except Exception:
        pass
    return None

# ----------------------------
# Streamlit UI
# ----------------------------

url = st.text_input("Insira a URL a ser processada:")

if url:
    with st.spinner("⌛ Baixando e extraindo conteúdo…"):
        html = fetch_url_raw(url)
        text: str | None = None
        if html:
            text = extract_text(html)

        if not text:
            # tenta versão AMP
            amp_html = fetch_url_raw(maybe_amp_url(url))
            if amp_html:
                text = extract_text(amp_html)
                if text:
                    html = amp_html

        if not html:
            st.error("❌ Não foi possível baixar a página. Verifique a URL e tente novamente.")
        else:
            # ----- Título -----
            title: str | None = None
            try:
                from trafilatura import extract_title  # type: ignore
                title = extract_title(html)
            except Exception:
                pass
            if title is None:
                try:
                    meta = trafilatura.extract_metadata(html)
                    if meta:
                        if isinstance(meta, dict):
                            title = meta.get("title")
                        else:
                            title = getattr(meta, "title", None)
                        if title is None and isinstance(meta, str):
                            title = json.loads(meta).get("title")
                except Exception:
                    pass
            title = title or "Título não encontrado"

            text = text or "Texto não encontrado"

            # ----- UI -----
            st.success("✅ Conteúdo extraído com sucesso!")
            st.subheader("Título")
            st.code(title, language=None)
            st.subheader("Texto")
            st.code(text, language=None)
            st.caption("Clique no ícone de cópia (📋) no canto superior direito dos blocos para copiar.")

# ----------------------------
# Como rodar localmente
# ----------------------------
# 1. pip install streamlit trafilatura[all] requests readability-lxml beautifulsoup4
# 2. streamlit run trafilatura_streamlit_app.py

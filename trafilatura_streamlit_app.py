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
    """Realiza o download bruto do HTML.

    1. Tenta `trafilatura.fetch_url` (rápido, já segue redirects)
    2. Se falhar, faz `requests.get` com User‑Agent de desktop
    """
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
    """Tenta construir a versão /amp de uma URL."""
    if url.rstrip("/").endswith("/amp"):
        return url
    return url.rstrip("/") + "/amp"

# ----------------------------
# Next.js specific helper
# ----------------------------

def extract_from_next_data(html: str) -> str | None:
    """Extrai o corpo do artigo a partir do script JSON `__NEXT_DATA__`.

    • Captura todos os blocos `__NEXT_DATA__` (pode haver mais de um).
    • Itera de trás para frente: o último costuma conter o payload completo.
    • Procura os caminhos `props.pageProps.post.content` ou
      `props.pageProps.data.post.content`.
    """
    scripts = re.findall(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    if not scripts:
        return None

    for raw_json in reversed(scripts):
        try:
            data = json.loads(raw_json)
        except Exception:
            continue

        page_props = data.get("props", {}).get("pageProps", {})
        post_obj = page_props.get("post") or page_props.get("data", {}).get("post")
        if not post_obj or not isinstance(post_obj, dict):
            continue

        content_html = post_obj.get("content")
        if content_html and isinstance(content_html, str):
            txt = trafilatura.html2txt(content_html)
            if txt and len(txt.split()) > 50:
                return txt.strip()
    return None

# ----------------------------
# Extraction pipeline
# ----------------------------

def extract_text(html: str) -> str | None:
    """Executa uma cascata de técnicas para obter texto limpo."""
    # 0) Dados Next.js
    txt = extract_from_next_data(html)
    if txt:
        return txt

    # 1) Heurística padrão (precisão)
    txt = trafilatura.extract(html, include_formatting=False, include_links=False, favor_recall=False)
    if txt and len(txt.split()) > 50:
        return txt.strip()

    # 2) Heurística recall (captura mais, porém com ruído)
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

        if not text:  # tenta versão AMP
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

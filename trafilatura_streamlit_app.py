import json
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
    # 1) Trafilatura fetch_url
    html = trafilatura.fetch_url(url)
    if html:
        return html

    # 2) Requests fallback
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
            resp.encoding = resp.apparent_encoding  # garante unicode correto
            return resp.text
    except RequestException:
        pass

    return None


def maybe_amp_url(url: str) -> str:
    """Gera uma possível URL AMP (estática) para sites de notícia."""
    if url.rstrip("/").endswith("/amp"):
        return url  # já é AMP
    if url.endswith("/"):
        return url + "amp"
    return url + "/amp"


# ----------------------------
# Extraction logic
# ----------------------------

def extract_text(html: str) -> str | None:
    """Extrai texto limpo usando cascata de técnicas."""
    # 1) Precisão
    text = trafilatura.extract(html, include_formatting=False, include_links=False, favor_recall=False)
    if text and len(text.split()) > 50:
        return text.strip()

    # 2) Recall
    text = trafilatura.extract(html, include_formatting=False, include_links=False, favor_recall=True)
    if text and len(text.split()) > 50:
        return text.strip()

    # 3) Readability‑lxml → html2txt
    try:
        from readability import Document
        main_html = Document(html).summary(html_partial=True)
        text = trafilatura.html2txt(main_html)
        if text and len(text.split()) > 50:
            return text.strip()
    except Exception:
        pass

    # 4) html2txt puro
    try:
        text = trafilatura.html2txt(html)
        if text and len(text.split()) > 50:
            return text.strip()
    except Exception:
        pass

    # 5) BeautifulSoup fallback
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n", strip=True)
        if text and len(text.split()) > 50:
            return text
    except Exception:
        pass

    return None


# ----------------------------
# Streamlit UI
# ----------------------------

url = st.text_input("Insira a URL a ser processada:")

if url:
    with st.spinner("⌛ Baixando e extraindo conteúdo…"):
        # 1) Tenta URL normal
        html = fetch_url_raw(url)
        text: str | None = None
        if html:
            text = extract_text(html)

        # 2) Se falhar, tenta versão AMP (muitos sites de notícia têm HTML limpo lá)
        if not text or text == "" or text == "Texto não encontrado":
            amp_url = maybe_amp_url(url)
            if amp_url != url:
                amp_html = fetch_url_raw(amp_url)
                if amp_html:
                    text = extract_text(amp_html) or text
                    # Substitui html para extração de título caso texto AMP funcione
                    if text and len(text.split()) > 50:
                        html = amp_html

        if not html:
            st.error("❌ Não foi possível baixar a página. Verifique a URL e tente novamente.")
        else:
            # --------------  TÍTULO  --------------
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
                            meta_dict = json.loads(meta)
                            title = meta_dict.get("title")
                except Exception:
                    pass

            title = title or "Título não encontrado"

            # --------------  TEXTO  --------------
            text = text or "Texto não encontrado"

            # --------------  UI  --------------
            st.success("✅ Conteúdo extraído com sucesso!")

            st.subheader("Título")
            st.code(title, language=None)

            st.subheader("Texto")
            st.code(text, language=None)

            st.caption("Clique no ícone de cópia (📋) no canto superior direito dos blocos para copiar.")

# ----------------------------
#     Como rodar localmente
# ----------------------------
# 1. pip install streamlit trafilatura[all] requests readability‑lxml beautifulsoup4
# 2. streamlit run trafilatura_streamlit_app.py

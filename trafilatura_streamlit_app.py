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

def fetch_with_fallback(url: str) -> str | None:
    """Tenta baixar a página com Trafilatura; se falhar, usa requests com um User‑Agent comum."""
    # 1) Tentativa direta (Trafilatura já define um UA próprio)
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        return downloaded

    # 2) Fallback manual com requests
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
            return resp.text
    except RequestException:
        pass

    return None


# ----------------------------
# Extraction logic
# ----------------------------

def extract_text(html: str) -> str | None:
    """Extrai texto limpo usando uma cascata de técnicas."""
    # 1) Heurísticas padrão (precisão)
    text = trafilatura.extract(
        html,
        include_formatting=False,
        include_links=False,
        favor_recall=False,
    )
    if text:
        return text.strip()

    # 2) Heurísticas de recall (mais permissivas)
    text = trafilatura.extract(
        html,
        include_formatting=False,
        include_links=False,
        favor_recall=True,
    )
    if text:
        return text.strip()

    # 3) Readability‑lxml (útil para páginas com muito JS ou paywall)
    try:
        from readability import Document  # pip install readability‑lxml

        doc = Document(html)
        main_html = doc.summary(html_partial=True)
        text = trafilatura.html2txt(main_html)
        if text:
            return text.strip()
    except Exception:
        pass

    # 4) Conversão bruta HTML→TXT (captura tudo)
    try:
        text = trafilatura.html2txt(html)
        if text:
            return text.strip()
    except Exception:
        pass

    # 5) Fallback BeautifulSoup (último recurso, pode trazer lixo)
    try:
        from bs4 import BeautifulSoup  # pip install beautifulsoup4

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n", strip=True)
        if text:
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
        html = fetch_with_fallback(url)
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
            text = extract_text(html) or "Texto não encontrado"

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

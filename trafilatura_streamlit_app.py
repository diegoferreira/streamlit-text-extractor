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


def fetch_with_fallback(url: str) -> str | None:
    """Tenta baixar a página com Trafilatura; se falhar, usa requests com um User‑Agent comum."""
    # 1) Tentativa direta (Trafilatura já define um User‑Agent aceitável)
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        return downloaded

    # 2) Fallback manual caso o site bloqueie o crawler
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


url = st.text_input("Insira a URL a ser processada:")

if url:
    with st.spinner("⌛ Baixando e extraindo conteúdo…"):
        downloaded = fetch_with_fallback(url)
        if not downloaded:
            st.error("❌ Não foi possível baixar a página. Verifique a URL e tente novamente.")
        else:
            # ------------------  TÍTULO  ------------------
            title: str | None = None

            # 1) Função oficial (Trafilatura ≥ 1.6)
            try:
                from trafilatura import extract_title  # type: ignore
                title = extract_title(downloaded)
            except Exception:
                pass

            # 2) Metadados (funciona em várias versões)
            if title is None:
                try:
                    meta = trafilatura.extract_metadata(downloaded)
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

            # ------------------  TEXTO  ------------------
            try:
                text = trafilatura.extract(
                    downloaded,
                    include_formatting=False,
                    include_links=False,
                    favor_recall=False,
                )
            except Exception:
                text = None

            text = text or "Texto não encontrado"

            # ------------------  UI  ------------------
            st.success("✅ Conteúdo extraído com sucesso!")

            st.subheader("Título")
            st.code(title, language=None)

            st.subheader("Texto")
            st.code(text, language=None)

            st.caption("Clique no ícone de cópia (📋) no canto superior direito dos blocos para copiar.")

# ----------------------------
#     Como rodar localmente
# ----------------------------
# 1. pip install streamlit trafilatura[all] requests
# 2. streamlit run trafilatura_streamlit_app.py

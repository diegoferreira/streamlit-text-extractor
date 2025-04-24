import streamlit as st
import trafilatura

st.set_page_config(page_title="Trafilatura Content Extractor", layout="wide")

st.title("🔗 Extrator de Título e Texto via Trafilatura")
st.markdown(
    "Cole a URL de qualquer página pública. O app fará o download, limpará o HTML e mostrará **Título** e **Texto** prontos para copiar."
)

url = st.text_input("Insira a URL a ser processada:")

if url:
    with st.spinner("⌛ Baixando e extraindo conteúdo…"):
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            st.error("❌ Não foi possível baixar a página. Verifique a URL e tente novamente.")
        else:
            # --- TÍTULO ---
            # Versões recentes da Trafilatura (≥ 1.6) expõem extract_title; faça fallback caso não exista
            try:
                from trafilatura import extract_title  # type: ignore
                title = extract_title(downloaded)
            except (ImportError, AttributeError):
                meta = trafilatura.extract_metadata(downloaded)
                title = meta["title"] if meta and meta.get("title") else None

            title = title or "Título não encontrado"

            # --- TEXTO ---
            text = trafilatura.extract(
                downloaded,
                include_formatting=False,
                include_links=False,
                favor_recall=False,
            ) or "Texto não encontrado"

            st.success("✅ Conteúdo extraído com sucesso!")

            st.subheader("Título")
            st.code(title, language=None)

            st.subheader("Texto")
            st.code(text, language=None)

            st.caption("Os blocos acima possuem um ícone de cópia no canto superior direito.")

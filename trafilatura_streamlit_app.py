import streamlit as st
import trafilatura

st.set_page_config(page_title="Trafilatura Content Extractor", layout="wide")

st.title("🔗 Extrator de Título e Texto via Trafilatura")
st.markdown(
    "Entre com a URL de qualquer página pública. O app fará o download, limpará o HTML e mostrará **Título** e **Texto** prontos para copiar."  # noqa: E501
)

url = st.text_input("Insira a URL a ser processada:")

if url:
    with st.spinner("⌛ Baixando e extraindo conteúdo…"):
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            st.error("❌ Não foi possível baixar a página. Verifique a URL e tente novamente.")
        else:
            # Extrai o título de forma dedicada; Trafilatura retorna None caso não encontre
            title = trafilatura.extract_title(downloaded) or "Título não encontrado"
            # Extrai o texto principal, removendo links e formatação extra
            text = trafilatura.extract(
                downloaded,
                include_formatting=False,
                include_links=False,
                favor_recall=False,
            ) or "Texto não encontrado"

            st.success("✅ Conteúdo extraído com sucesso!")

            st.subheader("Título")
            # st.code oferece botão embutido de copiar ☑️
            st.code(title, language=None)

            st.subheader("Texto")
            st.code(text, language=None)

            st.caption(
                "Os blocos acima possuem um ícone de cópia no canto superior direito para facilitar o uso em outros lugares."
            )

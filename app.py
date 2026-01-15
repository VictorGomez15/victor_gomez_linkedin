"""
Comandos rápidos para levantar la app:
pip install pandas streamlit plotly
streamlit run app.py
"""

from pathlib import Path
import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_PATH = Path(__file__).parent / "Connections.csv"
PHOTO_PATH = Path(__file__).parent / "VictorGomez.jpeg"
px.defaults.template = "simple_white"
px.defaults.color_discrete_sequence = px.colors.qualitative.Plotly


def estilizar_figura(fig):
    """Aplica tipografía oscura y fondos claros a cualquier figura."""
    fig.update_layout(
        font=dict(color="#111827", size=14),
        title_font=dict(color="#111827", size=18),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        legend_title_font=dict(color="#111827"),
        legend_font=dict(color="#111827"),
    )
    fig.update_xaxes(title_font_color="#111827", tickfont_color="#111827")
    fig.update_yaxes(title_font_color="#111827", tickfont_color="#111827")
    return fig


def clasificar_seniority(posicion: str) -> str:
    """Devuelve High/Medium/Low según palabras clave en la posición."""
    if not isinstance(posicion, str) or not posicion.strip():
        return "Low"

    texto = posicion.strip().upper()
    high = ["CEO", "FOUNDER", "OWNER", "PARTNER", "DIRECTOR", "HEAD", "VP", "PRESIDENT", "CHIEF"]
    medium = ["MANAGER", "LEAD", "SENIOR", "COORDINATOR", "CONSULTANT"]

    if any(clave in texto for clave in high):
        return "High"
    if any(clave in texto for clave in medium):
        return "Medium"
    return "Low"


def _quitar_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar_posicion(posicion: str) -> str:
    """Agrupa variaciones comunes de cargos para el gráfico Top 15."""
    if not isinstance(posicion, str):
        return ""
    texto = posicion.strip().lower()
    texto = re.sub(r"\s+", " ", texto)
    texto_sin = _quitar_acentos(texto)
    texto_clean = re.sub(r"[^a-z0-9\s/,&-]", " ", texto_sin)
    texto_clean = re.sub(r"\s+", " ", texto_clean).strip()

    # Detección por inclusiones para robustez
    if "chief executive officer" in texto_clean or re.search(r"\bceo\b", texto_clean):
        return "CEO"
    if re.search(r"\brector[ae]?\b", texto_clean):
        return "Rector"
    if re.search(r"\bvicerrector[ae]?\s+academic", texto_clean) or re.search(r"\bvice\s+chancellor\b", texto_clean):
        return "Vicerrector Académico"
    if (
        re.search(r"\bgerente\s+general\b", texto_clean)
        or re.search(r"\bgernte\s+general\b", texto_clean)
        or re.search(r"\bgeneral\s+manager\b", texto_clean)
        or re.search(r"\bgerente\b", texto_clean)
    ):
        return "Gerente General"
    if re.search(r"\bdirector[ao]?\b", texto_clean):
        return "Director"
    if re.search(r"\bpresident[ea]?\b", texto_clean):
        return "Presidente"
    if re.search(r"\bfundador\b", texto_clean) or re.search(r"\bfounder\b", texto_clean):
        return "Fundador"
    if (
        re.search(r"\bprof+esor\b", texto_clean)
        or re.search(r"\bprofessor\b", texto_clean)
        or re.search(r"\bdocent[ea]?\b", texto_clean)
        or re.search(r"\bdocencia\b", texto_clean)
    ):
        return "Profesor/Docente"
    if re.search(r"\bconsultor\b", texto_clean):
        return "Consultor"
    return posicion.strip()


@st.cache_data(show_spinner=False)
def cargar_datos(archivo):
    df = pd.read_csv(archivo, skiprows=3)
    df["Connected On"] = pd.to_datetime(df["Connected On"], format="%d %b %Y", errors="coerce")
    df["Position"] = df["Position"].fillna("").str.strip()
    df["Position_norm"] = df["Position"].apply(normalizar_posicion)
    df["Year"] = df["Connected On"].dt.year
    df["Seniority"] = df["Position"].apply(clasificar_seniority)
    return df


def crear_grafico_crecimiento(df):
    crecimiento = (
        df.dropna(subset=["Year"])
        .groupby("Year")
        .size()
        .reset_index(name="Nuevos contactos")
        .sort_values("Year")
    )
    fig = px.bar(
        crecimiento,
        x="Year",
        y="Nuevos contactos",
        text="Nuevos contactos",
        title="Crecimiento de nuevos contactos por año",
    )
    fig.update_traces(textposition="outside", marker_color="#2980b9")
    fig.update_layout(yaxis_title="Nuevos contactos", xaxis_title="Año", uniformtext_minsize=8)
    return estilizar_figura(fig)


def crear_grafico_posiciones(df):
    top_posiciones = (
        df[df["Position_norm"] != ""]
        .groupby("Position_norm")
        .size()
        .reset_index(name="Conteo")
        .sort_values("Conteo", ascending=False)
        .head(15)
    )
    fig = px.bar(
        top_posiciones.sort_values("Conteo"),
        x="Conteo",
        y="Position_norm",
        orientation="h",
        title="Top 15 cargos/posiciones",
        text="Conteo",
    )
    fig.update_traces(marker_color="#27ae60", textposition="outside")
    fig.update_layout(xaxis_title="Cantidad", yaxis_title="Cargo/Posición")
    return estilizar_figura(fig)


def crear_grafico_seniority(df):
    niveles = df["Seniority"].value_counts().reset_index()
    niveles.columns = ["Seniority", "Cantidad"]
    fig = px.pie(
        niveles,
        names="Seniority",
        values="Cantidad",
        hole=0.45,
        title="Distribución por nivel (High / Medium / Low)",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label", textfont_color="#111827")
    return estilizar_figura(fig)


def aplicar_filtros(df):
    st.sidebar.header("Filtros")
    if df["Year"].dropna().empty:
        return df

    min_year, max_year = int(df["Year"].min()), int(df["Year"].max())
    rango = st.sidebar.slider("Rango de años", min_year, max_year, (min_year, max_year), step=1)
    return df[(df["Year"] >= rango[0]) & (df["Year"] <= rango[1])]


def main():
    st.set_page_config(page_title="Analítica del perfil de Linkedln de Victor Gómez", layout="wide")
    st.markdown(
        """
        <style>
        :root {
            color-scheme: light;
            --background-color: #ffffff;
            --secondary-background-color: #f7f7f7;
            --text-color: #111827;
            --primary-color: #2563eb;
        }
        body, .stApp, p, h1, h2, h3, h4, h5, h6, label, span {
            background-color: #ffffff !important;
            color: #111827 !important;
        }
        .stApp { background-color: #ffffff; }
        [data-testid="stSidebar"] { background-color: #f7f7f7; color: #111827; }
        [data-testid="stToolbar"], [data-testid="stHeader"] {
            background: #ffffff !important;
            color: #111827 !important;
        }
        /* File uploader claro */
        [data-testid="stFileUploadDropzone"], [data-testid="stFileUploader"] section {
            background: #ffffff !important;
            border: 1px solid #d7dde3 !important;
            color: #111827 !important;
        }
        [data-testid="stFileUploader"] div { color: #111827 !important; }
        [data-testid="stFileUploader"] button {
            background: #2563eb !important;
            color: #ffffff !important;
            border: 1px solid #1d4ed8 !important;
        }
        [data-testid="stFileUploader"] button:hover {
            background: #1d4ed8 !important;
            color: #ffffff !important;
        }
        /* Sliders claros */
        [data-baseweb="slider"] [role="slider"] { background: #d93025 !important; }
        [data-baseweb="slider"] div { color: #111827; }
        /* Select y entradas */
        [data-baseweb="select"] div, input, textarea, select {
            background: #ffffff !important;
            color: #111827 !important;
            border-color: #d7dde3 !important;
        }
        /* Métricas */
        [data-testid="metric-container"] {
            background: #ffffff;
            color: #111827;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 8px;
        }
        /* Dataframe tabla clara (AgGrid interno) */
        [data-testid="stDataFrame"] { background: #ffffff !important; }
        [data-testid="stDataFrame"] [role="grid"] { background: #ffffff !important; color: #111827 !important; }
        [data-testid="stDataFrame"] div[role="gridcell"],
        [data-testid="stDataFrame"] div[role="rowgroup"],
        [data-testid="stDataFrame"] div[role="row"] {
            background: #ffffff !important;
            color: #111827 !important;
        }
        [data-testid="stDataFrame"] [role="columnheader"] {
            background: #f3f4f6 !important;
            color: #111827 !important;
            border-color: #e5e7eb !important;
        }
        [data-testid="stDataFrame"] [role="row"] { background: #ffffff !important; }
        [data-testid="stDataFrame"] [role="row"]:nth-child(even) { background: #f9fafb !important; }
        [data-testid="stDataFrame"] div { color: #111827 !important; }
        [data-testid="stDataFrame"] table { background: #ffffff !important; color: #111827 !important; }
        [data-testid="stDataFrame"] thead tr th { background: #f3f4f6 !important; color: #111827 !important; }
        [data-testid="stDataFrame"] tbody tr { background: #ffffff !important; }
        [data-testid="stDataFrame"] tbody tr:nth-child(even) { background: #f9fafb !important; }
        /* Toolbar y botones de dataframe */
        [data-testid="stDataFrame"] [data-testid="toolbar"] {
            background: #ffffff !important;
            color: #111827 !important;
            border: none !important;
        }
        [data-testid="stDataFrame"] [data-testid="toolbar"] button,
        [data-testid="stDataFrame"] [data-testid="toolbar"] svg {
            background: #ffffff !important;
            color: #111827 !important;
            fill: #111827 !important;
        }
        [data-testid="stDataFrame"] [role="columnheader"] button {
            background: transparent !important;
            color: #111827 !important;
        }
        /* Scrollbar claro dentro de la tabla */
        [data-testid="stDataFrame"] ::-webkit-scrollbar { width: 8px; height: 8px; }
        [data-testid="stDataFrame"] ::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 6px; }
        [data-testid="stDataFrame"] ::-webkit-scrollbar-track { background: #f3f4f6; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Analítica del perfil de Linkedln de Victor Gómez")
    st.caption("Dashboard interactivo local usando Streamlit + Plotly")

    st.sidebar.write("Carga un archivo o usa el `Connections.csv` local.")
    archivo_subido = st.sidebar.file_uploader("Archivo Connections.csv", type=["csv"])
    archivo = archivo_subido if archivo_subido else DATA_PATH

    if not Path(archivo.name).exists() and not archivo_subido:
        st.error("No se encontró `Connections.csv`. Sube el archivo o colócalo junto a app.py.")
        st.stop()

    df = cargar_datos(archivo)
    df_filtrado = aplicar_filtros(df)

    col_img, col_info = st.columns([1, 2])
    if PHOTO_PATH.exists():
        col_img.image(str(PHOTO_PATH), caption="Victor Gómez", width=320)
    else:
        col_img.warning("No se encontró VictorGomez.jpeg")
    with col_info:
        st.subheader("KPIs rápidos")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total contactos", f"{len(df_filtrado):,}".replace(",", "."))
        col2.metric("Empresas únicas", f"{df_filtrado['Company'].nunique():,}".replace(",", "."))
        col3.metric("Nuevos este año", df_filtrado[df_filtrado["Year"] == pd.Timestamp.now().year].shape[0])

    col_a, col_b = st.columns([2, 1])
    col_a.plotly_chart(crear_grafico_crecimiento(df_filtrado), use_container_width=True)
    col_b.plotly_chart(crear_grafico_seniority(df_filtrado), use_container_width=True)

    st.plotly_chart(crear_grafico_posiciones(df_filtrado), use_container_width=True)

    st.subheader("Tabla de contactos")
    columnas = ["First Name", "Last Name", "Company", "Position", "Connected On", "Seniority"]
    tabla = df_filtrado[columnas].sort_values("Connected On", ascending=False)
    st.dataframe(tabla, use_container_width=True)


if __name__ == "__main__":
    main()


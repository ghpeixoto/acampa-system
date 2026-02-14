import streamlit as st

# =======================================================
# 1. CONFIGURAÇÃO VISUAL
# =======================================================
st.set_page_config(
    page_title="AcampaSystem", 
    layout="wide", 
    page_icon="⛺"
)

# CSS PARA BOTÕES ESTILO CARD (AZUL E MODERNO)
st.markdown("""
<style>
    /* Fundo Geral */
    [data-testid="stAppViewContainer"] { background-color: #0a192f; color: #e6f1ff; }
    [data-testid="stHeader"] { background-color: #0a192f; }
    [data-testid="stSidebar"] { background-color: #112240; border-right: 1px solid #233554; }

    /* Estilo dos Botões Grandes */
    div.stButton > button {
        background: linear-gradient(135deg, #112240 0%, #172a45 100%) !important;
        color: #00c6ff !important;
        border: 2px solid #00c6ff !important;
        border-radius: 15px !important;
        height: 150px !important;  /* Altura do Card */
        width: 100% !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
        transition: all 0.3s ease !important;
        white-space: pre-wrap; /* Permite quebra de linha no texto */
    }

    /* Efeito Hover (Passar o mouse) */
    div.stButton > button:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 198, 255, 0.2) !important;
        background: #1d3557 !important;
        border-color: #64ffda !important;
        color: #64ffda !important;
    }
    
    h1 { color: #00c6ff !important; text-align: center; }
    h3 { color: #8892b0 !important; text-align: center; font-weight: 400; }
</style>
""", unsafe_allow_html=True)

# =======================================================
# 2. TÍTULO
# =======================================================
st.markdown("<h1>⛺ AcampaSystem</h1>", unsafe_allow_html=True)
st.markdown("<h3>Painel de Controle Central</h3>", unsafe_allow_html=True)
st.divider()

# =======================================================
# 3. MENU DE NAVEGAÇÃO (GRID)
# =======================================================

# --- LINHA 1 ---
col1, col2 = st.columns(2)

with col1:
    st.write("") # Espaçamento
    # Botão Check-in
    if st.button("✅\nCHECK-IN\n(Portaria)", use_container_width=True):
        st.switch_page("pages/Checkin.py")

with col2:
    st.write("") # Espaçamento
    # Botão Cantina
    if st.button("🍔\nCANTINA\n(Financeiro)", use_container_width=True):
        st.switch_page("pages/Cantina.py")

# --- LINHA 2 ---
col3, col4 = st.columns(2)

with col3:
    st.write("") # Espaçamento
    # Botão Enfermaria
    if st.button("💊\nMEDICAÇÕES\n(Lista)", use_container_width=True):
        st.switch_page("pages/Medicacoes.py")

with col4:
    st.write("") # Espaçamento
    # Botão Líderes
    if st.button("🛏️\nLÍDERES\n(Quartos)", use_container_width=True):
        st.switch_page("pages/Lideres.py")

# --- LINHA 3 ---
col5, col6 = st.columns(2)

with col5:
    st.write("") # Espaçamento
    # Botão Escala de Oração Atualizado
    if st.button("🙏\nESCALA DE ORAÇÃO\n(Servos)", use_container_width=True):
        st.switch_page("pages/Escala_de_Oracao.py")

with col6:
    st.empty()

# Rodapé
st.markdown("---")
st.markdown("<div style='text-align: center; color: #8892b0; font-size: 12px;'>Sistema Integrado AcampaTeens v3.2</div>", unsafe_allow_html=True)

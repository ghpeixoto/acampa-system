import streamlit as st
import pandas as pd
import time
from supabase import create_client

# =======================================================
# 1. CONFIGURAÇÃO
# =======================================================
st.set_page_config(page_title="Escala de Oração", layout="wide", page_icon="🙏")

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    SUPABASE_URL = "https://gerzjzmkbzpkdhrxacka.supabase.co"
    SUPABASE_KEY = "sb_secret_BcGLoGEXRfVMA-ajLuqhdw_0zlAFUmn"

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0a192f; color: #e6f1ff; }
    [data-testid="stHeader"] { background-color: #0a192f; }
    
    .slot-card {
        background-color: #112240;
        border-left: 5px solid #00c6ff;
        padding: 10px 15px;
        border-radius: 8px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    div.stButton > button {
        background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%) !important;
        color: white !important;
        border: none;
        border-radius: 50px;
        font-weight: bold;
    }
    
    /* Input da busca */
    div[data-baseweb="input"] > div {
        background-color: #172a45 !important;
        border: 1px solid #00c6ff !important;
        border-radius: 8px !important;
    }
    .stTextInput input { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# =======================================================
# 2. FUNÇÕES DE BANCO
# =======================================================
@st.cache_resource
def init_supabase():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None

def carregar_escala():
    sb = init_supabase()
    res = sb.table("escala_oracao").select("*").order("id").execute()
    return pd.DataFrame(res.data)

def atualizar_checkin(id_registro, status):
    sb = init_supabase()
    sb.table("escala_oracao").update({"checkin": status}).eq("id", id_registro).execute()

# =======================================================
# 3. INTERFACE
# =======================================================
st.title("🙏 Relógio de Oração (Servos)")
st.write("A oração não pode parar! Turnos de **10 minutos**, de 08:00 às 20:00.")

st.divider()

# Carrega Escala Atual
df_escala = carregar_escala()

if df_escala.empty:
    st.info("A escala ainda não foi gerada no banco de dados.")
else:
    # --- BARRA DE BUSCA ---
    st.markdown("### 🔍 Ache o seu horário")
    busca_nome = st.text_input("Digite seu nome para filtrar a lista:", placeholder="Ex: Thiago...")
    
    if busca_nome:
        df_escala = df_escala[df_escala['nome_servo'].str.contains(busca_nome, case=False, na=False)]
        st.success(f"Mostrando os turnos para: **{busca_nome}**")
        st.write("")
    
    # Separação por Dias em Abas (Tabs)
    tab_dom, tab_seg, tab_ter = st.tabs(["📅 Domingo", "📅 Segunda-feira", "📅 Terça-feira"])
    
    dias_abas = {
        "Domingo": tab_dom,
        "Segunda": tab_seg,
        "Terça": tab_ter
    }
    
    for dia_nome, aba in dias_abas.items():
        with aba:
            df_dia = df_escala[df_escala['dia'] == dia_nome]
            
            if df_dia.empty:
                if busca_nome:
                    st.info(f"Nenhum turno para '{busca_nome}' neste dia.")
                else:
                    st.info("Nenhum turno cadastrado para este dia.")
            else:
                for idx, row in df_dia.iterrows():
                    col_info, col_check = st.columns([5, 1])
                    
                    check_status = bool(row['checkin'])
                    cor_borda = "#25D366" if check_status else "#00c6ff"
                    icone_status = "✅ No Monte" if check_status else "⏳ Aguardando"
                    
                    with col_info:
                        st.markdown(f"""
                        <div style="background-color: #112240; border-left: 5px solid {cor_borda}; padding: 10px 15px; border-radius: 8px; margin-bottom: 5px; display: flex; align-items: center;">
                            <div style="font-size: 16px; font-weight: bold; color: {cor_borda}; width: 140px;">⏰ {row['hora']}</div>
                            <div style="font-size: 16px; color: white; flex-grow: 1;">👤 {row['nome_servo']}</div>
                            <div style="font-size: 13px; color: #aaa;">{icone_status}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_check:
                        st.write("") # Espaço para alinhar verticalmente
                        novo_status = st.checkbox("Check-in", value=check_status, key=f"chk_{row['id']}_{dia_nome}")
                        
                        if novo_status != check_status:
                            atualizar_checkin(row['id'], novo_status)
                            st.rerun()

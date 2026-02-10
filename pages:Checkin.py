import streamlit as st
import pandas as pd
from datetime import datetime
import time
from supabase import create_client, Client

# =======================================================
# 1. CONFIGURAÇÃO E CREDENCIAIS
# =======================================================
st.set_page_config(page_title="Check-in Acampa", layout="wide", page_icon="✅")

SUPABASE_URL = "https://gerzjzmkbzpkdhrxacka.supabase.co"
SUPABASE_KEY = "sb_secret_BcGLoGEXRfVMA-ajLuqhdw_0zlAFUmn"

# =======================================================
# 2. ESTILO VISUAL
# =======================================================
st.markdown("""
<style>
    /* Fundo */
    [data-testid="stAppViewContainer"] { background-color: #0a192f; color: #e6f1ff; }
    [data-testid="stHeader"] { background-color: #0a192f; }
    [data-testid="stSidebar"] { background-color: #112240; border-right: 1px solid #233554; }

    /* Inputs */
    div[data-baseweb="input"] > div {
        background-color: #172a45 !important;
        border: 1px solid #00c6ff !important;
        border-radius: 8px !important;
    }
    .stTextInput input, .stNumberInput input { color: #ffffff !important; }

    /* BOTÃO PRIMÁRIO (GRANDE - CONFIRMAR) */
    button[kind="primary"] {
        background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 50px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        padding: 10px 24px !important;
        min-height: 46px;
    }
    button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0, 114, 255, 0.4) !important;
    }

    /* BOTÃO SECUNDÁRIO (PEQUENO - TABELA) */
    button[kind="secondary"] {
        background-color: transparent !important;
        border: 1px solid #00c6ff !important;
        color: #00c6ff !important;
        border-radius: 20px !important;
        font-size: 12px !important;
        font-weight: bold !important;
        padding: 2px 10px !important;
        height: 28px !important;
        min-height: 28px !important;
    }
    button[kind="secondary"]:hover {
        background-color: #00c6ff !important;
        color: #0a192f !important;
    }

    /* Cards */
    div[data-testid="metric-container"] {
        background-color: #112240;
        border: 1px solid #233554;
        padding: 10px;
        border-radius: 8px;
    }

    h1, h2, h3 { color: #00c6ff !important; }
    p, label, span, div { color: #e6f1ff; }
</style>
""", unsafe_allow_html=True)

# =======================================================
# 3. FUNÇÕES DE BANCO DE DADOS
# =======================================================
@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Erro conexão Supabase: {e}")
        return None

@st.cache_data(ttl=5)
def carregar_dados():
    supabase = init_supabase()
    try:
        response = supabase.table("participantes").select("*").order("nome_completo").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erro ao ler dados: {e}")
        return pd.DataFrame()

# Função Check-in Padrão
def gravar_checkin(id_part, nome, valor, forma, obs, operador):
    supabase = init_supabase()
    dh_iso = datetime.now().isoformat()
    dh_br = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    try:
        # 1. Atualiza Status
        supabase.table("participantes").update({
            "check_in": True,
            "data_hr_check_in": dh_iso,
            "operador_check_in": operador
        }).eq("id", id_part).execute()

        # 2. Insere Financeiro
        if valor > 0:
            desc = f"Depósito Check-in ({forma})"
            if obs: desc += f" - {obs}"
            transacao = {
                "id_participante": id_part,
                "nome_participante": nome,
                "data_hora": dh_br,
                "item_descricao": desc,
                "valor": float(valor),
                "tipo": "Entrada",
                "operador": operador
            }
            supabase.table("transacoes").insert(transacao).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao gravar: {e}")
        return False

# Função SÓ Financeiro (Para o botão extra)
def gravar_deposito_tardio(id_part, nome, valor, forma, obs, operador):
    supabase = init_supabase()
    dh_br = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        desc = f"Depósito Tardio ({forma})"
        if obs: desc += f" - {obs}"
        
        transacao = {
            "id_participante": id_part,
            "nome_participante": nome,
            "data_hora": dh_br,
            "item_descricao": desc,
            "valor": float(valor),
            "tipo": "Entrada",
            "operador": operador
        }
        supabase.table("transacoes").insert(transacao).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao gravar depósito: {e}")
        return False

# =======================================================
# 4. MODAIS (POP-UPS)
# =======================================================

# MODAL 1: CHECK-IN COMPLETO (PRIMEIRA VEZ)
@st.dialog("📝 Confirmar Entrada")
def modal_checkin(id_part, nome, resp, tipo, operador):
    st.markdown(f"### {nome}")
    cor = "#00c6ff" if tipo == "Teens" else "#d946ef"
    st.markdown(f"<span style='background-color:{cor}; color:white; padding:4px 10px; border-radius:15px; font-weight:bold; font-size:12px'>{tipo}</span>", unsafe_allow_html=True)
    st.markdown(f"**Responsável:** {resp}")
    st.write("---")

    trouxe_dinheiro = st.toggle("💵 Trouxe Depósito/Dinheiro?", value=False)
    val, forma, obs = 0.0, "Dinheiro", ""
    if trouxe_dinheiro:
        c1, c2 = st.columns(2)
        val = c1.number_input("Valor (R$)", min_value=0.0, step=10.0)
        forma = c2.selectbox("Forma", ["Dinheiro", "PIX", "Cartão"])
        obs = st.text_input("Observação", placeholder="Ex: Envelope")

    st.write("")
    if st.button("✅ REALIZAR CHECK-IN", type="primary"):
        with st.spinner("Salvando..."):
            if gravar_checkin(id_part, nome, val, forma, obs, operador):
                st.toast(f"Check-in de {nome} realizado!", icon="🎉")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

# MODAL 2: DEPÓSITO EXTRA (SE ESQUECEU)
@st.dialog("💰 Lançar Depósito")
def modal_deposito_extra(id_part, nome, operador):
    st.warning(f"Adicionar Depósito para **{nome}** (Já fez check-in).")
    
    c1, c2 = st.columns(2)
    val = c1.number_input("Valor (R$)", min_value=0.0, step=10.0)
    forma = c2.selectbox("Forma", ["Dinheiro", "PIX", "Cartão"])
    obs = st.text_input("Observação", placeholder="Ex: Realizou o Pix 09/02/2026")
    
    st.write("")
    if st.button("💾 SALVAR PAGAMENTO", type="primary"):
        if val > 0:
            with st.spinner("Gravando financeiro..."):
                if gravar_deposito_tardio(id_part, nome, val, forma, obs, operador):
                    st.toast("Pagamento registrado com sucesso!", icon="💰")
                    time.sleep(1)
                    st.rerun()
        else:
            st.error("O valor deve ser maior que zero.")

# =======================================================
# 5. TELA PRINCIPAL
# =======================================================
if "operador_checkin" not in st.session_state:
    st.session_state.operador_checkin = ""

# --- LOGIN ---
if st.session_state.operador_checkin == "":
    st.title("🛡️ Check-in AcampaTeens 2026")
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        nome_op = st.text_input("Seu Nome:", placeholder="Ex: Isabela")
        st.write("")
        if st.button("ACESSAR", type="primary", use_container_width=True):
            if nome_op and nome_op.strip():
                st.session_state.operador_checkin = nome_op.strip()
                st.rerun()

# --- PAINEL ---
else:
    c_head, c_btn = st.columns([5, 1])
    c_head.title("✅ Check-in")
    if c_btn.button("Sair", type="secondary"):
        st.session_state.operador_checkin = ""
        st.rerun()

    st.caption(f"Operador: {st.session_state.operador_checkin}")

    df = carregar_dados()

    # --- MÉTRICAS ---
    if not df.empty:
        df_teens = df[df['tipo_participante'] == 'Teen']
        df_servos = df[df['tipo_participante'] == 'Servo']

        t_teens = len(df_teens)
        c_teens = len(df_teens[df_teens['check_in'] == True])
        f_teens = t_teens - c_teens

        t_servos = len(df_servos)
        c_servos = len(df_servos[df_servos['check_in'] == True])
        f_servos = t_servos - c_servos
    else:
        t_teens = c_teens = f_teen = 0
        t_servos = c_servos = f_servos = 0

    st.markdown("##### 🔵 Status Teens")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total", t_teens)
    m2.metric("Chegaram", c_teens)
    m3.metric("Faltam", f_teens)

    st.markdown("##### 🟣 Status Servos")
    m4, m5, m6 = st.columns(3)
    m4.metric("Total", t_servos)
    m5.metric("Chegaram", c_servos)
    m6.metric("Faltam", f_servos)

    st.divider()

    # --- BUSCA E FILTRO ---
    st.markdown("### 🔍 Pesquisar")
    col_busca, col_filtro = st.columns([3, 1])
    
    with col_busca:
        busca = st.text_input("Nome", placeholder="Digite o nome...", label_visibility="collapsed")
    with col_filtro:
        filtro_tipo = st.selectbox("Filtrar Tipo", ["Todos", "Teen", "Servo"], label_visibility="collapsed")

    df_show = df.copy()
    if busca:
        df_show = df_show[df_show['nome_completo'].astype(str).str.lower().str.contains(busca.lower())]
    if filtro_tipo != "Todos":
        df_show = df_show[df_show['tipo_participante'] == filtro_tipo]

    df_show = df_show.sort_values(by=['check_in', 'nome_completo'], ascending=[True, True])

    # --- TABELA ---
    if df_show.empty:
        st.info("Ninguém encontrado.")
    else:
        st.write("")
        # Cabeçalho
        c1, c2, c3, c4 = st.columns([3, 1, 2, 1.5])
        c1.markdown("**Nome**")
        c2.markdown("**Tipo**")
        c3.markdown("**Responsável**")
        c4.markdown("**Ação**")
        st.divider()

        limit = 50 if (not busca and filtro_tipo == "Todos") else len(df_show)

        for idx, row in df_show.head(limit).iterrows():
            with st.container():
                id_part = row['id']
                nome = str(row['nome_completo'])
                resp = str(row.get('nome_responsavel', '-'))
                tipo = str(row.get('tipo_participante', 'Teen'))
                ja_chegou = bool(row.get('check_in', False))

                k1, k2, k3, k4 = st.columns([3, 1, 2, 1.5])
                
                with k1:
                    if ja_chegou: st.markdown(f"✅ ~~{nome}~~")
                    else: st.markdown(f"**{nome}**")
                
                with k2:
                    cor = "#00c6ff" if tipo == "Teen" else "#d946ef"
                    st.markdown(f"<span style='color:{cor}; font-weight:bold; font-size:12px'>{tipo}</span>", unsafe_allow_html=True)
                
                with k3:
                    st.text(resp)
                
                with k4:
                    if ja_chegou:
                        # JÁ CHEGOU: MOSTRA HORA + BOTÃO DE ADD GRANA
                        hora = pd.to_datetime(row.get('data_hr_check_in')).strftime('%H:%M') if row.get('data_hr_check_in') else ""
                        st.caption(f"Chegou {hora}")
                        
                        # Botão para adicionar grana se esqueceu
                        if st.button("💰 Add $", key=f"add_{id_part}", type="secondary"):
                            modal_deposito_extra(id_part, nome, st.session_state.operador_checkin)
                    else:
                        # NÃO CHEGOU: BOTÃO DE CHECK-IN PADRÃO
                        if st.button("📍 Check-in", key=f"btn_{id_part}", type="secondary"):
                            modal_checkin(id_part, nome, resp, tipo, st.session_state.operador_checkin)
                
                st.markdown("<hr style='margin: 4px 0; border-color: #233554; opacity:0.5'>", unsafe_allow_html=True)
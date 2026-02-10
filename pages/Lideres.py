import streamlit as st
import pandas as pd
from datetime import datetime
import time
from supabase import create_client, Client

# =======================================================
# 1. CONFIGURAÇÃO E CSS (AZUL PADRÃO)
# =======================================================
st.set_page_config(page_title="Quartos", layout="wide", page_icon="🛏️")

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    SUPABASE_URL = "https://gerzjzmkbzpkdhrxacka.supabase.co"
    SUPABASE_KEY = "sb_secret_BcGLoGEXRfVMA-ajLuqhdw_0zlAFUmn"

st.markdown("""
<style>
    /* Fundo Geral */
    [data-testid="stAppViewContainer"] { background-color: #0a192f; color: #e6f1ff; }
    [data-testid="stHeader"] { background-color: #0a192f; }
    
    /* Inputs e Selects */
    .stTextInput input, div[data-baseweb="select"] > div {
        background-color: #172a45 !important; color: white !important; 
        border: 1px solid #00c6ff !important; border-radius: 12px;
    }
    
    /* CARD DO QUARTO */
    .card-quarto {
        background: linear-gradient(135deg, #112240 0%, #172a45 100%);
        border: 2px solid #00c6ff;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        transition: 0.3s;
        cursor: pointer;
        margin-bottom: 20px;
    }
    .card-quarto:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0, 198, 255, 0.2); }
    
    /* CARD ORAÇÃO */
    .card-oracao {
        background-color: #112240;
        border-left: 4px solid #ffd700;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    
    h1, h2, h3 { color: #00c6ff !important; }
    
    /* Botões Gerais (AZUL) */
    div.stButton > button {
        background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%) !important;
        color: white !important;
        border: none;
        border-radius: 50px;
        font-weight: bold;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 114, 255, 0.5) !important;
    }
</style>
""", unsafe_allow_html=True)

# =======================================================
# 2. FUNÇÕES DE BANCO
# =======================================================
@st.cache_resource
def init_supabase():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None

def carregar_dados():
    sb = init_supabase()
    q = sb.table("quartos").select("*").order("nome").execute()
    df_q = pd.DataFrame(q.data)
    p = sb.table("participantes").select("*").order("nome_completo").execute()
    df_p = pd.DataFrame(p.data)
    return df_q, df_p

def mover_participante(id_part, id_quarto_destino):
    sb = init_supabase()
    sb.table("participantes").update({"id_quarto": id_quarto_destino}).eq("id", id_part).execute()
    return True

def remover_do_quarto(id_part):
    sb = init_supabase()
    # Define id_quarto como Null (libera o participante)
    sb.table("participantes").update({"id_quarto": None}).eq("id", id_part).execute()
    return True

def carregar_ficha_resumo(id_part):
    sb = init_supabase()
    res = sb.table("ficha_medica").select("*").eq("id_participante", id_part).execute()
    if res.data: return res.data[0]
    return None

def salvar_oracao(texto):
    sb = init_supabase()
    sb.table("oracoes").insert({"pedido": texto}).execute()
    return True

def carregar_oracoes():
    sb = init_supabase()
    res = sb.table("oracoes").select("*").order("created_at", desc=True).execute()
    return pd.DataFrame(res.data)

def curtir_oracao(id_oracao, qtd_atual):
    sb = init_supabase()
    sb.table("oracoes").update({"curtidas": qtd_atual + 1}).eq("id", id_oracao).execute()
    return True

def criar_quarto(nome, lider, tel):
    sb = init_supabase()
    sb.table("quartos").insert({"nome": nome, "nome_lider": lider, "telefone_lider": tel}).execute()
    return True

def excluir_quarto(id_quarto):
    sb = init_supabase()
    try:
        sb.table("participantes").update({"id_quarto": None}).eq("id_quarto", id_quarto).execute()
        sb.table("quartos").delete().eq("id", id_quarto).execute()
        return True
    except: return False

# =======================================================
# 3. INTERFACE
# =======================================================
if 'quarto_ativo' not in st.session_state: st.session_state.quarto_ativo = None
if 'modo_oracao' not in st.session_state: st.session_state.modo_oracao = False

# --- HEADER ---
c_head, c_busca = st.columns([1, 1])
with c_head:
    st.markdown("## 🛏️ Quartos")
with c_busca:
    termo_busca = st.text_input("🔍 Buscar Teen (Filtra o Quarto)", placeholder="Digite o nome...")

# Botão Toggle Mural
if st.button(f"{'🏠 Voltar aos Quartos' if st.session_state.modo_oracao else '🙏 Mural de Oração'}", use_container_width=True):
    st.session_state.modo_oracao = not st.session_state.modo_oracao
    st.session_state.quarto_ativo = None
    st.rerun()

st.divider()

# =======================================================
# MODO MURAL DE ORAÇÃO
# =======================================================
if st.session_state.modo_oracao:
    st.markdown("### 🙏 Pedidos de Oração")
    st.info("Espaço anônimo para compartilharmos nossos pedidos e intercedermos uns pelos outros.")
    
    with st.form("nova_oracao"):
        txt_pedido = st.text_area("Escreva seu pedido aqui (Anônimo):")
        if st.form_submit_button("Enviar Pedido"):
            if txt_pedido:
                salvar_oracao(txt_pedido)
                st.success("Pedido enviado para o mural!")
                time.sleep(1); st.rerun()
    
    st.markdown("---")
    
    df_oracoes = carregar_oracoes()
    if not df_oracoes.empty:
        cols = st.columns(2)
        for i, row in df_oracoes.iterrows():
            with cols[i % 2]:
                try: dt = pd.to_datetime(row['created_at']).strftime("%d/%m às %H:%M")
                except: dt = "Data desc."
                
                st.markdown(f"""
                <div class="card-oracao">
                    <small style='color:#aaa'>📅 {dt}</small><br>
                    <span style='font-size:18px; color:white;'>"{row['pedido']}"</span>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"🙏 Orando ({row['curtidas']})", key=f"pray_{row['id']}", use_container_width=True):
                    curtir_oracao(row['id'], row['curtidas'])
                    st.rerun()
    else:
        st.write("Nenhum pedido ainda. Seja o primeiro!")

# =======================================================
# MODO GESTÃO DE QUARTOS
# =======================================================
elif st.session_state.quarto_ativo is None:
    # --- VISUALIZAÇÃO GERAL (CARDS) ---
    df_q, df_p = carregar_dados()
    quartos_para_mostrar = df_q
    
    if termo_busca and not df_p.empty and not df_q.empty:
        teens_filtrados = df_p[df_p['nome_completo'].str.contains(termo_busca, case=False, na=False)]
        ids_quartos_filtrados = teens_filtrados['id_quarto'].unique()
        quartos_para_mostrar = df_q[df_q['id'].isin(ids_quartos_filtrados)]
        if quartos_para_mostrar.empty:
            st.warning(f"Nenhum quarto encontrado com '{termo_busca}'. O teen pode estar sem quarto.")

    if not quartos_para_mostrar.empty:
        if termo_busca: st.caption(f"Exibindo quartos onde '{termo_busca}' foi encontrado.")
        colunas = st.columns(3)
        for idx, row in quartos_para_mostrar.iterrows():
            qid = row['id']
            qnome = row['nome']
            qlider = row['nome_lider']
            qtd = len(df_p[df_p['id_quarto'] == qid]) if not df_p.empty else 0
            
            with colunas[idx % 3]:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #112240 0%, #172a45 100%); border: 1px solid #00c6ff; border-radius: 15px; padding: 20px; text-align: center; margin-bottom:10px;">
                    <h3 style="margin:0; color:#00c6ff;">{qnome}</h3>
                    <p style="color:#aaa;">{qlider}</p> <h1 style="margin:0; color:white; font-size:40px;">{qtd}</h1>
                    <p style="font-size:12px;">Participantes</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Abrir {qnome}", key=f"btn_q_{qid}", use_container_width=True):
                    st.session_state.quarto_ativo = qid
                    st.rerun()
    else:
        st.info("Nenhum quarto cadastrado.")
        
    st.divider()
    with st.expander("➕ Criar Novo Quarto"):
        with st.form("new_room"):
            c1, c2 = st.columns(2)
            n_nome = c1.text_input("Nome Quarto")
            n_lider = c2.text_input("Nome Líder")
            n_tel = st.text_input("Zap Líder")
            if st.form_submit_button("Criar"):
                criar_quarto(n_nome, n_lider, n_tel); st.rerun()

# =======================================================
# MODO DETALHE DO QUARTO
# =======================================================
else:
    df_q, df_p = carregar_dados()
    qid_ativo = st.session_state.quarto_ativo
    quarto_dados = df_q[df_q['id'] == qid_ativo].iloc[0]
    teens_no_quarto = df_p[df_p['id_quarto'] == qid_ativo]
    
    c_voltar, c_info, c_delete = st.columns([1, 4, 1])
    with c_voltar:
        if st.button("⬅️ Voltar"):
            st.session_state.quarto_ativo = None
            st.rerun()
    with c_info:
        st.markdown(f"## 🏠 {quarto_dados['nome']}")
        st.caption(f"Líder: {quarto_dados['nome_lider']} | Total: {len(teens_no_quarto)}")
    with c_delete:
        @st.dialog("🗑️ Excluir Quarto?")
        def modal_excluir_quarto(qid, qnome):
            st.warning(f"Excluir **{qnome}**?")
            st.write("Os teens ficarão 'Sem Quarto'.")
            if st.button("Sim, Excluir", type="primary"):
                if excluir_quarto(qid):
                    st.session_state.quarto_ativo = None
                    st.success("Excluído!")
                    time.sleep(1); st.rerun()
        if st.button("🗑️ Excluir", use_container_width=True):
            modal_excluir_quarto(qid_ativo, quarto_dados['nome'])

    st.divider()
    
    if not teens_no_quarto.empty:
        for idx, teen in teens_no_quarto.iterrows():
            with st.container():
                # Layout: Nome | Resp | Botoes
                c1, c2, c3, c4, c5 = st.columns([2, 1.5, 0.8, 0.8, 0.8])
                
                with c1: st.markdown(f"**{teen['nome_completo']}**")
                with c2: st.caption(f"Resp: {teen['nome_responsavel']}")
                
                with c3:
                    # FICHA
                    @st.dialog(f"Ficha: {teen['nome_completo']}")
                    def modal_ficha(tid):
                        f = carregar_ficha_resumo(tid)
                        if f:
                            if f.get('tem_alergia') or f.get('tem_alergia_med'):
                                st.error(f"⚠️ ALERGIAS: {f.get('desc_alergia', '')} {f.get('desc_alergia_med', '')}")
                            else: st.success("✅ Sem alergias.")
                            st.write(f"💊 **Remédios:** {f.get('desc_med_atual', 'Nenhum')}")
                            st.write(f"🏥 **Condições:** {f.get('cond_outra', '-')}")
                            st.write(f"🚑 **Emergência:** {f.get('emergencia_nome', '-')}")
                        else: st.warning("Ficha vazia.")
                    if st.button("📋 Ficha", key=f"f_{teen['id']}"): modal_ficha(teen['id'])
                
                with c4:
                    # MOVER
                    @st.dialog("Mover")
                    def modal_troca(tid, tnome):
                        st.write(f"Mover **{tnome}** para:")
                        novos = df_q['nome'].tolist()
                        dest = st.selectbox("", novos)
                        if st.button("Confirmar"):
                            id_d = df_q[df_q['nome'] == dest].iloc[0]['id']
                            mover_participante(tid, id_d); st.success("Movido!"); time.sleep(1); st.rerun()
                    if st.button("🔄 Mover", key=f"mv_{teen['id']}"): modal_troca(teen['id'], teen['nome_completo'])
                
                with c5:
                    # REMOVER (SAIR DO QUARTO)
                    # Agora o botão é AZUL normal, mas funcionalmente remove
                    if st.button("❌ Sair", key=f"rm_{teen['id']}", help="Tira a pessoa deste quarto"):
                        if remover_do_quarto(teen['id']):
                            st.toast(f"{teen['nome_completo']} removido do quarto!"); time.sleep(1); st.rerun()
                
                st.markdown("<hr style='margin:5px 0; opacity:0.1'>", unsafe_allow_html=True)
    else:
        st.info("Quarto vazio.")

    st.markdown("#### ➕ Adicionar Participante")
    sem_quarto = df_p[pd.isna(df_p['id_quarto'])]
    if not sem_quarto.empty:
        add_sel = st.selectbox("Selecionar da lista 'Sem Quarto'", sem_quarto['nome_completo'].tolist())
        if st.button("Adicionar aqui"):
            pid_add = sem_quarto[sem_quarto['nome_completo'] == add_sel].iloc[0]['id']
            mover_participante(pid_add, qid_ativo); st.rerun()
    else:
        st.success("Todos os participantes já têm quarto!")

import streamlit as st
import pandas as pd
from datetime import datetime
import time
from urllib.parse import quote
from supabase import create_client, Client

# =======================================================
# 1. CONFIGURAÇÃO E CSS
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
    [data-testid="stAppViewContainer"] { background-color: #0a192f; color: #e6f1ff; }
    [data-testid="stHeader"] { background-color: #0a192f; }
    
    .stTextInput input, div[data-baseweb="select"] > div {
        background-color: #172a45 !important; color: white !important; 
        border: 1px solid #00c6ff !important; border-radius: 8px;
    }
    
    .card-oracao {
        background-color: #112240;
        border-left: 5px solid #ffd700;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    .stat-card {
        background-color: #112240;
        border: 1px solid #30475e;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* Cabeçalho de Seção (Feminino/Masculino) */
    .section-header {
        color: #e6f1ff;
        border-bottom: 2px solid #30475e;
        padding-bottom: 5px;
        margin-top: 20px;
        margin-bottom: 15px;
        font-size: 20px;
        font-weight: bold;
    }
    
    div.stButton > button {
        background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%) !important;
        color: white !important;
        border: none;
        border-radius: 50px;
        font-weight: bold;
    }
    
    div.stButton > button[kind="secondary"] {
        background: #2a3b55 !important;
        border: 1px solid #aaa !important;
    }
    
    a.zap-btn {
        text-decoration: none;
        background-color: #25D366;
        color: white;
        padding: 6px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        border: 1px solid #1da851;
        display: inline-flex;
        align-items: center;
        gap: 5px;
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
    
    if not df_p.empty:
        if 'sexo' not in df_p.columns: df_p['sexo'] = 'Indefinido'
        if 'tipo_participante' not in df_p.columns: df_p['tipo_participante'] = 'Teen'
        if 'idade' in df_p.columns:
            df_p['idade'] = df_p['idade'].fillna(0).astype(int)
        else:
            df_p['idade'] = 0
        
    return df_q, df_p

def mover_participante(id_part, id_quarto_destino):
    sb = init_supabase()
    sb.table("participantes").update({"id_quarto": id_quarto_destino}).eq("id", id_part).execute()
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

def criar_quarto(nome, lider, tel, time_cor, sexo_quarto):
    sb = init_supabase()
    dados = {
        "nome": nome, 
        "nome_lider": lider, 
        "telefone_lider": tel, 
        "time_cor": time_cor,
        "sexo": sexo_quarto
    }
    sb.table("quartos").insert(dados).execute()
    return True

def gerar_link_responsavel(nome_lider, nome_teen, tel_resp, tel_emergencia):
    telefone_final = None
    if tel_emergencia and len(str(tel_emergencia).strip()) >= 8: telefone_final = tel_emergencia
    elif tel_resp and len(str(tel_resp).strip()) >= 8: telefone_final = tel_resp
    
    if not telefone_final: return None
    tel_limpo = "".join([c for c in str(telefone_final) if c.isdigit()])
    msg = f"Graça e paz, tudo bom? Somos do Acampateens, meu nome é {nome_lider} responsavel pelo(a) {nome_teen}"
    return f"https://wa.me/55{tel_limpo}?text={quote(msg)}"

# =======================================================
# 3. INTERFACE
# =======================================================
if 'modo_oracao' not in st.session_state: st.session_state.modo_oracao = False
if 'quarto_aberto' not in st.session_state: st.session_state.quarto_aberto = None

df_q, df_p = carregar_dados() 

# HEADER
c_head, c_busca, c_filtro = st.columns([1, 1, 1])

with c_head: st.markdown("## 🛏️ Quartos")

if st.button(f"{'🏠 Voltar aos Quartos' if st.session_state.modo_oracao else '🙏 Mural de Oração'}", use_container_width=True):
    st.session_state.modo_oracao = not st.session_state.modo_oracao
    st.rerun()

# --- LÓGICA DE BUSCA ---
termo_busca_oracao = ""
busca_teen_selecionado = "🔍 Buscar Teen..."
mapa_busca_teens = {} 

with c_busca: 
    if st.session_state.modo_oracao:
        termo_busca_oracao = st.text_input("Busca", placeholder="🔍 Buscar na Oração...", label_visibility="collapsed")
    else:
        lista_opcoes = ["🔍 Buscar Teen..."]
        if not df_p.empty:
            df_teens_busca = df_p[df_p['tipo_participante'] == 'Teen'].sort_values('nome_completo')
            for idx, row in df_teens_busca.iterrows():
                label = f"{row['nome_completo']} ({int(row.get('idade',0))}a)"
                lista_opcoes.append(label)
                mapa_busca_teens[label] = row.get('id_quarto') 
        
        busca_teen_selecionado = st.selectbox("Busca", options=lista_opcoes, label_visibility="collapsed")

filtro_sexo = "Todos"
if not st.session_state.modo_oracao:
    with c_filtro:
        filtro_sexo = st.selectbox("Filtrar Sexo:", ["Todos", "Masculino", "Feminino"], label_visibility="collapsed")

st.divider()

# --- MURAL DE ORAÇÃO ---
if st.session_state.modo_oracao:
    st.markdown("### 🙏 Pedidos de Oração")
    with st.form("nova_oracao"):
        txt_pedido = st.text_area("Escreva seu pedido aqui (Anônimo):")
        if st.form_submit_button("Enviar Pedido"):
            if txt_pedido:
                salvar_oracao(txt_pedido); st.success("Enviado!"); time.sleep(1); st.rerun()
    
    st.markdown("---")
    df_oracoes = carregar_oracoes()
    if not df_oracoes.empty and termo_busca_oracao:
        df_oracoes = df_oracoes[df_oracoes['pedido'].str.contains(termo_busca_oracao, case=False, na=False)]
    
    if not df_oracoes.empty:
        cols = st.columns(2)
        for i, row in df_oracoes.iterrows():
            with cols[i % 2]:
                try: dt = pd.to_datetime(row['created_at']).strftime("%d/%m %H:%M")
                except: dt = "-"
                st.markdown(f"""
                <div class="card-oracao">
                    <small style="color:#aaa">📅 {dt}</small><br>
                    <span style="font-size:18px; color:white; font-style:italic">"{row['pedido']}"</span>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"🙏 Orando ({row['curtidas']})", key=f"pray_{row['id']}", use_container_width=True):
                    curtir_oracao(row['id'], row['curtidas']); st.rerun()
    else: st.write("Nenhum pedido.")

# --- LISTA DE QUARTOS ---
else:
    # ESTATÍSTICAS
    if not df_p.empty and not df_q.empty:
        df_teens_stats = df_p[df_p['tipo_participante'] == 'Teen']
        
        tot_teens = len(df_teens_stats)
        tot_masc = len(df_teens_stats[df_teens_stats['sexo'] == 'Masculino'])
        tot_fem = len(df_teens_stats[df_teens_stats['sexo'] == 'Feminino'])
        
        q_masc = len(df_q[df_q['sexo'] == 'Masculino'])
        q_fem = len(df_q[df_q['sexo'] == 'Feminino'])
        
        c_stats1, c_stats2 = st.columns(2)
        
        with c_stats1:
            st.markdown(f"""
            <div class="stat-card">
                <h5 style="color:#ddd; margin:0;">👥 Acampantes (Teens)</h5>
                <div style="display:flex; justify-content:space-around; margin-top:10px;">
                    <div><span style="font-size:24px; font-weight:bold; color:white;">{tot_teens}</span><br><span style="font-size:12px; color:#aaa;">Total</span></div>
                    <div><span style="font-size:24px; font-weight:bold; color:#4da6ff;">{tot_masc}</span><br><span style="font-size:12px; color:#aaa;">Meninos</span></div>
                    <div><span style="font-size:24px; font-weight:bold; color:#ff66b2;">{tot_fem}</span><br><span style="font-size:12px; color:#aaa;">Meninas</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_stats2:
            st.markdown(f"""
            <div class="stat-card">
                <h5 style="color:#ddd; margin:0;">🏠 Quartos</h5>
                <div style="display:flex; justify-content:space-around; margin-top:10px;">
                    <div><span style="font-size:24px; font-weight:bold; color:#4da6ff;">{q_masc}</span><br><span style="font-size:12px; color:#aaa;">Masculino</span></div>
                    <div><span style="font-size:24px; font-weight:bold; color:#ff66b2;">{q_fem}</span><br><span style="font-size:12px; color:#aaa;">Feminino</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.write("")

    # FILTROS E BUSCAS
    if filtro_sexo != "Todos" and not df_p.empty:
        df_p_view = df_p[df_p['sexo'] == filtro_sexo]
        if not df_q.empty and 'sexo' in df_q.columns:
            df_q = df_q[df_q['sexo'] == filtro_sexo]
    else:
        df_p_view = df_p

    quarto_destaque_id = None
    if busca_teen_selecionado != "🔍 Buscar Teen...":
        quarto_encontrado = mapa_busca_teens.get(busca_teen_selecionado)
        if pd.isna(quarto_encontrado) or not quarto_encontrado:
            st.warning(f"Opa! {busca_teen_selecionado} ainda não tem quarto definido.")
            df_q = pd.DataFrame() 
        else:
            df_q = df_q[df_q['id'] == quarto_encontrado]
            quarto_destaque_id = quarto_encontrado
            st.session_state.quarto_aberto = quarto_encontrado

    # === RENDERIZAÇÃO DOS QUARTOS (DIVIDIDO) ===
    
    if not df_q.empty:
        # Separa os dataframes
        df_fem = df_q[df_q['sexo'] == 'Feminino']
        df_masc = df_q[df_q['sexo'] == 'Masculino']
        
        # Cria uma lista de "Seções" para iterar e evitar duplicar código
        # Tupla: (Titulo, DataFrame, IconeTitulo)
        secoes = [
            ("🌸 Quartos Femininos", df_fem),
            ("🔵 Quartos Masculinos", df_masc)
        ]
        
        for titulo_secao, df_subset in secoes:
            if not df_subset.empty:
                st.markdown(f"<div class='section-header'>{titulo_secao}</div>", unsafe_allow_html=True)
                
                for idx, row in df_subset.iterrows():
                    qid = row['id']
                    teens_no_quarto = df_p_view[df_p_view['id_quarto'] == qid] if not df_p_view.empty else pd.DataFrame()
                    qtd = len(teens_no_quarto)
                    
                    cor_time = row.get('time_cor', '-')
                    sexo_quarto = row.get('sexo', 'Misto')
                    icone_q = "🔵" if sexo_quarto == "Masculino" else ("🌸" if sexo_quarto == "Feminino" else "🏠")
                    
                    col_resumo, col_btn = st.columns([5, 1])
                    esta_aberto = (st.session_state.quarto_aberto == qid)
                    destaque = "border: 2px solid #ffd700;" if (quarto_destaque_id == qid) else "border: 1px solid #00c6ff;"
                    
                    with col_resumo:
                        st.markdown(f"""
                        <div style="background-color: #112240; {destaque} border-radius: 10px; padding: 10px; display: flex; align-items: center; justify-content: space-between;">
                            <span style="font-size:16px; font-weight:bold; color:white;">{icone_q} {row['nome']}</span>
                            <span style="color:#ddd; font-size:14px;">👤 {row['nome_lider']}</span>
                            <span style="background-color:#0072ff; padding:2px 8px; border-radius:10px; color:white; font-size:12px;">👥 {qtd}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_btn:
                        lbl_btn = "📂 Abrir" if not esta_aberto else "❌ Fechar"
                        tipo_btn = "primary" if not esta_aberto else "secondary"
                        if st.button(lbl_btn, key=f"toggle_{qid}", use_container_width=True, type=tipo_btn):
                            if esta_aberto: st.session_state.quarto_aberto = None
                            else: st.session_state.quarto_aberto = qid
                            st.rerun()

                    if esta_aberto:
                        with st.container():
                            st.info(f"Gerenciando: {row['nome']}")
                            
                            if not teens_no_quarto.empty:
                                for i, teen in teens_no_quarto.iterrows():
                                    c1, c2, c3 = st.columns([3, 0.5, 0.5])
                                    icone_sexo = "👦" if teen.get('sexo') == "Masculino" else "👧"
                                    idade_val = teen.get('idade', 0)
                                    idade_str = f"({idade_val} anos)" if idade_val > 0 else ""
                                    
                                    with c1: 
                                        st.markdown(f"**{icone_sexo} {teen['nome_completo']} {idade_str}**")
                                        st.caption(f"Resp: {teen['nome_responsavel']}")
                                    
                                    f_resumo = carregar_ficha_resumo(teen['id'])
                                    tel_emerg = f_resumo.get('emergencia_tel') if f_resumo else None
                                    link_zap = gerar_link_responsavel(row['nome_lider'], teen['nome_completo'], teen['celular_responsavel'], tel_emerg)
                                    with c2:
                                        if link_zap: st.markdown(f"<a href='{link_zap}' target='_blank' class='zap-btn'>💬</a>", unsafe_allow_html=True)

                                    with c3:
                                        @st.dialog(f"Ficha: {teen['nome_completo']}")
                                        def modal_ficha(f, tid):
                                            if f:
                                                alerg_g = f.get('desc_alergia') if f.get('tem_alergia') else "Não"
                                                alerg_m = f.get('desc_alergia_med') if f.get('tem_alergia_med') else "Não"
                                                st.markdown(f"🚨 **Alergia:** {alerg_g}")
                                                st.markdown(f"💊 **Med:** {alerg_m}")
                                                st.markdown("---")
                                                conds = [k.replace('cond_', '').title() for k, v in f.items() if k.startswith('cond_') and v is True]
                                                if f.get('cond_outra'): conds.append(f.get('cond_outra'))
                                                st.markdown(f"🏥 **Saúde:** {', '.join(conds) if conds else 'Ok'}")
                                                st.markdown(f"💉 **Tratamento:** {f.get('tratamento_condicao','-')}")
                                                st.markdown("---")
                                                st.write(f"🚑 **Emergência:** {f.get('emergencia_nome','-')} {f.get('emergencia_tel','-')}")
                                            else: st.warning("Sem ficha.")
                                        
                                        if st.button("📋", key=f"btn_f_{teen['id']}", help="Ver Ficha"): modal_ficha(f_resumo, teen['id'])
                                    
                                    st.markdown("<hr style='margin:5px 0; opacity:0.1'>", unsafe_allow_html=True)
                            else:
                                st.info("Quarto vazio.")

                            st.markdown("#### ➕ Adicionar ao Quarto")
                            
                            sem_quarto = df_p[
                                (pd.isna(df_p['id_quarto'])) & 
                                (df_p['tipo_participante'] == 'Teen')
                            ]
                            
                            if sexo_quarto == "Masculino":
                                sem_quarto = sem_quarto[sem_quarto['sexo'] == 'Masculino']
                            elif sexo_quarto == "Feminino":
                                sem_quarto = sem_quarto[sem_quarto['sexo'] == 'Feminino']
                            
                            if not sem_quarto.empty:
                                c_add, c_btn = st.columns([3, 1])
                                mapa_teens = {}
                                for idx_sq, row_sq in sem_quarto.iterrows():
                                     label = f"{row_sq['nome_completo']} ({int(row_sq.get('idade',0))}a)"
                                     mapa_teens[label] = row_sq['id']
                                
                                with c_add:
                                    sel_nome_display = st.selectbox("Selecione:", list(mapa_teens.keys()), key=f"add_sel_{qid}", label_visibility="collapsed")
                                with c_btn:
                                    if st.button("Add", key=f"btn_add_{qid}"):
                                        pid_add = mapa_teens[sel_nome_display]
                                        mover_participante(pid_add, qid); st.rerun()
                            else:
                                st.success("Todos alocados!")
                    
                    st.write("") 

    else:
        st.info("Nenhum quarto cadastrado ou encontrado na busca.")

    st.divider()
    with st.expander("➕ CADASTRAR NOVO QUARTO"):
        with st.form("new_room"):
            c1, c2 = st.columns(2)
            n_nome = c1.text_input("Nome Quarto")
            lista_servos = []
            if not df_p.empty:
                servos_df = df_p[df_p['tipo_participante'].str.contains("Servo", case=False, na=False)]
                lista_servos = servos_df['nome_completo'].unique().tolist()
            n_lider = c2.selectbox("Selecione o Líder (Servo):", lista_servos)
            c3, c4 = st.columns(2)
            n_sexo = c3.selectbox("Gênero do Quarto", ["Masculino", "Feminino"])
            n_time = c4.selectbox("Time", ["Roxo", "Verde"])
            
            if st.form_submit_button("Salvar Quarto"):
                if n_nome and n_lider:
                    n_tel_auto = ""
                    try:
                        dados_servo = servos_df[servos_df['nome_completo'] == n_lider].iloc[0]
                        n_tel_auto = dados_servo.get('celular_responsavel', '')
                    except: pass
                    
                    criar_quarto(n_nome, n_lider, n_tel_auto, n_time, n_sexo)
                    st.success("Quarto Criado!"); time.sleep(1); st.rerun()
                else:
                    st.error("Preencha Nome e Líder.")

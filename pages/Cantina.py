import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
from urllib.parse import quote
import io 
from supabase import create_client, Client

# =======================================================
# 1. CONFIGURAÇÃO E CHAVES
# =======================================================
st.set_page_config(page_title="AcampaSystem", layout="wide", page_icon="🍔")

# Tenta pegar dos secrets ou usa padrão
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    SUPABASE_URL = "https://gerzjzmkbzpkdhrxacka.supabase.co"
    SUPABASE_KEY = "sb_secret_BcGLoGEXRfVMA-ajLuqhdw_0zlAFUmn"

# =======================================================
# 2. BLOQUEIO DE SEGURANÇA
# =======================================================
if 'cantina_liberada' not in st.session_state:
    st.session_state.cantina_liberada = False

if not st.session_state.cantina_liberada:
    st.markdown("""
    <style>
    .stApp { background-color: #0a192f; color: white; }
    .block-container { padding-top: 5rem; }
    input { text-align: center; font-size: 24px !important; letter-spacing: 5px; }
    </style>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #00c6ff;'>🔐 Acesso Restrito</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #8892b0;'>Digite o código da Cantina para entrar.</p>", unsafe_allow_html=True)
        
        senha = st.text_input("Código de Acesso", type="password", placeholder="Digite aqui...")
        
        col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
        with col_b2:
            if st.button("🔓 LIBERAR ACESSO", use_container_width=True, type="primary"):
                if senha == "2107307":
                    st.session_state.cantina_liberada = True
                    st.success("Acesso Autorizado!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("🚫 Código Incorreto!")
    
    st.stop() 

# =======================================================
# 3. ESTILO VISUAL E FUNÇÕES AUXILIARES
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
        border-radius: 12px !important;
    }
    .stTextInput input, .stNumberInput input, div[data-baseweb="input"] input {
        color: #ffffff !important;
        height: 50px !important;
        padding: 10px 14px !important;
        background-color: transparent !important;
    }

    /* Botões */
    div.stButton > button {
        background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 50px !important;
        font-weight: 700 !important;
        padding: 10px 24px !important;
        transition: all 0.3s ease !important;
        display: flex; justify-content: center; align-items: center;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 114, 255, 0.5) !important;
    }

    /* Botão Secundário */
    button[kind="secondary"] {
        background: transparent !important;
        border: none !important;
        color: #ffffff !important;
        box-shadow: none !important;
        height: auto !important;
        padding: 0 !important;
    }
    button[kind="secondary"]:hover {
        color: #00c6ff !important;
        transform: scale(1.2);
    }

    /* Tabelas e Cards */
    div[data-testid="stDataFrame"] { border: 1px solid #233554; border-radius: 10px; }
    div[data-testid="metric-container"] {
        background-color: #112240;
        border: 1px solid #0072ff;
        border-radius: 12px;
        padding: 15px;
    }
    div[data-testid="stExpander"] {
        background-color: #112240;
        border: 1px solid #233554;
        border-radius: 12px;
    }

    h1, h2, h3 { color: #00c6ff !important; }
    p, label, span, div { color: #e6f1ff; }
    div[data-baseweb="checkbox"] div { background-color: #00c6ff !important; }
</style>
""", unsafe_allow_html=True)

def fmt_real(valor):
    if pd.isna(valor): valor = 0.0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =======================================================
# 4. FUNÇÕES DE BANCO DE DADOS
# =======================================================
@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Erro conexão Supabase: {e}")
        return None

def carregar_dados_gerais():
    supabase = init_supabase()
    try:
        res_part = supabase.table("participantes").select("*").order("nome_completo").execute()
        df_part = pd.DataFrame(res_part.data)
        res_prod = supabase.table("produtos").select("*").order("nome").execute()
        df_prod = pd.DataFrame(res_prod.data)
        res_trans = supabase.table("transacoes").select("*").order("created_at", desc=True).execute()
        df_trans = pd.DataFrame(res_trans.data)
        return df_part, df_prod, df_trans
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# DEVOLVER SALDO
def devolver_saldo(id_part, nome, saldo_atual, operador):
    supabase = init_supabase()
    dh = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        supabase.table("transacoes").insert({
            "id_participante": int(id_part),
            "nome_participante": nome,
            "data_hora": dh,
            "item_descricao": "Devolução de Saldo (Final)",
            "valor": -float(saldo_atual),
            "tipo": "Saída",
            "operador": operador
        }).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao devolver: {e}")
        return False

# ZAP
def gerar_msg_zap(id_part, nome, nome_resp, tel_resp, tipo, saldo_atual, saldo_inicial, df_trans):
    tel_limpo = "".join([c for c in str(tel_resp) if c.isdigit()])
    if not tel_limpo: return None
    
    itens_txt = ""
    if not df_trans.empty:
        consumo = df_trans[(df_trans['id_participante'] == id_part) & (df_trans['valor'] < 0)]
        if not consumo.empty:
            for _, row in consumo.head(15).iterrows():
                itens_txt += f"- {row['item_descricao']} ({fmt_real(abs(row['valor']))})\n"
        else:
            itens_txt = "(Sem consumo registrado)"

    tipo_str = str(tipo).strip().lower()
    msg = ""
    pix_dados = f"Favor realizar o pix para conta:\nconnecteens.filadelfia@gmail.com\nE envie o comprovante para Carina:\n21 99348-0675"

    if "teen" in tipo_str and saldo_atual < 0:
        msg = f"Graça e paz {nome_resp}\n\nSeu filho(a) *{nome}* iniciou o encontro com um saldo de {fmt_real(saldo_inicial)}.\nNo momento, o saldo atual dele(a) é: *{fmt_real(saldo_atual)}*\n\n🔴 Precisamos que acerte o valor {fmt_real(abs(saldo_atual))} pendente.\n\n🧾 *Extrato do que foi consumido:*\n{itens_txt}\n{pix_dados}"
    elif "servo" in tipo_str and saldo_atual < 0:
        msg = f"Graça e paz!\n\n🔴 Precisamos que acerte o valor {fmt_real(abs(saldo_atual))} pendente referente ao consumo na cantina.\n\n🧾 *Extrato do que foi consumido:*\n{itens_txt}\n{pix_dados}"
    elif "teen" in tipo_str and 0 <= saldo_atual <= 1:
        msg = f"Graça e paz {nome_resp}\n\nSeu filho(a) *{nome}* iniciou o encontro com um saldo de {fmt_real(saldo_inicial)}.\nNo momento, o saldo atual dele(a) está zerado, deseja incluir mais valor para ele?\n\n🧾 *Extrato do que foi consumido:*\n{itens_txt}\n\nCaso desejar, deverá realizar o pix para conta:\nconnecteens.filadelfia@gmail.com\nE envie o comprovante para Carina:\n21 99348-0675"
    else:
        msg = f"Olá, saldo atual: {fmt_real(saldo_atual)}"

    return f"https://wa.me/55{tel_limpo}?text={quote(msg)}"

# Funções Banco - ATUALIZADAS COM SEXO E IDADE
def cadastrar_participante(nome, resp, cel, tipo, sexo, idade, saldo_inicial, operador):
    supabase = init_supabase()
    try:
        res = supabase.table("participantes").insert({
            "nome_completo": nome.replace('*', '').strip(), 
            "nome_responsavel": resp, 
            "celular_responsavel": cel,
            "tipo_participante": tipo, 
            "sexo": sexo,
            "idade": int(idade),
            "saldo_inicial": 0
        }).execute()
        
        if res.data and saldo_inicial > 0:
            dh = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            supabase.table("transacoes").insert({
                "id_participante": res.data[0]['id'], 
                "nome_participante": nome.replace('*', '').strip(), 
                "data_hora": dh,
                "item_descricao": "Saldo Inicial (Cadastro)", 
                "valor": float(saldo_inicial), 
                "tipo": "Entrada", 
                "operador": operador
            }).execute()
        return True
    except Exception as e: 
        st.error(f"Erro ao cadastrar: {e}")
        return False

def atualizar_participante(id_part, nome, resp, cel, tipo, sexo, idade):
    supabase = init_supabase()
    try:
        supabase.table("participantes").update({
            "nome_completo": nome.replace('*', '').strip(), 
            "nome_responsavel": resp, 
            "celular_responsavel": cel, 
            "tipo_participante": tipo,
            "sexo": sexo,
            "idade": int(idade)
        }).eq("id", id_part).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False

def excluir_participante_db(id_part):
    supabase = init_supabase()
    try:
        supabase.table("transacoes").delete().eq("id_participante", id_part).execute()
        supabase.table("participantes").delete().eq("id", id_part).execute()
        return True
    except: return False

def processar_venda(carrinho, pagadores, operador):
    supabase = init_supabase()
    dh = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    resultados = [] 
    try:
        for p in pagadores:
            supabase.table("transacoes").insert({
                "id_participante": int(p['id']), "nome_participante": p['nome'], "data_hora": dh,
                "item_descricao": p['desc'], "valor": float(p['valor']) * -1, "tipo": "Venda", "operador": operador
            }).execute()
            res = supabase.table("transacoes").select("valor").eq("id_participante", int(p['id'])).execute()
            saldo_novo = sum([x['valor'] for x in res.data])
            resultados.append({"nome": p['nome'], "gasto": p['valor'], "novo_saldo": saldo_novo})
        for i in carrinho:
            if i.get('id_produto'):
                res = supabase.table("produtos").select("estoque").eq("id", i['id_produto']).execute()
                if res.data: supabase.table("produtos").update({"estoque": res.data[0]['estoque'] - 1}).eq("id", i['id_produto']).execute()
        return True, resultados
    except Exception as e: st.error(e); return False, []

def salvar_recarga(id_part, nome, valor, forma, obs, operador):
    supabase = init_supabase()
    dh = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        supabase.table("transacoes").insert({
            "id_participante": int(id_part), "nome_participante": nome, "data_hora": dh,
            "item_descricao": f"Recarga ({forma}) - {obs}", "valor": float(valor), "tipo": "Entrada", "operador": operador
        }).execute()
        return True
    except: return False

def calcular_vendidos(df_prod, df_trans):
    df_prod['Vendidos'] = 0 
    if df_prod.empty or df_trans.empty: return df_prod
    vendas = df_trans[df_trans['valor'] < 0]['item_descricao'].fillna("").tolist()
    contagem = {p: 0 for p in df_prod['Produto']}
    for desc in vendas:
        for prod in contagem: 
            contagem[prod] += desc.count(prod)
    df_prod['Vendidos'] = df_prod['Produto'].map(contagem).fillna(0)
    return df_prod

# =======================================================
# 5. CARREGAMENTO
# =======================================================
df_part, df_prod, df_trans = carregar_dados_gerais()

if not df_part.empty:
    df_part.rename(columns={'id': 'ID', 'nome_completo': 'Nome', 'nome_responsavel': 'Resp', 'celular_responsavel': 'Cel'}, inplace=True)
    # Garante que as colunas novas existam no DF para não dar erro
    if 'sexo' not in df_part.columns: df_part['sexo'] = 'Indefinido'
    if 'idade' not in df_part.columns: df_part['idade'] = 0
    df_part['idade'] = df_part['idade'].fillna(0).astype(int)

if not df_prod.empty:
    df_prod.rename(columns={'id': 'ID', 'nome': 'Produto', 'preco': 'Preco', 'estoque': 'Estoque'}, inplace=True)

dict_saldos = {}
dict_depositos = {}
if not df_part.empty and not df_trans.empty:
    saldos_series = df_trans.groupby('id_participante')['valor'].sum()
    dict_saldos = saldos_series.to_dict()
    depositos_series = df_trans[df_trans['valor'] > 0].groupby('id_participante')['valor'].sum()
    dict_depositos = depositos_series.to_dict()

# =======================================================
# 6. MODAIS (ATUALIZADO COM SEXO E IDADE)
# =======================================================
@st.dialog("✏️ Editar Participante")
def modal_editar(id_part, nome_atual, resp_atual, cel_atual, tipo_atual, sexo_atual, idade_atual):
    st.write(f"Editando: **{nome_atual}**")
    
    n_nome = st.text_input("Nome", value=nome_atual)
    
    # Sexo e Idade
    c_s, c_i = st.columns(2)
    opcoes_sexo = ["Masculino", "Feminino"]
    idx_sexo = opcoes_sexo.index(sexo_atual) if sexo_atual in opcoes_sexo else 0
    n_sexo = c_s.selectbox("Sexo", opcoes_sexo, index=idx_sexo)
    n_idade = c_i.number_input("Idade", min_value=0, value=int(idade_atual) if idade_atual else 0, step=1)
    
    n_resp = st.text_input("Responsável", value=resp_atual)
    n_cel = st.text_input("Celular", value=cel_atual)
    
    idx_tipo = 0
    opcoes_tipo = ["Teen", "Servo"]
    if tipo_atual in opcoes_tipo: idx_tipo = opcoes_tipo.index(tipo_atual)
    n_tipo = st.selectbox("Tipo", opcoes_tipo, index=idx_tipo)
    
    st.write("")
    if st.button("💾 SALVAR", type="primary"):
        with st.spinner("..."):
            if atualizar_participante(id_part, n_nome, n_resp, n_cel, n_tipo, n_sexo, n_idade):
                st.success("Salvo!"); st.cache_data.clear(); time.sleep(1); st.rerun()

@st.dialog("💸 Devolver Saldo")
def modal_devolver(id_part, nome, saldo_atual):
    st.warning(f"Confirmar devolução para **{nome}**?")
    st.write(f"O saldo de **{fmt_real(saldo_atual)}** será zerado e registrado como devolvido no sistema.")
    st.write("")
    if st.button("✅ CONFIRMAR DEVOLUÇÃO", type="primary"):
        with st.spinner("Processando..."):
            if devolver_saldo(id_part, nome, saldo_atual, "Admin"):
                st.toast("Saldo devolvido com sucesso!"); time.sleep(1.5); st.rerun()

# =======================================================
# 7. MENU
# =======================================================
st.sidebar.markdown("## 🏕️ Cantina")
menu = st.sidebar.radio("Menu", ["📊 Dashboard", "🍔 Nova Venda", "💰 Recarga", "📦 Estoque", "📄 Extrato", "👥 Participantes"])
st.sidebar.markdown("---")
# Botão para Sair
if st.sidebar.button("🔒 Bloquear"):
    st.session_state.cantina_liberada = False
    st.rerun()

# =======================================================
# TELA 1: DASHBOARD
# =======================================================
if menu == "📊 Dashboard":
    st.title("Painel Geral")
    ent = 0; sai = 0; div = 0
    if not df_trans.empty:
        ent = df_trans[df_trans['valor'] > 0]['valor'].sum()
        sai = df_trans[df_trans['valor'] < 0]['valor'].sum()
        div = sum(v for v in dict_saldos.values() if v < 0)

    c1, c2, c3 = st.columns(3)
    c1.metric("Caixa Físico", fmt_real(ent + sai))
    c2.metric("Vendas Totais", fmt_real(abs(sai)))
    c3.metric("Total em Dívida", fmt_real(div), delta_color="inverse")
    
    st.divider()
    st.subheader("🚨 Controle de Saldos (Negativos/Zerados)")
    
    if not df_part.empty:
        lista_alertas = []
        for idx, row in df_part.iterrows():
            pid = row['ID']
            saldo = dict_saldos.get(pid, 0.0)
            if saldo <= 1.0:
                saldo_ini = dict_depositos.get(pid, 0.0)
                tipo_p = row.get('tipo_participante', 'Teen')
                link_zap = gerar_msg_zap(pid, row['Nome'], row['Resp'], row['Cel'], tipo_p, saldo, saldo_ini, df_trans)
                status_icon = "🔴 Dívida" if saldo < 0 else "🟡 Zerado"
                cel_display = row['Cel']
                if not row['Cel'] or str(row['Cel']).strip() == "" or str(row['Cel']).strip() == "None":
                    cel_display = "🚫 Sem Celular"; link_zap = None
                lista_alertas.append({"Nome": row['Nome'], "Tipo": tipo_p, "Status": status_icon, "Saldo": fmt_real(saldo), "Responsável": row['Resp'], "Contato": cel_display, "LinkZap": link_zap})
        
        if lista_alertas:
            df_alertas = pd.DataFrame(lista_alertas)
            st.dataframe(df_alertas, column_order=("Nome", "Tipo", "Status", "Saldo", "Responsável", "Contato", "LinkZap"), column_config={"LinkZap": st.column_config.LinkColumn("Ação", display_text="💬 Enviar Aviso"), "Status": st.column_config.TextColumn("Situação")}, use_container_width=True, hide_index=True)
        else: st.success("Tudo em dia!")
    if st.button("🔄 Atualizar"): st.rerun()

# =======================================================
# TELA 2: NOVA VENDA
# =======================================================
elif menu == "🍔 Nova Venda":
    if 'recibo_dados' in st.session_state:
        recibo = st.session_state.recibo_dados
        st.markdown("<div style='background-color:#112240; padding:15px; border-radius:12px; border:1px solid #00c6ff; text-align:center'><h2 style='color:#00c6ff; margin:0'>✅ Venda Finalizada!</h2></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🛒 Consumo")
            for i in recibo['itens']: st.write(f"- {i['item']} ({fmt_real(i['preco'])})")
            st.markdown(f"**Total: {fmt_real(recibo['total'])}**")
        with c2:
            st.markdown("### 💰 Saldos Atualizados")
            for pag in recibo['pagadores']:
                cor = "#00c6ff" if pag['novo_saldo'] >= 0 else "#ff4b4b"
                st.markdown(f"**{pag['nome']}**")
                st.markdown(f"Novo Saldo: <span style='color:{cor}; font-weight:bold'>{fmt_real(pag['novo_saldo'])}</span>", unsafe_allow_html=True)
        if st.button("🔄 NOVA VENDA", use_container_width=True):
            del st.session_state.recibo_dados; st.session_state.carrinho = []; st.rerun()
    else:
        if 'carrinho' not in st.session_state: st.session_state.carrinho = []
        st.title("Caixa Cantina")
        nomes = ["Selecione..."] + sorted(df_part['Nome'].tolist())
        cliente = st.selectbox("Cliente Principal:", nomes)
        id_cli = None; saldo_atual = 0.0
        
        if cliente != "Selecione...":
            dados_cli = df_part[df_part['Nome'] == cliente].iloc[0]
            id_cli = dados_cli['ID']; saldo_atual = dict_saldos.get(id_cli, 0.0)
            cor = "#00c6ff" if saldo_atual > 0 else "#ff4b4b"
            st.markdown(f"<h2 style='color:{cor}'>Saldo: {fmt_real(saldo_atual)}</h2>", unsafe_allow_html=True)
            
            cp, cc = st.columns([1.5, 1])
            with cp:
                st.subheader("Produtos")
                
                # --- NOVA BARRA DE PESQUISA DE PRODUTOS ---
                busca_produto = st.text_input("🔍 Buscar produto...", placeholder="Nome do doce, bebida...", label_visibility="collapsed")
                
                if not df_prod.empty:
                    df_prod_show = df_prod.copy()
                    
                    # Filtra os produtos baseados no campo de busca
                    if busca_produto:
                        df_prod_show = df_prod_show[df_prod_show['Produto'].str.contains(busca_produto, case=False, na=False)]
                    
                    if df_prod_show.empty:
                        st.info("Nenhum produto encontrado com esse nome.")
                    else:
                        cols = st.columns(3)
                        # Usando enumerate para espalhar certinho as colunas independentemente do índice original
                        for idx, (original_idx, r) in enumerate(df_prod_show.iterrows()):
                            with cols[idx % 3]:
                                with st.container(border=True):
                                    st.markdown(f"**{r['Produto']}**")
                                    st.markdown(f"{fmt_real(r['Preco'])}")
                                    if st.button("➕", key=f"ad_{r['ID']}", disabled=r['Estoque']<=0, use_container_width=True):
                                        st.session_state.carrinho.append({"id_produto": r['ID'], "item": r['Produto'], "preco": float(r['Preco'])})
                                        st.rerun()
            with cc:
                st.subheader("Carrinho")
                if st.session_state.carrinho:
                    dfc = pd.DataFrame(st.session_state.carrinho)
                    dfc['pf'] = dfc['preco'].apply(fmt_real)
                    st.dataframe(dfc[['item', 'pf']], hide_index=True, use_container_width=True)
                    tot = dfc['preco'].sum()
                    st.markdown(f"### Total: {fmt_real(tot)}")
                    st.divider()
                    
                    div = st.checkbox("Dividir?")
                    pags = []; valid = True; txt_itens = ", ".join([x['item'] for x in st.session_state.carrinho])
                    
                    if div:
                        amigos = st.multiselect("Com quem?", [n for n in nomes if n!="Selecione..." and n!=cliente])
                        if amigos:
                            todos = [cliente]+amigos; taloc = 0; sug = tot/len(todos)
                            for pn in todos:
                                pd_ = df_part[df_part['Nome']==pn].iloc[0]
                                pid = pd_['ID']; psal = dict_saldos.get(pid, 0.0)
                                ci, cin = st.columns([1.5, 1])
                                with ci: 
                                    st.write(f"**{pn}**")
                                    crs = "#00c6ff" if psal>=0 else "#ff4b4b"
                                    st.markdown(f"<small>Saldo: <span style='color:{crs}'>{fmt_real(psal)}</span></small>", unsafe_allow_html=True)
                                with cin: v = st.number_input(f"v_{pid}", min_value=0.0, value=float(sug), step=0.5, label_visibility="collapsed")
                                pags.append({"id": pid, "nome": pn, "valor": v, "desc": f"Dividido: {txt_itens}", "saldo_anterior": psal})
                                taloc += v
                            
                            diff = tot - taloc
                            if diff > 0.01: st.warning(f"⚠️ Faltam: {fmt_real(diff)}"); valid = False
                            elif diff < -0.01: st.error(f"🚫 Passou: {fmt_real(abs(diff))} (Tem a mais)"); valid = False
                            else: st.success("✅ Total Batendo!"); valid = True
                    else:
                        pags.append({"id": id_cli, "nome": cliente, "valor": tot, "desc": txt_itens, "saldo_anterior": saldo_atual})
                        proj = saldo_atual - tot
                        cpj = "#00c6ff" if proj>=0 else "#ff4b4b"
                        st.markdown(f"Saldo Final: <span style='color:{cpj}'>{fmt_real(proj)}</span>", unsafe_allow_html=True)

                    if st.button("✅ FINALIZAR", type="primary", use_container_width=True, disabled=not valid):
                        ok, res = processar_venda(st.session_state.carrinho, pags, "Cantina")
                        if ok: st.session_state.recibo_dados={"itens":st.session_state.carrinho,"total":tot,"pagadores":res}; st.rerun()
                    if st.button("🗑️ Limpar", type="secondary", use_container_width=True): st.session_state.carrinho=[]; st.rerun()

# =======================================================
# TELA 3: RECARGA
# =======================================================
elif menu == "💰 Recarga":
    st.title("Lançar Crédito")
    if df_part.empty: st.warning("Sem participantes.")
    else:
        c1, c2 = st.columns([2, 1])
        with c1: nr = st.selectbox("Participante:", df_part['Nome'].tolist())
        with c2: vr = st.number_input("Valor", min_value=0.0, step=5.0)
        c3, c4 = st.columns([1, 2])
        with c3: fr = st.selectbox("Forma", ["PIX", "Dinheiro", "Cartão"])
        with c4: obs = st.text_input("Obs", placeholder="Opcional")
        st.write("")
        if st.button("💾 CONFIRMAR", type="primary"):
            if vr > 0:
                pid = df_part[df_part['Nome'] == nr].iloc[0]['ID']
                with st.spinner("..."):
                    if salvar_recarga(pid, nr, vr, fr, obs, "Cantina"):
                        st.success(f"Recarga de {fmt_real(vr)} OK!"); time.sleep(2); st.rerun()
            else: st.error("Valor inválido.")

# =======================================================
# TELA 4: ESTOQUE
# =======================================================
elif menu == "📦 Estoque":
    st.title("Produtos")
    with st.expander("➕ Novo Produto"):
        with st.form("new"):
            n = st.text_input("Nome"); c1,c2 = st.columns(2)
            p = c1.number_input("Preço", min_value=0.1); e = c2.number_input("Estoque", min_value=0)
            if st.form_submit_button("Criar"):
                supabase = init_supabase()
                supabase.table("produtos").insert({"nome": n, "preco": p, "estoque": e}).execute()
                st.success("Criado!"); time.sleep(1); st.rerun()
    if not df_prod.empty:
        df_prod = calcular_vendidos(df_prod, df_trans)
        sel = st.selectbox("Editar:", ["Selecione..."]+df_prod['Produto'].tolist())
        if sel!="Selecione...":
            r = df_prod[df_prod['Produto']==sel].iloc[0]
            with st.form("edit"):
                c1,c2 = st.columns(2)
                np = c1.number_input("Preço", value=float(r['Preco']))
                ne = c2.number_input("Estoque", value=int(r['Estoque']))
                if st.form_submit_button("Salvar"):
                    supabase=init_supabase()
                    supabase.table("produtos").update({"preco":np, "estoque":ne}).eq("id", int(r['ID'])).execute()
                    st.success("Salvo!"); time.sleep(1); st.rerun()
        df_show = df_prod.copy(); df_show['Preco'] = df_show['Preco'].apply(fmt_real)
        st.dataframe(df_show[['Produto', 'Preco', 'Estoque', 'Vendidos']], use_container_width=True, hide_index=True)

# =======================================================
# TELA 5: EXTRATO
# =======================================================
elif menu == "📄 Extrato":
    st.title("Extrato")
    if not df_trans.empty:
        c1, c2 = st.columns(2)
        fn = c1.multiselect("Nome", df_trans['nome_participante'].unique())
        ft = c2.multiselect("Tipo", df_trans['tipo'].unique())
        dfs = df_trans.copy()
        if fn: dfs = dfs[dfs['nome_participante'].isin(fn)]
        if ft: dfs = dfs[dfs['tipo'].isin(ft)]
        dfs['valor_fmt'] = dfs['valor'].apply(fmt_real)
        st.dataframe(dfs[['data_hora', 'nome_participante', 'item_descricao', 'valor_fmt', 'tipo']], use_container_width=True, hide_index=True)
        
        c_down, _ = st.columns([1, 4])
        with c_down:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_export = dfs[['data_hora', 'nome_participante', 'item_descricao', 'valor', 'tipo', 'operador']].copy()
                df_export.columns = ['Data/Hora', 'Participante', 'Descrição', 'Valor (R$)', 'Tipo', 'Operador']
                df_export.to_excel(writer, index=False, sheet_name='Extrato')
            st.download_button(label="📊 Baixar Excel", data=buffer, file_name=f"Extrato_{datetime.now().strftime('%d-%m')}.xlsx", mime="application/vnd.ms-excel", type="primary")

# =======================================================
# TELA 6: PARTICIPANTES
# =======================================================
elif menu == "👥 Participantes":
    st.title("Participantes")
    with st.expander("➕ Adicionar Novo"):
        with st.form("add"):
            c1, c2 = st.columns(2); nm = c1.text_input("Nome"); rs = c2.text_input("Responsável")
            
            # NOVAS COLUNAS: SEXO E IDADE
            c_sex, c_age = st.columns(2)
            sex = c_sex.selectbox("Sexo", ["Masculino", "Feminino"])
            age = c_age.number_input("Idade", min_value=0, step=1)
            
            c3, c4 = st.columns(2); cl = c3.text_input("Celular"); tp = c4.selectbox("Tipo", ["Teen", "Servo"])
            sd = st.number_input("Depósito Inicial", min_value=0.0)
            
            if st.form_submit_button("Salvar"):
                if nm: 
                    # Passando sexo e idade para a função
                    if cadastrar_participante(nm, rs, cl, tp, sex, age, sd, "Admin"): st.success("OK!"); time.sleep(1); st.rerun()
                else: st.error("Nome obrigatório")
    
    st.divider()
    cb, cf = st.columns([3, 1])
    bu = cb.text_input("Buscar Nome")
    fi = cf.selectbox("Tipo", ["Todos", "Teen", "Servo"])
    
    ld = []
    if not df_part.empty:
        for i, r in df_part.iterrows():
            if bu and bu.lower() not in str(r['Nome']).lower(): continue
            if fi!="Todos" and str(r.get('tipo_participante','Teen'))!=fi: continue
            pid=r['ID']
            tr = df_trans[df_trans['id_participante']==pid] if not df_trans.empty else pd.DataFrame()
            ent = tr[tr['valor']>0]['valor'].sum() if not tr.empty else 0
            gas = tr[tr['valor']<0]['valor'].sum() if not tr.empty else 0
            
            txt_dev = ""
            if not tr.empty:
                devs = tr[tr['item_descricao'] == "Devolução de Saldo (Final)"]
                if not devs.empty:
                    last_dev = devs.iloc[0]
                    v_dev = abs(last_dev['valor'])
                    try:
                        d_obj = datetime.strptime(last_dev['data_hora'], "%d/%m/%Y %H:%M:%S")
                        d_str = d_obj.strftime("%d/%m %H:%M")
                    except: d_str = last_dev['data_hora']
                    txt_dev = f"↩️ Devolvido: {fmt_real(v_dev)} em {d_str}"

            ld.append({
                "ID": pid, 
                "Nome": str(r['Nome']).replace('*', '').strip(), 
                "Tipo": r.get('tipo_participante','Teen'), 
                "Sexo": r.get('sexo', '-'),
                "Idade": r.get('idade', 0),
                "Resp": r['Resp'], 
                "Cel": r['Cel'], 
                "Ent": ent, "Sai": abs(gas), "Sal": ent+gas, "MsgDev": txt_dev
            })
    
    dfs = pd.DataFrame(ld)
    if not dfs.empty:
        c1,c2,c3,c4,c5,c6 = st.columns([2.5, 1, 1, 1.5, 1.5, 1.5])
        c1.markdown("**Nome**"); c2.markdown("**Entrou**"); c3.markdown("**Gastou**"); c4.markdown("**Saldo**"); c5.markdown("**Resp**"); c6.markdown("**Ações**")
        st.divider()
        for i, r in dfs.iterrows():
            with st.container():
                k1,k2,k3,k4,k5,k6 = st.columns([2.5, 1, 1, 1.5, 1.5, 1.5])
                with k1: 
                    st.write(f"{r['Nome']}")
                    # Mostra idade ao lado do tipo
                    st.caption(f"{r['Tipo']} | {int(r['Idade'])} anos | {r['Sexo']}")
                with k2: st.write(f"<span style='color:green'>{fmt_real(r['Ent'])}</span>", unsafe_allow_html=True)
                with k3: st.write(f"<span style='color:red'>{fmt_real(r['Sai'])}</span>", unsafe_allow_html=True)
                with k4: 
                    cr = "green" if r['Sal']>=0 else "red"
                    st.markdown(f"<span style='color:{cr}; font-weight:bold'>{fmt_real(r['Sal'])}</span>", unsafe_allow_html=True)
                    if r['MsgDev']: st.caption(r['MsgDev'])
                with k5: st.write(r['Resp']); st.caption(r['Cel'])
                with k6:
                    a1, a2, a3 = st.columns(3)
                    with a1:
                        # Passando sexo e idade para o modal de editar
                        if st.button("✏️", key=f"e_{r['ID']}", type="secondary", help="Editar"): 
                            modal_editar(r['ID'], r['Nome'], r['Resp'], r['Cel'], r['Tipo'], r['Sexo'], r['Idade'])
                    with a2:
                        if st.button("🗑️", key=f"d_{r['ID']}", type="secondary", help="Excluir"):
                            if excluir_participante_db(r['ID']): st.toast("Tchau!"); time.sleep(1); st.rerun()
                    with a3:
                        if r['Sal'] > 0:
                            if st.button("💸", key=f"r_{r['ID']}", type="secondary", help="Devolver Saldo"): modal_devolver(r['ID'], r['Nome'], r['Sal'])
                st.markdown("<hr style='margin:5px 0; opacity:0.2'>", unsafe_allow_html=True)

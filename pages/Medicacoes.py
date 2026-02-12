import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from urllib.parse import quote
from supabase import create_client

# =======================================================
# 1. CONFIGURAÇÃO
# =======================================================
st.set_page_config(page_title="Enfermaria", layout="wide", page_icon="💊")

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
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input, .stTimeInput input, div[data-baseweb="select"] > div {
        background-color: #172a45 !important; color: white !important; border: 1px solid #00c6ff !important; border-radius: 8px !important;
    }
    label[data-baseweb="checkbox"] { color: #e6f1ff !important; }
    div.stButton > button { background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%); color: white; border: none; border-radius: 50px; font-weight: bold; }
    h1, h2, h3, h4 { color: #00c6ff !important; }
</style>
""", unsafe_allow_html=True)

# =======================================================
# 2. FUNÇÕES DE BANCO
# =======================================================
def agora_br():
    return datetime.utcnow() - timedelta(hours=3)

@st.cache_resource
def init_supabase():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None

# --- PARTICIPANTES ---
def carregar_dados_completos():
    sb = init_supabase()
    res = sb.table("participantes").select("id, nome_completo, tipo_participante, celular_responsavel, quartos(nome_lider, telefone_lider)").order("nome_completo").execute()
    lista = []
    for item in res.data:
        quarto = item.get('quartos') or {} 
        lista.append({
            "id": item['id'],
            "nome": item['nome_completo'],
            "tipo": item.get('tipo_participante', 'Teen'), 
            "celular": item.get('celular_responsavel', ''),
            "lider": quarto.get('nome_lider', 'Sem Quarto'),
            "tel_lider": quarto.get('telefone_lider', '')
        })
    return pd.DataFrame(lista)

# --- EQUIPE ENFERMARIA ---
def carregar_equipe():
    sb = init_supabase()
    res = sb.table("equipe_enfermaria").select("*").execute()
    return pd.DataFrame(res.data)

def adicionar_equipe(nome, telefone):
    sb = init_supabase()
    existe = sb.table("equipe_enfermaria").select("*").eq("telefone", telefone).execute()
    if not existe.data:
        sb.table("equipe_enfermaria").insert({"nome": nome, "telefone": telefone}).execute()
        return True
    return False

def remover_equipe(id_membro):
    sb = init_supabase()
    sb.table("equipe_enfermaria").delete().eq("id", id_membro).execute()
    return True

# --- FICHAS ---
def carregar_ficha(id_part):
    sb = init_supabase()
    res = sb.table("ficha_medica").select("*").eq("id_participante", id_part).execute()
    return res.data[0] if res.data else {}

def salvar_ficha_parcial(dados):
    sb = init_supabase()
    existe = carregar_ficha(dados['id_participante'])
    if existe: sb.table("ficha_medica").update(dados).eq("id_participante", dados['id_participante']).execute()
    else: sb.table("ficha_medica").insert(dados).execute()
    return True

# --- AGENDAMENTO ---
def agendar_medicacao_auto(id_part, nome_part, remedio, dose, data_ini, freq_tipo, param_horario, dias, lider, tel_lider):
    sb = init_supabase()
    lista_inserts = []
    
    if freq_tipo == "Horário Fixo":
        for d in range(dias):
            dia_atual = data_ini + timedelta(days=d)
            for h_obj in param_horario:
                dh = datetime.combine(dia_atual, h_obj)
                lista_inserts.append(montar_obj_med(id_part, nome_part, remedio, dose, dh, lider, tel_lider))
    else:
        hora_base = param_horario
        dt_base = datetime.combine(data_ini, hora_base)
        intervalos = {"A cada 1h":1, "A cada 2h":2, "A cada 4h":4, "A cada 6h":6, "A cada 8h":8, "A cada 12h":12, "1x ao dia":24}
        horas_int = intervalos.get(freq_tipo, 0)
        if horas_int > 0:
            qtd_doses = int((dias * 24) / horas_int)
            for i in range(1, qtd_doses + 1):
                prox = dt_base + timedelta(hours=i*horas_int)
                lista_inserts.append(montar_obj_med(id_part, nome_part, remedio, dose, prox, lider, tel_lider))

    if lista_inserts:
        sb.table("medicacoes").insert(lista_inserts).execute()
        return True, len(lista_inserts)
    return False, 0

def montar_obj_med(pid, nome, rem, dose, datahora, lid, tel):
    return {
        "id_participante": int(pid), "nome_participante": nome,
        "nome_medicamento": rem, "dosagem": dose,
        "data_hora_prevista": datahora.isoformat(),
        "status": "Pendente", "nome_lider": lid, "telefone_lider": tel
    }

def carregar_alertas():
    sb = init_supabase()
    res = sb.table("medicacoes").select("*").eq("status", "Pendente").order("data_hora_prevista").execute()
    df = pd.DataFrame(res.data)
    if not df.empty: df['data_hora_prevista'] = pd.to_datetime(df['data_hora_prevista'])
    return df

def baixar_med(id_med, operador):
    sb = init_supabase()
    sb.table("medicacoes").update({
        "status": "Administrado",
        "data_hora_realizada": agora_br().isoformat(),
        "operador_realizou": operador
    }).eq("id", id_med).execute()
    return True

def link_zap(nome_lider, nome_part, remedio, dosagem, hora_prevista, tel_lider):
    if not tel_lider: return None
    tel = "".join([c for c in str(tel_lider) if c.isdigit()])
    hora_str = hora_prevista.strftime('%H:%M')
    msg = f"Olá {nome_lider}! HORA DO REMÉDIO.\nO(a) *{nome_part}* precisa tomar:\n💊 *{remedio}* ({dosagem}) às {hora_str}."
    return f"https://wa.me/55{tel}?text={quote(msg)}"

# =======================================================
# 3. INTERFACE
# =======================================================
st.title("💊 Fichas Médicas")

tab_alerta, tab_ficha, tab_equipe = st.tabs(["🚨 Painel de Alertas", "📋 Ficha de Saúde (Anamnese)", "⚙️ Responsável pela Medicação"])

# --- TAB 1: PAINEL ---
with tab_alerta:
    st.markdown("### 🕒 Medicamentos Agendados")
    if st.button("🔄 Atualizar"): st.rerun()
    
    df = carregar_alertas()
    if df.empty:
        st.info("Nenhuma medicação pendente.")
    else:
        agora = agora_br()
        for idx, row in df.iterrows():
            previsto = row['data_hora_prevista']
            diff = (agora - previsto).total_seconds() / 60 
            
            if diff > 15: cor = "#ff4b4b"; status = f"🔴 ATRASADO ({int(diff)}m)"
            elif diff > -30: cor = "#ffd700"; status = "🟡 PRÓXIMO"
            else: cor = "#00c6ff"; status = "🔵 FUTURO"
            
            with st.container():
                st.markdown(f"""
                <div style="border: 2px solid {cor}; background-color: #112240; padding: 15px; border-radius: 12px; margin-bottom: 10px;">
                    <h3 style="margin:0; color:white;">{row['nome_participante']}</h3>
                    <p style="color:{cor}; font-weight:bold;">💊 {row['nome_medicamento']} ({row['dosagem']})</p>
                    <small style="color:#aaa;">📅 {previsto.strftime('%d/%m/%Y')} ⏰ {previsto.strftime('%H:%M')} | Líder: {row.get('nome_lider')}</small>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                if c1.button("✅ BAIXAR", key=f"ok_{row['id']}", use_container_width=True):
                    baixar_med(row['id'], "Enfermaria"); st.toast("Baixado!"); time.sleep(1); st.rerun()
                
                link = link_zap(row.get('nome_lider',''), row['nome_participante'], row['nome_medicamento'], row['dosagem'], previsto, row.get('telefone_lider'))
                if link: c2.link_button("📢 ZAP", link, use_container_width=True)

# --- TAB 2: FICHA ---
with tab_ficha:
    st.markdown("### 📋 Anamnese e Medicamentos")
    df_part = carregar_dados_completos()
    
    if not df_part.empty:
        sel_nome = st.selectbox("Selecione o Participante:", df_part['nome'].tolist())
        part = df_part[df_part['nome'] == sel_nome].iloc[0]
        pid = part['id']
        
        f = carregar_ficha(pid)
        st.info(f"**Líder do Quarto:** {part['lider']}")
        
        with st.form("form_perguntas"):
            st.markdown("#### 1. Alergias")
            c1, c2 = st.columns(2)
            alergia_sim = c1.checkbox("Tem Alergia Geral?", value=f.get('tem_alergia', False))
            desc_alergia = c1.text_input("Fator e Tratamento:", value=f.get('desc_alergia', ""))
            
            alergia_med_sim = c2.checkbox("Alergia a Medicamento?", value=f.get('tem_alergia_med', False))
            desc_alergia_med = c2.text_input("Qual remédio?", value=f.get('desc_alergia_med', ""))
            
            st.markdown("#### 2. Condições de Saúde")
            col_a, col_b, col_c = st.columns(3)
            epilepsia = col_a.checkbox("Epilepsia", value=f.get('cond_epilepsia', False))
            diabetes = col_b.checkbox("Diabetes", value=f.get('cond_diabetes', False))
            asma = col_c.checkbox("Asma", value=f.get('cond_asma', False))
            cardiaco = col_a.checkbox("Problema Cardíaco", value=f.get('cond_cardiaco', False))
            hipo = col_b.checkbox("Hipoglicemia", value=f.get('cond_hipoglicemia', False))
            hiper = col_c.checkbox("Hipertensão", value=f.get('cond_hipertensao', False))
            
            outra_cond = st.text_input("Outra condição:", value=f.get('cond_outra', ""))
            trat_cond = st.text_input("Tratamento da condição:", value=f.get('tratamento_condicao', ""))
            
            st.markdown("#### 3. Outros")
            k1, k2, k3 = st.columns(3)
            sonambulo = k1.checkbox("É sonâmbulo?", value=f.get('e_sonambulo', False))
            enurese = k2.checkbox("Enurese noturna?", value=f.get('tem_enurese', False))
            rest_fisica = k3.checkbox("Restrição Física?", value=f.get('tem_restricao_fisica', False))
            desc_rest = st.text_input("Qual restrição?", value=f.get('desc_restricao_fisica', ""))
            
            plano = st.text_input("Plano de Saúde (Nome/Nº):", value=f.get('desc_plano', ""))
            
            st.markdown("#### 4. Emergência (Se diferente dos pais)")
            ec1, ec2 = st.columns(2)
            em_nome = ec1.text_input("Nome Contato", value=f.get('emergencia_nome', ""))
            em_tel = ec2.text_input("Telefone", value=f.get('emergencia_tel', ""))
            
            if st.form_submit_button("💾 SALVAR DADOS DE SAÚDE"):
                dados_salvar = {
                    "id_participante": int(pid), "nome_participante": sel_nome,
                    "tem_alergia": alergia_sim, "desc_alergia": desc_alergia,
                    "tem_alergia_med": alergia_med_sim, "desc_alergia_med": desc_alergia_med,
                    "cond_epilepsia": epilepsia, "cond_diabetes": diabetes, "cond_asma": asma,
                    "cond_cardiaco": cardiaco, "cond_hipoglicemia": hipo, "cond_hipertensao": hiper,
                    "cond_outra": outra_cond, "tratamento_condicao": trat_cond,
                    "e_sonambulo": sonambulo, "tem_enurese": enurese,
                    "tem_restricao_fisica": rest_fisica, "desc_restricao_fisica": desc_rest,
                    "desc_plano": plano, "emergencia_nome": em_nome, "emergencia_tel": em_tel
                }
                if salvar_ficha_parcial(dados_salvar):
                    st.success("Dados salvos!"); time.sleep(1); st.rerun()

        st.divider()
        
        # --- PARTE 2: MEDICAMENTOS ---
        st.markdown("#### 💊 3. Está tomando algum medicamento?")
        
        toma_remedio = st.checkbox("Sim, estou tomando", value=False)
        
        if toma_remedio:
            st.markdown("##### Cadastrar Medicamento e Gerar Alertas")
            
            c_med1, c_med2 = st.columns(2)
            remedio_nome = c_med1.text_input("Nome do Medicamento")
            dose = c_med2.text_input("Dosagem (Ex: 1cp)")
            
            st.markdown("**Cálculo de Horários**")
            cf1, cf2 = st.columns(2)
            
            freq_tipo = cf1.selectbox("Frequência", [
                "Horário Fixo", "1x ao dia", 
                "A cada 12h", "A cada 8h", "A cada 6h", "A cada 4h", "A cada 2h", "A cada 1h"
            ])
            
            dias_duracao = st.number_input("Duração (dias)", 1, 15, 4)
            
            # Lógica de Input
            param_horario = None
            valido = False
            
            if freq_tipo == "Horário Fixo":
                txt_horarios = cf2.text_input("Digite os horários (Ex: 08:00, 20:00)", placeholder="08:00, 20:00")
                if txt_horarios:
                    try:
                        param_horario = [datetime.strptime(h.strip(), "%H:%M").time() for h in txt_horarios.split(",")]
                        valido = True; data_base = agora_br().date()
                    except: st.error("Formato inválido. Use HH:MM separados por vírgula.")
            else:
                txt_ultima = cf2.text_input("Que horas foi a ÚLTIMA dose?", placeholder="Ex: 14:00")
                if txt_ultima:
                    try:
                        param_horario = datetime.strptime(txt_ultima.strip(), "%H:%M").time()
                        valido = True; data_base = agora_br().date()
                    except: st.error("Formato inválido. Use HH:MM")

            col_save, _ = st.columns([1, 4])
            
            if col_save.button("💾 SALVAR E AGENDAR", type="primary"):
                if remedio_nome and valido:
                    # Permite agendar mesmo se 'lider' for 'Sem Quarto'
                    ok, qtd = agendar_medicacao_auto(
                        pid, sel_nome, remedio_nome, dose, 
                        data_base, freq_tipo, param_horario, dias_duracao,
                        part['lider'], part['tel_lider']
                    )
                    if ok: st.success(f"{qtd} horários agendados!"); st.balloons(); time.sleep(2); st.rerun()
                else: st.error("Preencha todos os campos corretamente.")

# --- TAB 3: RESPONSAVEL ---
with tab_equipe:
    st.markdown("### ⚙️ Responsável pela Medicação")
    st.info("Pessoas nesta lista receberão as notificações automáticas do Robô.")
    
    df_part = carregar_dados_completos()
    
    if not df_part.empty:
        filtro_servos = df_part['tipo'].str.contains("Servo", case=False, na=False)
        lista_servos = df_part[filtro_servos]
        
        if lista_servos.empty:
            st.warning("Nenhum participante marcado como 'Servo' encontrado. Mostrando todos.")
            lista_para_exibir = df_part
        else:
            lista_para_exibir = lista_servos
            
        with st.form("add_team"):
            col_sel, col_btn = st.columns([3, 1])
            nome_add = col_sel.selectbox("Selecione o Servo:", lista_para_exibir['nome'].unique())
            
            if col_btn.form_submit_button("Adicionar"):
                dados_servo = df_part[df_part['nome'] == nome_add].iloc[0]
                tel = dados_servo['celular']
                
                if tel and len(str(tel)) >= 8:
                    if adicionar_equipe(nome_add, tel): st.success(f"{nome_add} adicionado!"); st.rerun()
                    else: st.warning("Já está na lista.")
                else: st.error("Este servo não tem celular cadastrado!")
    else:
        st.info("Nenhum participante cadastrado no sistema ainda.")

    st.divider()
    df_equipe = carregar_equipe()
    if not df_equipe.empty:
        st.markdown("#### Membros Atuais")
        for i, row in df_equipe.iterrows():
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.write(f"👤 **{row['nome']}**")
            c2.write(f"📱 {row['telefone']}")
            if c3.button("🗑️ Remover", key=f"del_team_{row['id']}"):
                remover_equipe(row['id']); st.rerun()
    else:
        st.warning("Ninguém na lista de responsáveis ainda.")

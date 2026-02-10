import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import time
from urllib.parse import quote
from supabase import create_client, Client

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
    
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input, .stTimeInput input {
        background-color: #172a45 !important; color: white !important; border: 1px solid #00c6ff !important; border-radius: 8px !important;
    }
    div[data-baseweb="select"] > div { background-color: #172a45 !important; border-color: #00c6ff !important; color: white !important; }
    
    label[data-baseweb="checkbox"] { color: #e6f1ff !important; }
    
    div.stButton > button { background: linear-gradient(90deg, #00c6ff 0%, #0072ff 100%); color: white; border: none; border-radius: 50px; font-weight: bold; }
    h1, h2, h3, h4 { color: #00c6ff !important; }
</style>
""", unsafe_allow_html=True)

# =======================================================
# 2. FUNÇÕES DE BANCO E LÓGICA
# =======================================================

# --- AJUSTE DE FUSO HORÁRIO (BRASIL -3h) ---
def agora_br():
    # Pega hora UTC (servidor) e tira 3 horas
    return datetime.utcnow() - timedelta(hours=3)

@st.cache_resource
def init_supabase():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None

def carregar_dados_completos():
    sb = init_supabase()
    res = sb.table("participantes").select("id, nome_completo, quartos(nome_lider, telefone_lider)").order("nome_completo").execute()
    lista = []
    for item in res.data:
        quarto = item.get('quartos') or {} 
        lista.append({
            "id": item['id'],
            "nome": item['nome_completo'],
            "lider": quarto.get('nome_lider', 'Sem Quarto'),
            "tel_lider": quarto.get('telefone_lider', '')
        })
    return pd.DataFrame(lista)

def carregar_ficha(id_part):
    sb = init_supabase()
    res = sb.table("ficha_medica").select("*").eq("id_participante", id_part).execute()
    if res.data: return res.data[0]
    return {}

def salvar_ficha_parcial(dados):
    sb = init_supabase()
    existe = carregar_ficha(dados['id_participante'])
    if existe:
        sb.table("ficha_medica").update(dados).eq("id_participante", dados['id_participante']).execute()
    else:
        sb.table("ficha_medica").insert(dados).execute()
    return True

# Função de Agendamento Inteligente
def agendar_medicacao_auto(id_part, nome_part, remedio, dose, data_ini, freq_tipo, param_horario, dias, lider, tel_lider):
    sb = init_supabase()
    lista_inserts = []
    
    # Lógica 1: Horário Fixo (Lista de horários)
    if freq_tipo == "Horário Fixo":
        horarios_fixos = param_horario 
        for d in range(dias):
            dia_atual = data_ini + timedelta(days=d)
            for h_obj in horarios_fixos:
                dh_final = datetime.combine(dia_atual, h_obj)
                lista_inserts.append({
                    "id_participante": int(id_part),
                    "nome_participante": nome_part,
                    "nome_medicamento": remedio,
                    "dosagem": dose,
                    "data_hora_prevista": dh_final.isoformat(),
                    "status": "Pendente",
                    "nome_lider": lider,
                    "telefone_lider": tel_lider
                })

    # Lógica 2: Intervalos (Calcula a partir da última dose)
    else:
        hora_base = param_horario
        dt_base = datetime.combine(data_ini, hora_base)
        
        horas_intervalo = 0
        if freq_tipo == "A cada 1h": horas_intervalo = 1
        elif freq_tipo == "A cada 2h": horas_intervalo = 2
        elif freq_tipo == "A cada 4h": horas_intervalo = 4
        elif freq_tipo == "A cada 6h": horas_intervalo = 6
        elif freq_tipo == "A cada 8h": horas_intervalo = 8
        elif freq_tipo == "A cada 12h": horas_intervalo = 12
        elif freq_tipo == "1x ao dia": horas_intervalo = 24
        
        if horas_intervalo > 0:
            total_horas = dias * 24
            qtd_doses = int(total_horas / horas_intervalo)
            
            for i in range(1, qtd_doses + 1):
                proxima_dose = dt_base + timedelta(hours=i*horas_intervalo)
                lista_inserts.append({
                    "id_participante": int(id_part),
                    "nome_participante": nome_part,
                    "nome_medicamento": remedio,
                    "dosagem": dose,
                    "data_hora_prevista": proxima_dose.isoformat(),
                    "status": "Pendente",
                    "nome_lider": lider,
                    "telefone_lider": tel_lider
                })

    if lista_inserts:
        sb.table("medicacoes").insert(lista_inserts).execute()
        return True, len(lista_inserts)
    return False, 0

def carregar_alertas():
    sb = init_supabase()
    res = sb.table("medicacoes").select("*").eq("status", "Pendente").order("data_hora_prevista").execute()
    df = pd.DataFrame(res.data)
    if not df.empty: df['data_hora_prevista'] = pd.to_datetime(df['data_hora_prevista'])
    return df

def baixar_med(id_med, operador):
    sb = init_supabase()
    # Usa agora_br() para salvar o horário real do Brasil
    sb.table("medicacoes").update({
        "status": "Administrado",
        "data_hora_realizada": agora_br().isoformat(),
        "operador_realizou": operador
    }).eq("id", id_med).execute()
    return True

# MENSAGEM ZAP CORRIGIDA
def link_zap(nome_lider, nome_part, remedio, dosagem, hora_prevista, tel_lider):
    if not tel_lider: return None
    tel = "".join([c for c in str(tel_lider) if c.isdigit()])
    hora_str = hora_prevista.strftime('%H:%M')
    
    msg = f"Olá {nome_lider}!\n"
    msg += f"🔔 *HORA DO REMÉDIO*\n"
    msg += f"O(a) participante *{nome_part}* precisa tomar:\n"
    msg += f"💊 *{remedio}* ({dosagem}) às {hora_str}."
    
    return f"https://wa.me/55{tel}?text={quote(msg)}"

# =======================================================
# 3. INTERFACE
# =======================================================
st.title("💊 Fichas Médicas")

tab_alerta, tab_ficha = st.tabs(["🚨 Painel de Alertas", "📋 Ficha de Saúde (Anamnese)"])

# --- TAB 1: PAINEL DE ALERTAS ---
with tab_alerta:
    st.markdown("### 🕒 Medicamentos Agendados")
    if st.button("🔄 Atualizar Painel"): st.rerun()
    
    df = carregar_alertas()
    if df.empty:
        st.info("Tudo tranquilo! Nenhuma medicação pendente.")
    else:
        # Usa agora_br() para comparar com os horários do banco
        agora = agora_br()
        
        for idx, row in df.iterrows():
            previsto = row['data_hora_prevista']
            # Diferença em minutos
            diff = (agora - previsto).total_seconds() / 60 
            
            if diff > 15: cor = "#ff4b4b"; status = f"🔴 ATRASADO ({int(diff)} min)"
            elif diff > -30: cor = "#ffd700"; status = "🟡 PRÓXIMO"
            else: cor = "#00c6ff"; status = "🔵 FUTURO"
            
            with st.container():
                st.markdown(f"""
                <div style="border: 2px solid {cor}; background-color: #112240; padding: 15px; border-radius: 12px; margin-bottom: 15px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h2 style="margin:0; color:white; font-size:22px;">{row['nome_participante']}</h2>
                            <p style="margin:5px 0; color:{cor}; font-weight:bold; font-size:18px;">
                                💊 {row['nome_medicamento']} <span style="color:#ccc; font-size:16px">({row['dosagem']})</span>
                            </p>
                            <p style="margin:0; color:#aaa;">⏰ Horário: {previsto.strftime('%H:%M')} | Líder: {row.get('nome_lider', 'N/A')}</p>
                        </div>
                        <div style="text-align:right;">
                            <span style="background-color:{cor}; color:{'white' if cor!='#ffd700' else 'black'}; padding:5px 10px; border-radius:5px; font-weight:bold;">{status}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button("✅ DAR BAIXA", key=f"ok_{row['id']}", use_container_width=True):
                        baixar_med(row['id'], "Enfermaria"); st.toast("Baixa OK!"); time.sleep(1); st.rerun()
                with c2:
                    link = link_zap(row.get('nome_lider','Líder'), row['nome_participante'], row['nome_medicamento'], row['dosagem'], previsto, row.get('telefone_lider'))
                    if link: st.link_button("📢 ZAP LÍDER", link, use_container_width=True)
                    else: st.button("🚫 Sem Contato", disabled=True, use_container_width=True)

# --- TAB 2: FICHA DE SAÚDE ---
with tab_ficha:
    st.markdown("### 📋 Anamnese e Medicamentos")
    
    df_part = carregar_dados_completos()
    
    if not df_part.empty:
        nomes = df_part['nome'].tolist()
        selecionado_nome = st.selectbox("Selecione o Participante:", nomes)
        
        participante = df_part[df_part['nome'] == selecionado_nome].iloc[0]
        pid = participante['id']
        lider_nome = participante['lider']
        lider_tel = participante['tel_lider']
        
        f = carregar_ficha(pid)
        st.info(f"**Líder do Quarto:** {lider_nome}")
        
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
                    "id_participante": int(pid), "nome_participante": selecionado_nome,
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
        
        # --- PARTE 2: MEDICAMENTOS (AGENDAMENTO DINÂMICO) ---
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
            
            # --- LÓGICA DE INPUT (TEXTO vs HORA) ---
            param_horario = None
            valido = False
            
            if freq_tipo == "Horário Fixo":
                txt_horarios = cf2.text_input("Digite os horários (Ex: 08:00, 20:00)", placeholder="08:00, 20:00")
                if txt_horarios:
                    try:
                        param_horario = [datetime.strptime(h.strip(), "%H:%M").time() for h in txt_horarios.split(",")]
                        valido = True
                        data_base = agora_br().date() # Usa data de hoje no Brasil
                    except:
                        st.error("Formato inválido. Use HH:MM separados por vírgula.")
            else:
                txt_ultima = cf2.text_input("Que horas foi a ÚLTIMA dose?", placeholder="Ex: 14:00")
                if txt_ultima:
                    try:
                        param_horario = datetime.strptime(txt_ultima.strip(), "%H:%M").time()
                        valido = True
                        data_base = agora_br().date() # Usa data de hoje no Brasil
                    except:
                        st.error("Formato inválido. Use HH:MM")

            col_save, col_clear = st.columns([1, 4])
            
            if col_save.button("💾 SALVAR E AGENDAR", type="primary"):
                if remedio_nome and valido:
                    if lider_nome != 'Sem Quarto':
                        ok, qtd = agendar_medicacao_auto(
                            pid, selecionado_nome, remedio_nome, dose, 
                            data_base, freq_tipo, param_horario, dias_duracao,
                            lider_nome, lider_tel
                        )
                        if ok:
                            st.success(f"{qtd} horários agendados!"); st.balloons(); time.sleep(2); st.rerun()
                    else:
                        st.error("Participante sem Líder/Quarto. Aloque ele antes.")
                else:
                    st.error("Preencha todos os campos corretamente.")
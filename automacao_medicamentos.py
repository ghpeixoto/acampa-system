import os
import time
from datetime import datetime, timedelta
import pytz
from supabase import create_client
from twilio.rest import Client

# --- CONFIGURAÇÕES ---
# Se estiver rodando local, você pode colocar as chaves direto aqui ou usar variáveis de ambiente
# Para facilitar no PC local, você pode preencher as strings abaixo se as variáveis não funcionarem
SUPABASE_URL = os.environ.get("SUPABASE_URL") 
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM")

# Link do seu sistema para facilitar a baixa
LINK_SISTEMA = "https://acampateens.streamlit.app/"

def enviar_alertas_inteligentes():
    if not SUPABASE_URL:
        print("❌ ERRO: Variáveis de ambiente não encontradas.")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    
    # 1. Definir Agora (Horário Brasil)
    tz_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz_br)
    
    print(f"\n--- 🔎 Verificando às {agora.strftime('%H:%M:%S')} ---")

    # 2. Buscar TUDO que está Pendente (Passado e Futuro Próximo)
    # Pegamos tudo até daqui a 20 minutos para garantir
    limite_busca = agora + timedelta(minutes=20)
    
    # Precisamos converter para string ISO sem fuso para comparar com o banco (se o banco for naive)
    # Ou usamos a lógica de trazer tudo pendente e filtramos no Python
    res = supabase.table("medicacoes").select("*").eq("status", "Pendente").execute()
    pendentes = res.data
    
    if not pendentes:
        print("✅ Tudo limpo! Nenhum remédio pendente.")
        return

    # 3. Filtrar e Processar
    for med in pendentes:
        id_med = med['id']
        nome_rem = med['nome_medicamento']
        participante = med['nome_participante']
        
        # Converte horário previsto do banco
        dt_prevista = datetime.fromisoformat(med['data_hora_prevista'])
        # Garante que temos fuso para comparar (assumindo que no banco está o horário visual BR)
        if dt_prevista.tzinfo is None:
            dt_prevista = tz_br.localize(dt_prevista)
        
        # Diferença de tempo (Negativo = Atrasado, Positivo = Futuro)
        diff_minutos = (dt_prevista - agora).total_seconds() / 60
        
        # Recupera último aviso (se houver)
        ultimo_aviso_str = med.get('ultimo_aviso')
        ultimo_aviso_dt = None
        if ultimo_aviso_str:
            ultimo_aviso_dt = datetime.fromisoformat(ultimo_aviso_str)
            if ultimo_aviso_dt.tzinfo is None:
                ultimo_aviso_dt = tz_br.localize(ultimo_aviso_dt)

        enviar = False
        tipo_msg = ""
        
        # --- LÓGICA DE DECISÃO ---
        
        # CASO 1: Futuro Próximo (Daqui a 10 min ou menos)
        if 0 < diff_minutos <= 15:
            # Se nunca avisou, avisa agora (Pré-alerta)
            if not ultimo_aviso_dt:
                enviar = True
                tipo_msg = "🟡 *PRÓXIMO (15min)*"
                texto_extra = "⚠️ Preparar."

        # CASO 2: Atrasado (Já passou do horário)
        elif diff_minutos <= 0:
            # Se nunca avisou (talvez o script estava desligado antes), avisa agora!
            if not ultimo_aviso_dt:
                enviar = True
                tipo_msg = "🔴 *AGORA/ATRASADO*"
                texto_extra = "⚠️ *Entregar!*"
            
            # Se já avisou, vamos ver quanto tempo faz (Cobrança)
            else:
                tempo_desde_ultimo = (agora - ultimo_aviso_dt).total_seconds() / 60
                # Só cobra se passou mais de 10 min do último grito
                if tempo_desde_ultimo >= 10:
                    enviar = True
                    tipo_msg = "⏰ *COBRANÇA*"
                    texto_extra = "⚠️ *Alerta já enviado! Ainda não foi baixado.* Foi entregue?"

        # --- ENVIO ---
        if enviar:
            # Busca Equipe
            equipe = supabase.table("equipe_enfermaria").select("*").execute().data
            
            # Busca Dados Quarto/Líder
            try:
                p_data = supabase.table("participantes").select("quartos(nome, nome_lider)").eq("id", med['id_participante']).execute()
                if p_data.data and p_data.data[0].get('quartos'):
                    q = p_data.data[0]['quartos']
                    quarto = q.get('nome', '-')
                    lider = q.get('nome_lider', '-')
                else:
                    quarto, lider = "Sem Quarto", "-"
            except:
                quarto, lider = "-", "-"

            msg = (
                f"🚨 *ALERTA REMÉDIO* {tipo_msg}\n\n"
                f"💊 *{nome_rem}* ({med['dosagem']})\n"
                f"👤 {participante}\n"
                f"🛏️ {quarto} | 🛡️ {lider}\n"
                f"⏰ Horário: {dt_prevista.strftime('%H:%M')}\n\n"
                f"{texto_extra}\n"
                f"🔗 Baixar aqui: {LINK_SISTEMA}"
            )

            print(f"📤 Enviando: {participante} - {nome_rem} ({tipo_msg})")
            
            for membro in equipe:
                tel = "".join(filter(str.isdigit, str(membro['telefone'])))
                if not tel.startswith("55") and len(tel) > 10: tel = "55" + tel
                try:
                    client.messages.create(from_=TWILIO_FROM, body=msg, to=f"whatsapp:+{tel}")
                except Exception as e:
                    print(f"Erro zap: {e}")
            
            # ATUALIZA O ÚLTIMO AVISO NO BANCO PARA NÃO REPETIR IMEDIATAMENTE
            supabase.table("medicacoes").update({"ultimo_aviso": agora.isoformat()}).eq("id", id_med).execute()
        
        else:
            # Apenas log para você saber que ele viu, mas decidiu esperar
            if diff_minutos <= 0:
                print(f"⏳ {participante}: Atrasado, mas avisado há pouco tempo. Aguardando 10min...")

if __name__ == "__main__":
    # Teste único se rodar direto
    enviar_alertas_inteligentes()

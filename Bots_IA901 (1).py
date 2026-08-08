import streamlit as st
import json
import pandas as pd

# 💡 DICA PARA A AULA 1: A Importação
# Graças à atualização do Azure AI Foundry, podemos usar a biblioteca 
# padrão da OpenAI, o que torna nosso código muito mais portável!
from openai import OpenAI

# ==========================================
# 1. Configuração da Página e Funções Auxiliares
# ==========================================
st.set_page_config(page_title="HelpDesk de TI", page_icon="🖥️", layout="wide")

def abrir_chamado_ti(descricao, prioridade, departamento):
    """Simula a abertura de um chamado no sistema da empresa."""
    numero_ticket = f"INC-{st.session_state.interaction_count * 100}"
    st.toast(f"Chamado {numero_ticket} aberto com sucesso no sistema!", icon="✅")
    return json.dumps({"status": "sucesso", "numero_ticket": numero_ticket})

def limpar_conversa():
    st.session_state.messages = [
        {"role": "system", "content": "Você é o Bot Supervisor de TI da Contoso Corp. Avalie o problema do usuário. Se for hardware/software, use a ferramenta de abrir chamado. Para outros problemas, oriente educadamente."}
    ]
    st.session_state.token_history = []
    st.session_state.interaction_count = 0
    st.session_state.total_tokens = 0

# ==========================================
# 2. Inicialização do Estado (Session State)
# ==========================================
if "messages" not in st.session_state:
    limpar_conversa()

# ==========================================
# 3. Configuração do Cliente OpenAI (Azure Foundry)
# ==========================================
# 💡 DICA PARA A AULA 2: O Endpoint Inteligente
# Note que o endereço termina com '/openai/v1'. Isso avisa aos servidores da 
# Microsoft que vamos conversar no padrão universal, dispensando o 'api_version'.
endpoint = "https://marcelomaffeis-05082026-resource.services.ai.azure.com/openai/v1"
deployment_name = "gpt-5.4-mini"

# 💡 DICA PARA A AULA 3: Segurança de Credenciais
# Em um ambiente real, nunca deixamos a chave exposta no código.
# O Streamlit oferece o st.secrets para gerenciar isso com segurança.
client = OpenAI(
    base_url=endpoint,
    api_key="6t2pTNsmNafDyo53MDAFIrvvQRBZXP7dLcr5j3TLxMS34LQVq3ZUJQQJ99CHACHYHv6XJ3w3AAAAACOGT7os" # Recomende aos alunos usar: st.secrets["AZURE_API_KEY"]
)

# Definição da Ferramenta para o modelo (Function Calling)
ferramentas = [
    {
        "type": "function",
        "function": {
            "name": "abrir_chamado_ti",
            "description": "Abre um ticket de suporte técnico para problemas de TI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "descricao": {"type": "string"},
                    "prioridade": {"type": "string", "enum": ["alta", "media", "baixa"]},
                    "departamento": {"type": "string"}
                },
                "required": ["descricao", "prioridade", "departamento"]
            }
        }
    }
]

# ==========================================
# 4. Interface da Barra Lateral (Sidebar)
# ==========================================
with st.sidebar:
    st.title("⚙️ Painel de Controle")
    
    if st.button("🗑️ Nova Conversa / Limpar Histórico", use_container_width=True):
        limpar_conversa()
        st.rerun()
    
    st.divider()
    
    st.subheader("📊 Consumo de Tokens")
    st.metric(label="Tokens Totais (Sessão)", value=st.session_state.total_tokens)
    
    if st.session_state.token_history:
        # 💡 DICA PARA A AULA 4: Integração com Pandas
        # Transformamos um dicionário simples em um DataFrame Pandas 
        # para alimentar rapidamente os gráficos nativos do Streamlit.
        df_tokens = pd.DataFrame(st.session_state.token_history)
        df_tokens.set_index("Interação", inplace=True)
        
        st.markdown("**Histórico por Interação:**")
        st.bar_chart(df_tokens["Tokens"])

# ==========================================
# 5. Interface Principal do Chat
# ==========================================
st.title("🤖 Bot Supervisor de TI")
st.markdown("Relate seu problema. Eu avaliarei e, se necessário, abrirei um chamado automaticamente.")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"): st.markdown(msg["content"])
    elif msg["role"] == "assistant" and msg.get("content"):
        with st.chat_message("assistant"): st.markdown(msg["content"])

# ==========================================
# 6. Lógica de Processamento do Input
# ==========================================
prompt = st.chat_input("Ex: Minha tela ficou azul e sou do setor Financeiro...")

if prompt:
    st.session_state.interaction_count += 1
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    tokens_nesta_rodada = 0

    with st.chat_message("assistant"):
        with st.spinner("Analisando e decidindo ação..."):
            
            # Primeira chamada à API
            resposta = client.chat.completions.create(
                model=deployment_name,
                messages=st.session_state.messages,
                tools=ferramentas,
                tool_choice="auto"
            )
            
            mensagem_ia = resposta.choices[0].message
            tokens_nesta_rodada += resposta.usage.total_tokens
            
            # Converte a mensagem para dict para armazenar perfeitamente no session_state
            st.session_state.messages.append(mensagem_ia.model_dump(exclude_none=True))
            
            # Verifica se a IA decidiu usar a ferramenta
            if mensagem_ia.tool_calls:
                for tool_call in mensagem_ia.tool_calls:
                    if tool_call.function.name == "abrir_chamado_ti":
                        args = json.loads(tool_call.function.arguments)
                        
                        # Executa a nossa função em Python local
                        resultado = abrir_chamado_ti(args.get("descricao"), args.get("prioridade"), args.get("departamento"))
                        
                        # Devolve o resultado para o histórico da IA
                        st.session_state.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": resultado
                        })
                
                # Segunda chamada à API para a IA interpretar o resultado da ferramenta
                resposta_final = client.chat.completions.create(
                    model=deployment_name,
                    messages=st.session_state.messages
                )
                
                texto_final = resposta_final.choices[0].message.content
                tokens_nesta_rodada += resposta_final.usage.total_tokens
                st.session_state.messages.append({"role": "assistant", "content": texto_final})
                st.markdown(texto_final)
                
            else:
                # Caso a IA não tenha precisado usar ferramentas (ex: dúvidas gerais)
                st.markdown(mensagem_ia.content)
    
    # Atualiza as métricas e força o redesenho da tela
    st.session_state.total_tokens += tokens_nesta_rodada
    st.session_state.token_history.append({
        "Interação": f"Turno {st.session_state.interaction_count}",
        "Tokens": tokens_nesta_rodada
    })
    
    st.rerun()
import streamlit as st
from typing import Annotated, Literal
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI

# --- TOOLS ---
@tool
def retrieve_places(country: str):
    """Returns top travel destinations for a country."""
    data = {"Japan": "Tokyo, Kyoto, Osaka", "Bali": "Uluwatu, Ubud", "France": "Paris, Nice"}
    return f"Top places in {country}: {data.get(country, 'Generic tropical islands')}."

@tool
def weather_info(city: str):
    """Returns fake weather info for a city."""
    return f"The weather in {city} is currently Sunny and 28°C."

tools = [retrieve_places, weather_info]
llm = ChatOllama(model="qwen3:0.6b", temperature=0).bind_tools(tools)
#llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash",google_api_key="AIzaSyAKG6cgaK09uWvywKlAuyc4llzVXdFXhdY", temperature=0).bind_tools(tools)


# --- GRAPH LOGIC ---
def router(state: MessagesState) -> Literal["tools", "__end__"]:
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "tools"
    return END

def agent_node(state: MessagesState):
    # System message enforces memory awareness
    sys_msg = SystemMessage(content="You are a travel agent. Remember user preferences mentioned earlier.")
    messages = [sys_msg] + state["messages"]
    return {"messages": [llm.invoke(messages)]}

"""# Build Graph
builder = StateGraph(MessagesState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", router)
builder.add_edge("tools", "agent")

# MemorySaver enables "Time Travel" / State Persistence
memory = MemorySaver()
app = builder.compile(checkpointer=memory)"""

@st.cache_resource
def get_app():
    # Use InMemorySaver for session-level persistence
    checkpointer = MemorySaver()
    
    # Define and build your graph as before
    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", router)
    builder.add_edge("tools", "agent")
    
    # Compile with the checkpointer
    return builder.compile(checkpointer=checkpointer)

# Call the cached function to get the persistent app instance
app = get_app()

st.set_page_config(page_title="2026 Travel Agent", layout="wide")
st.title("🧳 AI Travel Agent (Ollama + LangGraph)")

# Initialize session state for the thread ID (allows resuming/time travel)
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "user_1"

# --- SIDEBAR: State & Memory ---
with st.sidebar:
    st.header("Settings")
    if st.button("Reset Conversation"):
        st.session_state.thread_id = f"user_{st.session_state.thread_id}_new"
        st.rerun()
    st.info(f"Thread ID: {st.session_state.thread_id}")

# --- CHAT INTERFACE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about destinations or weather..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Invoke Graph
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    input_data = {"messages": [HumanMessage(content=prompt)]}
    
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        # Streaming from the graph to display tool data
        for event in app.stream(input_data, config, stream_mode="values"):
            if "messages" in event:
                msg = event["messages"][-1]
                
                # If tool output exists, show it in an expander
                if msg.type == "tool":
                    with st.expander(f"🛠️ Tool Used: {msg.name}", expanded=False):
                        st.write(msg.content)
                
                # If final AI response
                if msg.type == "ai" and msg.content:
                    full_response = msg.content
                    print("Final AI Response:", full_response)
                    response_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

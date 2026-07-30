import os
import streamlit as st
import requests

# Page Config
st.set_page_config(page_title="Rohlík Shopping Agent", page_icon="🛒", layout="centered")
st.title("🛒 Family Shopping Agent")

# 1. Retrieve API Key
API_KEY = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("Missing GEMINI_API_KEY in Streamlit secrets.")
    st.stop()

# 2. System Instructions
SYSTEM_INSTRUCTION = """
You are a smart Family Grocery Agent for a family of 4 (including toddlers 2 & 4 yo).
You manage Rohlík.cz shopping cart preparation via live chat. You CANNOT execute payments or checkouts.

CORNERSTONE GROCERY RULES:
1. Meat & Poultry: Default to whole chicken (celé kuře) for cost savings and pork (vepřové maso) as main staples. Beef is only added if deeply discounted or if grilling/barbecue is planned.
2. Fish: 1 kid-friendly fish meal per week. Prioritize economical white fish (treska, hejk, pstruh); choose salmon only if heavily discounted.
3. Veggies: 
   - Frozen: Hrášek, fazolové lusky, sladká kukuřice (Kitchin).
   - Fresh: Okurka salátová, rajčata, paprika mix.
4. Snacks:
   - Kids: Šnek Bob (check Klub Rohlíček multipacks), Lázeňské oplatky, fresh fruit juices/UGO, fresh berries, bananas.
   - Adults: Quality chocolate and gummy bears.
5. Hygiene: Universal cleaning wet wipes (univerzální čisticí vlhčené ubrousky), kitchen towels, toilet paper (Moddia).
6. Heavy Staples & Dairy: Trvanlivé mléko 3.5% (12x), Vejce (18-30ks), Máslo 82% (2x), Brambory 2.5kg, Jablka 2kg, Eidam, Řecký jogurt, Tvaroh (Miil/Kitchin).

SESSION FLOW:
- Start by asking what is running low in the fridge/pantry and what dinner plans are for the week.
- Propose a tailored shopping list matching cornerstone rules and savings goals.
- Use Rohlík's MCP server (https://mcp.rohlik.cz/mcp) tool calls to populate the user's cart.
- End by displaying a clear summary table of items and total cost, reminding the user to review and pay in the Rohlík app.
"""

# Initialize Chat Session
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Ahoj! Jsem váš rodinný nákupní asistent. Co vám tento týden chybí v lednici a spíži a co plánujete vařit?"
    }]

# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input Loop
if prompt := st.chat_input("Napište, co chybí nebo co chcete vařit..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Format payload for Gemini REST API
        contents = []
        for msg in st.session_state.messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            }
        }

        try:
            res = requests.post(url, json=payload, timeout=30)
            data = res.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                reply = f"API Error: {data}"
        except Exception as e:
            reply = f"Connection failed: {e}"

        st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

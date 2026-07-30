import os
import requests
import streamlit as st

# Page Config
st.set_page_config(
    page_title="Rohlík Shopping Agent", page_icon="🛒", layout="centered"
)
st.title("🛒 Family Shopping Agent")

# 1. Retrieve Credentials
API_KEY = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
ROHLIK_COOKIE = os.environ.get("ROHLIK_COOKIE") or st.secrets.get(
    "ROHLIK_COOKIE"
)

if not API_KEY:
  st.error("Missing GEMINI_API_KEY in Streamlit secrets.")
  st.stop()


# 2. Rohlík API Helpers
def get_rohlik_headers():
  return {
      "Cookie": ROHLIK_COOKIE or "",
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      ),
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
  }


def search_rohlik(query: str):
  """Search Rohlík for products matching query."""
  url = f"https://www.rohlik.cz/services/frontend-service/autocomplete?search={query}"
  try:
    res = requests.get(url, headers=get_rohlik_headers(), timeout=10)
    data = res.json()
    products = []
    # Extract top 5 relevant items
    for item in data.get("productResults", [])[:5]:
      products.append({
          "id": item.get("id"),
          "name": item.get("name"),
          "price": item.get("price", {}).get("amount"),
          "unit": item.get("unit"),
      })
    return products if products else "No products found."
  except Exception as e:
    return f"Search error: {e}"


def add_to_rohlik_cart(product_id: int, quantity: int = 1):
  """Add a specific product ID to Rohlík cart."""
  url = "https://www.rohlik.cz/services/frontend-service/cart/items"
  payload = [{"productId": product_id, "quantity": quantity}]
  try:
    res = requests.post(
        url, json=payload, headers=get_rohlik_headers(), timeout=10
    )
    if res.status_code in [200, 201]:
      return f"Successfully added {quantity}x product ID {product_id} to Rohlík cart!"
    return f"Failed to add item (Status {res.status_code}): {res.text}"
  except Exception as e:
    return f"Cart API error: {e}"


# Tool declarations for Gemini API
TOOLS = [{
    "functionDeclarations": [
        {
            "name": "search_rohlik",
            "description": (
                "Search for groceries on Rohlík.cz by name (in Czech) to locate"
                " product IDs."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {
                        "type": "STRING",
                        "description": (
                            "Search keyword in Czech (e.g., 'mleko',"
                            " 'maslo', 'vajicka')"
                        ),
                    }
                },
                "required": ["query"],
            },
        },
        {
            "name": "add_to_rohlik_cart",
            "description": (
                "Add a product directly to the user's live Rohlík shopping cart"
                " using product_id."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "product_id": {
                        "type": "INTEGER",
                        "description": "The numerical ID of the product.",
                    },
                    "quantity": {
                        "type": "INTEGER",
                        "description": "Quantity to add.",
                    },
                },
                "required": ["product_id", "quantity"],
            },
        },
    ]
}]

# 3. System Instructions
SYSTEM_INSTRUCTION = """
You are an active Family Grocery Agent for Rohlík.cz.
When the user agrees on items to purchase, you MUST:
1. Search for matching items using `search_rohlik(query)`.
2. Select appropriate, affordable options matching family cornerstone preferences.
3. Automatically execute `add_to_rohlik_cart(product_id, quantity)` for each selected product.
4. Report back with exact items successfully added to their cart.

CORNERSTONE GROCERY RULES:
- Staples: Trvanlivé mléko 3.5%, Vejce, Máslo 82%, Brambory, Eidam, Tvaroh.
- Meat: Default to whole chicken (celé kuře) and pork (vepřové maso).
- Veggies & Fruit: Cucumber, tomatoes, frozen peas, bananas.
"""

# Initialize Chat Session
if "messages" not in st.session_state:
  st.session_state.messages = [{
      "role": "assistant",
      "content": (
          "Ahoj! Jsem váš rodinný nákupní asistent. Napište, co chybí,"
          " a já vybrané položky rovnou přidám do vašeho košíku na Rohlík.cz!"
      ),
  }]

# Render Chat History
for msg in st.session_state.messages:
  with st.chat_message(msg["role"]):
    st.markdown(msg["content"])

# User Input Loop
if prompt := st.chat_input("Co mám přidat do košíku?"):
  st.session_state.messages.append({"role": "user", "content": prompt})
  with st.chat_message("user"):
    st.markdown(prompt)

  with st.chat_message("assistant"):
    contents = []
    for msg in st.session_state.messages:
      role = "user" if msg["role"] == "user" else "model"
      contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={API_KEY}"
    payload = {
        "contents": contents,
        "tools": TOOLS,
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
    }

    try:
      res = requests.post(url, json=payload, timeout=30).json()
      candidate = res.get("candidates", [{}])[0]
      parts = candidate.get("content", {}).get("parts", [])

      # Check if model requested tool execution
      function_call = None
      text_reply = ""

      for part in parts:
        if "functionCall" in part:
          function_call = part["functionCall"]
        elif "text" in part and not part.get("thought", False):
          text_reply += part["text"]

      if function_call:
        fn_name = function_call["name"]
        args = function_call["args"]

        if fn_name == "search_rohlik":
          result = search_rohlik(args.get("query", ""))
          st.info(f"🔎 Vyhledávám na Rohlíku: '{args.get('query')}'")
          reply = f"Nalezené položky: {result}"
        elif fn_name == "add_to_rohlik_cart":
          result = add_to_rohlik_cart(
              int(args.get("product_id")), int(args.get("quantity", 1))
          )
          st.success(f"🛒 Vkládám do košíku...")
          reply = result
        else:
          reply = text_reply or "Hotovo."
      else:
        reply = text_reply or "Můžete upřesnit, co přesně chcete přidat?"

    except Exception as e:
      reply = f"Chyba při komunikaci: {e}"

    st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

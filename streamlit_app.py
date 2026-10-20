import os, textwrap, zipfile

root = "/mnt/data/showroom_pos"
os.makedirs(root + "/pages", exist_ok=True)
os.makedirs(root + "/.streamlit", exist_ok=True)

files = {
"app.py": r'''
import streamlit as st

st.set_page_config(page_title="Showroom POS", page_icon="🛍️", layout="wide")

st.title("Showroom POS")
st.caption("Sales • Inventory • Management")

st.sidebar.title("Showroom POS")
st.sidebar.caption("Use the pages below to navigate.")

st.info(
    "Choose **Sales POS**, **Inventory**, or **Management** from the sidebar. "
    "For API actions that require a token, enter it in the API Token field in the sidebar."
)

col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("🛒 Sales")
    st.write("Create bills and record sales.")
with col2:
    st.subheader("📦 Inventory")
    st.write("Add products and manage stock.")
with col3:
    st.subheader("📊 Management")
    st.write("Review totals, expenses, and closing balances.")

st.warning(
    "This is the frontend starter. API endpoints for listing products, creating sales, "
    "expenses, and daily closing must match your existing backend functions before those "
    "operations can be enabled."
)
''',
"api_client.py": r'''
"""Shared HTTP client for the existing API.

The API token is entered by the user in the Streamlit sidebar and is not saved to disk.
This client sends it as a `token` query parameter to match the API URL pattern previously
provided by the project owner. Change `TOKEN_MODE` only if the backend expects another format.
"""
import os
import requests
import streamlit as st

TOKEN_MODE = "query"  # "query" or "bearer"

def get_base_url() -> str:
    try:
        configured = st.secrets.get("API_BASE_URL", "")
    except Exception:
        configured = ""
    return (configured or os.getenv("API_BASE_URL", "")).rstrip("/")

def get_api_token() -> str:
    return st.session_state.get("api_token", "").strip()

def api_request(method: str, endpoint: str, *, params=None, json=None, requires_token=True):
    base_url = get_base_url()
    if not base_url:
        raise RuntimeError(
            "API_BASE_URL is not configured. Set it in Streamlit Cloud Secrets "
            "or in your local .streamlit/secrets.toml."
        )

    token = get_api_token()
    if requires_token and not token:
        raise RuntimeError("Enter your API token in the sidebar before using this action.")

    url = f"{base_url}/{endpoint.lstrip('/')}"
    request_params = dict(params or {})
    headers = {}

    if requires_token and token:
        if TOKEN_MODE == "query":
            request_params["token"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"

    response = requests.request(
        method=method.upper(),
        url=url,
        params=request_params,
        json=json,
        headers=headers,
        timeout=25,
    )
    response.raise_for_status()

    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text

def create_product(barcode, price, name, category):
    """Matches the known create-product endpoint pattern and its `bardcode` spelling."""
    return api_request(
        "GET",
        "create-product/",
        params={
            "bardcode": str(barcode),
            "price": price,
            "name": name,
            "category": category,
        },
        requires_token=True,
    )
''',
"pages/1_Sales_POS.py": r'''
import streamlit as st
from api_client import api_request

st.set_page_config(page_title="Sales POS", page_icon="🛒", layout="wide")
st.title("🛒 Sales POS")
st.caption("Billing screen — connect the controls to your existing sales endpoints.")

with st.form("sale_form"):
    st.subheader("Add item to bill")
    barcode = st.text_input("Barcode", placeholder="Scan or enter product barcode")
    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
    add_item = st.form_submit_button("Look up / add item")

if add_item:
    if not barcode.strip():
        st.error("Enter a barcode first.")
    else:
        st.info(
            "Barcode entered. Product lookup is not wired yet because the exact existing "
            "product-search endpoint and response schema have not been supplied in this chat."
        )

st.divider()
st.subheader("Current bill")
st.write("Cart, price calculation, payment recording, stock deduction, and receipt printing will be wired to your existing sales API.")
st.button("Complete sale", disabled=True, help="Enable after connecting the exact sales endpoint.")
''',
"pages/2_Inventory.py": r'''
import streamlit as st
from api_client import create_product

st.set_page_config(page_title="Inventory", page_icon="📦", layout="wide")
st.title("📦 Inventory")
st.caption("Create products through your existing API.")

with st.form("create_product_form"):
    st.subheader("Add new product")
    barcode = st.text_input("Barcode", placeholder="Enter barcode")
    name = st.text_input("Product name", placeholder="e.g. suit")
    category = st.text_input("Category", placeholder="e.g. suit")
    price = st.number_input("Selling price (₹)", min_value=0.0, step=100.0, format="%.2f")
    submitted = st.form_submit_button("Create product")

if submitted:
    if not all([barcode.strip(), name.strip(), category.strip()]) or price <= 0:
        st.error("Enter barcode, product name, category, and a price greater than zero.")
    else:
        try:
            with st.spinner("Creating product..."):
                result = create_product(barcode, price, name, category)
            st.success("API request completed.")
            st.json(result)
        except Exception as exc:
            st.error(f"Product creation failed: {exc}")

st.divider()
st.subheader("Product catalogue")
st.info("Product listing, editing, stock adjustments, and low-stock alerts need the exact endpoint names and response format from your existing API.")
''',
"pages/3_Management.py": r'''
import streamlit as st

st.set_page_config(page_title="Management", page_icon="📊", layout="wide")
st.title("📊 Management")
st.caption("Sales totals, expenses, and end-of-day cash closing.")

col1, col2, col3 = st.columns(3)
col1.metric("Today's sales", "—", help="Connect to sales-summary API")
col2.metric("Expenses", "—", help="Connect to expense API")
col3.metric("Expected closing cash", "—", help="Calculated from opening cash, cash sales, and cash expenses")

st.divider()
tab1, tab2, tab3 = st.tabs(["Daily summary", "Add expense", "Day closing"])

with tab1:
    st.subheader("Daily summary")
    st.info("Sales totals and payment-method breakdown will appear here after connecting the reporting endpoint.")

with tab2:
    st.subheader("Record expense")
    with st.form("expense_form"):
        expense_date = st.date_input("Expense date")
        category = st.selectbox("Category", ["Rent", "Transport", "Food", "Utilities", "Supplies", "Other"])
        amount = st.number_input("Amount (₹)", min_value=0.0, step=50.0)
        note = st.text_input("Note", placeholder="Optional details")
        submitted = st.form_submit_button("Save expense")
    if submitted:
        st.warning("Expense was not saved: connect this form to your existing expense endpoint first.")

with tab3:
    st.subheader("Day closing")
    opening = st.number_input("Opening cash (₹)", min_value=0.0, step=100.0)
    cash_sales = st.number_input("Cash sales (₹)", min_value=0.0, step=100.0)
    cash_expenses = st.number_input("Cash expenses (₹)", min_value=0.0, step=100.0)
    withdrawals = st.number_input("Cash withdrawals (₹)", min_value=0.0, step=100.0)
    expected = opening + cash_sales - cash_expenses - withdrawals
    st.metric("Expected closing cash", f"₹{expected:,.2f}")
    actual = st.number_input("Actual counted closing cash (₹)", min_value=0.0, step=100.0)
    st.metric("Cash difference", f"₹{actual - expected:,.2f}")
    st.button("Save day closing", disabled=True, help="Enable after connecting your existing closing-balance endpoint.")
''',
"requirements.txt": "streamlit>=1.35.0\nrequests>=2.31.0\n",
".gitignore": ".streamlit/secrets.toml\n__pycache__/\n*.py[cod]\n.venv/\n.env\n",
".streamlit/secrets.toml.example": 'API_BASE_URL = "https://YOUR_PROJECT.supabase.co/functions/v1"\n',
"README.md": r'''
# Showroom POS — Streamlit frontend starter

This project is a frontend-only Streamlit app. It calls your existing API and does not create a new backend or database.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set your API base URL:

```toml
API_BASE_URL = "https://YOUR_PROJECT.supabase.co/functions/v1"
```

Then run:

```bash
streamlit run app.py
```

## API token behavior

Enter the API token in the password-style field in the sidebar. The token is held in Streamlit session state and is not saved to a file. Protected API calls are blocked if the field is empty.

The known create-product URL pattern used by this starter sends `token` as a query parameter, matching the previously shared API URL. Confirm this is still how the backend expects authentication. If the backend uses a Bearer header instead, set `TOKEN_MODE = "bearer"` in `api_client.py`.

## Streamlit Cloud

1. Push the project to a private or public GitHub repository.
2. Create a Streamlit Community Cloud app using `app.py`.
3. Add `API_BASE_URL` under App settings → Secrets.
4. Do not commit `.streamlit/secrets.toml`.

## Important implementation status

The known create-product call is wired. Sales lookup/billing, product listing/editing, expense saving, reports, and day closing are intentionally not wired until the exact endpoint paths, HTTP methods, request parameters, and response formats are confirmed. The app does not pretend to save these records until connected.
'''
}

for rel, content in files.items():
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).lstrip())

# Insert a global sidebar token field into each page and app after page config/title context.
# Keep it in each script so users can enter token from any page; session_state shares it across pages.
for rel in ["app.py", "pages/1_Sales_POS.py", "pages/2_Inventory.py", "pages/3_Management.py"]:
    path = os.path.join(root, rel)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    marker = "\n"
    insert = '''
with st.sidebar:
    st.subheader("API access")
    st.text_input(
        "API Token",
        type="password",
        key="api_token",
        placeholder="Enter API token when required",
        help="Protected API actions will not work until a token is entered. The token is not saved to disk.",
    )
'''
    # place after set_page_config line (must be before other Streamlit output)
    lines = content.splitlines(True)
    idx = next(i for i, line in enumerate(lines) if "st.set_page_config" in line)
    lines.insert(idx + 1, insert + "\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

zip_path = "/mnt/data/showroom_pos_streamlit_starter.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            full = os.path.join(dirpath, filename)
            arc = os.path.relpath(full, root)
            z.write(full, arc)

print("Created project files:", len(files))
print("ZIP:", zip_path)

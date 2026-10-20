
import os
import requests
import streamlit as st
from datetime import date

st.set_page_config(
    page_title="Showroom POS",
    page_icon="🛍️",
    layout="wide",
)

# ---------------- CONFIG ----------------
try:
    API_BASE_URL = st.secrets.get("API_BASE_URL", "")
except Exception:
    API_BASE_URL = ""

API_BASE_URL = (
    API_BASE_URL or os.getenv("API_BASE_URL", "")
).rstrip("/")

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("🛍️ Showroom POS")

    page = st.radio(
        "Navigation",
        ["Sales POS", "Inventory", "Management"],
    )

    st.divider()
    st.subheader("API Access")

    api_token = st.text_input(
        "API Token",
        type="password",
        placeholder="Enter API token",
        help="Protected API actions require a valid token.",
    )

# ---------------- API CLIENT ----------------
def api_request(
    method,
    endpoint,
    params=None,
    payload=None,
    requires_token=True,
):
    if not API_BASE_URL:
        raise RuntimeError(
            "API_BASE_URL is missing. Configure it in Streamlit Cloud Secrets."
        )

    if requires_token and not api_token.strip():
        raise RuntimeError(
            "Enter your API token in the sidebar before using this function."
        )

    request_params = dict(params or {})
    headers = {}

    # Your previously shared create-product URL uses ?token=...
    if requires_token:
        request_params["token"] = api_token.strip()

    response = requests.request(
        method=method,
        url=f"{API_BASE_URL}/{endpoint.lstrip('/')}",
        params=request_params,
        json=payload,
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


def show_api_result(result):
    if isinstance(result, (dict, list)):
        st.json(result)
    else:
        st.write(result)


# ---------------- SALES POS ----------------
if page == "Sales POS":
    st.title("🛒 Sales POS")
    st.caption("Showroom billing counter")

    st.subheader("Add product to bill")

    barcode = st.text_input(
        "Barcode",
        placeholder="Scan or enter barcode",
        key="sales_barcode",
    )

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        value=1,
        step=1,
        key="sales_quantity",
    )

    if st.button("Look up product", use_container_width=True):
        st.warning(
            "Product lookup is not connected yet. Configure your existing "
            "product-search endpoint before enabling this action."
        )

    st.divider()
    st.subheader("Current Bill")
    st.info(
        "The cart, totals, payment collection, stock deduction and receipt "
        "will be connected to your existing sales API."
    )

    st.button(
        "Complete Sale",
        disabled=True,
        use_container_width=True,
        help="Enable after connecting the actual sales endpoint.",
    )


# ---------------- INVENTORY ----------------
elif page == "Inventory":
    st.title("📦 Inventory Management")
    st.caption("Create products using your existing API")

    with st.form("create_product_form"):
        barcode = st.text_input(
            "Barcode",
            placeholder="Enter product barcode",
        )
        name = st.text_input(
            "Product Name",
            placeholder="e.g. Suit",
        )
        category = st.text_input(
            "Category",
            placeholder="e.g. Suit",
        )
        price = st.number_input(
            "Selling Price (₹)",
            min_value=0.0,
            step=100.0,
            format="%.2f",
        )

        submitted = st.form_submit_button(
            "Create Product",
            use_container_width=True,
        )

    if submitted:
        if not all([barcode.strip(), name.strip(), category.strip()]):
            st.error("Please fill in the barcode, name and category.")
        elif price <= 0:
            st.error("Price must be greater than zero.")
        elif not api_token.strip():
            st.error("Enter your API token in the sidebar.")
        else:
            try:
                with st.spinner("Creating product..."):
                    result = api_request(
                        "GET",
                        "create-product/",
                        params={
                            "bardcode": barcode.strip(),
                            "price": price,
                            "name": name.strip(),
                            "category": category.strip(),
                        },
                        requires_token=True,
                    )

                st.success("Product API request completed.")
                show_api_result(result)

            except requests.HTTPError as exc:
                st.error(f"API returned an HTTP error: {exc}")
                if exc.response is not None:
                    st.code(exc.response.text[:2000])

            except Exception as exc:
                st.error(f"Product creation failed: {exc}")

    st.divider()
    st.subheader("Product Catalogue")
    st.info(
        "Product listing, editing, stock adjustments and low-stock alerts "
        "require the corresponding existing API endpoint details."
    )


# ---------------- MANAGEMENT ----------------
elif page == "Management":
    st.title("📊 Management")
    st.caption("Daily sales, expenses and closing balance")

    col1, col2, col3 = st.columns(3)

    col1.metric("Today's Sales", "—")
    col2.metric("Today's Expenses", "—")
    col3.metric("Expected Closing Cash", "—")

    st.divider()

    tab1, tab2, tab3 = st.tabs(
        ["Daily Summary", "Add Expense", "Day Closing"]
    )

    with tab1:
        st.subheader("Daily Sales Summary")
        st.info(
            "Connect the existing reporting endpoint to display sales "
            "totals and cash, UPI and card collections."
        )

    with tab2:
        st.subheader("Record Expense")

        with st.form("expense_form"):
            expense_date = st.date_input(
                "Expense Date",
                value=date.today(),
            )

            expense_category = st.selectbox(
                "Category",
                [
                    "Rent",
                    "Salary",
                    "Transport",
                    "Electricity",
                    "Supplies",
                    "Other",
                ],
            )

            expense_amount = st.number_input(
                "Amount (₹)",
                min_value=0.0,
                step=50.0,
            )

            expense_note = st.text_input(
                "Description",
                placeholder="Expense details",
            )

            expense_submitted = st.form_submit_button(
                "Save Expense",
                use_container_width=True,
            )

        if expense_submitted:
            st.warning(
                "Expense not saved. Connect this form to your existing "
                "expense API before using it for real accounts."
            )

    with tab3:
        st.subheader("End-of-Day Closing")

        opening_cash = st.number_input(
            "Opening Cash (₹)",
            min_value=0.0,
            step=100.0,
        )

        cash_sales = st.number_input(
            "Cash Sales (₹)",
            min_value=0.0,
            step=100.0,
        )

        cash_expenses = st.number_input(
            "Cash Expenses (₹)",
            min_value=0.0,
            step=100.0,
        )

        withdrawals = st.number_input(
            "Cash Withdrawals (₹)",
            min_value=0.0,
            step=100.0,
        )

        expected_closing = (
            opening_cash + cash_sales - cash_expenses - withdrawals
        )

        st.metric(
            "Expected Closing Cash",
            f"₹{expected_closing:,.2f}",
        )

        actual_closing = st.number_input(
            "Actual Counted Cash (₹)",
            min_value=0.0,
            step=100.0,
        )

        difference = actual_closing - expected_closing

        st.metric(
            "Cash Difference",
            f"₹{difference:,.2f}",
        )

        st.info(
            "Closing balances are currently calculated on screen only. "
            "Connect your existing closing API to save them permanently."
        )

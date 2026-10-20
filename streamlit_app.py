
import os
import requests
import streamlit as st
import pandas as pd

# =========================================================
# SHOWROOM POS - SINGLE FILE STREAMLIT APP
# =========================================================

st.set_page_config(
    page_title="Showroom POS",
    page_icon="🛍️",
    layout="wide",
)

# Your Supabase Edge Functions base URL.
# You can also set API_BASE_URL in Streamlit Cloud Secrets.
DEFAULT_API_BASE_URL = (
    "https://kkdvzhwrhifjgfnrhxta.supabase.co/functions/v1"
)

try:
    API_BASE_URL = st.secrets.get(
        "API_BASE_URL", DEFAULT_API_BASE_URL
    ).rstrip("/")
except Exception:
    API_BASE_URL = os.getenv(
        "API_BASE_URL", DEFAULT_API_BASE_URL
    ).rstrip("/")


# =========================================================
# SESSION STATE
# =========================================================

if "cart" not in st.session_state:
    st.session_state.cart = []

if "found_product" not in st.session_state:
    st.session_state.found_product = None

if "last_api_result" not in st.session_state:
    st.session_state.last_api_result = None


# =========================================================
# API HELPER
# =========================================================

def api_request(
    method,
    endpoint,
    params=None,
    payload=None,
    requires_token=True,
):
    """Call a Supabase Edge Function and return JSON."""

    token = st.session_state.get("api_token", "").strip()

    if requires_token and not token:
        raise ValueError(
            "Enter your API token in the sidebar before continuing."
        )

    url = f"{API_BASE_URL}/{endpoint.lstrip('/')}"

    query_params = dict(params or {})

    # Existing API uses the custom 'token' query parameter.
    if requires_token:
        query_params["token"] = token

    response = requests.request(
        method=method.upper(),
        url=url,
        params=query_params,
        json=payload,
        timeout=20,
    )

    try:
        data = response.json()
    except ValueError:
        data = {"message": response.text}

    if not response.ok:
        message = (
            data.get("error")
            or data.get("message")
            or data.get("detail")
            or str(data)
        )
        raise RuntimeError(
            f"API returned HTTP {response.status_code}: {message}"
        )

    if isinstance(data, dict) and data.get("success") is False:
        raise RuntimeError(
            data.get("error")
            or data.get("message")
            or "The API reported that the operation failed."
        )

    return data


def money(value):
    try:
        return f"₹{float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🛍️ Showroom POS")
st.sidebar.caption("Sales • Inventory • Management")

page = st.sidebar.radio(
    "Navigation",
    ["Sales POS", "Inventory", "Management"],
)

st.sidebar.divider()
st.sidebar.subheader("API Connection")

st.sidebar.text_input(
    "API Token",
    type="password",
    key="api_token",
    placeholder="Enter your API token",
    help="Used for API requests that require token authentication.",
)

st.sidebar.caption("API URL")
st.sidebar.code(API_BASE_URL, language=None)

if not st.session_state.api_token.strip():
    st.sidebar.warning("Enter your API token to use protected APIs.")
else:
    st.sidebar.success("API token entered")


# =========================================================
# SALES POS
# =========================================================

if page == "Sales POS":
    st.title("Sales POS")
    st.caption("Find products by barcode and prepare a sale.")

    with st.form("product_lookup_form"):
        barcode = st.text_input(
            "Scan or enter product barcode",
            placeholder="e.g. 0001",
        )
        find_product = st.form_submit_button(
            "Find Product",
            type="primary",
            use_container_width=True,
        )

    if find_product:
        if not barcode.strip():
            st.warning("Please enter a barcode.")
        else:
            try:
                result = api_request(
                    "GET",
                    "products/",
                    params={"barcode": barcode.strip()},
                    requires_token=True,
                )

                product = result.get("product")

                if result.get("success") and isinstance(product, dict):
                    st.session_state.found_product = product
                    st.success("Product found.")
                else:
                    st.session_state.found_product = None
                    st.warning("Product was not found.")

            except Exception as exc:
                st.error(f"Product lookup failed: {exc}")

    product = st.session_state.found_product

    if product:
        st.divider()
        st.subheader("Product Details")

        col1, col2, col3 = st.columns(3)

        col1.metric("Product", product.get("name", "Unknown"))
        col2.metric("Price", money(product.get("price")))
        col3.metric("Barcode", str(product.get("barcode", "")))

        st.write("**Category:**", product.get("category") or "—")

        with st.form("add_to_cart_form"):
            quantity = st.number_input(
                "Quantity",
                min_value=1,
                max_value=999,
                value=1,
                step=1,
            )

            add_to_cart = st.form_submit_button(
                "Add to Cart",
                type="primary",
                use_container_width=True,
            )

        if add_to_cart:
            barcode_value = str(product.get("barcode", "")).strip()

            if not barcode_value:
                st.error("The API product response has no barcode.")
            else:
                # Increase quantity if this product is already in the cart.
                existing = next(
                    (
                        item
                        for item in st.session_state.cart
                        if str(item["barcode"]) == barcode_value
                    ),
                    None,
                )

                if existing:
                    existing["quantity"] += int(quantity)
                else:
                    st.session_state.cart.append(
                        {
                            "barcode": barcode_value,
                            "name": product.get("name", "Unknown"),
                            "price": float(product.get("price") or 0),
                            "quantity": int(quantity),
                        }
                    )

                st.success("Product added to cart.")

    st.divider()
    st.subheader("Current Cart")

    cart = st.session_state.cart

    if cart:
        cart_rows = []

        for item in cart:
            cart_rows.append(
                {
                    "Barcode": item["barcode"],
                    "Product": item["name"],
                    "Price": money(item["price"]),
                    "Quantity": item["quantity"],
                    "Subtotal": money(
                        item["price"] * item["quantity"]
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(cart_rows),
            use_container_width=True,
            hide_index=True,
        )

        total = sum(
            item["price"] * item["quantity"]
            for item in cart
        )

        st.metric("Cart Total", money(total))

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Clear Cart", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

        with col2:
            checkout = st.button(
                "Complete Sale",
                type="primary",
                use_container_width=True,
            )

        if checkout:
            if not st.session_state.api_token.strip():
                st.error("Enter your API token in the sidebar.")
            else:
                st.warning(
                    "Checkout sends one request per cart item. "
                    "If a request fails after an earlier item succeeds, "
                    "the sale may be partially processed. Verify your "
                    "sell-product function supports barcode and quantity "
                    "query parameters before using this for real sales."
                )

                completed = []
                failed = []

                progress = st.progress(0)

                for index, item in enumerate(cart):
                    try:
                        # Assumes sell-product accepts these query parameters.
                        # Change this request if your Edge Function expects
                        # a different HTTP method or parameter names.
                        result = api_request(
                            "GET",
                            "sell-product/",
                            params={
                                "barcode": item["barcode"],
                                "quantity": item["quantity"],
                            },
                            requires_token=True,
                        )

                        completed.append(
                            {
                                "product": item["name"],
                                "quantity": item["quantity"],
                                "result": result,
                            }
                        )

                    except Exception as exc:
                        failed.append(
                            f"{item['name']} ({item['barcode']}): {exc}"
                        )

                    progress.progress((index + 1) / len(cart))

                if completed:
                    st.success(
                        f"{len(completed)} cart item(s) processed "
                        "without an API error."
                    )
                    with st.expander("API responses"):
                        for item in completed:
                            st.write(
                                item["product"],
                                "— quantity:",
                                item["quantity"],
                            )
                            st.json(item["result"])

                if failed:
                    st.error("Some checkout requests failed.")
                    for message in failed:
                        st.write(f"- {message}")

                # Clear only if every request succeeded.
                if completed and not failed:
                    st.session_state.cart = []
                    st.session_state.found_product = None
                    st.rerun()

    else:
        st.info("Your cart is empty. Find a product and add it here.")


# =========================================================
# INVENTORY
# =========================================================

elif page == "Inventory":
    st.title("Inventory")
    st.caption("Create a product in your Supabase database.")

    st.subheader("Add New Product")

    with st.form("create_product_form", clear_on_submit=False):
        new_barcode = st.text_input(
            "Barcode",
            placeholder="e.g. 0002",
        )

        new_name = st.text_input(
            "Product Name",
            placeholder="e.g. Men's suit",
        )

        new_price = st.number_input(
            "Price (₹)",
            min_value=0.0,
            value=0.0,
            step=100.0,
        )

        new_category = st.text_input(
            "Category",
            placeholder="e.g. suit",
        )

        create_product = st.form_submit_button(
            "Create Product",
            type="primary",
            use_container_width=True,
        )

    if create_product:
        if not new_barcode.strip():
            st.warning("Barcode is required.")
        elif not new_name.strip():
            st.warning("Product name is required.")
        elif not new_category.strip():
            st.warning("Category is required.")
        else:
            try:
                # Your previously supplied create-product URL used
                # the parameter spelling 'bardcode'.
                result = api_request(
                    "GET",
                    "create-product/",
                    params={
                        "bardcode": new_barcode.strip(),
                        "price": new_price,
                        "name": new_name.strip(),
                        "category": new_category.strip(),
                    },
                    requires_token=True,
                )

                st.success("Create-product API request succeeded.")
                st.json(result)

            except Exception as exc:
                st.error(f"Product creation failed: {exc}")

    st.divider()
    st.subheader("Find Existing Product")

    with st.form("inventory_lookup_form"):
        inventory_barcode = st.text_input(
            "Barcode to look up",
            placeholder="e.g. 0001",
        )

        inventory_lookup = st.form_submit_button("Look Up Product")

    if inventory_lookup:
        if not inventory_barcode.strip():
            st.warning("Enter a barcode.")
        else:
            try:
                result = api_request(
                    "GET",
                    "products/",
                    params={"barcode": inventory_barcode.strip()},
                    requires_token=True,
                )

                if result.get("success") and result.get("product"):
                    st.json(result["product"])
                else:
                    st.warning("Product was not found.")

            except Exception as exc:
                st.error(f"Inventory lookup failed: {exc}")

    st.info(
        "The product creation request uses the 'bardcode' parameter "
        "from your existing API URL. Product lookup uses 'barcode'."
    )


# =========================================================
# MANAGEMENT
# =========================================================

elif page == "Management":
    st.title("Management")
    st.caption("API diagnostics and management tools.")

    st.subheader("Test Product API")

    test_barcode = st.text_input(
        "Barcode for API test",
        value="0001",
        key="management_test_barcode",
    )

    if st.button("Test API Connection", type="primary"):
        if not test_barcode.strip():
            st.warning("Enter a barcode to test.")
        else:
            try:
                result = api_request(
                    "GET",
                    "products/",
                    params={"barcode": test_barcode.strip()},
                    requires_token=True,
                )

                st.success("The products endpoint responded successfully.")
                st.json(result)

            except Exception as exc:
                st.error(f"API test failed: {exc}")

    st.divider()
    st.subheader("Additional Management Features")

    st.info(
        "Sales reports, expenses, cash closing, and product updates "
        "are not connected yet. These require the exact request formats "
        "and response structures of your existing Supabase functions."
    )

    st.caption(
        "Available endpoint names in this app: products, create-product, "
        "sell-product. The update-product endpoint has not been wired "
        "because its required parameters have not been confirmed."
    )


# =========================================================
# FOOTER
# =========================================================

st.sidebar.divider()
st.sidebar.caption("Showroom POS • Supabase API")

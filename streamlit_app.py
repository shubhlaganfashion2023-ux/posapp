
import os
import requests
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Showroom POS",
    page_icon="🛍️",
    layout="wide",
)

# -------------------- CONFIG --------------------

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


# -------------------- SESSION STATE --------------------

if "cart" not in st.session_state:
    st.session_state.cart = []

if "found_product" not in st.session_state:
    st.session_state.found_product = None


# -------------------- API HELPER --------------------

def api_request(
    method,
    endpoint,
    params=None,
    payload=None,
    requires_token=False,
):
    """
    Public read requests do not require a token.
    Protected create, update, and sale requests do.
    """
    token = st.session_state.get("api_token", "").strip()

    if requires_token and not token:
        raise ValueError(
            "Enter your API token in the sidebar first."
        )

    url = f"{API_BASE_URL}/{endpoint.lstrip('/')}"
    query_params = dict(params or {})

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
            or "API operation failed."
        )

    return data


def money(value):
    try:
        return f"₹{float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


def lookup_product(barcode):
    """
    Public product lookup: NO TOKEN is sent.
    Confirmed endpoint: /products/?barcode=0001
    """
    return api_request(
        "GET",
        "products/",
        params={"barcode": barcode.strip()},
        requires_token=False,
    )


# -------------------- SIDEBAR --------------------

st.sidebar.title("🛍️ Showroom POS")

page = st.sidebar.radio(
    "Navigation",
    ["Sales POS", "Inventory", "Management"],
)

st.sidebar.divider()
st.sidebar.subheader("API Settings")

st.sidebar.text_input(
    "API Token",
    type="password",
    key="api_token",
    placeholder="Enter API token",
    help="Required only for protected operations.",
)

st.sidebar.caption("Product lookup does not require this token.")


# ==================================================
# SALES POS
# ==================================================

if page == "Sales POS":
    st.title("Sales POS")
    st.caption("Search products and create customer sales.")

    # Customer details
    st.subheader("Customer Details")

    customer_name = st.text_input(
        "Customer Name *",
        key="sale_customer_name",
        placeholder="Enter customer name",
    )

    customer_number = st.text_input(
        "Customer Phone Number *",
        key="sale_customer_number",
        placeholder="Enter customer phone number",
    )

    st.divider()
    st.subheader("Find Product")

    with st.form("product_lookup_form"):
        barcode = st.text_input(
            "Scan or enter barcode",
            placeholder="e.g. 0001",
        )
        find_product = st.form_submit_button(
            "Find Product",
            type="primary",
            use_container_width=True,
        )

    if find_product:
        if not barcode.strip():
            st.warning("Enter a barcode.")
        else:
            try:
                result = lookup_product(barcode)

                product = result.get("product")

                if result.get("success") and isinstance(product, dict):
                    st.session_state.found_product = product
                    st.success("Product found.")
                else:
                    st.session_state.found_product = None
                    st.warning("Product not found.")

            except Exception as exc:
                st.error(f"Product lookup failed: {exc}")

    product = st.session_state.found_product

    if product:
        st.divider()
        st.subheader("Product Details")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Product",
            product.get("name") or "Unknown",
        )
        col2.metric(
            "Price",
            money(product.get("price")),
        )
        col3.metric(
            "Barcode",
            str(product.get("barcode") or ""),
        )

        st.write("**Category:**", product.get("category") or "—")

        with st.form("add_to_cart_form"):
            quantity = st.number_input(
                "Quantity",
                min_value=1,
                max_value=999,
                value=1,
                step=1,
            )

            add_item = st.form_submit_button(
                "Add to Cart",
                use_container_width=True,
            )

        if add_item:
            product_barcode = str(
                product.get("barcode") or ""
            ).strip()

            if not product_barcode:
                st.error("The product response does not contain a barcode.")
            else:
                existing = next(
                    (
                        item for item in st.session_state.cart
                        if item["barcode"] == product_barcode
                    ),
                    None,
                )

                if existing:
                    existing["quantity"] += int(quantity)
                else:
                    st.session_state.cart.append({
                        "barcode": product_barcode,
                        "name": product.get("name") or "Unknown",
                        "price": float(product.get("price") or 0),
                        "quantity": int(quantity),
                    })

                st.success("Added to cart.")

    # -------------------- CART --------------------

    st.divider()
    st.subheader("Current Cart")

    cart = st.session_state.cart

    if not cart:
        st.info("Cart is empty. Find a product to add it.")
    else:
        rows = []

        for item in cart:
            rows.append({
                "Barcode": item["barcode"],
                "Product": item["name"],
                "Price": money(item["price"]),
                "Quantity": item["quantity"],
                "Subtotal": money(
                    item["price"] * item["quantity"]
                ),
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

        total = sum(
            item["price"] * item["quantity"]
            for item in cart
        )

        st.metric("Total Amount", money(total))

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Clear Cart", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

        with col2:
            complete_sale = st.button(
                "Complete Sale",
                type="primary",
                use_container_width=True,
            )

        if complete_sale:
            if not customer_name.strip():
                st.error("Customer name is required.")
            elif not customer_number.strip():
                st.error("Customer phone number is required.")
            elif not st.session_state.api_token.strip():
                st.error("Enter your API token in the sidebar.")
            else:
                # The existing API returned "customer_name is required".
                # These customer details are sent with every sale request.
                completed = []
                failures = []

                progress = st.progress(0)

                for index, item in enumerate(cart):
                    try:
                        result = api_request(
                            "GET",
                            "sell-product/",
                            params={
                                "barcode": item["barcode"],
                                "quantity": item["quantity"],
                                "customer_name": customer_name.strip(),
                                "customer_number": customer_number.strip(),
                            },
                            requires_token=True,
                        )

                        completed.append({
                            "name": item["name"],
                            "quantity": item["quantity"],
                            "result": result,
                        })

                    except Exception as exc:
                        failures.append(
                            f"{item['name']} ({item['barcode']}): {exc}"
                        )

                    progress.progress((index + 1) / len(cart))

                if completed:
                    st.success(
                        f"{len(completed)} sale request(s) succeeded."
                    )

                    with st.expander("Sale API responses"):
                        for item in completed:
                            st.write(
                                f"{item['name']} — "
                                f"quantity {item['quantity']}"
                            )
                            st.json(item["result"])

                if failures:
                    st.error("Some sale requests failed.")
                    for failure in failures:
                        st.write(f"- {failure}")

                    st.warning(
                        "Check your API/database before retrying. "
                        "Some cart items may already have been sold."
                    )

                if completed and not failures:
                    st.session_state.cart = []
                    st.session_state.found_product = None
                    st.success("All cart requests completed.")
                    st.rerun()


# ==================================================
# INVENTORY
# ==================================================

elif page == "Inventory":
    st.title("Inventory")

    st.subheader("Create Product")
    st.caption("Creating a product requires your API token.")

    with st.form("create_product_form"):
        barcode_new = st.text_input(
            "Barcode",
            placeholder="e.g. 0002",
        )

        name_new = st.text_input(
            "Product Name",
            placeholder="Enter product name",
        )

        price_new = st.number_input(
            "Price (₹)",
            min_value=0.0,
            value=0.0,
            step=100.0,
        )

        category_new = st.text_input(
            "Category",
            placeholder="e.g. suit",
        )

        create_clicked = st.form_submit_button(
            "Create Product",
            type="primary",
            use_container_width=True,
        )

    if create_clicked:
        if not barcode_new.strip():
            st.warning("Barcode is required.")
        elif not name_new.strip():
            st.warning("Product name is required.")
        elif not category_new.strip():
            st.warning("Category is required.")
        elif not st.session_state.api_token.strip():
            st.error("Enter your API token in the sidebar.")
        else:
            try:
                result = api_request(
                    "GET",
                    "create-product/",
                    params={
                        # Retaining spelling from your existing endpoint URL.
                        "bardcode": barcode_new.strip(),
                        "price": price_new,
                        "name": name_new.strip(),
                        "category": category_new.strip(),
                    },
                    requires_token=True,
                )

                st.success("Create-product request succeeded.")
                st.json(result)

            except Exception as exc:
                st.error(f"Product creation failed: {exc}")

    st.divider()
    st.subheader("Find Product")
    st.caption("Product lookup is public and does not require a token.")

    with st.form("inventory_lookup_form"):
        inventory_barcode = st.text_input(
            "Barcode to find",
            placeholder="e.g. 0001",
        )
        inventory_find = st.form_submit_button("Find Product")

    if inventory_find:
        if not inventory_barcode.strip():
            st.warning("Enter a barcode.")
        else:
            try:
                result = lookup_product(inventory_barcode)

                if result.get("success") and result.get("product"):
                    st.json(result["product"])
                else:
                    st.warning("Product not found.")

            except Exception as exc:
                st.error(f"Product lookup failed: {exc}")

    st.divider()
    st.subheader("Update Product")

    st.info(
        "The update-product API has not been wired yet because "
        "its required parameters have not been confirmed. Any "
        "update request will require the API token."
    )


# ==================================================
# MANAGEMENT
# ==================================================

elif page == "Management":
    st.title("Management")

    st.subheader("Test Product Lookup")
    st.caption("This read-only test does not require a token.")

    test_barcode = st.text_input(
        "Barcode to test",
        value="0001",
        key="management_test_barcode",
    )

    if st.button("Test Product API", type="primary"):
        if not test_barcode.strip():
            st.warning("Enter a barcode.")
        else:
            try:
                result = lookup_product(test_barcode)
                st.success("Product API responded.")
                st.json(result)

            except Exception as exc:
                st.error(f"Product API test failed: {exc}")

    st.divider()
    st.subheader("Management Features")

    st.info(
        "Sales reports, expenses, cash closing, and product updates "
        "still need to be connected to their corresponding API functions."
    )


# -------------------- FOOTER --------------------

st.sidebar.divider()
st.sidebar.caption("Showroom POS • Supabase")

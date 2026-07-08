from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"
CATEGORIES = ["avtokredit", "mikroqarz", "kredit_karta", "istemol_krediti"]


def fetch_products(category: str) -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/products", params={"category": category}, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_recommendation(category: str, amount_som: int, term_months: int, collateral_ok: bool) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/recommend",
        json={
            "category": category,
            "amount_som": amount_som,
            "term_months": term_months,
            "collateral_ok": collateral_ok,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


st.title("Bank Mahsulotlari Bozor Tahlili")

category = st.selectbox("Kategoriya", CATEGORIES)

st.subheader("Mavjud mahsulotlar")
products = fetch_products(category)
if products:
    st.dataframe(products)
else:
    st.info("Bu kategoriya uchun hozircha ma'lumot yo'q.")

st.subheader("Tavsiya olish")
with st.form("recommend_form"):
    amount_som = st.number_input("Summa (so'm)", min_value=1_000_000, step=1_000_000, value=50_000_000)
    term_months = st.number_input("Muddat (oy)", min_value=1, max_value=120, value=12)
    collateral_ok = st.checkbox("Garov taqdim eta olaman", value=False)
    submitted = st.form_submit_button("Tavsiya olish")

if submitted:
    result = fetch_recommendation(category, int(amount_som), int(term_months), collateral_ok)
    for item in result["recommendations"]:
        st.write(f"**{item['bank']}** — {item['product_name']} (ball: {item['score']})")
    st.write(result["explanation"])

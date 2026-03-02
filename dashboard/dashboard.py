import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Загрузка .env (локально) или secrets (Streamlit Cloud)
load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

st.set_page_config(
    page_title="Рынок керамической плитки России",
    page_icon="🪟",
    layout="wide",
)

# ─── Загрузка данных ────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Supabase возвращает максимум 1000 строк — читаем постранично
    all_rows = []
    page = 0
    page_size = 1000
    while True:
        response = (
            client.table("tiles")
            .select("*")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )
        rows = response.data
        if not rows:
            break
        all_rows.extend(rows)
        page += 1
    df = pd.DataFrame(all_rows)
    # Нормализация типов
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["discount"] = pd.to_numeric(df["discount"], errors="coerce")
    df["thickness"] = pd.to_numeric(df["thickness"], errors="coerce")
    df["total_stock"] = pd.to_numeric(df["total_stock"], errors="coerce")
    df["total_stock_units"] = pd.to_numeric(df["total_stock_units"], errors="coerce")
    return df

df = load_data()

# ─── Заголовок ──────────────────────────────────────────────────────────────

st.title("Рынок керамической плитки России")
st.caption(
    f"Данные: {df['store'].nunique()} магазина  •  "
    f"{len(df):,} позиций  •  "
    f"Дата обновления: {df['date'].max()}"
)

# ─── Сайдбар — фильтры ──────────────────────────────────────────────────────

with st.sidebar:
    st.header("Фильтры")

    stores = st.multiselect(
        "Магазин",
        options=sorted(df["store"].dropna().unique()),
        default=sorted(df["store"].dropna().unique()),
    )

    materials = st.multiselect(
        "Материал",
        options=sorted(df["material"].dropna().unique()),
        default=sorted(df["material"].dropna().unique()),
    )

    surface_types = st.multiselect(
        "Тип поверхности",
        options=sorted(df["surface_type"].dropna().unique()),
        default=sorted(df["surface_type"].dropna().unique()),
    )

    price_min = int(df["price"].dropna().min())
    price_max = int(df["price"].dropna().max())
    price_range = st.slider(
        "Цена, руб/м² (или шт.)",
        min_value=price_min,
        max_value=price_max,
        value=(price_min, min(price_max, 5000)),
        step=100,
    )

    only_with_price = st.checkbox("Только с ценой", value=True)
    only_with_stock = st.checkbox("Только с остатками", value=False)

# ─── Применение фильтров ────────────────────────────────────────────────────

filtered = df.copy()

if stores:
    filtered = filtered[filtered["store"].isin(stores)]
if materials:
    filtered = filtered[filtered["material"].isin(materials)]
if surface_types:
    filtered = filtered[filtered["surface_type"].isin(surface_types)]
if only_with_price:
    filtered = filtered[filtered["price"].notna()]
    filtered = filtered[filtered["price"].between(price_range[0], price_range[1])]
if only_with_stock:
    filtered = filtered[filtered["total_stock"].notna() & (filtered["total_stock"] > 0)]

# ─── KPI метрики ────────────────────────────────────────────────────────────

st.subheader("Обзор рынка")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Позиций", f"{len(filtered):,}")
k2.metric("Брендов", filtered["brand"].nunique())
k3.metric(
    "Средняя цена",
    f"{filtered['price'].mean():.0f} ₽" if filtered["price"].notna().any() else "—",
)
k4.metric(
    "Медианная цена",
    f"{filtered['price'].median():.0f} ₽" if filtered["price"].notna().any() else "—",
)
k5.metric(
    "Со скидкой",
    f"{filtered['discount'].notna().sum():,}",
)

st.divider()

# ─── Раздел 1: Цены ─────────────────────────────────────────────────────────

st.subheader("Распределение цен")

col_a, col_b = st.columns(2)

with col_a:
    fig = px.box(
        filtered[filtered["price"].notna()],
        x="store",
        y="price",
        color="store",
        title="Цены по магазинам (box plot)",
        labels={"store": "Магазин", "price": "Цена, руб."},
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    fig2 = px.histogram(
        filtered[filtered["price"].notna()],
        x="price",
        nbins=60,
        color="store",
        barmode="overlay",
        opacity=0.7,
        title="Гистограмма цен",
        labels={"price": "Цена, руб.", "count": "Кол-во"},
    )
    st.plotly_chart(fig2, use_container_width=True)

# ─── Раздел 2: Магазины и материалы ─────────────────────────────────────────

st.subheader("Структура ассортимента")

col_c, col_d, col_e = st.columns(3)

with col_c:
    store_counts = filtered["store"].value_counts().reset_index()
    store_counts.columns = ["store", "count"]
    fig3 = px.pie(
        store_counts,
        names="store",
        values="count",
        title="Доля позиций по магазинам",
    )
    fig3.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    mat_counts = filtered["material"].value_counts().reset_index()
    mat_counts.columns = ["material", "count"]
    fig4 = px.pie(
        mat_counts,
        names="material",
        values="count",
        title="Доля по материалам",
    )
    fig4.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig4, use_container_width=True)

with col_e:
    surf_counts = (
        filtered["surface_type"]
        .value_counts()
        .head(8)
        .reset_index()
    )
    surf_counts.columns = ["surface_type", "count"]
    fig5 = px.bar(
        surf_counts,
        x="count",
        y="surface_type",
        orientation="h",
        title="Топ типов поверхности",
        labels={"surface_type": "", "count": "Кол-во"},
    )
    fig5.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig5, use_container_width=True)

# ─── Раздел 3: Бренды ───────────────────────────────────────────────────────

st.subheader("Бренды")

col_f, col_g = st.columns([2, 1])

with col_f:
    top_n = st.slider("Показать топ-N брендов", 5, 30, 15)
    top_brands = (
        filtered.groupby("brand")
        .agg(
            count=("name", "count"),
            avg_price=("price", "mean"),
        )
        .sort_values("count", ascending=False)
        .head(top_n)
        .reset_index()
    )
    fig6 = px.bar(
        top_brands,
        x="brand",
        y="count",
        color="avg_price",
        color_continuous_scale="RdYlGn_r",
        title=f"Топ-{top_n} брендов по количеству позиций",
        labels={"brand": "Бренд", "count": "Позиций", "avg_price": "Ср. цена"},
    )
    fig6.update_xaxes(tickangle=45)
    st.plotly_chart(fig6, use_container_width=True)

with col_g:
    brand_price = (
        filtered.groupby("brand")["price"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    brand_price.columns = ["brand", "avg_price"]
    brand_price["avg_price"] = brand_price["avg_price"].round(0)
    fig7 = px.bar(
        brand_price,
        x="avg_price",
        y="brand",
        orientation="h",
        title="Топ-10 брендов по средней цене",
        labels={"brand": "", "avg_price": "Ср. цена, руб."},
    )
    fig7.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig7, use_container_width=True)

# ─── Раздел 4: Форматы и дизайн ─────────────────────────────────────────────

st.subheader("Форматы и дизайн")

col_h, col_i = st.columns(2)

with col_h:
    top_formats = (
        filtered["format"]
        .value_counts()
        .head(15)
        .reset_index()
    )
    top_formats.columns = ["format", "count"]
    fig8 = px.bar(
        top_formats,
        x="format",
        y="count",
        title="Топ форматов плитки",
        labels={"format": "Формат (см)", "count": "Кол-во"},
    )
    fig8.update_xaxes(tickangle=45)
    st.plotly_chart(fig8, use_container_width=True)

with col_i:
    top_designs = (
        filtered["primary_design"]
        .dropna()
        .value_counts()
        .head(12)
        .reset_index()
    )
    top_designs.columns = ["design", "count"]
    fig9 = px.bar(
        top_designs,
        x="count",
        y="design",
        orientation="h",
        title="Топ дизайнов (основной)",
        labels={"design": "", "count": "Кол-во"},
    )
    fig9.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig9, use_container_width=True)

# ─── Раздел 5: Страны ───────────────────────────────────────────────────────

st.subheader("Страны производства")

country_counts = (
    filtered.groupby("country")
    .agg(count=("name", "count"), avg_price=("price", "mean"))
    .sort_values("count", ascending=False)
    .head(15)
    .reset_index()
)

fig10 = px.bar(
    country_counts,
    x="country",
    y="count",
    color="avg_price",
    color_continuous_scale="Blues",
    title="Количество позиций по стране производства",
    labels={"country": "Страна", "count": "Позиций", "avg_price": "Ср. цена"},
)
fig10.update_xaxes(tickangle=30)
st.plotly_chart(fig10, use_container_width=True)

# ─── Раздел 6: Остатки (только где есть) ────────────────────────────────────

st.subheader("Остатки")

df_stock = filtered[filtered["total_stock"].notna() & (filtered["total_stock"] > 0)]

if len(df_stock) > 0:
    col_j, col_k = st.columns(2)

    with col_j:
        stock_by_store = (
            df_stock.groupby("store")["total_stock"]
            .sum()
            .reset_index()
        )
        fig11 = px.pie(
            stock_by_store,
            names="store",
            values="total_stock",
            title="Объём остатков по магазинам (м²/шт.)",
        )
        st.plotly_chart(fig11, use_container_width=True)

    with col_k:
        stock_by_mat = (
            df_stock.groupby("material")["total_stock"]
            .sum()
            .reset_index()
        )
        fig12 = px.bar(
            stock_by_mat,
            x="material",
            y="total_stock",
            title="Остатки по материалам",
            labels={"material": "Материал", "total_stock": "Остаток (м²/шт.)"},
        )
        st.plotly_chart(fig12, use_container_width=True)
else:
    st.info("Нет данных об остатках для выбранных фильтров.")

# ─── Раздел 7: Таблица данных ────────────────────────────────────────────────

st.subheader("Данные")

DISPLAY_COLS = [
    "name", "store", "price", "price_unit", "discount",
    "material", "format", "primary_design", "primary_color",
    "surface_type", "brand", "country", "availability",
    "total_stock", "url",
]

show_cols = [c for c in DISPLAY_COLS if c in filtered.columns]

st.dataframe(
    filtered[show_cols].reset_index(drop=True),
    use_container_width=True,
    column_config={
        "url": st.column_config.LinkColumn("Ссылка"),
        "price": st.column_config.NumberColumn("Цена", format="%.0f ₽"),
        "discount": st.column_config.NumberColumn("Скидка", format="%.0f%%"),
        "total_stock": st.column_config.NumberColumn("Остаток"),
    },
)

st.caption(f"Показано {len(filtered):,} из {len(df):,} записей")

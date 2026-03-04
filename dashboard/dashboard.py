import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from pathlib import Path
from io import BytesIO
from dotenv import load_dotenv
from supabase import create_client

# Загрузка .env (локально) или secrets (Streamlit Cloud)
load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

KERAMIN_BRAND    = "КЕРАМИН"
STORES_WITH_STOCK = ["LemanaPRO", "OBI", "Petrovich"]
COLOR_KERAMIN    = "#E63946"
COLOR_MARKET     = "#457B9D"
KEY_COUNTRIES    = [
    "Азербайджан", "Беларусь", "Индия", "Иран",
    "Казахстан", "Китай", "Кыргызстан", "Россия", "Узбекистан",
]
KEY_FORMATS      = [
    "120x60", "60x60", "60x30", "40x40", "30x30",
    "90x30", "40x25", "30x10", "25x5",
]
MATERIAL_FORMATS = {
    "Керамика":     ["90x30", "60x30", "40x25"],
    "Керамогранит": ["120x60", "60x60", "60x30", "40x40", "30x30"],
    "Клинкер":      ["40x40", "30x30", "25x5"],
}

st.set_page_config(
    page_title="Рынок керамической плитки России",
    page_icon="🪟",
    layout="wide",
)

# ─── Загрузка данных ────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
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
    df["price"]             = pd.to_numeric(df["price"], errors="coerce")
    df["discount"]          = pd.to_numeric(df["discount"], errors="coerce")
    df["thickness"]         = pd.to_numeric(df["thickness"], errors="coerce")
    df["total_stock"]       = pd.to_numeric(df["total_stock"], errors="coerce")
    df["total_stock_units"] = pd.to_numeric(df["total_stock_units"], errors="coerce")
    # Глобальный фильтр: только цены за м²
    df = df[df["price"].notna() & (df["price_unit"] == "м²")]
    return df

df = load_data()

# ─── Заголовок ──────────────────────────────────────────────────────────────

st.title("Рынок керамической плитки России")
st.caption(
    f"Данные: {df['store'].nunique()} магазина  •  "
    f"{len(df):,} позиций (цена за м²)  •  "
    f"Дата обновления: {df['date'].max()}"
)

# ─── Session state и callbacks ───────────────────────────────────────────────

_price_min_default = int(df["price"].min())
for _k, _v in [("pr_lo", _price_min_default), ("pr_hi", 3000), ("disc_max", 30)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

def _on_price_slider():
    lo, hi = st.session_state["_price_slider"]
    st.session_state.pr_lo = lo
    st.session_state.pr_hi = hi

def _on_disc_slider():
    st.session_state.disc_max = st.session_state["_disc_slider"]

# ─── Сайдбар — фильтры ──────────────────────────────────────────────────────

with st.sidebar:
    st.header("Фильтры")

    st.markdown("**Магазин**")
    store_counts = df["store"].value_counts()
    stores = [
        s for s in sorted(df["store"].dropna().unique())
        if st.checkbox(f"{s}  ({store_counts.get(s, 0):,})", value=True, key=f"store_{s}")
    ]

    all_formats_list = sorted(df["format"].dropna().unique())
    key_formats_only = st.checkbox("Только ключевые форматы", value=True)

    st.markdown("**Материал**")
    material_counts = df["material"].value_counts()
    materials = []
    sub_format_selections = {}
    for m in sorted(df["material"].dropna().unique()):
        if st.checkbox(f"{m}  ({material_counts.get(m, 0):,})", value=True, key=f"mat_{m}"):
            materials.append(m)
        if key_formats_only and m in MATERIAL_FORMATS:
            mat_fmt_opts = [f for f in MATERIAL_FORMATS[m] if f in all_formats_list]
            if mat_fmt_opts:
                sel = st.pills(
                    "", options=mat_fmt_opts, selection_mode="multi", default=[],
                    label_visibility="collapsed", key=f"sub_fmt_{m}",
                )
                sub_format_selections[m] = list(sel) if sel else []

    st.markdown("**Тип поверхности**")
    sf_opts = sorted(df["surface_finish"].dropna().replace("", pd.NA).dropna().unique())
    sf_counts = df["surface_finish"].value_counts()
    surface_finishes = [
        s for s in sf_opts
        if st.checkbox(f"{s}  ({sf_counts.get(s, 0):,})", value=True, key=f"sf_{s}")
    ]

    st.markdown("**Формат**")
    if key_formats_only:
        fmt_opts = [f for f in KEY_FORMATS if f in all_formats_list]
        formats = st.pills(
            "", options=fmt_opts, selection_mode="multi", default=fmt_opts,
            label_visibility="collapsed",
        )
    else:
        formats = st.multiselect("", options=all_formats_list, placeholder="Все форматы",
                                 label_visibility="collapsed")

    designs = st.multiselect(
        "Дизайн",
        options=sorted(df["primary_design"].dropna().unique()),
        placeholder="Все дизайны",
    )

    st.markdown("**Страна производства**")
    country_mode = st.radio(
        "", ["Ключевые страны", "Все страны"],
        horizontal=True, key="country_mode", label_visibility="collapsed",
    )
    all_countries_list = sorted(df["country"].dropna().unique())
    if country_mode == "Ключевые страны":
        country_opts = [c for c in KEY_COUNTRIES if c in all_countries_list]
        countries = st.pills(
            "Страны", options=country_opts, selection_mode="multi", default=country_opts,
            label_visibility="collapsed",
        )
    else:
        countries = st.multiselect(
            "Страна", options=all_countries_list, default=all_countries_list,
        )

    st.markdown("**Цена, руб/м²**")
    st.slider(
        "", 0, 12000,
        (st.session_state.pr_lo, st.session_state.pr_hi),
        step=100, key="_price_slider",
        on_change=_on_price_slider,
        label_visibility="collapsed",
    )
    pc1, pc2 = st.columns(2)
    new_lo = pc1.number_input("от ₽", 0, 12000, st.session_state.pr_lo, step=100)
    new_hi = pc2.number_input("до ₽", 0, 12000, st.session_state.pr_hi, step=100)
    if int(new_lo) != st.session_state.pr_lo or int(new_hi) != st.session_state.pr_hi:
        lo_v, hi_v = int(new_lo), int(new_hi)
        if lo_v > hi_v:
            lo_v, hi_v = hi_v, lo_v
        st.session_state.pr_lo = lo_v
        st.session_state.pr_hi = hi_v
        st.session_state["_price_slider"] = (lo_v, hi_v)
        st.rerun()
    price_range = (st.session_state.pr_lo, st.session_state.pr_hi)

    st.markdown("**Макс. скидка, %**")
    st.slider(
        "", 0, 100, st.session_state.disc_max,
        step=5, key="_disc_slider",
        on_change=_on_disc_slider,
        label_visibility="collapsed",
        help="Исключить товары со скидкой выше указанного. Товары без скидки всегда включаются.",
    )
    new_disc = st.number_input("значение, %", 0, 100, st.session_state.disc_max, step=5)
    if int(new_disc) != st.session_state.disc_max:
        st.session_state.disc_max = int(new_disc)
        st.session_state["_disc_slider"] = int(new_disc)
        st.rerun()
    max_discount = st.session_state.disc_max

    only_with_stock = st.checkbox(
        "Только с остатками",
        value=False,
        help="Анализируются только DIY-сети: Lemana PRO, OBI, Petrovich",
    )

    st.divider()
    st.caption(f"КЕРАМИН выделен красным на всех графиках")

# ─── Применение фильтров ────────────────────────────────────────────────────

filtered = df.copy()

if stores:
    filtered = filtered[filtered["store"].isin(stores)]

# Материал × формат: если выбраны sub-format pills — cross-фильтр, иначе обычные фильтры
_any_sub = any(len(v) > 0 for v in sub_format_selections.values())
if _any_sub:
    cross = pd.Series(False, index=filtered.index)
    for mat, fmts in sub_format_selections.items():
        if fmts and mat in materials:
            cross |= (filtered["material"] == mat) & (filtered["format"].isin(fmts))
    filtered = filtered[cross]
else:
    if materials:
        filtered = filtered[filtered["material"].isin(materials)]
    if formats:
        filtered = filtered[filtered["format"].isin(formats)]

if surface_finishes:
    filtered = filtered[filtered["surface_finish"].isin(surface_finishes)]
if designs:
    filtered = filtered[filtered["primary_design"].isin(designs)]
if countries:
    filtered = filtered[filtered["country"].isin(countries)]

filtered = filtered[filtered["price"].between(price_range[0], price_range[1])]
# Товары без скидки оставляем, со скидкой > порога — исключаем
filtered = filtered[filtered["discount"].isna() | (filtered["discount"] <= max_discount)]

if only_with_stock:
    filtered = filtered[filtered["total_stock"].notna() & (filtered["total_stock"] > 0)]

df_keramin = filtered[filtered["brand"] == KERAMIN_BRAND]
df_market  = filtered[filtered["brand"] != KERAMIN_BRAND]

# ─── ХЕЛПЕР: средневзвешенная цена ──────────────────────────────────────────

def weighted_avg_price(group: pd.DataFrame) -> float:
    g = group[group["total_stock"].notna() & (group["total_stock"] > 0)]
    if len(g) == 0 or g["total_stock"].sum() == 0:
        return group["price"].mean()
    return (g["price"] * g["total_stock"]).sum() / g["total_stock"].sum()

# ─── ХЕЛПЕР: экспорт в Excel ────────────────────────────────────────────────

def to_excel(data: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Данные")
    return buf.getvalue()

def download_button(data: pd.DataFrame, filename: str, label: str = "Скачать Excel"):
    st.download_button(
        label=label,
        data=to_excel(data),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ─── ТАБЫ ────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Обзор рынка",
    "Позиция КЕРАМИН",
    "Средневзвешенная цена",
    "Угрозы: скидки",
    "Поиск аналогов",
    "Данные",
])

# ════════════════════════════════════════════════════════════════════════════
# ТАБ 1 — ОБЗОР РЫНКА
# ════════════════════════════════════════════════════════════════════════════

with tab1:
    st.subheader("Обзор рынка")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Позиций", f"{len(filtered):,}")
    k2.metric("Брендов", filtered["brand"].nunique())
    k3.metric("Средняя цена",   f"{filtered['price'].mean():.0f} ₽"   if len(filtered) > 0 else "—")
    k4.metric("Медианная цена", f"{filtered['price'].median():.0f} ₽" if len(filtered) > 0 else "—")
    k5.metric("Со скидкой", f"{filtered['discount'].notna().sum():,}")

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.box(
            filtered, x="store", y="price", color="store",
            title="Распределение цен по магазинам",
            labels={"store": "Магазин", "price": "Цена, руб/м²"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        fig2 = px.histogram(
            filtered, x="price", nbins=60, color="store",
            barmode="overlay", opacity=0.7,
            title="Гистограмма цен",
            labels={"price": "Цена, руб/м²"},
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Структура ассортимента")
    col_c, col_d, col_e = st.columns(3)

    with col_c:
        sc = filtered["store"].value_counts().reset_index()
        sc.columns = ["store", "count"]
        fig3 = px.pie(sc, names="store", values="count", title="Доля по магазинам")
        fig3.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        mc = filtered["material"].value_counts().reset_index()
        mc.columns = ["material", "count"]
        fig4 = px.pie(mc, names="material", values="count", title="Доля по материалам")
        fig4.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig4, use_container_width=True)

    with col_e:
        surc = filtered["surface_finish"].value_counts().head(8).reset_index()
        surc.columns = ["surface_finish", "count"]
        fig5 = px.bar(
            surc, x="count", y="surface_finish", orientation="h",
            title="Типы поверхности",
            labels={"surface_finish": "", "count": "Кол-во"},
        )
        fig5.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig5, use_container_width=True)

    col_f, col_g = st.columns(2)
    with col_f:
        top_n = st.slider("Топ-N брендов", 5, 30, 15, key="top_n_brands")
        tb = (
            filtered.groupby("brand_country")
            .agg(count=("name", "count"), avg_price=("price", "mean"))
            .sort_values("count", ascending=False).head(top_n).reset_index()
        )
        tb["color"] = tb["brand_country"].apply(lambda x: COLOR_KERAMIN if x.startswith(KERAMIN_BRAND) else COLOR_MARKET)
        fig6 = px.bar(
            tb, x="brand_country", y="count", color="color",
            color_discrete_map="identity",
            title=f"Топ-{top_n} брендов по количеству позиций",
            labels={"brand_country": "Бренд (страна)", "count": "Позиций"},
        )
        fig6.update_xaxes(tickangle=45)
        fig6.update_layout(showlegend=False)
        st.plotly_chart(fig6, use_container_width=True)

    with col_g:
        tf = filtered["format"].value_counts().head(15).reset_index()
        tf.columns = ["format", "count"]
        fig7 = px.bar(
            tf, x="count", y="format", orientation="h",
            title="Топ форматов",
            labels={"format": "", "count": "Кол-во"},
        )
        fig7.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig7, use_container_width=True)

    st.subheader("Страны производства")
    cd = (
        filtered.groupby("country")
        .agg(count=("name", "count"), avg_price=("price", "mean"))
        .sort_values("count", ascending=False).head(15).reset_index()
    )
    fig8 = px.bar(
        cd, x="country", y="count", color="avg_price",
        color_continuous_scale="Blues",
        title="Позиций по стране производства",
        labels={"country": "Страна", "count": "Позиций", "avg_price": "Ср. цена"},
    )
    fig8.update_xaxes(tickangle=30)
    st.plotly_chart(fig8, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# ТАБ 2 — ПОЗИЦИЯ КЕРАМИН
# ════════════════════════════════════════════════════════════════════════════

with tab2:
    st.subheader("Позиция КЕРАМИН на рынке")

    if len(df_keramin) == 0:
        st.warning("КЕРАМИН не найден в выбранных фильтрах.")
    else:
        keramin_med = df_keramin["price"].median()
        market_med  = df_market["price"].median()
        diff_pct    = ((keramin_med - market_med) / market_med * 100) if market_med else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Позиций КЕРАМИН", f"{len(df_keramin):,}")
        k2.metric("Медиана КЕРАМИН", f"{keramin_med:.0f} ₽")
        k3.metric("Медиана рынка",   f"{market_med:.0f} ₽")
        k4.metric("КЕРАМИН vs рынок", f"{diff_pct:+.1f}%",
                  delta=f"{diff_pct:+.1f}%", delta_color="inverse")

        st.divider()

        col_a, col_b = st.columns(2)

        with col_a:
            top_fmt = filtered["format"].value_counts().head(12).index.tolist()
            dp = filtered[filtered["format"].isin(top_fmt)].copy()
            dp["Бренд"] = dp["brand"].apply(lambda x: "КЕРАМИН" if x == KERAMIN_BRAND else "Рынок")
            fig = px.box(
                dp, x="format", y="price", color="Бренд",
                color_discrete_map={"КЕРАМИН": COLOR_KERAMIN, "Рынок": COLOR_MARKET},
                title="Цены КЕРАМИН vs рынок по форматам",
                labels={"format": "Формат", "price": "Цена, руб/м²"},
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            dp2 = filtered.copy()
            dp2["Бренд"] = dp2["brand"].apply(lambda x: "КЕРАМИН" if x == KERAMIN_BRAND else "Рынок")
            fig2 = px.box(
                dp2, x="surface_finish", y="price", color="Бренд",
                color_discrete_map={"КЕРАМИН": COLOR_KERAMIN, "Рынок": COLOR_MARKET},
                title="Цены КЕРАМИН vs рынок по типам поверхности",
                labels={"surface_finish": "Тип поверхности", "price": "Цена, руб/м²"},
            )
            fig2.update_xaxes(tickangle=30)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Все позиции КЕРАМИН на фоне рынка")
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df_market["format"], y=df_market["price"],
            mode="markers", name="Рынок",
            marker=dict(color=COLOR_MARKET, opacity=0.25, size=5),
        ))
        fig3.add_trace(go.Scatter(
            x=df_keramin["format"], y=df_keramin["price"],
            mode="markers", name="КЕРАМИН",
            marker=dict(color=COLOR_KERAMIN, size=10, symbol="diamond"),
            text=df_keramin["name"],
            hovertemplate="<b>%{text}</b><br>Цена: %{y:.0f} ₽<extra></extra>",
        ))
        fig3.update_layout(
            title="Позиции КЕРАМИН vs рынок (по форматам)",
            xaxis_title="Формат", yaxis_title="Цена, руб/м²",
            xaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Детализация: КЕРАМИН vs медиана рынка по форматам")
        market_med_fmt = df_market.groupby("format")["price"].median().rename("медиана_рынка")
        kd = df_keramin[["name","format","material","surface_type","primary_design",
                         "primary_color","price","store","availability","url"]].copy()
        kd = kd.merge(market_med_fmt, on="format", how="left")
        kd["vs_рынок_%"] = ((kd["price"] - kd["медиана_рынка"]) / kd["медиана_рынка"] * 100).round(1)
        kd_out = kd.sort_values("vs_рынок_%").reset_index(drop=True)
        st.dataframe(
            kd_out,
            use_container_width=True,
            column_config={
                "url": st.column_config.LinkColumn("Ссылка"),
                "price": st.column_config.NumberColumn("Цена", format="%.0f ₽"),
                "медиана_рынка": st.column_config.NumberColumn("Медиана рынка", format="%.0f ₽"),
                "vs_рынок_%": st.column_config.NumberColumn("vs рынок, %", format="%.1f%%"),
            },
        )
        download_button(kd_out, "keramin_vs_market.xlsx", "Скачать Excel")

# ════════════════════════════════════════════════════════════════════════════
# ТАБ 3 — СРЕДНЕВЗВЕШЕННАЯ ЦЕНА
# ════════════════════════════════════════════════════════════════════════════

with tab3:
    st.subheader("Средневзвешенная цена рынка")
    st.caption("Только магазины с данными об остатках: LemanaPRO, OBI, Petrovich. "
               "Вес = объём остатков в м²")

    df_sw = filtered[
        filtered["store"].isin(STORES_WITH_STOCK) &
        filtered["total_stock"].notna() &
        (filtered["total_stock"] > 0)
    ]

    if len(df_sw) == 0:
        st.warning("Нет данных с остатками для выбранных фильтров.")
    else:
        # По форматам
        col_a, col_b = st.columns(2)

        with col_a:
            wa_fmt = (
                df_sw.groupby("format")
                .apply(weighted_avg_price).reset_index()
            )
            wa_fmt.columns = ["format", "weighted_price"]
            wa_fmt = wa_fmt.sort_values("weighted_price", ascending=False).head(15)
            keramin_formats = set(df_keramin["format"].unique())
            wa_fmt["color"] = wa_fmt["format"].apply(
                lambda x: COLOR_KERAMIN if x in keramin_formats else COLOR_MARKET
            )
            fig = px.bar(
                wa_fmt, x="format", y="weighted_price",
                color="color", color_discrete_map="identity",
                title="Средневзвешенная цена по форматам",
                labels={"format": "Формат", "weighted_price": "Ср/взв цена, руб/м²"},
            )
            fig.update_xaxes(tickangle=45)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            wa_mat = (
                df_sw.groupby("material")
                .apply(weighted_avg_price).reset_index()
            )
            wa_mat.columns = ["material", "weighted_price"]
            fig2 = px.bar(
                wa_mat, x="material", y="weighted_price",
                title="Средневзвешенная цена по материалам",
                labels={"material": "Материал", "weighted_price": "Ср/взв цена, руб/м²"},
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("По брендам (топ-20)")
        wa_brand = (
            df_sw.groupby("brand_country")
            .apply(weighted_avg_price).reset_index()
        )
        wa_brand.columns = ["brand_country", "weighted_price"]
        wa_brand = wa_brand.sort_values("weighted_price", ascending=False).head(20)
        wa_brand["color"] = wa_brand["brand_country"].apply(
            lambda x: COLOR_KERAMIN if x.startswith(KERAMIN_BRAND) else COLOR_MARKET
        )
        fig3 = px.bar(
            wa_brand, x="brand_country", y="weighted_price",
            color="color", color_discrete_map="identity",
            title="Средневзвешенная цена по брендам",
            labels={"brand_country": "Бренд (страна)", "weighted_price": "Ср/взв цена, руб/м²"},
        )
        fig3.update_xaxes(tickangle=45)
        fig3.update_layout(showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

        col_c, col_d = st.columns(2)
        with col_c:
            wa_des = (
                df_sw.groupby("primary_design")
                .apply(weighted_avg_price).reset_index()
            )
            wa_des.columns = ["primary_design", "weighted_price"]
            wa_des = wa_des.dropna().sort_values("weighted_price", ascending=False).head(12)
            fig4 = px.bar(
                wa_des, x="weighted_price", y="primary_design", orientation="h",
                title="Средневзвешенная цена по дизайну",
                labels={"primary_design": "", "weighted_price": "Ср/взв цена, руб/м²"},
            )
            fig4.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig4, use_container_width=True)

        with col_d:
            wa_surf = (
                df_sw.groupby("surface_finish")
                .apply(weighted_avg_price).reset_index()
            )
            wa_surf.columns = ["surface_finish", "weighted_price"]
            fig5 = px.bar(
                wa_surf, x="weighted_price", y="surface_finish", orientation="h",
                title="Средневзвешенная цена по типу поверхности",
                labels={"surface_finish": "", "weighted_price": "Ср/взв цена, руб/м²"},
            )
            fig5.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig5, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# ТАБ 4 — УГРОЗЫ: СКИДКИ
# ════════════════════════════════════════════════════════════════════════════

with tab4:
    st.subheader("Угрозы: скидочные товары с остатками")
    st.caption("Конкуренты, которые демпингуют с реальным товаром на складе")

    df_thr = filtered[
        filtered["discount"].notna() & (filtered["discount"] > 0) &
        filtered["total_stock"].notna() & (filtered["total_stock"] > 0)
    ].copy()

    if len(df_thr) == 0:
        st.info("Нет скидочных товаров с остатками для выбранных фильтров.")
    else:
        k1, k2, k3 = st.columns(3)
        k1.metric("Скидочных позиций с остатками", f"{len(df_thr):,}")
        k2.metric("Средняя скидка", f"{df_thr['discount'].mean():.1f}%")
        k3.metric("Брендов со скидками", df_thr["brand"].nunique())

        st.divider()

        df_thr["Группа"] = df_thr["brand"].apply(
            lambda x: "КЕРАМИН" if x == KERAMIN_BRAND else "Конкурент"
        )

        col_a, col_b = st.columns(2)
        with col_a:
            tbb = (
                df_thr.groupby("brand_country")
                .agg(count=("name", "count"), avg_discount=("discount", "mean"))
                .sort_values("count", ascending=False).head(15).reset_index()
            )
            tbb["color"] = tbb["brand_country"].apply(
                lambda x: COLOR_KERAMIN if x.startswith(KERAMIN_BRAND) else COLOR_MARKET
            )
            fig = px.bar(
                tbb, x="brand_country", y="count", color="color",
                color_discrete_map="identity",
                title="Топ брендов по скидочным позициям",
                labels={"brand_country": "Бренд (страна)", "count": "Позиций"},
            )
            fig.update_xaxes(tickangle=45)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            tbf = (
                df_thr.groupby("format")
                .agg(count=("name", "count"), avg_discount=("discount", "mean"))
                .sort_values("count", ascending=False).head(12).reset_index()
            )
            fig2 = px.bar(
                tbf, x="format", y="count",
                color="avg_discount", color_continuous_scale="Reds",
                title="Скидочные позиции по форматам",
                labels={"format": "Формат", "count": "Позиций", "avg_discount": "Ср. скидка %"},
            )
            fig2.update_xaxes(tickangle=45)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Детальный список")
        TCOLS = ["Группа", "brand_country", "name", "format", "material", "surface_type",
                 "primary_design", "price", "discount", "total_stock", "store", "url"]
        tcols = [c for c in TCOLS if c in df_thr.columns]
        thr_out = df_thr[tcols].sort_values("discount", ascending=False).reset_index(drop=True)
        st.dataframe(
            thr_out,
            use_container_width=True,
            column_config={
                "url": st.column_config.LinkColumn("Ссылка"),
                "price": st.column_config.NumberColumn("Цена", format="%.0f ₽"),
                "discount": st.column_config.NumberColumn("Скидка", format="%.0f%%"),
                "total_stock": st.column_config.NumberColumn("Остаток м²"),
            },
        )
        download_button(thr_out, "discount_threats.xlsx", "Скачать Excel")

# ════════════════════════════════════════════════════════════════════════════
# ТАБ 5 — ПОИСК АНАЛОГОВ
# ════════════════════════════════════════════════════════════════════════════

with tab5:
    st.subheader("Поиск аналогов")
    st.caption("Найдите аналоги для обоснования изменения цен — скачайте таблицу в Excel")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        a_format = st.selectbox("Формат *", [""] + sorted(df["format"].dropna().unique()))
    with c2:
        a_material = st.multiselect(
            "Материал",
            sorted(df["material"].dropna().unique()),
            default=sorted(df["material"].dropna().unique()),
        )
    with c3:
        a_design = st.multiselect("Дизайн", sorted(df["primary_design"].dropna().unique()))
    with c4:
        a_color = st.multiselect("Цвет", sorted(df["primary_color"].dropna().unique()))

    c4, c5 = st.columns(2)
    with c4:
        a_surface_finish = st.multiselect(
            "Тип поверхности (узкий)",
            sorted(df["surface_finish"].dropna().replace("", pd.NA).dropna().unique()),
            help="Полированный / Лаппатированный / Не полированный",
        )
    with c5:
        a_surface_type = st.multiselect(
            "Тип поверхности (широкий)",
            sorted(df["surface_type"].dropna().unique()),
            help="Более детальная классификация: Матовая, Глянцевая, Сатинированная и др.",
        )

    a_price = st.slider(
        "Диапазон цены аналогов, руб/м²",
        min_value=int(df["price"].min()),
        max_value=int(df["price"].max()),
        value=(int(df["price"].min()), 3500),
        step=100,
    )

    if a_format:
        analogs = df[df["format"] == a_format].copy()
        if a_material:
            analogs = analogs[analogs["material"].isin(a_material)]
        if a_surface_finish:
            analogs = analogs[analogs["surface_finish"].isin(a_surface_finish)]
        if a_surface_type:
            analogs = analogs[analogs["surface_type"].isin(a_surface_type)]
        if a_design:
            analogs = analogs[analogs["primary_design"].isin(a_design)]
        if a_color:
            analogs = analogs[analogs["primary_color"].isin(a_color)]
        analogs = analogs[analogs["price"].between(a_price[0], a_price[1])]

        st.info(f"Найдено: **{len(analogs):,}** позиций от **{analogs['brand'].nunique()}** брендов")

        if len(analogs) > 0:
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Мин. цена",  f"{analogs['price'].min():.0f} ₽")
            s2.metric("Медиана",    f"{analogs['price'].median():.0f} ₽")
            s3.metric("Средняя",    f"{analogs['price'].mean():.0f} ₽")
            s4.metric("Макс. цена", f"{analogs['price'].max():.0f} ₽")

            ACOLS = ["brand_country","name","format","material","surface_finish","surface_type",
                     "primary_design","primary_color","price","discount","total_stock",
                     "store","availability","url"]
            acols = [c for c in ACOLS if c in analogs.columns]
            analogs_out = analogs[acols].sort_values("price").reset_index(drop=True)
            analogs_out.insert(0, "КЕРАМИН", analogs_out["brand"] == KERAMIN_BRAND)

            st.dataframe(
                analogs_out,
                use_container_width=True,
                column_config={
                    "url": st.column_config.LinkColumn("Ссылка"),
                    "price": st.column_config.NumberColumn("Цена", format="%.0f ₽"),
                    "discount": st.column_config.NumberColumn("Скидка", format="%.0f%%"),
                    "total_stock": st.column_config.NumberColumn("Остаток м²"),
                    "КЕРАМИН": st.column_config.CheckboxColumn("КЕРАМИН"),
                },
            )

            download_button(
                analogs_out.drop(columns=["КЕРАМИН"], errors="ignore"),
                f"analogs_{a_format}.xlsx",
                "Скачать Excel",
            )
    else:
        st.info("Выберите формат для поиска аналогов")

# ════════════════════════════════════════════════════════════════════════════
# ТАБ 6 — ДАННЫЕ
# ════════════════════════════════════════════════════════════════════════════

with tab6:
    st.subheader("Все данные")

    DCOLS = ["name","store","price","price_unit","discount","material","format",
             "primary_design","primary_color","surface_type","brand_country","country",
             "availability","total_stock","url"]
    dcols = [c for c in DCOLS if c in filtered.columns]

    all_data_out = filtered[dcols].reset_index(drop=True)
    st.dataframe(
        all_data_out,
        use_container_width=True,
        column_config={
            "url": st.column_config.LinkColumn("Ссылка"),
            "price": st.column_config.NumberColumn("Цена", format="%.0f ₽"),
            "discount": st.column_config.NumberColumn("Скидка", format="%.0f%%"),
            "total_stock": st.column_config.NumberColumn("Остаток"),
        },
    )
    st.caption(f"Показано {len(filtered):,} из {len(df):,} записей")
    download_button(all_data_out, "tiles_data.xlsx", "Скачать Excel")

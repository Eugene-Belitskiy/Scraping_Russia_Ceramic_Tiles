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
    "АЗЕРБАЙДЖАН", "БЕЛАРУСЬ", "ИНДИЯ", "ИРАН",
    "КАЗАХСТАН", "КИТАЙ", "КЫРГЫЗСТАН", "РОССИЯ", "УЗБЕКИСТАН",
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
RUSSIA_PREMIUM_BRANDS  = ["KERAMA", "ITALON", "ESTIMA"]
CENTRAL_ASIA_COUNTRIES = ["УЗБЕКИСТАН", "КАЗАХСТАН", "КЫРГЫЗСТАН"]
EUROPE_COUNTRIES       = ["ПОЛЬША", "ИСПАНИЯ", "ИТАЛИЯ"]
COMP_ORDER  = ["КЕРАМИН", "Россия (премиум)", "Россия (прочие)",
               "Индия", "Китай", "Средняя Азия", "Европа", "Прочие"]
COMP_COLORS = {
    "КЕРАМИН":           "#E63946",
    "Россия (премиум)":  "#F4A261",
    "Россия (прочие)":   "#457B9D",
    "Индия":             "#E9C46A",
    "Китай":             "#2A9D8F",
    "Средняя Азия":      "#9B5DE5",
    "Европа":            "#06D6A0",
    "Прочие":            "#CCCCCC",
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
            client.table("tiles_v2")
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

def _assign_comp_group(brand: str, country: str) -> str:
    brand_u = str(brand).upper()
    country_u = str(country).upper()
    if brand == KERAMIN_BRAND:
        return "КЕРАМИН"
    if any(brand_u.startswith(pb) for pb in RUSSIA_PREMIUM_BRANDS):
        return "Россия (премиум)"
    if country_u == "РОССИЯ":
        return "Россия (прочие)"
    if country_u == "ИНДИЯ":
        return "Индия"
    if country_u == "КИТАЙ":
        return "Китай"
    if country_u in CENTRAL_ASIA_COUNTRIES:
        return "Средняя Азия"
    if country_u in EUROPE_COUNTRIES:
        return "Европа"
    return "Прочие"

def _reset_filters():
    for s in df["store"].dropna().unique():
        st.session_state[f"store_{s}"] = True
    for m in df["material"].dropna().unique():
        st.session_state[f"mat_{m}"] = True
    for m in MATERIAL_FORMATS:
        st.session_state[f"sub_fmt_{m}"] = []
    for s in df["surface_finish"].dropna().replace("", pd.NA).dropna().unique():
        st.session_state[f"sf_{s}"] = True
    st.session_state["key_formats_only"] = True
    st.session_state["fmt_pills"] = [f for f in KEY_FORMATS if f in df["format"].dropna().unique()]
    st.session_state["fmt_multi"] = []
    st.session_state["designs"] = []
    st.session_state["colors"] = []
    st.session_state["country_mode"] = "Ключевые страны"
    st.session_state["countries_pills"] = [c for c in KEY_COUNTRIES if c in df["country"].dropna().unique()]
    st.session_state["countries_multi"] = sorted(df["country"].dropna().unique())
    st.session_state.pr_lo = _price_min_default
    st.session_state.pr_hi = 3000
    st.session_state["_price_slider"] = (_price_min_default, 3000)
    st.session_state.disc_max = 30
    st.session_state["_disc_slider"] = 30
    st.session_state["only_with_stock"] = False

# ─── Сайдбар — фильтры ──────────────────────────────────────────────────────

with st.sidebar:
    st.header("Фильтры")

    st.markdown("**Магазин**")
    store_counts = df["store"].value_counts()
    stores = [
        s for s in sorted(df["store"].dropna().unique())
        if st.checkbox(f"{s}  ({store_counts.get(s, 0):,})", value=True, key=f"store_{s}")
    ]

    st.divider()
    all_formats_list = sorted(df["format"].dropna().unique())
    key_formats_only = st.checkbox("Только ключевые форматы", value=True, key="key_formats_only")

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
            label_visibility="collapsed", key="fmt_pills",
        )
    else:
        formats = st.multiselect("", options=all_formats_list, placeholder="Все форматы",
                                 label_visibility="collapsed", key="fmt_multi")

    designs = st.multiselect(
        "Дизайн",
        options=sorted(df["primary_design"].dropna().unique()),
        placeholder="Все дизайны",
        key="designs",
    )
    colors = st.multiselect(
        "Цвет",
        options=sorted(df["primary_color"].dropna().replace("", pd.NA).dropna().unique()),
        placeholder="Все цвета",
        key="colors",
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
            label_visibility="collapsed", key="countries_pills",
        )
    else:
        countries = st.multiselect(
            "Страна", options=all_countries_list, default=all_countries_list,
            key="countries_multi",
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
        key="only_with_stock",
        help="Анализируются только DIY-сети: Lemana PRO, OBI, Petrovich",
    )

    st.divider()
    st.button("↩ Сбросить фильтры", on_click=_reset_filters, use_container_width=True)
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
if colors:
    filtered = filtered[filtered["primary_color"].isin(colors)]
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

# ─── ХЕЛПЕР: bubble chart угроз ─────────────────────────────────────────────

def build_threat_bubbles(df_mkt: pd.DataFrame, df_ker: pd.DataFrame) -> pd.DataFrame:
    """Агрегирует конкурентов по format×brand_country: средн.цена, сумм.остаток, % vs КЕРАМИН."""
    keramin_median = df_ker.groupby("format")["price"].median()
    rows = []
    for (fmt, bc, grp), g in df_mkt.groupby(["format", "brand_country", "Группа"]):
        if fmt not in keramin_median.index:
            continue
        avg_price = g["price"].mean()
        stock = g["total_stock"].sum()
        k_med = keramin_median[fmt]
        pct = (avg_price - k_med) / k_med * 100
        rows.append({
            "format": fmt,
            "brand_country": bc,
            "Группа": grp,
            "avg_price": round(avg_price),
            "stock_m2": stock if pd.notna(stock) else 0.0,
            "pct_vs_keramin": round(pct, 1),
            "k_median": round(k_med),
        })
    return pd.DataFrame(rows)

# ─── ТАБЫ ────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Ценовой ландшафт",
    "Угрозы КЕРАМИН",
    "Позиция по форматам",
    "Поиск аналогов",
    "Данные",
])

# ════════════════════════════════════════════════════════════════════════════
# ТАБ 1 — ЦЕНОВОЙ ЛАНДШАФТ
# ════════════════════════════════════════════════════════════════════════════

with tab1:
    st.subheader("Ценовой ландшафт рынка")

    keramin_med_global = df_keramin["price"].median() if len(df_keramin) > 0 else None
    mkt_cheaper_pct = (
        (df_market["price"] < keramin_med_global).mean() * 100
        if keramin_med_global and len(df_market) > 0 else 0.0
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Позиций на рынке", f"{len(filtered):,}")
    k2.metric("Брендов", filtered["brand"].nunique())
    k3.metric("Средняя цена рынка", f"{filtered['price'].mean():.0f} ₽" if len(filtered) > 0 else "—")
    k4.metric("Цена КЕРАМИН (медиана)", f"{keramin_med_global:.0f} ₽" if keramin_med_global else "—")
    k5.metric("% рынка дешевле КЕРАМИН", f"{mkt_cheaper_pct:.1f}%")

    st.divider()

    if len(df_keramin) == 0:
        st.warning("КЕРАМИН не найден в выбранных фильтрах.")
    else:
        st.markdown("### Плотность цен по конкурентным группам")
        st.caption("Violin показывает, где реально сосредоточена масса предложений. КЕРАМИН — красные точки.")

        dp1 = filtered[filtered["price"].notna()].copy()
        dp1["Группа"] = dp1.apply(lambda r: _assign_comp_group(r["brand"], r["country"]), axis=1)

        fmt_opts1 = sorted(dp1["format"].dropna().unique())
        sel_fmt1 = st.pills(
            "Форматы", options=fmt_opts1,
            selection_mode="multi",
            default=fmt_opts1[:4] if len(fmt_opts1) >= 4 else fmt_opts1,
            key="t1_fmt_pills",
        )
        dp1_f = dp1[dp1["format"].isin(sel_fmt1)] if sel_fmt1 else dp1

        fig_vio1 = go.Figure()
        for group in COMP_ORDER:
            subset = dp1_f[dp1_f["Группа"] == group].copy()
            if len(subset) < 3:
                continue
            is_keramin = group == "КЕРАМИН"
            if is_keramin:
                cd = subset[["name", "primary_design", "primary_color"]].fillna("—").values
                hover = (
                    "<b>%{customdata[0]}</b><br>"
                    "Цена: %{y:.0f} ₽<br>"
                    "Дизайн: %{customdata[1]}<br>"
                    "Цвет: %{customdata[2]}<extra></extra>"
                )
            else:
                cd = subset[["name", "brand", "primary_design", "primary_color"]].fillna("—").values
                hover = (
                    "<b>%{customdata[0]}</b><br>"
                    "Бренд: %{customdata[1]}<br>"
                    "Цена: %{y:.0f} ₽<br>"
                    "Дизайн: %{customdata[2]}<br>"
                    "Цвет: %{customdata[3]}<extra></extra>"
                )
            fig_vio1.add_trace(go.Violin(
                y=subset["price"],
                name=group,
                line_color=COMP_COLORS[group],
                fillcolor=COMP_COLORS[group],
                opacity=0.8 if is_keramin else 0.35,
                points="all",
                pointpos=0,
                jitter=0.3,
                marker=dict(
                    size=7 if is_keramin else 5,
                    opacity=1.0,
                    color="#ffffff" if is_keramin else "#1a1a1a",
                    line=dict(color=COMP_COLORS[group], width=2 if is_keramin else 1),
                ),
                meanline_visible=True,
                box_visible=True,
                spanmode="soft",
                customdata=cd,
                hovertemplate=hover,
            ))
        fig_vio1.update_layout(
            yaxis_title="Цена, руб/м²",
            xaxis_title="Конкурентная группа",
            violingap=0.15,
            violinmode="overlay",
            height=550,
            showlegend=False,
        )
        st.plotly_chart(fig_vio1, use_container_width=True)

        st.divider()
        st.markdown("### Распределение цен рынка")

        fig_hist1 = go.Figure()
        bin_size1 = max(50, int((dp1_f["price"].max() - dp1_f["price"].min()) / 60))
        for group in COMP_ORDER:
            subset = dp1_f[dp1_f["Группа"] == group]
            if len(subset) == 0:
                continue
            fig_hist1.add_trace(go.Histogram(
                x=subset["price"],
                name=group,
                opacity=0.7,
                marker_color=COMP_COLORS[group],
                xbins=dict(size=bin_size1),
                hovertemplate=f"<b>{group}</b><br>Цена: %{{x}}<br>Позиций: %{{y}}<extra></extra>",
            ))
        if keramin_med_global:
            fig_hist1.add_vline(
                x=keramin_med_global,
                line_dash="dash",
                line_color=COLOR_KERAMIN,
                line_width=2,
                annotation_text=f"КЕРАМИН: {keramin_med_global:.0f} ₽",
                annotation_position="top right",
                annotation_font_color=COLOR_KERAMIN,
            )
        fig_hist1.update_layout(
            barmode="overlay",
            xaxis_title="Цена, руб/м²",
            yaxis_title="Количество позиций",
            legend_title="Группа",
            height=420,
        )
        st.plotly_chart(fig_hist1, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# ТАБ 2 — УГРОЗЫ КЕРАМИН
# ════════════════════════════════════════════════════════════════════════════

with tab2:
    st.subheader("Угрозы КЕРАМИН")
    st.caption("Конкурентная среда вокруг цен КЕРАМИН. Дешевле с большим остатком = главная угроза.")

    if len(df_keramin) == 0:
        st.warning("КЕРАМИН не найден в выбранных фильтрах.")
    else:
        dp2 = filtered[filtered["price"].notna()].copy()
        dp2["Группа"] = dp2.apply(lambda r: _assign_comp_group(r["brand"], r["country"]), axis=1)
        dp2_market  = dp2[dp2["Группа"] != "КЕРАМИН"]
        dp2_keramin = dp2[dp2["Группа"] == "КЕРАМИН"]

        threat_df = build_threat_bubbles(dp2_market, dp2_keramin)
        threat_cheaper = threat_df[threat_df["pct_vs_keramin"] < 0]

        # KPIs
        k1, k2, k3 = st.columns(3)
        k1.metric("Конкурентов дешевле КЕРАМИН", f"{len(threat_cheaper):,}")
        k2.metric("Их остаток на складах, м²",
                  f"{threat_cheaper['stock_m2'].sum():.0f}" if len(threat_cheaper) > 0 else "0")
        k3.metric("Среднее отклонение цены",
                  f"{threat_cheaper['pct_vs_keramin'].mean():.1f}%" if len(threat_cheaper) > 0 else "—")

        st.divider()

        # ── Bubble chart угроз ──────────────────────────────────────────────
        st.markdown("### Кто дешевле КЕРАМИН и сколько у них на складе")
        st.caption(
            "Ось X: % отклонения цены от медианы КЕРАМИН (отрицательное = дешевле = угроза). "
            "Размер пузырька = остаток м². Красная зона слева — зона угроз."
        )

        if len(threat_df) == 0:
            st.info("Нет данных для bubble chart.")
        else:
            stock_max = threat_df["stock_m2"].max()
            sizeref2 = 2.0 * stock_max / (50 ** 2) if stock_max > 0 else 1.0

            fig_bubble = go.Figure()
            for group in COMP_ORDER:
                subset = threat_df[threat_df["Группа"] == group]
                if len(subset) == 0:
                    continue
                fig_bubble.add_trace(go.Scatter(
                    x=subset["pct_vs_keramin"],
                    y=subset["format"],
                    mode="markers",
                    name=group,
                    marker=dict(
                        size=subset["stock_m2"].clip(lower=0),
                        sizemode="area",
                        sizeref=sizeref2,
                        sizemin=5,
                        color=COMP_COLORS[group],
                        opacity=0.8,
                        line=dict(color="white", width=1),
                    ),
                    customdata=subset[["brand_country", "avg_price", "stock_m2", "k_median"]].values,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Формат: %{y}<br>"
                        "Средняя цена: %{customdata[1]:.0f} ₽<br>"
                        "Цена КЕРАМИН: %{customdata[3]:.0f} ₽<br>"
                        "% vs КЕРАМИН: %{x:+.1f}%<br>"
                        "Остаток: %{customdata[2]:.0f} м²"
                        "<extra></extra>"
                    ),
                ))
            fig_bubble.add_vline(
                x=0, line_color=COLOR_KERAMIN, line_width=2, line_dash="dash",
                annotation_text="Цена КЕРАМИН", annotation_position="top",
                annotation_font_color=COLOR_KERAMIN,
            )
            fig_bubble.add_vrect(
                x0=threat_df["pct_vs_keramin"].min() - 5, x1=0,
                fillcolor="red", opacity=0.04, line_width=0,
                annotation_text="Дешевле КЕРАМИН",
                annotation_position="top left",
            )
            fig_bubble.update_layout(
                xaxis_title="Отклонение от цены КЕРАМИН, %",
                yaxis_title="Формат",
                height=520,
                xaxis=dict(zeroline=True, zerolinecolor=COLOR_KERAMIN, zerolinewidth=2),
                legend_title="Группа",
            )
            st.plotly_chart(fig_bubble, use_container_width=True)

        st.divider()

        # ── Тепловая карта плотности ──────────────────────────────────────
        st.markdown("### Тепловая карта: где скапливаются конкуренты")
        st.caption(
            "Цвет = количество конкурентных позиций в ценовом диапазоне. "
            "Красные линии — цены КЕРАМИН в каждом формате."
        )

        fmt_opts2 = sorted(dp2["format"].dropna().unique())
        sel_fmt2 = st.pills(
            "Форматы для анализа", options=fmt_opts2,
            selection_mode="multi",
            default=fmt_opts2[:4] if len(fmt_opts2) >= 4 else fmt_opts2,
            key="t2_fmt_pills",
        )
        dp2_f = dp2[dp2["format"].isin(sel_fmt2)] if sel_fmt2 else dp2

        bin_step2 = st.select_slider(
            "Шаг ценового диапазона, ₽", options=[100, 200, 300, 500],
            value=200, key="t2_heatmap_bin",
        )

        if sel_fmt2:
            price_min2 = int(dp2_f["price"].min() // bin_step2 * bin_step2)
            price_max2 = int(dp2_f["price"].max() // bin_step2 * bin_step2) + bin_step2
            bins2 = range(price_min2, price_max2 + bin_step2, bin_step2)

            heat_rows2 = []
            for fmt in sel_fmt2:
                mkt_fmt = dp2_market[dp2_market["format"] == fmt]["price"]
                for b in bins2:
                    cnt = int(((mkt_fmt >= b) & (mkt_fmt < b + bin_step2)).sum())
                    heat_rows2.append({"Формат": fmt, "Цена": b, "Позиций": cnt})
            heat_df2 = pd.DataFrame(heat_rows2)
            heat_pivot2 = heat_df2.pivot(index="Цена", columns="Формат", values="Позиций").fillna(0)

            fig_heat2 = px.imshow(
                heat_pivot2,
                color_continuous_scale="Blues",
                labels={"color": "Позиций", "x": "Формат", "y": "Цена, ₽"},
                aspect="auto",
            )
            k_fmt_med2 = dp2_keramin[dp2_keramin["format"].isin(sel_fmt2)].groupby("format")["price"].median()
            for fmt, kprice in k_fmt_med2.items():
                x_idx = list(sel_fmt2).index(fmt) if fmt in sel_fmt2 else None
                if x_idx is not None:
                    fig_heat2.add_shape(
                        type="line", x0=x_idx - 0.5, x1=x_idx + 0.5,
                        y0=kprice, y1=kprice,
                        line=dict(color=COLOR_KERAMIN, width=3),
                    )
            fig_heat2.update_layout(height=500)
            st.plotly_chart(fig_heat2, use_container_width=True)

        st.divider()

        # ── Ценовой пояс ──────────────────────────────────────────────────
        st.markdown("### Ценовой пояс: конкуренты в ±N% от каждой позиции КЕРАМИН")
        st.caption(
            "Для каждой позиции КЕРАМИН — сколько конкурентов находится "
            "в выбранном ценовом поясе. Показывает реальное давление."
        )

        band_pct2 = st.slider("Ширина пояса ±%", 5, 50, 20, step=5, key="t2_band_pct")

        band_rows2 = []
        for _, krow in dp2_keramin.iterrows():
            kp = krow["price"]
            lo2, hi2 = kp * (1 - band_pct2 / 100), kp * (1 + band_pct2 / 100)
            rivals2 = dp2_market[
                (dp2_market["format"] == krow["format"]) &
                (dp2_market["price"] >= lo2) &
                (dp2_market["price"] <= hi2)
            ]
            cheaper2 = rivals2[rivals2["price"] < kp]
            pricier2 = rivals2[rivals2["price"] >= kp]
            band_rows2.append({
                "Позиция": krow.get("name", ""),
                "Формат":  krow["format"],
                "Цена КЕРАМИН": int(kp),
                f"Дешевле (±{band_pct2}%)": len(cheaper2),
                f"Дороже (±{band_pct2}%)":  len(pricier2),
                "Всего конкурентов": len(rivals2),
            })

        band_df2 = pd.DataFrame(band_rows2).sort_values("Всего конкурентов", ascending=False).reset_index(drop=True)

        fig_band2 = px.bar(
            band_df2,
            x="Позиция",
            y=[f"Дешевле (±{band_pct2}%)", f"Дороже (±{band_pct2}%)"],
            barmode="stack",
            color_discrete_map={
                f"Дешевле (±{band_pct2}%)": "#E63946",
                f"Дороже (±{band_pct2}%)":  "#457B9D",
            },
            labels={"value": "Конкурентов", "variable": ""},
            height=420,
        )
        fig_band2.update_xaxes(tickangle=45)
        st.plotly_chart(fig_band2, use_container_width=True)
        st.dataframe(
            band_df2,
            use_container_width=True,
            column_config={"Цена КЕРАМИН": st.column_config.NumberColumn(format="%d ₽")},
        )

# ════════════════════════════════════════════════════════════════════════════
# ТАБ 3 — ПОЗИЦИЯ ПО ФОРМАТАМ
# ════════════════════════════════════════════════════════════════════════════

with tab3:
    st.subheader("Позиция КЕРАМИН по форматам")
    st.caption("Детальное позиционирование и средневзвешенные цены с учётом складских остатков.")

    if len(df_keramin) == 0:
        st.warning("КЕРАМИН не найден в выбранных фильтрах.")
    else:
        dp3 = filtered[filtered["price"].notna()].copy()
        dp3["Группа"] = dp3.apply(lambda r: _assign_comp_group(r["brand"], r["country"]), axis=1)
        dp3_market  = dp3[dp3["Группа"] != "КЕРАМИН"]
        dp3_keramin = dp3[dp3["Группа"] == "КЕРАМИН"]

        threshold3 = st.slider(
            "Порог «на уровне», %", 0, 30, 10, step=5,
            help="Бренды в диапазоне ±N% от цены КЕРАМИН считаются «на уровне»",
            key="t3_pos_threshold",
        )

        keramin_fmt_price3 = (
            dp3_keramin.groupby(["material", "format"])["price"]
            .mean()
            .reset_index(name="керамин_цена")
        )

        bc_fmt3 = (
            dp3_market.groupby(["material", "format", "Группа", "brand_country"])
            .agg(
                SKU=("price", "count"),
                Средняя_цена=("price", "mean"),
                Остаток_м2=("total_stock", "sum"),
            )
            .round({"Средняя_цена": 0, "Остаток_м2": 0})
            .reset_index()
        )
        bc_fmt3["Средняя_цена"] = bc_fmt3["Средняя_цена"].astype(int)
        bc_fmt3["Остаток_м2"]   = bc_fmt3["Остаток_м2"].fillna(0).astype(int)

        bc_fmt3 = bc_fmt3.merge(keramin_fmt_price3, on=["material", "format"], how="inner")
        bc_fmt3["vs КЕРАМИН, %"] = (
            (bc_fmt3["Средняя_цена"] - bc_fmt3["керамин_цена"]) / bc_fmt3["керамин_цена"] * 100
        ).round(1)

        def _classify3(pct: float) -> str:
            if pct < -threshold3:
                return "Дешевле"
            elif pct > threshold3:
                return "Дороже"
            return "На уровне"

        bc_fmt3["Позиция"] = bc_fmt3["vs КЕРАМИН, %"].apply(_classify3)
        bc_fmt3["керамин_цена"] = bc_fmt3["керамин_цена"].round(0).astype(int)

        grp_ord3 = {g: i for i, g in enumerate(COMP_ORDER)}
        bc_fmt3["_ord"] = bc_fmt3["Группа"].map(grp_ord3)
        bc_fmt3 = (
            bc_fmt3.sort_values(["material", "format", "_ord", "Средняя_цена"])
            .drop(columns=["_ord"])
            .reset_index(drop=True)
        )

        pos_order3 = ["Дешевле", "На уровне", "Дороже"]
        pos_counts3 = bc_fmt3["Позиция"].value_counts().reindex(pos_order3, fill_value=0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Дешевле КЕРАМИН", pos_counts3["Дешевле"])
        c2.metric("На уровне",       pos_counts3["На уровне"])
        c3.metric("Дороже КЕРАМИН",  pos_counts3["Дороже"])

        sku_max3 = int(bc_fmt3["SKU"].max()) if len(bc_fmt3) > 0 else 1
        st.dataframe(
            bc_fmt3.rename(columns={
                "material": "Материал", "format": "Формат",
                "brand_country": "Бренд-страна",
                "керамин_цена": "Цена КЕРАМИН",
                "Остаток_м2": "Остаток м²",
            }),
            use_container_width=True,
            column_config={
                "Материал":      st.column_config.TextColumn("Материал"),
                "Формат":        st.column_config.TextColumn("Формат"),
                "Группа":        st.column_config.TextColumn("Группа"),
                "Бренд-страна":  st.column_config.TextColumn("Бренд-страна"),
                "SKU": st.column_config.ProgressColumn(
                    "SKU", min_value=0, max_value=sku_max3, format="%d"
                ),
                "Средняя_цена":  st.column_config.NumberColumn("Средняя цена", format="%d ₽"),
                "Цена КЕРАМИН":  st.column_config.NumberColumn("Цена КЕРАМИН", format="%d ₽"),
                "vs КЕРАМИН, %": st.column_config.NumberColumn("vs КЕРАМИН, %", format="%.1f%%"),
                "Позиция":       st.column_config.TextColumn("Позиция"),
                "Остаток м²":    st.column_config.NumberColumn("Остаток м²", format="%d"),
            },
        )
        download_button(
            bc_fmt3.rename(columns={
                "material": "Материал", "format": "Формат",
                "brand_country": "Бренд-страна",
                "керамин_цена": "Цена КЕРАМИН",
                "Остаток_м2": "Остаток м²",
            }),
            "keramin_positioning.xlsx", "Скачать Excel",
        )

        st.divider()

        # ── Bubble chart бренд-стран (violin-shape + пузырьки) ────────────
        st.markdown("### Плотность цен + позиции бренд-стран")
        st.caption("Форма violin = плотность. Пузырьки = бренд-страны. Размер = кол-во SKU.")

        fmt_opts3 = sorted(dp3["format"].dropna().unique())
        sel_fmt3 = st.pills(
            "Форматы", options=fmt_opts3,
            selection_mode="multi",
            default=fmt_opts3[:4] if len(fmt_opts3) >= 4 else fmt_opts3,
            key="t3_fmt_pills",
        )
        dp3_f = dp3[dp3["format"].isin(sel_fmt3)] if sel_fmt3 else dp3

        bc_agg3 = (
            dp3_f.groupby(["Группа", "brand_country"])
            .agg(avg_price=("price", "mean"), SKU=("price", "count"))
            .round({"avg_price": 0})
            .reset_index()
        )
        bc_agg3["avg_price"] = bc_agg3["avg_price"].astype(int)
        sku_max_bc = int(bc_agg3["SKU"].max()) if len(bc_agg3) > 0 else 1
        sizeref3 = 2.0 * sku_max_bc / (38 ** 2)

        fig_vio3 = go.Figure()
        for group in COMP_ORDER:
            subset3 = dp3_f[dp3_f["Группа"] == group]
            if len(subset3) < 3:
                continue
            fig_vio3.add_trace(go.Violin(
                y=subset3["price"],
                name=group,
                line_color=COMP_COLORS[group],
                fillcolor=COMP_COLORS[group],
                opacity=0.3,
                points=False,
                meanline_visible=True,
                box_visible=True,
                spanmode="soft",
                showlegend=False,
            ))
        for group in COMP_ORDER:
            subset_bc3 = bc_agg3[bc_agg3["Группа"] == group]
            if len(subset_bc3) == 0:
                continue
            fig_vio3.add_trace(go.Scatter(
                x=[group] * len(subset_bc3),
                y=subset_bc3["avg_price"],
                mode="markers",
                name=group,
                marker=dict(
                    size=subset_bc3["SKU"].tolist(),
                    sizemode="area",
                    sizeref=sizeref3,
                    sizemin=6,
                    color=COMP_COLORS[group],
                    opacity=0.85,
                    line=dict(color="white", width=1.5),
                ),
                customdata=subset_bc3[["brand_country", "avg_price", "SKU"]].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Средняя цена: %{customdata[1]} ₽<br>"
                    "SKU: %{customdata[2]:.0f}"
                    "<extra></extra>"
                ),
                showlegend=False,
            ))
        fig_vio3.update_layout(
            yaxis_title="Цена, руб/м²",
            xaxis_title="Конкурентная группа",
            violingap=0.15,
            violinmode="overlay",
            height=550,
        )
        st.plotly_chart(fig_vio3, use_container_width=True)

        st.divider()

        # ── Средневзвешенная цена по форматам ─────────────────────────────
        st.markdown("### Средневзвешенная цена по форматам")
        st.caption("Вес = объём остатков м². Только магазины с данными об остатках: LemanaPRO, OBI, Petrovich.")

        df_sw3 = filtered[
            filtered["store"].isin(STORES_WITH_STOCK) &
            filtered["total_stock"].notna() &
            (filtered["total_stock"] > 0)
        ]
        if len(df_sw3) == 0:
            st.info("Нет данных с остатками для выбранных фильтров.")
        else:
            wa_fmt3 = (
                df_sw3.groupby("format")
                .apply(weighted_avg_price).reset_index()
            )
            wa_fmt3.columns = ["format", "weighted_price"]
            wa_fmt3 = wa_fmt3.sort_values("weighted_price", ascending=False).head(15)
            keramin_formats3 = set(df_keramin["format"].unique())
            wa_fmt3["color"] = wa_fmt3["format"].apply(
                lambda x: COLOR_KERAMIN if x in keramin_formats3 else COLOR_MARKET
            )
            fig_wa3 = px.bar(
                wa_fmt3, x="format", y="weighted_price",
                color="color", color_discrete_map="identity",
                title="Средневзвешенная цена по форматам",
                labels={"format": "Формат", "weighted_price": "Ср/взв цена, руб/м²"},
            )
            if keramin_med_global:
                fig_wa3.add_hline(
                    y=keramin_med_global,
                    line_dash="dash",
                    line_color=COLOR_KERAMIN,
                    annotation_text=f"КЕРАМИН медиана: {keramin_med_global:.0f} ₽",
                    annotation_position="top right",
                )
            fig_wa3.update_xaxes(tickangle=45)
            fig_wa3.update_layout(showlegend=False)
            st.plotly_chart(fig_wa3, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# ТАБ 4 — ПОИСК АНАЛОГОВ (б/и)
# ════════════════════════════════════════════════════════════════════════════

with tab4:
    st.subheader("Поиск аналогов")
    st.caption("Найдите аналоги для обоснования изменения цен — скачайте таблицу в Excel")

    # Используем tab4 (бывший tab5) — содержимое не меняется
    c1_a, c2_a, c3_a, c4_a = st.columns(4)
    with c1_a:
        a_format = st.selectbox("Формат *", [""] + sorted(df["format"].dropna().unique()))
    with c2_a:
        a_material = st.multiselect(
            "Материал",
            sorted(df["material"].dropna().unique()),
            default=sorted(df["material"].dropna().unique()),
        )
    with c3_a:
        a_design = st.multiselect("Дизайн", sorted(df["primary_design"].dropna().unique()))
    with c4_a:
        a_color = st.multiselect("Цвет", sorted(df["primary_color"].dropna().unique()))

    c5_a, c6_a = st.columns(2)
    with c5_a:
        a_surface_finish = st.multiselect(
            "Тип поверхности (узкий)",
            sorted(df["surface_finish"].dropna().replace("", pd.NA).dropna().unique()),
            help="Полированный / Лаппатированный / Не полированный",
        )
    with c6_a:
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

            ACOLS = ["brand_country", "name", "format", "material", "surface_finish",
                     "surface_type", "primary_design", "primary_color", "price",
                     "discount", "total_stock", "store", "availability", "url"]
            acols = [c for c in ACOLS if c in analogs.columns]
            analogs_out = analogs[acols].sort_values("price").reset_index(drop=True)
            analogs_out.insert(0, "КЕРАМИН", analogs_out["brand"] == KERAMIN_BRAND if "brand" in analogs_out.columns else False)

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
# ТАБ 5 — ДАННЫЕ
# ════════════════════════════════════════════════════════════════════════════

with tab5:
    st.subheader("Все данные")

    DCOLS = ["name", "store", "price", "price_unit", "discount", "material", "format",
             "primary_design", "primary_color", "surface_type", "brand_country", "country",
             "availability", "total_stock", "url"]
    dcols = [c for c in DCOLS if c in filtered.columns]

    all_data_out = filtered[dcols].reset_index(drop=True)

    # Приводим url к строке (None → "") чтобы избежать ошибки LinkColumn
    if "url" in all_data_out.columns:
        all_data_out["url"] = all_data_out["url"].fillna("").astype(str)

    col_cfg = {
        "price":    st.column_config.NumberColumn("Цена", format="%.0f ₽"),
        "discount": st.column_config.NumberColumn("Скидка", format="%.0f%%"),
        "total_stock": st.column_config.NumberColumn("Остаток"),
    }
    if "url" in all_data_out.columns:
        col_cfg["url"] = st.column_config.LinkColumn("Ссылка")

    st.dataframe(all_data_out, use_container_width=True, column_config=col_cfg, height=600)
    st.caption(f"Показано {len(filtered):,} из {len(df):,} записей")
    download_button(all_data_out, "tiles_data.xlsx", "Скачать Excel")


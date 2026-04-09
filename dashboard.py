"""
dashboard.py — Streamlit analytics dashboard for РезюмеАИ bot.

Runs on port 8501 (Streamlit default) — does NOT touch port 8000 (FastAPI).
Reads from /opt/resumeaibot/bot.db using sqlite3 (sync, read-only queries only).
Password protected.

Run: streamlit run /opt/resumeaibot/dashboard.py
Access via SSH tunnel: ssh -L 8501:localhost:8501 root@72.56.250.53
Then open: http://localhost:8501
"""

import sqlite3
from datetime import date, timedelta, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH           = "/opt/resumeaibot/bot.db"
DASHBOARD_PASSWORD = "resumeai2025"   # Change this to something strong
GOAL_PAID_USERS   = 1000

st.set_page_config(
    page_title="РезюмеАИ Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Password gate ─────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 РезюмеАИ Analytics")
    pw = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if pw == DASHBOARD_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверный пароль")
    st.stop()

# ── Auto-refresh every 60 seconds ─────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60_000, key="autorefresh")
except ImportError:
    st.sidebar.warning("⚠️ streamlit-autorefresh не установлен — автообновление отключено")

# ── DB helper — all queries are synchronous, read-only ───────────────────────

@st.cache_data(ttl=60)   # cache results for 60 seconds
def _query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Execute a SELECT query and return a DataFrame. Read-only, cached 60s."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        df = pd.read_sql_query(sql, con, params=params)
    finally:
        con.close()
    return df


def _scalar(sql: str, params: tuple = (), default=0):
    """Execute a query that returns a single scalar value."""
    df = _query(sql, params)
    if df.empty or df.iloc[0, 0] is None:
        return default
    return df.iloc[0, 0]


# ── Sidebar navigation ────────────────────────────────────────────────────────

PAGES = [
    "🏠 Обзор",
    "💰 Выручка",
    "🔗 Рефералы",
    "📣 Каналы роста",
    "🎯 Цель",
]

st.sidebar.title("РезюмеАИ Analytics")
st.sidebar.markdown(f"🕐 Обновлено: {datetime.now().strftime('%H:%M:%S')}")
page = st.sidebar.radio("Страница", PAGES)
st.sidebar.divider()
if st.sidebar.button("Выйти"):
    st.session_state.authenticated = False
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Overview
# ══════════════════════════════════════════════════════════════════════════════

if page == "🏠 Обзор":
    st.title("🏠 Обзор")
    today = date.today().isoformat()

    # ── KPI cards ─────────────────────────────────────────────────────────────
    total_users    = _scalar("SELECT COUNT(*) FROM users")
    paid_users     = _scalar("SELECT COUNT(DISTINCT telegram_id) FROM payments WHERE status='succeeded'")
    conversion_pct = round(paid_users / total_users * 100, 1) if total_users > 0 else 0
    total_revenue  = _scalar("SELECT COALESCE(SUM(amount_rub),0) FROM payments WHERE status='succeeded'")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Всего пользователей", f"{total_users:,}")
    c2.metric("💳 Платных пользователей", f"{paid_users:,}")
    c3.metric("📈 Конверсия", f"{conversion_pct:.1f}%")
    c4.metric("💰 Выручка (всего)", f"{total_revenue:,.0f}₽")

    st.divider()

    # ── New users last 30 days ─────────────────────────────────────────────────
    df_users = _query(
        """SELECT DATE(created_at) AS day, COUNT(*) AS new_users
           FROM users WHERE created_at >= date('now','-30 days')
           GROUP BY day ORDER BY day""",
    )
    if not df_users.empty:
        fig = px.line(
            df_users, x="day", y="new_users",
            title="Новые пользователи — последние 30 дней",
            labels={"day": "Дата", "new_users": "Новых"},
            template="plotly_dark",
        )
        fig.update_traces(line_color="#00d2ff", line_width=2)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Недостаточно данных о пользователях")

    # ── Cumulative paid users vs goal ──────────────────────────────────────────
    df_paid = _query(
        """SELECT DATE(created_at) AS day, COUNT(DISTINCT telegram_id) AS cnt
           FROM payments WHERE status='succeeded'
           GROUP BY day ORDER BY day""",
    )
    if not df_paid.empty:
        df_paid["cumulative"] = df_paid["cnt"].cumsum()
        fig2 = px.line(
            df_paid, x="day", y="cumulative",
            title=f"Накопительно платных пользователей (цель: {GOAL_PAID_USERS})",
            labels={"day": "Дата", "cumulative": "Платных"},
            template="plotly_dark",
        )
        fig2.update_traces(line_color="#ff6b6b")
        # Goal line
        fig2.add_hline(
            y=GOAL_PAID_USERS,
            line_dash="dash",
            line_color="yellow",
            annotation_text=f"Цель: {GOAL_PAID_USERS}",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Feature usage bar chart ────────────────────────────────────────────────
    df_feat = _query(
        """SELECT type, COUNT(*) AS cnt
           FROM generation_logs
           GROUP BY type ORDER BY cnt DESC""",
    )
    if not df_feat.empty:
        # Rename type values to human-readable labels
        label_map = {
            "resume":       "Резюме",
            "cover_letter": "Письма",
            "interview":    "Собеседования",
            "analysis":     "Анализы вакансий",
            "assistant":    "AI-сообщения",
        }
        df_feat["label"] = df_feat["type"].map(label_map).fillna(df_feat["type"])
        fig3 = px.bar(
            df_feat, x="label", y="cnt",
            title="Использование функций (всего)",
            labels={"label": "Функция", "cnt": "Количество"},
            template="plotly_dark",
            color="cnt",
            color_continuous_scale="Blues",
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── Last 10 new users table ────────────────────────────────────────────────
    st.subheader("Последние 10 новых пользователей")
    df_new = _query(
        """SELECT u.telegram_id, u.username, u.full_name,
                  DATE(u.created_at) AS joined,
                  js.source,
                  CASE WHEN p.telegram_id IS NOT NULL THEN '✅' ELSE '—' END AS paid
           FROM users u
           LEFT JOIN join_sources js ON js.user_id = u.telegram_id
           LEFT JOIN (
               SELECT DISTINCT telegram_id FROM payments WHERE status='succeeded'
           ) p ON p.telegram_id = u.telegram_id
           ORDER BY u.created_at DESC LIMIT 10""",
    )
    if not df_new.empty:
        st.dataframe(df_new, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Revenue
# ══════════════════════════════════════════════════════════════════════════════

elif page == "💰 Выручка":
    st.title("💰 Выручка")

    today   = date.today().isoformat()
    week_s  = (date.today() - timedelta(days=7)).isoformat()
    month_s = (date.today() - timedelta(days=30)).isoformat()

    total_rev  = _scalar("SELECT COALESCE(SUM(amount_rub),0) FROM payments WHERE status='succeeded'")
    today_rev  = _scalar(
        "SELECT COALESCE(SUM(amount_rub),0) FROM payments WHERE status='succeeded' AND DATE(created_at)=?",
        (today,)
    )
    week_rev   = _scalar(
        "SELECT COALESCE(SUM(amount_rub),0) FROM payments WHERE status='succeeded' AND DATE(created_at)>=?",
        (week_s,)
    )
    month_rev  = _scalar(
        "SELECT COALESCE(SUM(amount_rub),0) FROM payments WHERE status='succeeded' AND DATE(created_at)>=?",
        (month_s,)
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Всего выручки", f"{total_rev:,.0f}₽")
    c2.metric("📅 Сегодня", f"{today_rev:,.0f}₽")
    c3.metric("📅 Эта неделя", f"{week_rev:,.0f}₽")
    c4.metric("📅 Этот месяц", f"{month_rev:,.0f}₽")

    st.divider()

    # ── Revenue by day bar chart ───────────────────────────────────────────────
    df_rev_day = _query(
        """SELECT DATE(created_at) AS day, SUM(amount_rub) AS revenue
           FROM payments WHERE status='succeeded' AND created_at >= date('now','-30 days')
           GROUP BY day ORDER BY day""",
    )
    if not df_rev_day.empty:
        fig = px.bar(
            df_rev_day, x="day", y="revenue",
            title="Выручка по дням — последние 30 дней",
            labels={"day": "Дата", "revenue": "Выручка (₽)"},
            template="plotly_dark",
            color="revenue",
            color_continuous_scale="Greens",
        )
        st.plotly_chart(fig, use_container_width=True)

    col_l, col_r = st.columns(2)

    # ── Revenue by method (from daily_stats) ──────────────────────────────────
    with col_l:
        df_method = _query(
            """SELECT
                 COALESCE(SUM(revenue_crypto), 0)  AS Крипто,
                 COALESCE(SUM(revenue_card), 0)    AS Карта,
                 COALESCE(SUM(revenue_revolut), 0) AS Revolut
               FROM daily_stats""",
        )
        if not df_method.empty:
            method_data = df_method.iloc[0].to_dict()
            fig_pie = px.pie(
                names=list(method_data.keys()),
                values=list(method_data.values()),
                title="Выручка по способу оплаты",
                template="plotly_dark",
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Данные по методам появятся после первых транзакций через трекер")

    # ── Revenue by plan ────────────────────────────────────────────────────────
    with col_r:
        df_plan = _query(
            """SELECT package, COALESCE(SUM(amount_rub),0) AS revenue
               FROM payments WHERE status='succeeded'
               GROUP BY package ORDER BY revenue DESC""",
        )
        if not df_plan.empty:
            fig_plan = px.pie(
                df_plan, names="package", values="revenue",
                title="Выручка по пакетам",
                template="plotly_dark",
            )
            st.plotly_chart(fig_plan, use_container_width=True)

    # ── Last 20 payments table ─────────────────────────────────────────────────
    st.subheader("Последние 20 платежей")
    df_pays = _query(
        """SELECT id, telegram_id, amount_rub, package, status, created_at
           FROM payments ORDER BY created_at DESC LIMIT 20""",
    )
    if not df_pays.empty:
        st.dataframe(df_pays, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Referrals
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🔗 Рефералы":
    st.title("🔗 Рефералы")

    total_refs = _scalar(
        "SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL"
    )
    paid_via_ref = _scalar(
        """SELECT COUNT(DISTINCT u.telegram_id)
           FROM users u
           JOIN payments p ON p.telegram_id = u.telegram_id
           WHERE u.referred_by IS NOT NULL AND p.status='succeeded'"""
    )
    ref_conversion = round(paid_via_ref / total_refs * 100, 1) if total_refs > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("🔗 Всего рефералов", total_refs)
    c2.metric("💳 Стали платными", paid_via_ref)
    c3.metric("📈 Конверсия рефералов", f"{ref_conversion:.1f}%")

    st.divider()

    # ── Top 10 referrers bar chart ─────────────────────────────────────────────
    df_top = _query(
        """SELECT u.username, u.telegram_id, COUNT(*) AS referred
           FROM users r
           JOIN users u ON u.telegram_id = r.referred_by
           WHERE r.referred_by IS NOT NULL
           GROUP BY r.referred_by
           ORDER BY referred DESC LIMIT 10""",
    )
    if not df_top.empty:
        df_top["label"] = df_top.apply(
            lambda row: f"@{row['username']}" if row["username"] else f"id{row['telegram_id']}",
            axis=1,
        )
        fig = px.bar(
            df_top, x="label", y="referred",
            title="Топ 10 рефереров",
            labels={"label": "Пользователь", "referred": "Приглашённых"},
            template="plotly_dark",
            color="referred",
            color_continuous_scale="Purples",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Рефералов пока нет")

    # ── Referrals per day line chart ───────────────────────────────────────────
    df_ref_day = _query(
        """SELECT DATE(created_at) AS day, COUNT(*) AS cnt
           FROM users WHERE referred_by IS NOT NULL
             AND created_at >= date('now','-30 days')
           GROUP BY day ORDER BY day""",
    )
    if not df_ref_day.empty:
        fig2 = px.line(
            df_ref_day, x="day", y="cnt",
            title="Рефералы по дням — последние 30 дней",
            labels={"day": "Дата", "cnt": "Рефералов"},
            template="plotly_dark",
        )
        fig2.update_traces(line_color="#b44fc9")
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Growth Channels
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📣 Каналы роста":
    st.title("📣 Каналы роста")

    # ── Users by join source ───────────────────────────────────────────────────
    df_src = _query(
        """SELECT source, COUNT(*) AS cnt FROM join_sources GROUP BY source ORDER BY cnt DESC"""
    )
    if not df_src.empty:
        fig = px.bar(
            df_src, x="source", y="cnt",
            title="Пользователи по источнику прихода",
            labels={"source": "Источник", "cnt": "Пользователей"},
            template="plotly_dark",
            color="cnt",
            color_continuous_scale="Oranges",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Данные по источникам появятся после подключения track_start() в /start хэндлере")

    st.divider()

    # ── Outreach messages vs conversions ──────────────────────────────────────
    df_out = _query(
        """SELECT date, messages_sent, estimated_conversions FROM outreach_log ORDER BY date"""
    )
    if not df_out.empty:
        fig2 = px.line(
            df_out, x="date", y=["messages_sent", "estimated_conversions"],
            title="Аутрич: отправлено сообщений vs конверсий",
            labels={"date": "Дата", "value": "Количество", "variable": "Метрика"},
            template="plotly_dark",
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Данные аутрича появятся после вызовов log_outreach()")

    st.divider()

    # ── Content log table + add form ──────────────────────────────────────────
    st.subheader("📝 Контент-лог")
    df_cont = _query(
        """SELECT date, platform, post_title, post_url, estimated_clicks
           FROM content_log ORDER BY date DESC"""
    )
    if not df_cont.empty:
        st.dataframe(df_cont, use_container_width=True)

        # Estimated clicks per day line chart
        df_clicks = _query(
            """SELECT date, SUM(estimated_clicks) AS clicks
               FROM content_log GROUP BY date ORDER BY date"""
        )
        if not df_clicks.empty and df_clicks["clicks"].sum() > 0:
            fig3 = px.line(
                df_clicks, x="date", y="clicks",
                title="Расчётные клики из контента по дням",
                template="plotly_dark",
            )
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Записей в контент-логе пока нет")

    # ── Manual entry form ─────────────────────────────────────────────────────
    with st.expander("➕ Добавить запись в контент-лог"):
        with st.form("content_form"):
            c_date     = st.date_input("Дата публикации", value=date.today())
            c_platform = st.selectbox("Платформа", ["Reddit", "VK", "Telegram", "Habr", "VC.ru", "Другое"])
            c_title    = st.text_input("Заголовок поста")
            c_url      = st.text_input("URL поста")
            c_clicks   = st.number_input("Расчётных кликов", min_value=0, value=0)
            submitted  = st.form_submit_button("Добавить")
        if submitted and c_title:
            import asyncio
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from analytics_db import log_content
            asyncio.run(log_content(c_date.isoformat(), c_platform, c_title, c_url, c_clicks))
            st.success("Запись добавлена!")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Goal Tracker
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🎯 Цель":
    st.title("🎯 Цель: 1000 платных пользователей")

    paid_total = _scalar(
        "SELECT COUNT(DISTINCT telegram_id) FROM payments WHERE status='succeeded'"
    )
    pct = round(paid_total / GOAL_PAID_USERS * 100, 1)

    # ── Big progress bar ───────────────────────────────────────────────────────
    st.progress(min(paid_total / GOAL_PAID_USERS, 1.0))
    st.markdown(
        f"### {paid_total} / {GOAL_PAID_USERS} &nbsp; ({pct:.1f}%)"
    )

    # ── ETA ───────────────────────────────────────────────────────────────────
    df_growth = _query(
        """SELECT AVG(new_paid_users) AS avg7
           FROM daily_stats
           WHERE date >= date('now','-7 days') AND date < date('now')"""
    )
    avg7 = df_growth.iloc[0]["avg7"] if not df_growth.empty and df_growth.iloc[0]["avg7"] else 0

    remaining = max(0, GOAL_PAID_USERS - paid_total)
    if avg7 and avg7 > 0:
        days_left = int(remaining / avg7)
        eta_date  = (date.today() + timedelta(days=days_left)).strftime("%d.%m.%Y")
        st.info(f"📅 При текущем темпе (+{avg7:.1f}/день) цель будет достигнута ~**{eta_date}**")
    else:
        st.info("📅 Недостаточно данных для расчёта срока достижения цели")

    st.divider()

    # ── Daily stats table — last 30 days ──────────────────────────────────────
    st.subheader("Ежедневная статистика — последние 30 дней")
    df_ds = _query(
        """SELECT date, new_users, active_users, new_paid_users, total_paid_users,
                  revenue_crypto + revenue_card + revenue_revolut AS revenue_total,
                  resumes_generated, letters_generated, interviews_done,
                  vacancy_analyses, ai_messages, referrals_made
           FROM daily_stats ORDER BY date DESC LIMIT 30"""
    )
    if not df_ds.empty:
        st.dataframe(df_ds, use_container_width=True)
    else:
        st.info("Данные daily_stats появятся после первых событий")

    # ── Weekly cohort table ────────────────────────────────────────────────────
    st.subheader("Когортный анализ (по неделям)")
    df_cohort = _query(
        """SELECT
             strftime('%Y-W%W', created_at) AS week,
             COUNT(*) AS joined,
             SUM(CASE WHEN DATE(last_active) >= date('now','-7 days') THEN 1 ELSE 0 END) AS active_now,
             ROUND(
               100.0 * SUM(CASE WHEN DATE(last_active) >= date('now','-7 days') THEN 1 ELSE 0 END)
               / COUNT(*), 1
             ) AS retention_pct
           FROM users
           WHERE created_at >= date('now','-90 days')
           GROUP BY week
           ORDER BY week DESC"""
    )
    if not df_cohort.empty:
        st.dataframe(df_cohort, use_container_width=True)
    else:
        st.info("Данные когорт появятся по мере накопления пользователей")

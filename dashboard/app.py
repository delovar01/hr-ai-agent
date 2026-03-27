import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

from src.agent.core import hr_agent
from src.agent.state import agent_state
from config.settings import HR_TOPICS, USER_ROLES, RISK_LEVELS, TIME_RANGES

# Page config
st.set_page_config(
    page_title="HR AI Агент | Сбер",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #21a038;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .insight-card {
        background: var(--secondary-background-color);
        color: var(--text-color);
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #21a038;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .insight-card * {
        color: inherit !important;
    }
    .alert-critical { border-left-color: #FF4444 !important; }
    .alert-high { border-left-color: #FF8C00 !important; }
    .alert-medium { border-left-color: #FFD700 !important; }
    .alert-low { border-left-color: #32CD32 !important; }
    .agent-status {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        font-weight: bold;
    }
    .status-active { background: #d4edda; color: #155724; }
    .status-idle { background: #fff3cd; color: #856404; }
    .run-button button {
        font-size: 1.2rem !important;
        padding: 0.75rem 2rem !important;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "agent_running" not in st.session_state:
        st.session_state.agent_running = False
    if "last_cycle_result" not in st.session_state:
        st.session_state.last_cycle_result = None
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False


def render_sidebar():
    """Render sidebar with agent configuration."""
    st.sidebar.markdown("## ⚙️ Настройки агента")

    # Role selection
    role = st.sidebar.selectbox(
        "Ваша роль",
        options=list(USER_ROLES.keys()),
        format_func=lambda x: USER_ROLES[x]["name"],
        index=0
    )

    # Time range filter
    time_range = st.sidebar.selectbox(
        "⏰ Временной диапазон",
        options=list(TIME_RANGES.keys()),
        format_func=lambda x: TIME_RANGES[x]["label"],
        index=2  # Default: "24h"
    )

    # Topic priorities
    st.sidebar.markdown("### Приоритетные темы")
    selected_topics = []
    for topic_key, topic_name in HR_TOPICS.items():
        if st.sidebar.checkbox(topic_name, value=topic_key in USER_ROLES[role]["focus"]):
            selected_topics.append(topic_key)

    # Risk sensitivity with explanation
    sensitivity = st.sidebar.select_slider(
        "Чувствительность к рискам",
        options=["low", "medium", "high"],
        value="medium",
        format_func=lambda x: {"low": "Низкая", "medium": "Средняя", "high": "Высокая"}[x]
    )

    sensitivity_desc = {
        "low": "Уведомления только при высоком риске (порог 0.7)",
        "medium": "Уведомления при среднем и высоком риске (порог 0.5)",
        "high": "Уведомления при любых отклонениях (порог 0.3)"
    }
    st.sidebar.caption(sensitivity_desc[sensitivity])

    # Apply configuration
    hr_agent.configure(
        role=role,
        topics=selected_topics,
        sensitivity=sensitivity,
        time_range=time_range
    )

    st.sidebar.markdown("---")

    # Status
    status = hr_agent.get_status()
    st.sidebar.markdown("### 📊 Статус агента")
    st.sidebar.metric("Всего наблюдений", status["total_observations"])
    st.sidebar.metric("Инсайтов", status["total_insights"])
    st.sidebar.metric("Уведомлений о рисках", status["pending_alerts"])

    if status["last_check"]:
        last_check = datetime.fromisoformat(status["last_check"])
        st.sidebar.caption(f"Последняя проверка: {last_check.strftime('%H:%M:%S')}")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Сбросить состояние агента"):
        agent_state.reset()
        st.success("Состояние сброшено!")
        st.rerun()


def render_header():
    """Render main header."""
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown('<p class="main-header">🤖 HR AI Агент</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Проактивный мониторинг и аналитика для HR</p>', unsafe_allow_html=True)

    with col2:
        status = hr_agent.get_status()
        if status["last_check"]:
            st.markdown(
                '<span class="agent-status status-active">● Активен</span>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<span class="agent-status status-idle">○ Ожидание</span>',
                unsafe_allow_html=True
            )

    with col3:
        st.markdown(f"**Роль:** {USER_ROLES[hr_agent.user_config['role']]['name']}")
        time_label = TIME_RANGES[hr_agent.user_config.get('time_range', '24h')]['label']
        st.markdown(f"**Период:** {time_label}")
        st.markdown(f"**Дата:** {datetime.now().strftime('%d.%m.%Y')}")


def render_agent_controls():
    """Render agent control panel at the top — the first thing the user sees."""
    st.markdown("### 🚀 Управление агентом")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        run_clicked = st.button(
            "▶️ Запустить цикл анализа",
            use_container_width=True,
            type="primary",
            help="Агент соберёт новости из RSS-источников, переведёт, классифицирует и сгенерирует инсайты через GigaChat"
        )
        if run_clicked:
            with st.spinner("Агент анализирует данные... Это может занять 30-60 секунд."):
                result = hr_agent.run_cycle()
                st.session_state.last_cycle_result = result
            st.rerun()

    with col2:
        st.session_state.auto_refresh = st.checkbox(
            "🔁 Авто-обновление (30 сек)",
            value=st.session_state.auto_refresh
        )

    with col3:
        if st.session_state.last_cycle_result:
            result = st.session_state.last_cycle_result
            debug = result.get("debug_info", {})
            st.caption(
                f"Получено: {debug.get('total_fetched', 0)} новостей | "
                f"Новых: {result.get('new_items', 0)} | "
                f"Инсайтов: {len(result.get('insights_generated', []))}"
            )


def render_metrics():
    """Render key metrics."""
    data = hr_agent.get_dashboard_data()
    metrics = data.get("metrics", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Циклов мониторинга",
            metrics.get("total_sources_checked", 0),
            help="Сколько раз агент проверял источники данных"
        )

    with col2:
        st.metric(
            "Инсайтов",
            metrics.get("total_insights_generated", 0),
            help="Рекомендации, автоматически сгенерированные GigaChat на основе анализа новостей"
        )

    with col3:
        st.metric(
            "Аномалий",
            metrics.get("anomalies_detected", 0),
            help="Резкие отклонения от нормы по какой-либо HR-теме (порог: >30%)"
        )

    with col4:
        alerts = data.get("alerts", [])
        critical_count = len([a for a in alerts if a.get("risk_level") == "critical"])
        st.metric(
            "Критических уведомлений",
            critical_count,
            help="Ситуации, требующие немедленного внимания HR-руководства"
        )


def render_insights():
    """Render proactive insights section."""
    st.markdown("## 💡 Проактивные инсайты")
    st.caption(
        "Инсайт — это рекомендация, которую агент генерирует сам, без запроса пользователя. "
        "На основе собранных новостей GigaChat формулирует: что произошло, почему это важно для HR, "
        "и что конкретно рекомендуется сделать."
    )

    data = hr_agent.get_dashboard_data()
    insights = data.get("insights", [])

    if not insights:
        st.info("💤 Пока нет инсайтов. Нажмите «Запустить цикл анализа» выше — агент соберёт новости и сгенерирует рекомендации.")
        return

    for insight in insights[:5]:
        risk_level = insight.get("risk_level", "medium")
        risk_color = RISK_LEVELS.get(risk_level, {}).get("color", "#666")
        topic_name = insight.get("topic_name", "HR")

        with st.container():
            st.markdown(f"""
            <div class="insight-card alert-{risk_level}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span style="font-weight: bold; font-size: 1.1rem;">📌 {topic_name}</span>
                    <span style="background: {risk_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;">
                        {RISK_LEVELS.get(risk_level, {}).get("label", risk_level)}
                    </span>
                </div>
                <p><strong>Что изменилось:</strong> {insight.get("what_changed", "—")}</p>
                <p><strong>Почему важно:</strong> {insight.get("why_important", "—")}</p>
                <p><strong>Рекомендация:</strong> {insight.get("recommendation", "—")}</p>
                <div style="font-size: 0.8rem; color: #888; margin-top: 0.5rem;">
                    Источник: {insight.get("source", "—")} |
                    Срочность: {{"immediate": "Немедленно", "week": "В течение недели", "month": "В течение месяца"}}.get(insight.get("urgency", "week"), "—")]
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_trends():
    """Render trend charts."""
    st.markdown("## 📈 Тренды по HR-темам")

    data = hr_agent.get_dashboard_data()
    trends = data.get("trends", {})

    tab1, tab2 = st.tabs(["Графики трендов", "Сводная таблица"])

    with tab1:
        cols = st.columns(2)

        for idx, (topic, trend_info) in enumerate(trends.items()):
            with cols[idx % 2]:
                topic_name = HR_TOPICS.get(topic, topic)

                if trend_info.get("data"):
                    df = pd.DataFrame(trend_info["data"])
                    df["timestamp"] = pd.to_datetime(df["timestamp"])

                    fig = px.line(
                        df, x="timestamp", y="value",
                        title=f"{topic_name}",
                        labels={"timestamp": "Время", "value": "Уровень риска"}
                    )
                    fig.update_layout(
                        height=250,
                        margin=dict(l=0, r=0, t=40, b=0),
                        showlegend=False
                    )
                    fig.update_traces(line_color="#21a038")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.markdown(f"**{topic_name}**")
                    st.caption("Недостаточно данных")

    with tab2:
        summary_data = []
        for topic, trend_info in trends.items():
            summary_data.append({
                "Тема": HR_TOPICS.get(topic, topic),
                "Направление": {"up": "↑ Рост", "down": "↓ Снижение", "stable": "→ Стабильно"}.get(trend_info.get("direction", "stable"), "—"),
                "Изменение": f"{trend_info.get('change', 0):.1f}%",
                "Описание": trend_info.get("description", "—")
            })

        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)


def render_alerts():
    """Render risk notifications section."""
    st.markdown("## 🚨 Уведомления о рисках")
    st.caption(
        "Уведомление создаётся автоматически, когда риск-скор новости превышает порог "
        "чувствительности. Чем выше чувствительность (в настройках слева) — тем больше уведомлений."
    )

    data = hr_agent.get_dashboard_data()
    alerts = data.get("alerts", [])

    if not alerts:
        st.success("✅ Нет уведомлений — ситуация стабильная")
        return

    for alert in alerts[:10]:
        risk_level = alert.get("risk_level", "medium")
        risk_info = RISK_LEVELS.get(risk_level, RISK_LEVELS["medium"])

        with st.expander(f"⚠️ {alert.get('title', 'Уведомление')}", expanded=risk_level in ["critical", "high"]):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(alert.get("content", ""))
                st.caption(f"Источник: {alert.get('source', '—')} | Создано: {alert.get('created_at', '—')}")
            with col2:
                st.markdown(
                    f'<div style="background: {risk_info["color"]}; color: white; padding: 10px; '
                    f'border-radius: 5px; text-align: center; font-weight: bold;">'
                    f'{risk_info["label"]}</div>',
                    unsafe_allow_html=True
                )


def render_data_sources():
    """Explain where data comes from."""
    with st.expander("📡 Откуда берутся данные?", expanded=False):
        st.markdown("""
**Агент собирает данные из двух типов источников:**

**1. RSS-ленты (реальные новости):**
| Источник | Язык | Описание |
|----------|------|----------|
| Harvard Business Review | EN | Статьи об управлении и HR |
| SHRM News | EN | Новости от крупнейшей HR-ассоциации |
| VC.ru | RU | Российские бизнес-новости |
| Habr | RU | Технологические новости |
| The Muse | EN | Карьера и рынок труда |
| Hacker News | EN | Технологические тренды |
| Reddit CS Careers | EN | Обсуждения карьеры в IT |

**2. Демо-данные (для демонстрации):**
- Генерируются автоматически для показа работы агента
- Помечены как mock-данные
- Можно отключить в production

**Как агент обрабатывает данные:**
1. Собирает новости из RSS → 2. Переводит через GigaChat → 3. Классифицирует по HR-темам → 4. Считает риск-скор → 5. Генерирует инсайты
        """)


def render_agent_explanation():
    """Render explanation of why this is an agent, not a chatbot."""
    with st.expander("ℹ️ Почему это AI-агент, а не чат-бот?", expanded=False):
        st.markdown("""
### Ключевые отличия от чат-ботов и поисковиков:

| Характеристика | Чат-бот/Поисковик | HR AI Агент |
|----------------|-------------------|-------------|
| **Инициатива** | Ждёт запроса пользователя | Проактивно генерирует инсайты |
| **Память** | Нет памяти между сессиями | Хранит историю наблюдений |
| **Анализ** | Отвечает на вопросы | Выявляет тренды и аномалии |
| **Персонализация** | Через промпты | Через конфигурацию роли |
| **Действия** | Только ответы | Уведомления, рекомендации, прогнозы |

### Что делает агент за один цикл:
1. 🔄 **Мониторит** RSS-ленты и источники данных
2. 🌐 **Переводит** англоязычный контент через GigaChat
3. 🏷️ **Классифицирует** по HR-тематикам (GigaChat)
4. 📊 **Анализирует** тренды и выявляет аномалии
5. 💡 **Генерирует инсайты** — рекомендации без запроса пользователя
6. ⚠️ **Создаёт уведомления** при обнаружении рисков
        """)


def render_glossary():
    """Render glossary of terms used in the dashboard."""
    with st.expander("📖 Глоссарий терминов", expanded=False):
        st.markdown("""
| Термин | Что это значит |
|--------|---------------|
| **Проактивный инсайт** | Рекомендация, которую агент генерирует сам (без запроса). GigaChat анализирует новость и формулирует: что произошло, почему важно, что делать. |
| **Уведомление о риске** | Сигнал о том, что риск-скор новости превысил порог. Чем выше чувствительность — тем ниже порог и больше уведомлений. |
| **Риск-скор** | Числовая оценка от 0.0 до 1.0. Рассчитывается по ключевым словам в тексте. 0.8+ = критический, 0.6+ = высокий, 0.4+ = средний. |
| **Аномалия** | Резкое отклонение риск-скора от среднего (>30%). Означает, что по теме произошло что-то необычное. |
| **Цикл мониторинга** | Один запуск агента: сбор → перевод → классификация → анализ → инсайты. |
| **Чувствительность** | Порог срабатывания уведомлений. Высокая = уведомлять обо всём, низкая = только критичное. |
        """)


def main():
    """Main dashboard function."""
    init_session_state()
    render_sidebar()
    render_header()

    st.markdown("---")

    # Agent controls — first thing the user sees
    render_agent_controls()

    st.markdown("---")

    # Metrics row
    render_metrics()

    st.markdown("---")

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        render_insights()

    with col2:
        render_alerts()

    st.markdown("---")

    render_trends()

    st.markdown("---")

    # Info sections
    render_data_sources()
    render_agent_explanation()
    render_glossary()

    # Auto-refresh
    if st.session_state.auto_refresh:
        time.sleep(30)
        result = hr_agent.run_cycle()
        st.session_state.last_cycle_result = result
        st.rerun()


if __name__ == "__main__":
    main()

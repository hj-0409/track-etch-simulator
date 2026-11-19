import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import streamlit as st

st.set_page_config(
    page_title="Photo Track & Etch Virtual Process Simulator",
    layout="wide",
)

st.title("🧪 Photo Track & Etch Virtual Process Simulator")
st.markdown(
    "반도체 Photo Track(스핀 코터·베이킹)과 Etch(식각) 공정의 주요 설비 파라미터가 "
    "박막 두께, 균일도, 식각률·선택비 및 단면 프로파일에 미치는 물리적 경향성을 시뮬레이션합니다."
)
st.markdown("---")

tab_track, tab_etch, tab_limits = st.tabs([
    "🌀 1. Photo Track (Spin Coater & Bake)",
    "⚡ 2. Plasma Etch (Rate, Selectivity & Profile)",
    "📐 3. 모델 가정 및 한계점 (Engineering Notes)",
])

# ==============================================================================
# TAB 1: Photo Track 시뮬레이터
# ==============================================================================
with tab_track:
    st.subheader("스핀 코터(Spin Coater) & 열판(Bake Plate) 경향성 시뮬레이터")

    col_ctrl, col_vis = st.columns([1, 1.4])

    with col_ctrl:
        rpm = st.slider("스핀 회전속도 (RPM)", min_value=500, max_value=5000, value=2500, step=100)
        viscosity = st.slider("PR 점도 (cP, 상대 지수)", min_value=5.0, max_value=50.0, value=18.0, step=1.0)
        bake_temp = st.slider("Soft Bake / PEB 온도 (°C)", min_value=80, max_value=140, value=105, step=5)
        target_thickness = st.number_input("목표 PR 두께 (nm, 역산 추천용)", min_value=100.0, max_value=3000.0, value=650.0, step=50.0)

        # 단순화된 해석적 경향성 모델 (가정: 두께 t ∝ viscosity^0.5 / rpm^0.5, 고온 Bake 시 소폭 수축)
        # 기준점(RPM=2500, 점도=18cP, 105°C)에서 약 650nm 수준이 나오도록 스케일링
        shrink_factor = 1.0 - max(0.0, (bake_temp - 105) * 0.0012)
        thickness_nm = 650.0 * ((viscosity / 18.0) ** 0.5) * ((2500.0 / rpm) ** 0.5) * shrink_factor

        # 고속 RPM일수록 원심력 구배로 외곽 두께 편차(WIWNU %) 증가 경향 반영 (단순화 선형 경향성 모델)
        wiwnu_pct = 1.2 + (rpm / 5000.0) * 3.8 + max(0.0, (105 - bake_temp) * 0.03)

        # 목표 두께 달성을 위한 권장 RPM 역산 (현재 점도·온도 기준)
        base_ratio = (viscosity / 18.0) ** 0.5 * shrink_factor * 650.0 / target_thickness
        raw_recommended_rpm = 2500.0 * (base_ratio ** 2)
        recommended_rpm = int(np.clip(raw_recommended_rpm, 500, 5000))

        if raw_recommended_rpm < 500:
            st.warning(
                f"⚠️ 현재 점도({viscosity:.0f} cP)에서는 목표 두께({target_thickness:.0f} nm) 달성을 위한 "
                f"이론 RPM({raw_recommended_rpm:.0f} RPM)이 최소 회전수(500 RPM) 미만입니다. 더 높은 점도의 PR 선택이 필요합니다."
            )
        elif raw_recommended_rpm > 5000:
            st.warning(
                f"⚠️ 현재 점도({viscosity:.0f} cP)에서는 목표 두께({target_thickness:.0f} nm) 달성을 위한 "
                f"이론 RPM({raw_recommended_rpm:.0f} RPM)이 최대 회전수(5000 RPM)를 초과합니다. 더 낮은 점도의 PR 선택이 필요합니다."
            )
        else:
            st.info(f"✅ 현재 점도·Bake 조건에서 목표 두께 달성을 위한 권장 회전속도는 **{recommended_rpm} RPM**입니다.")

    with col_vis:
        m1, m2, m3 = st.columns(3)
        m1.metric("예상 PR 두께", f"{thickness_nm:.1f} nm")
        m2.metric("추정 균일도 (WIWNU)", f"±{wiwnu_pct:.2f} %")
        m3.metric("목표 두께 권장 RPM", f"{recommended_rpm} RPM")
        st.caption("※ WIWNU(%)는 고속 회전 시 외곽 두께 편차 증가를 반영한 단순화 선형 경향성 지표입니다.")

        # RPM 스윕 곡선
        rpm_grid = np.linspace(500, 5000, 100)
        thick_curve = 650.0 * ((viscosity / 18.0) ** 0.5) * ((2500.0 / rpm_grid) ** 0.5) * shrink_factor

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(rpm_grid, thick_curve, color="#2563eb", linewidth=2, label="Thickness vs. RPM")
        ax.scatter([rpm], [thickness_nm], color="#dc2626", zorder=5, label=f"Current ({rpm} RPM, {thickness_nm:.0f} nm)")
        ax.axhline(target_thickness, color="#16a34a", linestyle="--", alpha=0.8, label=f"Target ({target_thickness:.0f} nm)")
        ax.set_title("Spin Speed vs. Photoresist Thickness (Simplified Trend)", fontweight="bold")
        ax.set_xlabel("Spin Speed (RPM)")
        ax.set_ylabel("Film Thickness (nm)")
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend()
        st.pyplot(fig, use_container_width=True)

# ==============================================================================
# TAB 2: Plasma Etch 시뮬레이터
# ==============================================================================
with tab_etch:
    st.subheader("플라즈마 식각(Etch) 식각률·선택비·단면 프로파일 시뮬레이터")

    col_ectrl, col_evis = st.columns([1, 1.4])

    with col_ectrl:
        rf_power = st.slider("RF Source Power (W)", min_value=200, max_value=1500, value=800, step=50)
        chamber_press = st.slider("챔버 압력 (mTorr)", min_value=5, max_value=80, value=25, step=5)
        aniso_ratio = st.slider("이방성 제어 지수 (바이어스/측벽 보호 비율)", min_value=0.1, max_value=1.0, value=0.75, step=0.05)
        etch_time = st.slider("식각 시간 (sec)", min_value=10, max_value=120, value=45, step=5)
        target_depth = st.number_input("목표 식각 깊이 (nm)", min_value=20.0, max_value=500.0, value=100.0, step=10.0)

        # 단순화된 식각률(nm/min) 및 선택비 경향성 모델
        etch_rate_nm_min = 120.0 * ((rf_power / 800.0) ** 0.85) * ((chamber_press / 25.0) ** 0.25)
        etched_depth_nm = etch_rate_nm_min * (etch_time / 60.0)
        selectivity = max(2.0, 18.0 - (rf_power - 500) * 0.006 - max(0.0, chamber_press - 30) * 0.08)
        depth_progress_pct = (etched_depth_nm / target_depth) * 100.0

        if depth_progress_pct < 95.0:
            st.warning(f"⏳ 목표 깊이 대비 **{depth_progress_pct:.1f}%** 진행 (Under-etch 상태: 식각 시간 또는 파워 보완 검토)")
        elif depth_progress_pct <= 115.0:
            st.success(f"✅ 목표 깊이 대비 **{depth_progress_pct:.1f}%** 도달 (적정 Etch / 경미한 Over-etch 구간)")
        else:
            st.error(f"⚠️ 목표 깊이 대비 **{depth_progress_pct:.1f}%** 초과 (과도한 Over-etch: 하부막 손상 및 선택비 저하 주의)")

    with col_evis:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("추정 식각률", f"{etch_rate_nm_min:.1f} nm/min")
        e2.metric("누적 식각 깊이", f"{etched_depth_nm:.1f} nm")
        e3.metric("목표 대비 진행률", f"{depth_progress_pct:.1f} %")
        e4.metric("추정 선택비 (PR 대비)", f"{selectivity:.1f} : 1")
        st.caption("※ 트레이드오프: RF Power 상승 시 식각률은 빨라지나, 이온 충격 증가로 PR 대비 선택비(Selectivity)는 감소하는 경향을 반영했습니다.")

        # 트렌치/홀 단면 프로파일 시각화 (정규화 좌표)
        x_prof = np.linspace(-1.0, 1.0, 200)
        mask_open = np.abs(x_prof) <= 0.45

        # 등방성 성분 + 이방성(수직) 성분 결합
        iso_component = (1.0 - aniso_ratio) * 0.45 * np.clip(1.0 - (np.abs(x_prof) - 0.45) / 0.35, 0.0, 1.0)
        depth_norm = min(1.0, etched_depth_nm / 500.0)
        target_norm = min(1.0, target_depth / 500.0)
        vertical_trench = np.where(mask_open, depth_norm, 0.0)
        undercut_profile = np.where(~mask_open, iso_component * depth_norm, 0.0)

        # 초기 웨이퍼 표면(y=0) 아래로 파고드는 형태
        y_surface = -np.maximum(vertical_trench, undercut_profile)

        fig_e, ax_e = plt.subplots(figsize=(7, 4))
        ax_e.fill_between(x_prof, y_surface, -1.2, color="#94a3b8", alpha=0.55, label="Substrate")
        ax_e.plot(x_prof, y_surface, color="#0f172a", linewidth=2, label="Etched Profile")
        ax_e.axhline(-target_norm, color="#16a34a", linestyle="--", linewidth=1.3, label=f"Target Depth ({target_depth:.0f} nm)")
        # 마스크 영역 표시
        ax_e.hlines(0.08, -1.0, -0.45, colors="#f59e0b", linewidth=6, label="PR Mask")
        ax_e.hlines(0.08, 0.45, 1.0, colors="#f59e0b", linewidth=6)
        ax_e.set_ylim(-1.15, 0.25)
        ax_e.set_xlim(-1.0, 1.0)
        ax_e.set_title("Cross-Section Profile Trend (Isotropic vs. Anisotropic)", fontweight="bold")
        ax_e.set_xlabel("Normalized Position across Feature")
        ax_e.set_ylabel("Normalized Depth / Profile")
        ax_e.grid(True, linestyle=":", alpha=0.5)
        ax_e.legend(loc="lower right")
        st.pyplot(fig_e, use_container_width=True)

# ==============================================================================
# TAB 3: 모델 가정 및 한계점
# ==============================================================================
with tab_limits:
    st.subheader("물리 모델링 가정 및 한계점 (면접·검증용 기준)")

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("#### 🌀 Photo Track 모델 가정 및 배제 변수")
        st.markdown(
            """
- **적용 수식 경향:** 스핀 코팅 최종 두께는 점도의 제곱근에 비례하고 회전속도(RPM)의 제곱근에 반비례($t \\propto \\mu^{0.5} / \\omega^{0.5}$)한다는 고전적 스핀 코팅 근사식을 기준으로 기준점 스케일링했습니다.
- **단순화 및 배제 항목:** 용매 휘발 속도(Evaporation rate), 디스펜스 노즐 이동·토출량, 컵(Cup) 배기 유량, 열판(Bake Plate) 존별 온도 편차 및 웨이퍼 에지 비드(Edge Bead) 현상은 모델에서 제외했습니다.
- **WIWNU 가정:** 고속 회전 시 원심력 구배로 인해 외곽 편차가 커지는 경향을 1차 선형식으로 단순화했습니다.
            """
        )

    with col_l2:
        st.markdown("#### ⚡ Plasma Etch 모델 가정 및 배제 변수")
        st.markdown(
            """
- **적용 수식 경향:** RF Power 증가에 따른 플라즈마 밀도·이온 에너지 상승으로 식각률이 증가하되, 물리적 스퍼터링 비중이 커져 PR 대비 선택비(Selectivity)는 감소하는 트레이드오프를 반영했습니다.
- **단순화 및 배제 항목:** 실제 식각 가스 화학종($\\text{CF}_4$, $\\text{SF}_6$, $\\text{Cl}_2$, $\\text{O}_2$ 등) 비율, 라디칼 대 이온 플럭스 비율, 측벽 폴리머 패시베이션 두께, 종횡비 의존 식각(ARDE/Micro-loading) 및 챔버 월 컨디션 변화는 포함하지 않았습니다.
- **프로파일 표현:** 단면 프로파일은 등방성(언더컷)과 이방성(수직 식각)의 상대 비율을 시각적으로 비교하기 위한 정규화 2D 근사 그래프입니다.
            """
        )

    st.info(
        "📌 **핵심 결론:** 본 시뮬레이터는 공정 파라미터 변화에 따른 물리적 경향성과 트레이드오프를 직관적으로 학습·시연하기 위한 1차 해석 모델이며, 실제 양산 팹의 레시피나 설비 세팅값을 대체할 수 없습니다."
    )

# ==============================================================================
# Gemini AI 공정/설비 엔지니어 보조 진단
# ==============================================================================
st.markdown("---")
st.subheader("🤖 Gemini AI 공정/설비 엔지니어 점검 가이드")

if st.button("🚀 현재 시뮬레이션 조건 기반 점검 포인트 생성", type="primary"):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        st.warning("⚠️ `GEMINI_API_KEY`가 설정되지 않았습니다. Streamlit Secrets 또는 환경변수를 확인해 주세요.")
    else:
        prompt = (
            "너는 반도체 Photo Track 및 식각(Etch) 설비/공정 엔지니어링 학습을 돕는 기술 멘토다.\n"
            "단순화된 시뮬레이션 기준값은 다음과 같다.\n"
            f"- Track 조건: RPM={rpm}, 점도={viscosity}cP, Bake={bake_temp}°C -> 예상 두께={thickness_nm:.1f}nm, WIWNU=±{wiwnu_pct:.2f}%, 목표 두께={target_thickness:.0f}nm(권장 RPM={recommended_rpm})\n"
            f"- Etch 조건: RF Power={rf_power}W, 압력={chamber_press}mTorr, 이방성 지수={aniso_ratio}, 시간={etch_time}s -> 식각률={etch_rate_nm_min:.1f}nm/min, 깊이={etched_depth_nm:.1f}nm(목표 {target_depth:.0f}nm 대비 {depth_progress_pct:.1f}%), 선택비={selectivity:.1f}:1\n\n"
            "실제 양산 설비/공정 관점에서 다음 3가지만 간결하게 정리해 줘(확정 진단이 아닌 점검 가설 위주로 작성):\n"
            "1) 두께/균일도 또는 식각률/선택비 변화 시 우선 점검할 공정·장비 변수\n"
            "2) 공정 편차 발생 시 확인해야 할 트레이드오프\n"
            "3) 이 시뮬레이션 모델이 놓치고 있는 실제 팹 변수 1~2가지"
        )
        models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        with st.spinner("🤖 점검 포인트를 정리 중입니다..."):
            try:
                session = requests.Session()
                retry = Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[502, 503, 504],
                    raise_on_status=False,
                )
                session.mount("https://", HTTPAdapter(max_retries=retry))

                success_text = None
                last_status = None
                last_detail = None

                for model_name in models_to_try:
                    url = (
                        f"https://generativelanguage.googleapis.com/v1beta/models/"
                        f"{model_name}:generateContent?key={api_key}"
                    )
                    resp = session.post(url, headers=headers, json=payload, timeout=30)
                    last_status = resp.status_code

                    if resp.status_code == 200:
                        data = resp.json()
                        if "candidates" in data and data["candidates"]:
                            parts = data["candidates"][0].get("content", {}).get("parts", [])
                            if parts and "text" in parts[0]:
                                success_text = parts[0]["text"].strip()
                                break
                        last_detail = f"응답 형식 오류: {data}"
                        break
                    elif resp.status_code == 404:
                        last_detail = f"모델({model_name}) 404 — 다음 모델로 재시도 중"
                        continue
                    else:
                        last_detail = f"API 서버 상태 코드: {resp.status_code} ({resp.text[:200]})"
                        break

                if success_text:
                    st.success(success_text)
                else:
                    st.error(f"⚠️ {last_detail or f'API 요청 실패 (상태 코드: {last_status})'}")
            except Exception as e:
                st.error(f"요청 실패: {e}")
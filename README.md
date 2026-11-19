# 🧪 Photo Track & Etch Virtual Process Simulator

반도체 **Photo Track(Spin Coater · Bake Plate)** 및 **Plasma Etch** 공정의 주요 설비 파라미터 변화가 박막 두께, 균일도(WIWNU), 식각률(Etch Rate), 선택비(Selectivity), 단면 프로파일에 미치는 **물리적 경향성과 트레이드오프**를 탐색하기 위한 Streamlit 웹 시뮬레이터입니다.

> **Engineering Notice:** 본 프로젝트는 반도체 공정·설비 원리 학습 및 포트폴리오 시연 목적의 **1차 해석 경향성 모델**입니다. 실제 양산 팹(Fab)의 공정 레시피, 화학반응·플라즈마 물리 해석 결과, 설비 세팅값을 대체하지 않습니다.

---

## 🔗 Live Demo & Screen Capture

- **Live App:** https://track-etch-simulator-mfvomdxzufhgujx62st4nl.streamlit.app/
- **Screen Captures:**
  - `assets/track_tab.png` — Photo Track 파라미터 조절, 두께-RPM 스윕 곡선 및 권장 RPM 역산 화면
  - `assets/etch_tab.png` — Plasma Etch 식각률·선택비·목표 깊이 진행률 및 2D 단면 프로파일 화면
  - `assets/limits_tab.png` — Track/Etch 모델링 가정, 배제 변수 및 한계점 정리 화면

---

## 🎯 프로젝트 설계 의도 및 핵심 포인트

- **단순 곡선 생성이 아닌 경향성·트레이드오프 시각화:** 공정 변수를 바꿀 때 어떤 지표가 개선되고 어떤 지표가 손해를 보는지(예: Etch에서 RF Power 상승 시 식각률은 증가하지만 PR 선택비는 감소하는 경향)를 직관적으로 확인하도록 구성했습니다.
- **역산 및 공정 진행 상태 피드백:** Photo Track에서는 목표 PR 두께에 대응하는 권장 RPM을 역산하고 슬라이더 범위 이탈 시 점도 조정을 안내하며, Etch에서는 목표 식각 깊이 대비 진행률과 Under/Over-etch 구간을 표시합니다.
- **AI 기능의 현실적 포지셔닝:** Gemini API 연동 점검 가이드는 '정답 진단기'가 아니라 현재 시뮬레이션 조건에서 **우선 점검할 변수·트레이드오프·놓친 팹 변수 가설**을 정리하는 보조 도구로 설계했습니다.

---

## 📊 주요 파라미터 및 트레이드오프 요약

| 공정 구분 | 조절 변수 | 주요 출력 지표 | 핵심 경향성 및 트레이드오프 |
| :--- | :--- | :--- | :--- |
| **Photo Track** | RPM, PR 점도(cP), Bake 온도(°C), 목표 두께(nm) | 예상 두께(nm), WIWNU(%), 권장 RPM | 점도↑·RPM↓일수록 두께↑ 경향; 고속 RPM 영역에서는 외곽 두께 편차(WIWNU) 증가 리스크 고려 |
| **Plasma Etch** | RF Power(W), 압력(mTorr), 이방성 지수, 시간(s), 목표 깊이(nm) | 식각률(nm/min), 누적 깊이(nm), 진행률(%), 선택비 | RF Power·압력 변화에 따라 식각률 경향이 달라지며, 고파워/고압 조건에서는 선택비 저하 트레이드오프 발생 |

---

## ⚠️ 모델 가정 및 실제 팹 설비와의 한계점

### 1. Photo Track 모델 한계
- 스핀 코팅 두께 경향($t \propto \mu^{0.5} / \omega^{0.5}$ 기반 스케일링)과 Bake 수축·WIWNU를 단순화한 1차 모델입니다.
- **미반영 요소:** 용매 증발 kinetics, 디스펜스 노즐/토출량/컵 배기 유량, 열판(Bake Plate) 존별 온도 균일도, 에지 비드(Edge Bead) 제거 및 고속 회전 시 젖음(wetting)·외곽 편차의 비선형 거동.

### 2. Plasma Etch 모델 한계
- RF Power, 챔버 압력, 이방성 제어 지수, 식각 시간에 따른 대표 경향과 2D 단면 프로파일 근사치를 보여줍니다.
- **미반영 요소:** 식각 가스 화학종($\text{CF}_4$, $\text{SF}_6$, $\text{Cl}_2$, $\text{O}_2$ 등) 조성·유량, 라디칼/이온 플럭스 비율, 측벽 폴리머 패시베이션, 종횡비 의존 식각(ARDE/Micro-loading), 챔버 월(Chamber wall) 상태 변화.

---

## 💻 로컬 실행 및 환경 설정

```bash
pip install -r requirements.txt
streamlit run process_sim_app.py
import time
import streamlit as st


def show_analyze() -> None:
    user = st.session_state.user

    st.markdown(
        '<div style="margin-bottom:1rem">'
        '<div style="font-size:1.4rem;font-weight:700;color:#0F172A">🔬 Analyse Medication</div>'
        '<div style="color:#64748B;font-size:0.95rem;margin-top:0.2rem">'
        "Upload a photo of your pill bottle or pills for AI-powered safety analysis."
        "</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="background:#F0FDFA;border:1px solid #99F6E4;border-radius:10px;'
        'padding:0.75rem 1rem;margin-bottom:1.25rem;color:#0F766E;font-size:0.875rem">'
        "🤖 <strong>AI-Powered Analysis</strong> — our computer vision model identifies "
        "medications and provides safety guidance. Always verify with your pharmacist or doctor."
        "</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        st.markdown("##### Upload Image")
        uploaded = st.file_uploader(
            "Drag & drop or click to upload",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )

        if uploaded:
            st.image(uploaded, caption=uploaded.name, use_container_width=True)
            run = st.button(
                "🔬  Analyse Now", type="primary", use_container_width=True
            )
        else:
            st.markdown(
                '<div style="border:2px dashed #CBD5E1;border-radius:12px;padding:3rem 2rem;'
                'text-align:center;background:#F8FAFC">'
                '<div style="font-size:2.5rem">📷</div>'
                '<div style="color:#64748B;font-size:0.95rem;margin-top:0.5rem">'
                "Drop a pill bottle or pill image here</div>"
                '<div style="color:#94A3B8;font-size:0.8rem;margin-top:0.2rem">'
                "JPG · PNG · WEBP · up to 10 MB</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            run = False

    with right:
        result = st.session_state.get("analysis_result")
        if result:
            st.markdown("##### Results")

            st.markdown(
                f'<div style="background:#F0FDFA;border:1px solid #99F6E4;border-radius:10px;'
                f'padding:1rem 1.25rem;margin-bottom:1rem">'
                f'<div style="color:#64748B;font-size:0.75rem;font-weight:600;letter-spacing:0.05em">'
                f"CONFIDENCE</div>"
                f'<div style="font-size:2.2rem;font-weight:800;color:#0D9488">'
                f'{result["confidence"]}%</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

            for label, value in result["details"].items():
                c1, c2 = st.columns([1, 1.6])
                with c1:
                    st.markdown(
                        f'<span style="font-size:0.875rem;font-weight:600;color:#475569">'
                        f"{label}</span>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown(
                        f'<span style="font-size:0.875rem;color:#0F172A">{value}</span>',
                        unsafe_allow_html=True,
                    )

            st.markdown("---")
            st.markdown("##### 🤖 AI Guidance")
            st.markdown(
                f'<div style="background:#F0FDFA;border:1px solid #A7F3D0;border-radius:10px;'
                f'padding:1rem 1.25rem;color:#065F46;font-size:0.9rem;line-height:1.6">'
                f'{result["guidance"]}'
                f"</div>",
                unsafe_allow_html=True,
            )
            st.caption(
                "⚠️ AI-generated analysis for informational purposes only. "
                "Always consult your pharmacist or doctor."
            )

            if st.button("Analyse Another →", use_container_width=True):
                st.session_state.analysis_result = None
                st.rerun()
        else:
            st.markdown(
                '<div style="border:1px solid #E2E8F0;border-radius:12px;padding:3rem 2rem;'
                'text-align:center;background:white;height:100%">'
                '<div style="font-size:2.5rem">📊</div>'
                '<div style="color:#64748B;font-size:0.95rem;margin-top:0.5rem">Results will appear here</div>'
                '<div style="color:#94A3B8;font-size:0.85rem;margin-top:0.25rem">'
                "Upload an image and click Analyse Now</div>"
                "</div>",
                unsafe_allow_html=True,
            )

    # Run analysis
    if run and uploaded:
        with st.spinner("Analysing your medication image…"):
            time.sleep(1.5)

        # Demo result — real ML pipeline plugs in here (Sprint 4)
        st.session_state.analysis_result = {
            "confidence": 87,
            "details": {
                "Medication": "Metformin 500 mg",
                "Pill Count": "~30 tablets",
                "Colour / Shape": "White, round",
                "Label Match": "✅ Prescription label detected",
                "Expiry": "Dec 2026",
            },
            "guidance": (
                "<strong>Metformin 500 mg</strong> is commonly prescribed for Type 2 diabetes. "
                "Take with meals to reduce stomach upset. "
                "Do not crush or chew extended-release tablets. "
                "Store at room temperature, away from moisture and heat. "
                "Contact your doctor if you experience unusual muscle pain, "
                "difficulty breathing, or stomach pain."
            ),
        }

        try:
            from st_db import db_save_analysis
            db_save_analysis(
                user_id=user["id"],
                filename=uploaded.name,
                guidance=st.session_state.analysis_result["guidance"],
            )
            # Refresh medications_analyzed count in session
            st.session_state.user["medications_analyzed"] = (
                st.session_state.user.get("medications_analyzed", 0) + 1
            )
        except Exception:
            pass  # non-critical side-effect

        st.rerun()

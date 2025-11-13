import streamlit as st
import os
import json
import subprocess
from pathlib import Path
import requests
import pandas as pd

st.set_page_config(page_title="LLM Eval Demo", layout="wide")

st.title("LLM Evaluation — Streamlit Demo")

st.markdown("This demo runs a synchronous local evaluation using the `mock` engine and shows per-case results.")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RESULTS_DIR = DATA_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DATA = DATA_DIR / "sample_dataset_v1.json"

st.sidebar.header("Actions")
mode = st.sidebar.selectbox("Run mode", ["local-sync", "api-async"], index=0)

if mode == "local-sync":
    st.sidebar.write("Runs the synchronous local runner without Redis. Results are written to data/results/")
    if st.sidebar.button("Run local sync evaluation"):
        cmd = ["python", "backend/scripts/run_sync_evaluation.py", "--dataset", str(SAMPLE_DATA)]
        st.sidebar.write("Running:", " ".join(cmd))
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            st.sidebar.success("Run finished")
            st.code(proc.stdout[:1000])
        except subprocess.CalledProcessError as e:
            st.sidebar.error("Run failed")
            st.code(e.stdout)
            st.code(e.stderr)

if mode == "api-async":
    st.sidebar.write("Use the backend API to upload dataset and create async evaluation (requires backend + worker).")
    api_url = st.sidebar.text_input("Backend URL", "http://127.0.0.1:8000")
    tenant = st.sidebar.text_input("Tenant ID", "local")
    api_key = st.sidebar.text_input("X-API-Key (DEV)", "", type="password")
    if st.sidebar.button("Upload sample dataset & create async job"):
        import requests
        files = {"file": open(str(SAMPLE_DATA), "rb")}
        headers = {"X-API-Key": api_key} if api_key else {}
        try:
            r = requests.post(f"{api_url}/api/v1/tenants/{tenant}/datasets", files=files, headers=headers)
            r.raise_for_status()
            j = r.json()
            st.success(f"Uploaded dataset: {j.get('dataset_id')}")
            dataset_id = j.get("dataset_id")
            payload = {
                "dataset_id": dataset_id,
                "case_filters": {},
                "engine_selector": {"primary": "mock"},
                "evaluation_config": {"metrics": [{"id": "clarity", "weight": 0.2},{"id":"accuracy","weight":0.2}]},
                "mode": "async"
            }
            r2 = requests.post(f"{api_url}/api/v1/tenants/{tenant}/evaluations", json=payload, headers=headers)
            r2.raise_for_status()
            job_id = r2.json().get("job_id")
            st.success("Created job: " + str(job_id))
            # Poll for results (demo): call the results endpoint until available
            placeholder = st.empty()
            import time
            for i in range(60):
                try:
                    rr = requests.get(f"{api_url}/api/v1/tenants/{tenant}/evaluations/{job_id}/results", headers=headers, timeout=5)
                    if rr.status_code == 200:
                        data = rr.json()
                        results = data.get("results", [])
                        placeholder.success(f"Results ready: {len(results)} cases")
                        for r in results:
                            with st.expander(r.get("case_id") + " — " + str(round(r.get("aggregated_score", 0), 2))):
                                st.json(r)
                        break
                    else:
                        placeholder.info(f"Waiting for results... attempt {i+1}/60")
                except Exception:
                    placeholder.info(f"Waiting for results... attempt {i+1}/60")
                time.sleep(2)
        except Exception as e:
            st.error(str(e))

st.header("Results viewer")
st.write("Pick a results file produced by the local runner (NDJSON).")
files = list(RESULTS_DIR.glob("results_*.ndjson"))
sel = st.selectbox("Results file", [str(p.name) for p in files]) if files else None
if sel:
    p = RESULTS_DIR / sel
    with open(p, "r", encoding="utf-8") as f:
        lines = [json.loads(l) for l in f.read().splitlines() if l.strip()]
    st.write(f"Loaded {len(lines)} case results from {sel}")
    for r in lines:
        with st.expander(f"{r.get('case_id')} — score {r.get('aggregated_score'):.2f}"):
            st.json(r)


st.markdown("## Dashboard")
st.write("Visualize metric distributions and compare jobs via the backend API.")
api_url = st.text_input("Backend URL for dashboard", "http://127.0.0.1:8000")
tenant = st.text_input("Tenant ID", "local")

with st.expander("Metric distribution"):
    metric = st.selectbox("Metric", ["clarity", "completeness", "accuracy", "appropriateness", "multimodal_appropriateness"], index=0)
    job_for_dist = st.text_input("Job ID for distribution", "local-sync")
    group_by = st.selectbox("Group by (optional)", ["", "grade", "subject"], index=0)
    if st.button("Fetch distribution"):
        try:
            r = requests.get(f"{api_url}/api/v1/tenants/{tenant}/evaluations/{job_for_dist}/metrics/distribution?metric={metric}" + (f"&group_by={group_by}" if group_by else ""))
            r.raise_for_status()
            data = r.json()
            buckets = data.get("buckets", [])
            labels = ["0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]
            df = pd.DataFrame({"count": buckets}, index=labels)
            st.bar_chart(df)
            groups = data.get("groups", {})
            if groups:
                st.write("Groups:")
                for k, v in groups.items():
                    st.write(k)
                    st.bar_chart(pd.DataFrame({"count": v}, index=labels))
        except Exception as e:
            st.error(f"Failed to fetch distribution: {e}")

with st.expander("Compare jobs"):
    job_ids = st.text_input("Comma-separated job ids to compare", "local-sync")
    if st.button("Compare"):
        try:
            r = requests.get(f"{api_url}/api/v1/tenants/{tenant}/evaluations/comparison?job_ids={job_ids}")
            r.raise_for_status()
            js = r.json()
            comp = js.get("comparison", {})
            # build dataframe of per-metric averages
            rows = {}
            for jid, info in comp.items():
                per = info.get("per_metric_avg") or {}
                for m, v in per.items():
                    rows.setdefault(m, {})[jid] = v
            if rows:
                df = pd.DataFrame(rows).T
                st.dataframe(df)
                # allow selecting a metric to chart
                sel_metric = st.selectbox("Metric to plot", df.index.tolist())
                if sel_metric:
                    plot_df = df.loc[[sel_metric]].T
                    plot_df.columns = [sel_metric]
                    st.bar_chart(plot_df)
        except Exception as e:
            st.error(f"Comparison failed: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("Data files:")
for p in [SAMPLE_DATA]:
    st.sidebar.write(p.name)

st.markdown("---")
st.caption("This demo is a lightweight local UI. For production use, connect to the backend API and run workers in background.")

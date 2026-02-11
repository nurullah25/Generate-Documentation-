import os
import re
import datetime
import streamlit as st
import subprocess
import platform
import base64
import zipfile
from jinja2 import Environment, FileSystemLoader
from pdf_utils import html_to_pdf
from pypdf import PdfReader, PdfWriter

st.set_page_config(page_title="AERP DocGen", page_icon="📄", layout="wide")
st.markdown("""
<style>
            /* Style only the primary button (your Generate PDF button) */
            div[data-testid="stButton"] > button[kind="primary"] {
            background-color: #007bff !important;
            color: #white !important;
            border: 1px solid rgb(127 138 199 / 40%) !important;
            border-radius: 6px !important;
            padding: 0px !important;
            margin-top: 26px !important;
            font-weight: 600 !important;
            }
            div[data-testid="stButton"] > button[kind="primary"]:hover {
            filter: brightness(0.95);
            }

            .st-emotion-cache-1frkdi4 h1 {
    font-size: 2.75rem;
    font-weight: 700;
    padding: 1.25rem 0px 1rem;
    margin-top: -71px;
}
</style>
""", unsafe_allow_html=True)

TEMPLATE_DIR = "templates"
ASSET_CSS_PATH = os.path.join("assets", "style.css")
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def open_file(path: str):
    if platform.system() == "Windows":
        os.startfile(path)  # type: ignore
    elif platform.system() == "Darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)

def load_css() -> str:
    with open(ASSET_CSS_PATH, "r", encoding="utf-8") as f:
        return f.read()

def render_html(project: dict, modules: list,attachments:dict) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("doc.html")
    css = load_css()
    return template.render(project=project, modules=modules, css=css, attachments=attachments)

def safe_filename(name: str) -> str:
    name=name or "file"
    return re.sub(r'[^a-zA-Z0-9._-]', '_', name)

def merge_pdfs(pdf_paths: list, output_path: str) -> None:
    writer = PdfWriter()
    for path in pdf_paths:
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)

def make_zip(zip_path: str, files: list) -> None:
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for fpath,arcname in files:
            z.write(fpath, arcname)

st.title("📄 AERP Documentation Generator")
st.caption("Fill in your ERP info → preview → export PDF")

# Session storage so modules persist while you edit
if "modules" not in st.session_state:
    st.session_state.modules = []    

if "attachments" not in st.session_state:
    st.session_state.attachments = []

if "mod_uploader_key" not in st.session_state:
    st.session_state.mod_uploader_key = 0

# --- Left: Inputs ---
left, right = st.columns([0.42, 0.58], gap="large")

with left:
    st.subheader("Project Info")
    name = st.text_input("Project / ERP Name", value="My ERP System")
    version = st.text_input("Version", value="1.0.0")
    environment = st.selectbox("Environment", ["Production", "Staging", "Development"])
    overview = st.text_area("Overview (what this ERP does)", height=120, value="Describe the ERP and its goals...")

    st.divider()
    st.subheader("Add a Module")

    with st.form("add_module_form", clear_on_submit=True):
        m_name = st.text_input("Module name (e.g., Sales, Inventory, HR)")
        m_owner = st.text_input("Owner/Team (e.g., Admin Team, Finance Dept)", value="Product Team")
        m_desc = st.text_area("Module description", height=80)

        features_raw = st.text_area(
            "Features (one per line)",
            height=100,
            placeholder="Create invoice\nApprove order\nExport report"
        )
        roles_raw = st.text_area(
            "Roles & permissions (format: Role=Permission, one per line)",
            height=100,
            placeholder="Admin=Full access\nManager=Approve orders\nUser=Create orders"
        )

        uploaded = st.file_uploader(
            "Attachments for this module (images, pdf, any file)",
            accept_multiple_files=True,
            key=f"mod_files_{st.session_state.mod_uploader_key}"
        )

        submitted = st.form_submit_button("➕ Add module")

if submitted:
    features = [x.strip() for x in features_raw.splitlines() if x.strip()]

    roles = []
    for line in roles_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" in line:
            role, perm = line.split("=", 1)
            roles.append({"role": role.strip(), "permission": perm.strip()})
        else:
            roles.append({"role": line, "permission": "N/A"})

    st.session_state.modules.append({
        "name": m_name or "Untitled Module",
        "owner": m_owner or "N/A",
        "description": m_desc or "",
        "features": features,
        "roles": roles
    })

    # Save attachments only when Add module clicked
    if uploaded:
        for f in uploaded:
            st.session_state.attachments.append({
                "name": f.name,
                "bytes": f.getvalue(),
                "type": (f.type or "")
            })

    st.session_state.mod_uploader_key += 1
    st.success("Module added.")
    st.rerun()

# Show saved attachments (always visible, not inside submitted)
if st.session_state.attachments:
    st.divider()
    st.subheader("Saved Attachments")

    for i, att in enumerate(st.session_state.attachments):
        col1, col2 = st.columns([0.92, 0.08])
        with col1:
            st.write(f"- {att['name']}")
        with col2:
            if st.button("🗑️", key=f"att_del_{i}", help="Delete this attachment"):
                st.session_state.attachments.pop(i)
                st.rerun()
        

    if st.session_state.modules:
        st.divider()
        st.subheader("Modules Added")

        for i, m in enumerate(st.session_state.modules):
            rowL, rowR=st.columns([0.92, 0.08])

            with rowL:
                with st.expander(f"{i + 1}. {m['name']}"):
                    st.write(f"**Owner:** {m['owner']}")
                    st.write(m["description"])
                    if m.get("features"):
                        st.write("**Features:**")
                        for feat in m["features"]:
                            st.write(f"- {feat}")
                    if m.get("roles"):
                        st.write("**Roles & Permissions:**")
                        for r in m["roles"]:
                            st.write(f"- {r['role']}: {r['permission']}")
                
            with rowR:
                if st.button("🗑️", key=f"mod_del_{i}", help="Delete this module"):
                    st.session_state.modules.pop(i)
                    st.rerun()

# --- Right: Preview + Export ---
with right:
    project = {
        "name": name,
        "version": version,
        "environment": environment,
        "overview": overview,
        "date": datetime.date.today().strftime("%B %d, %Y"),
    }

    try:
        attachments_ctx={"images": [], "pdfs": [], "files": []}
        for a in st.session_state.attachments:
            name=a["name"]
            data=a["bytes"]
            lower=name.lower()
            size_kb=max(1,len(data)//1024)

            if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                mime=a["type"] or "image/png"
                b64=base64.b64encode(data).decode("utf-8")
                attachments_ctx["images"].append({"name": name, "size_kb": size_kb, "data_uri": f"data:{mime};base64,{b64}"
              })
            elif lower.endswith(".pdf"):
                attachments_ctx["pdfs"].append({"name": name, "size_kb":size_kb})
            else:
                attachments_ctx["files"].append({"name": name, "size_kb": size_kb})
        html = render_html(project, st.session_state.modules,attachments_ctx)
    except Exception as e:
        st.error(f"Template rendering failed: {e}")
        st.stop()

    st.subheader("Live Preview")
    st.components.v1.html(html, height=720, scrolling=True)

    st.divider()
    colA, colB = st.columns([0.6, 0.4])

    with colA:
        out_name = st.text_input("Output file name", value="documentation.pdf")

    with colB:
        if st.button("⬇️ Generate PDF", type="primary", use_container_width=True):
            out_path = os.path.join(OUTPUT_DIR, out_name)
            out_path=os.path.abspath(out_path)

            attach_dir=os.path.join(OUTPUT_DIR, "attachments")
            os.makedirs(attach_dir, exist_ok=True)

            try:
                html_to_pdf(html, out_path)
                saved_paths=[]
                pdf_paths_to_append=[]

                for a in st.session_state.attachments:
                    fname=safe_filename(a["name"])
                    fpath=os.path.join(attach_dir, fname)
                    with open(fpath, "wb") as f:
                        f.write(a["bytes"])
                    saved_paths.append((fpath, fname))

                    if fname.lower().endswith(".pdf"):
                        pdf_paths_to_append.append(fpath)

                final_pdf=out_path
                if pdf_paths_to_append:
                   merge_path=out_path.replace(".pdf", "_with_attachments.pdf")
                   merge_pdfs([out_path]+pdf_paths_to_append, merge_path)
                   final_pdf=merge_path

                st.success(f"✅ PDF generated successfully: {final_pdf}")

                with open(final_pdf, "rb") as f:
                    st.download_button(
                        "Download PDF",
                        data=f,
                        file_name=out_name,
                        mime="application/pdf"
                    )
                    
                zip_name=os.path.basename(final_pdf).replace(".pdf", "_with_attachments.zip")
                zip_path=os.path.join(OUTPUT_DIR, zip_name)

                zip_files=[(final_pdf, os.path.basename(final_pdf))]
                for fpath, original_name in saved_paths:
                    zip_files.append((fpath, original_name))

                make_zip(zip_path, zip_files)
                with open(zip_path, "rb") as f:
                    st.download_button(
                        "Download ZIP (PDF + attachments)",
                        data=f,
                        file_name=zip_name,
                        mime="application/zip"
                    )

            except Exception as e:
                st.exception(e)

def show_pdf(path):
    with open(path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
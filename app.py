import uuid
from datetime import date, datetime
from pathlib import Path

import streamlit as st

from db import get_session, init_db, insert_letter, insert_task, search_letters, get_all_letters, get_letter, get_pending_tasks, update_task, delete_task
from llm import extract_metadata
from pdf_utils import create_pdf
from processing import process_images

DATA_DIR = Path(__file__).parent / "data"
PDF_DIR = DATA_DIR / "pdfs"

# --- Init ---
init_db()

st.set_page_config(page_title="Letter Scanner", layout="wide")

page = st.sidebar.radio("Navigation", ["Ingest", "Archive", "Tasks"])


# ============================================================
# INGEST PAGE
# ============================================================
if page == "Ingest":
    st.header("Ingest Letter")

    input_mode = st.toggle("Use camera", value=False)

    uploaded_images: list[bytes] = []

    if input_mode:
        camera_img = st.camera_input("Take a photo of a letter page")
        if camera_img is not None:
            uploaded_images.append(camera_img.getvalue())
    else:
        files = st.file_uploader(
            "Upload letter page(s)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
        )
        if files:
            uploaded_images = [f.getvalue() for f in files]

    if uploaded_images:
        st.write(f"{len(uploaded_images)} page(s) ready")

        if st.button("Process", type="primary"):
            # Step 1: DocRes
            with st.status("Processing images with DocRes...", expanded=True) as status:
                processed = process_images(uploaded_images)
                status.update(label="DocRes done", state="complete")

            # Step 2: LLM OCR + metadata
            with st.status("Extracting metadata with LLM...", expanded=True) as status:
                metadata = extract_metadata(processed)
                status.update(label="Metadata extracted", state="complete")

            # Step 3: Generate PDF
            pdf_filename = f"{uuid.uuid4().hex}.pdf"
            pdf_path = str(PDF_DIR / pdf_filename)
            with st.status("Generating PDF...", expanded=True) as status:
                create_pdf(processed, pdf_path)
                status.update(label="PDF saved", state="complete")

            # Step 4: Save to DB
            with st.status("Saving to database...", expanded=True) as status:
                session = get_session()
                try:
                    creation_date = None
                    if metadata.get("creation_date"):
                        try:
                            creation_date = date.fromisoformat(metadata["creation_date"])
                        except (ValueError, TypeError):
                            pass

                    letter = insert_letter(
                        session,
                        title=metadata.get("title"),
                        summary=metadata.get("summary"),
                        sender=metadata.get("sender"),
                        receiver=metadata.get("receiver"),
                        creation_date=creation_date,
                        keywords=metadata.get("keywords"),
                        full_text=metadata.get("full_text"),
                        pdf_path=f"pdfs/{pdf_filename}",
                        page_count=len(processed),
                        raw_llm_response=metadata.get("raw_llm_response"),
                    )

                    for task_data in metadata.get("tasks", []):
                        deadline = None
                        if task_data.get("deadline"):
                            try:
                                deadline = date.fromisoformat(task_data["deadline"])
                            except (ValueError, TypeError):
                                pass
                        insert_task(
                            session,
                            letter_id=letter.id,
                            description=task_data.get("description", ""),
                            deadline=deadline,
                        )

                    session.commit()
                    status.update(label="Saved!", state="complete")
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

            # Show results
            st.success(f"Letter '{metadata.get('title', 'Untitled')}' ingested successfully!")
            with st.expander("Extracted Metadata", expanded=True):
                st.json({k: v for k, v in metadata.items() if k != "raw_llm_response"})


# ============================================================
# ARCHIVE PAGE
# ============================================================
elif page == "Archive":
    st.header("Letter Archive")

    query = st.text_input("Search letters", placeholder="Full-text search...")

    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("From", value=None)
    with col2:
        date_to = st.date_input("To", value=None)

    session = get_session()
    try:
        if query:
            letters = search_letters(session, query)
        else:
            letters = get_all_letters(session)

        # Apply date filters
        if date_from:
            letters = [l for l in letters if l.creation_date and l.creation_date >= date_from]
        if date_to:
            letters = [l for l in letters if l.creation_date and l.creation_date <= date_to]

        st.write(f"{len(letters)} letter(s) found")

        for letter in letters:
            with st.expander(
                f"**{letter.title or 'Untitled'}** — {letter.sender or '?'} → {letter.receiver or '?'} "
                f"({letter.creation_date or 'no date'})"
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Summary:** {letter.summary or '—'}")
                    st.write(f"**Keywords:** {letter.keywords or '—'}")
                    st.write(f"**Pages:** {letter.page_count or '?'}")
                    st.write(f"**Ingested:** {letter.ingested_at}")
                with col_b:
                    if letter.pdf_path:
                        pdf_full_path = DATA_DIR / letter.pdf_path
                        if pdf_full_path.exists():
                            st.download_button(
                                "Download PDF",
                                data=pdf_full_path.read_bytes(),
                                file_name=f"{letter.title or 'letter'}.pdf",
                                mime="application/pdf",
                                key=f"dl_{letter.id}",
                            )

                if letter.full_text:
                    st.text_area(
                        "Full Text",
                        value=letter.full_text,
                        height=200,
                        disabled=True,
                        key=f"ft_{letter.id}",
                    )

                # Show tasks for this letter
                if letter.tasks:
                    st.write("**Tasks:**")
                    for task in letter.tasks:
                        done = "~~" if task.is_done else ""
                        dl = f" (due: {task.deadline})" if task.deadline else ""
                        st.write(f"- {done}{task.description}{done}{dl}")
    finally:
        session.close()


# ============================================================
# TASKS PAGE
# ============================================================
elif page == "Tasks":
    st.header("Tasks")

    session = get_session()
    try:
        tasks = get_pending_tasks(session)
        today = date.today()

        if not tasks:
            st.info("No pending tasks.")
        else:
            for task in tasks:
                letter = get_letter(session, task.letter_id)
                letter_title = letter.title if letter else "Unknown"

                is_overdue = task.deadline and task.deadline < today
                deadline_str = str(task.deadline) if task.deadline else "No deadline"
                if is_overdue:
                    deadline_str += " (OVERDUE)"

                col1, col2, col3 = st.columns([0.05, 0.75, 0.2])
                with col1:
                    if st.checkbox("", key=f"done_{task.id}", value=False):
                        update_task(session, task.id, is_done=True)
                        session.commit()
                        st.rerun()
                with col2:
                    color = "red" if is_overdue else "inherit"
                    st.markdown(
                        f"<span style='color:{color}'><b>{task.description}</b><br/>"
                        f"<small>From: {letter_title} | Due: {deadline_str}</small></span>",
                        unsafe_allow_html=True,
                    )
                with col3:
                    if st.button("Delete", key=f"del_{task.id}"):
                        delete_task(session, task.id)
                        session.commit()
                        st.rerun()
    finally:
        session.close()

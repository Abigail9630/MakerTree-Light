"""Streamlit UI for MakerTree Library — tree view, quick capture, filters."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import streamlit as st

from maker_tree_store import BRANCHES, NODE_TYPES, MakerTreeStore, TreeNode


PAGE_SIZE = 40


def get_store() -> MakerTreeStore:
    if "maker_tree_store" not in st.session_state:
        st.session_state.maker_tree_store = MakerTreeStore()
    else:
        st.session_state.maker_tree_store.reload_if_changed()
    return st.session_state.maker_tree_store


def _init_library_state() -> None:
    defaults = {
        "library_branch": "rain",
        "library_search": "",
        "library_tag_filter": "",
        "library_project_filter": "",
        "library_date_from": None,
        "library_date_to": None,
        "library_selected_id": None,
        "library_search_mode": False,
        "library_child_offsets": {},
        "library_expanded": set(),
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _format_when(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y · %H:%M")
    except ValueError:
        return iso[:16] if iso else ""


def _project_label(store: MakerTreeStore, project_id: Optional[str]) -> str:
    if not project_id:
        return "—"
    proj = store.get(project_id)
    return proj.title if proj else project_id


def render_quick_capture_bar(store: MakerTreeStore, *, compact: bool = False) -> None:
    """Sticky quick capture — dumps into today's Rain with timestamp."""
    if compact:
        with st.form("quick_capture_compact", clear_on_submit=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                capture_text = st.text_input(
                    "Quick capture",
                    label_visibility="collapsed",
                    placeholder="⚡ Quick Capture — dump into today's Rain…",
                )
            with c2:
                submitted = st.form_submit_button("Capture", use_container_width=True)
            if submitted:
                if not capture_text.strip():
                    st.warning("Type something first.")
                else:
                    node = store.quick_capture(capture_text.strip())
                    st.session_state["library_selected_id"] = node.id
                    st.toast(f"Saved to Rain · {_format_when(node.created_at)}")
                    st.rerun()
        return

    st.markdown("##### ⚡ Quick Capture")
    st.caption("Dump a thought straight into today's Rain — dated and saved automatically.")
    with st.form("quick_capture_full", clear_on_submit=True):
        capture_text = st.text_area(
            "Quick capture",
            height=72,
            label_visibility="collapsed",
            placeholder="Type anything — idea, todo, rant, material note…",
        )
        submitted = st.form_submit_button("Capture", use_container_width=True)
        if submitted:
            if not capture_text.strip():
                st.warning("Type something first — even a single line counts.")
            else:
                node = store.quick_capture(capture_text.strip())
                st.session_state["library_selected_id"] = node.id
                st.session_state["library_branch"] = "rain"
                st.toast(f"Saved to Rain · {_format_when(node.created_at)}")
                st.rerun()


def _render_filters(store: MakerTreeStore) -> None:
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    with f1:
        st.session_state.library_search = st.text_input(
            "Search",
            value=st.session_state.library_search,
            key="library_search_input",
            placeholder="Search title, text, tags…",
        )
    with f2:
        projects = store.list_projects()
        proj_options = ["All projects"] + [p.id for p in projects]
        proj_labels = ["All projects"] + [p.title for p in projects]
        idx = 0
        if st.session_state.library_project_filter in proj_options:
            idx = proj_options.index(st.session_state.library_project_filter)
        choice = st.selectbox(
            "Project",
            range(len(proj_options)),
            index=idx,
            format_func=lambda i: proj_labels[i],
            key="library_project_select",
        )
        st.session_state.library_project_filter = proj_options[choice]
    with f3:
        all_tags = store.all_tags()
        tag_options = ["All tags"] + all_tags
        tidx = 0
        if st.session_state.library_tag_filter in tag_options:
            tidx = tag_options.index(st.session_state.library_tag_filter)
        tchoice = st.selectbox(
            "Tag",
            range(len(tag_options)),
            index=tidx,
            format_func=lambda i: tag_options[i],
            key="library_tag_select",
        )
        st.session_state.library_tag_filter = tag_options[tchoice]
    with f4:
        st.session_state.library_search_mode = st.checkbox(
            "Search all branches",
            value=st.session_state.library_search_mode,
            key="library_search_all",
        )

    d1, d2, d3 = st.columns([1, 1, 2])
    use_dates = st.session_state.get("library_use_dates", False)
    with d1:
        use_dates = st.checkbox("Date range", value=use_dates, key="library_use_dates_cb")
        st.session_state.library_use_dates = use_dates
    with d2:
        if use_dates:
            st.session_state.library_date_from = st.date_input(
                "From",
                value=st.session_state.library_date_from or date.today(),
                key="library_date_from_input",
            )
    with d3:
        if use_dates:
            st.session_state.library_date_to = st.date_input(
                "To",
                value=st.session_state.library_date_to or date.today(),
                key="library_date_to_input",
            )
        if st.button("Clear filters", key="library_clear_filters"):
            st.session_state.library_search = ""
            st.session_state.library_tag_filter = ""
            st.session_state.library_project_filter = ""
            st.session_state.library_date_from = None
            st.session_state.library_date_to = None
            st.session_state.library_use_dates = False
            st.session_state.library_search_mode = False
            st.rerun()


def _filter_kwargs(store: MakerTreeStore) -> dict:
    kwargs: dict = {}
    if st.session_state.library_search.strip():
        kwargs["query"] = st.session_state.library_search.strip()
    if st.session_state.library_project_filter and st.session_state.library_project_filter != "All projects":
        kwargs["project_id"] = st.session_state.library_project_filter
    if st.session_state.library_tag_filter and st.session_state.library_tag_filter != "All tags":
        kwargs["tags"] = [st.session_state.library_tag_filter]
    if st.session_state.get("library_use_dates"):
        if st.session_state.library_date_from:
            kwargs["date_from"] = st.session_state.library_date_from
        if st.session_state.library_date_to:
            kwargs["date_to"] = st.session_state.library_date_to
    return kwargs


def _render_node_row(store: MakerTreeStore, node: TreeNode, *, depth: int = 0) -> None:
    indent = "　" * depth
    icon = {
        "rain_day": "📅",
        "rain_capture": "💧",
        "sop": "📋",
        "project": "🌳",
        "folder": "📁",
        "note": "📝",
    }.get(node.node_type, "·")
    label = f"{indent}{icon} {node.title or '(untitled)'}"
    meta = _format_when(node.created_at)
    if node.tags:
        meta += f" · {', '.join(node.tags[:3])}"

    cols = st.columns([4, 1])
    with cols[0]:
        if st.button(label, key=f"lib_pick_{node.id}", use_container_width=True):
            st.session_state.library_selected_id = node.id
            st.rerun()
    with cols[1]:
        st.caption(meta)

    is_folder = node.node_type in ("rain_day", "folder", "project") or store.count_children(node.id) > 0
    if not is_folder:
        return

    expanded_key = f"lib_exp_{node.id}"
    default_expanded = not node.collapsed
    with st.expander(f"{indent}Show {store.count_children(node.id)} items", expanded=default_expanded):
        offset_key = node.id
        offset = st.session_state.library_child_offsets.get(offset_key, 0)
        children = store.list_children(node.id, limit=PAGE_SIZE, offset=offset)
        total = store.count_children(node.id)
        for child in children:
            _render_node_row(store, child, depth=depth + 1)
        if total > offset + PAGE_SIZE:
            if st.button(f"Load more… ({offset + PAGE_SIZE}/{total})", key=f"lib_more_{node.id}"):
                st.session_state.library_child_offsets[offset_key] = offset + PAGE_SIZE
                st.rerun()


def _render_branch_tree(store: MakerTreeStore, branch: str) -> None:
    st.markdown(f"**{BRANCHES.get(branch, branch)}**")
    roots = store.list_children(None, branch=branch, limit=PAGE_SIZE, offset=0)
    if not roots:
        st.info("Nothing here yet — use Quick Capture (Rain) or add a note below.")
        return
    for node in roots:
        _render_node_row(store, node)


def _render_search_results(store: MakerTreeStore) -> None:
    kwargs = _filter_kwargs(store)
    branch = None if st.session_state.library_search_mode else st.session_state.library_branch
    if branch:
        kwargs["branch"] = branch
    results = store.search(**kwargs, limit=PAGE_SIZE)
    st.markdown(f"**Search results** ({len(results)} shown, max {PAGE_SIZE})")
    if not results:
        st.info("No matches — try fewer filters or a shorter search phrase.")
        return
    for node in results:
        branch_label = BRANCHES.get(node.branch, node.branch)
        if st.button(
            f"[{branch_label}] {node.title or '(untitled)'}",
            key=f"lib_search_{node.id}",
            use_container_width=True,
        ):
            st.session_state.library_selected_id = node.id
            st.rerun()
        st.caption(_format_when(node.updated_at))


def _render_node_editor(store: MakerTreeStore, node_id: str) -> None:
    node = store.get(node_id)
    if not node:
        st.warning("That note was removed or moved.")
        return

    st.divider()
    st.markdown("**Edit note**")
    st.caption(f"{BRANCHES.get(node.branch, node.branch)} · {NODE_TYPES.get(node.node_type, node.node_type)} · {node.id}")

    title = st.text_input("Title", value=node.title, key=f"lib_edit_title_{node.id}")
    text = st.text_area("Text", value=node.text, height=220, key=f"lib_edit_text_{node.id}")
    tags_raw = st.text_input(
        "Tags (comma-separated)",
        value=", ".join(node.tags),
        key=f"lib_edit_tags_{node.id}",
    )

    projects = store.list_projects()
    proj_ids = [""] + [p.id for p in projects]
    proj_labels = ["No project"] + [p.title for p in projects]
    pidx = proj_ids.index(node.project_id) if node.project_id in proj_ids else 0
    proj_choice = st.selectbox(
        "Project",
        range(len(proj_ids)),
        index=pidx,
        format_func=lambda i: proj_labels[i],
        key=f"lib_edit_project_{node.id}",
    )
    selected_project = proj_ids[proj_choice] or None

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        if st.button("Save", key=f"lib_save_{node.id}", use_container_width=True):
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            store.update_node(node.id, title=title, text=text, tags=tags, project_id=selected_project)
            st.success("Saved.")
            st.rerun()
    with m2:
        if st.button("→ Projects", key=f"lib_to_proj_{node.id}", use_container_width=True):
            store.move_node(node.id, branch="projects", parent_id=None)
            st.toast("Moved to Projects")
            st.rerun()
    with m3:
        if st.button("→ Trunk SOP", key=f"lib_to_trunk_{node.id}", use_container_width=True):
            store.move_node(node.id, branch="trunk", node_type="sop", parent_id=None)
            st.toast("Moved to Trunk / SOPs")
            st.rerun()
    with m4:
        if st.button("→ Archive", key=f"lib_to_arch_{node.id}", use_container_width=True):
            store.move_node(node.id, branch="archive", parent_id=None)
            st.toast("Archived")
            st.rerun()

    if st.button("Delete this note", key=f"lib_del_{node.id}"):
        store.delete_node(node.id, recursive=node.node_type == "rain_day")
        st.session_state.library_selected_id = None
        st.rerun()


def _render_add_forms(store: MakerTreeStore, branch: str) -> None:
    with st.expander("Add new…"):
        if branch == "rain":
            st.caption("Rain entries are usually created via Quick Capture (auto-dated).")
        if branch == "projects":
            title = st.text_input("New project name", key="lib_new_project_title")
            if st.button("Create project", key="lib_new_project_btn"):
                if title.strip():
                    p = store.create_node(
                        title=title.strip(),
                        branch="projects",
                        node_type="project",
                    )
                    st.session_state.library_selected_id = p.id
                    st.rerun()
        if branch == "trunk":
            title = st.text_input("SOP title", key="lib_new_sop_title")
            body = st.text_area("SOP steps / process", height=120, key="lib_new_sop_body")
            projects = store.list_projects()
            pid = None
            if projects:
                opts = [""] + [p.id for p in projects]
                labels = ["No project"] + [p.title for p in projects]
                pc = st.selectbox(
                    "Link to project",
                    range(len(opts)),
                    format_func=lambda i: labels[i],
                    key="lib_new_sop_project",
                )
                pid = opts[pc] or None
            if st.button("Add SOP", key="lib_new_sop_btn"):
                if title.strip():
                    n = store.create_node(
                        title=title.strip(),
                        text=body,
                        branch="trunk",
                        node_type="sop",
                        project_id=pid,
                    )
                    st.session_state.library_selected_id = n.id
                    st.rerun()
        if branch in ("archive", "projects", "rain"):
            title = st.text_input("Note title", key=f"lib_new_note_title_{branch}")
            body = st.text_area("Note text", height=100, key=f"lib_new_note_body_{branch}")
            if st.button("Add note", key=f"lib_new_note_btn_{branch}"):
                if title.strip() or body.strip():
                    n = store.create_node(
                        title=title.strip() or "Note",
                        text=body,
                        branch=branch,
                        node_type="note",
                    )
                    st.session_state.library_selected_id = n.id
                    st.rerun()


def _render_csv_tools(store: MakerTreeStore) -> None:
    with st.expander("Import / export CSV (bulk old notes)"):
        st.caption(f"Data folder: `{store.data_dir}` — copy this folder to sync via USB or LocalSend.")
        st.download_button(
            "Export all nodes CSV",
            data=store.export_csv(),
            file_name="makertree_nodes.csv",
            mime="text/csv",
            use_container_width=True,
        )
        uploaded = st.file_uploader("Import CSV", type=["csv"], key="lib_csv_upload")
        merge = st.checkbox("Skip rows whose id already exists", value=True, key="lib_csv_merge")
        if uploaded is not None and st.button("Import file", key="lib_csv_import_btn"):
            text = uploaded.getvalue().decode("utf-8", errors="replace")
            imported, skipped = store.import_csv(text, merge=merge)
            st.success(f"Imported {imported} nodes ({skipped} skipped).")
            st.rerun()


def render_library_page() -> None:
    _init_library_state()
    store = get_store()

    st.subheader("Library")
    st.caption(
        "Runs **alongside** your Rain → Soil journey — not a replacement. "
        "Quick capture, dated Rain, SOPs by project, and archive live here. "
        "Nothing moves automatically from the maker journey pages yet."
    )
    st.caption(
        "*Note: deeper Library + Talis integration is paused while Abigail reviews — "
        "journey pages are wired first.*"
    )

    render_quick_capture_bar(store)
    st.divider()

    branch_keys = list(BRANCHES.keys())
    branch_labels = [BRANCHES[k] for k in branch_keys]
    bidx = branch_keys.index(st.session_state.library_branch) if st.session_state.library_branch in branch_keys else 0
    chosen = st.radio(
        "Branch",
        range(len(branch_keys)),
        index=bidx,
        format_func=lambda i: branch_labels[i],
        horizontal=True,
        key="library_branch_radio",
    )
    st.session_state.library_branch = branch_keys[chosen]

    _render_filters(store)
    st.divider()

    has_active_filters = bool(
        st.session_state.library_search.strip()
        or st.session_state.library_tag_filter not in ("", "All tags")
        or st.session_state.library_project_filter not in ("", "All projects")
        or st.session_state.get("library_use_dates")
    )

    if has_active_filters:
        _render_search_results(store)
    else:
        _render_branch_tree(store, st.session_state.library_branch)

    _render_add_forms(store, st.session_state.library_branch)
    _render_csv_tools(store)

    if st.session_state.library_selected_id:
        _render_node_editor(store, st.session_state.library_selected_id)

    st.caption(f"{store.node_count} nodes in library · file storage at `{store.data_dir}`")

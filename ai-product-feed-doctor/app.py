"""Streamlit entry point for AI Product Feed Doctor."""
import csv
import os

import streamlit as st

from ai_help import explain_issues
from feed import REQUIRED_COLUMNS, export_feed, read_feed, validate_feed


def reset_review():
    for key in (
        "approved_csv", "approve_export", "ai_guide", "draft", "previous_draft",
        "editor_revision", "issues_only", "required_extra_columns",
    ):
        st.session_state.pop(key, None)


def clear_export_approval():
    st.session_state.pop("approved_csv", None)
    st.session_state.pop("approve_export", None)


def change_validation_rules():
    clear_export_approval()
    st.session_state.pop("ai_guide", None)
    # The filtered editor may contain a different set of rows.
    st.session_state.editor_revision += 1


st.set_page_config(page_title="AI Product Feed Doctor", page_icon="🩺", layout="wide")
st.title("AI Product Feed Doctor")
st.write("Upload a product CSV, check it for errors, and review your corrections before exporting.")
uploaded = st.file_uploader("Product feed CSV", type=["csv"], on_change=reset_review)
if uploaded is None:
    st.info("Upload a CSV with the columns sku, name, price, and stock. You can try either file in the samples folder.")
    st.stop()

try:
    original = read_feed(uploaded.getvalue())
except (ValueError, csv.Error) as error:
    st.error(f"Could not read the CSV. {error}")
    st.stop()

extra_columns = [column for column in original.columns if column not in REQUIRED_COLUMNS]
required_extra_columns = []
if extra_columns:
    required_extra_columns = st.multiselect(
        "Required extra columns",
        extra_columns,
        default=extra_columns,
        key="required_extra_columns",
        on_change=change_validation_rules,
        help="Unselected extra columns may be blank. SKU, name, price, and stock are always checked.",
    )

issues = validate_feed(original, required_extra_columns)
rows, flagged_rows, total = st.columns(3)
rows.metric("Product rows", len(original))
flagged_rows.metric("Rows with issues", issues["CSV row"].nunique())
total.metric("Issues", len(issues))

with st.expander("Uploaded product table", expanded=True):
    st.dataframe(original.set_axis(range(2, len(original) + 2)).rename_axis("CSV row"), width="stretch")

st.header("Validation results")
st.caption("Row 1 is the header. Each CSV record counts as one row, even when it contains a quoted line break.")
if issues.empty:
    st.success("The uploaded feed passed all checks.")
else:
    st.dataframe(issues, hide_index=True, width="stretch")
    with st.expander("AI troubleshooting"):
        if os.environ.get("OPENAI_API_KEY", "").strip():
            st.caption("Generate a guide by sending issue types and counts to OpenAI.")
            if st.button("Generate troubleshooting guide"):
                st.session_state.pop("ai_guide", None)
                try:
                    with st.spinner("Generating troubleshooting guide…"):
                        st.session_state.ai_guide = explain_issues(issues["Issue"].value_counts().to_dict())
                except (OSError, ValueError):
                    st.error("Could not generate guidance. Check your API key, model access, and network, then try again.")
            if st.session_state.get("ai_guide"):
                st.text(st.session_state.ai_guide)
        else:
            st.caption("Set OPENAI_API_KEY in your terminal and restart the app to enable the guide.")

st.header("Review corrections")
st.caption("Enter verified values in the table. Check the updated results before approving an export.")
if "draft" not in st.session_state:
    st.session_state.draft = original.set_axis(range(2, len(original) + 2)).rename_axis("CSV row")
    st.session_state.editor_revision = 0

issues_only = st.checkbox("Show only rows with issues", key="issues_only")
if st.button("Undo last edit", key="undo_edit", disabled="previous_draft" not in st.session_state):
    st.session_state.draft = st.session_state.pop("previous_draft")
    clear_export_approval()
    st.session_state.editor_revision += 1
    st.rerun()

draft = st.session_state.draft
draft_issues = validate_feed(draft, required_extra_columns)
visible = draft.loc[draft.index.isin(draft_issues["CSV row"])] if issues_only else draft
if issues_only and visible.empty:
    st.info("No rows with issues in the current draft.")
else:
    edited = st.data_editor(
        visible,
        key=f"feed_editor_{st.session_state.editor_revision}_{issues_only}",
        width="stretch",
        num_rows="fixed",
        hide_index=False,
        disabled=["_index"],
        column_config={name: st.column_config.TextColumn(name) for name in draft.columns},
    ).fillna("")
    if not edited.equals(visible):
        st.session_state.previous_draft = draft.copy()
        draft.loc[edited.index, :] = edited
        clear_export_approval()
        # Start a fresh editor so old positional edits cannot apply to a new subset.
        st.session_state.editor_revision += 1
        st.rerun()

candidate = export_feed(draft)
change_mask = draft.reset_index(drop=True).ne(original)
changed_cells = int(change_mask.to_numpy().sum())
st.write(f"{changed_cells} cell(s) changed · {len(draft_issues)} issue(s) in the edited feed")
if not draft_issues.empty:
    st.dataframe(draft_issues, hide_index=True, width="stretch")
else:
    st.success("The edited feed passed all checks.")

approved = st.checkbox("I reviewed these values and any remaining issues.", key="approve_export")
if approved and st.button("Approve CSV export", key="approve_csv", type="primary"):
    st.session_state.approved_csv = candidate
if approved and st.session_state.get("approved_csv") == candidate:
    st.download_button("Download reviewed CSV", candidate, file_name="reviewed-product-feed.csv", mime="text/csv")

# AI Product Feed Doctor

Upload a product CSV, find errors, review corrections, and download a reviewed copy. The core workflow runs locally with Python, Pandas, and Streamlit.

## Install and run on Windows

Install Python 3.11 or newer. Open the project folder in File Explorer, type `powershell` in the address bar, and press Enter. Run these commands one at a time.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The first command creates an isolated Python environment. The second installs the packages listed in `requirements.txt`. The third starts the dashboard. Open the local URL printed in the terminal if the browser does not open automatically. Press **Ctrl+C** in PowerShell to stop the app. If your installation provides `python` instead of `py`, use `python -m venv .venv` for the first command.

On macOS or Linux, use `python3 -m venv .venv` and replace `.\.venv\Scripts\python.exe` with `./.venv/bin/python` in the other commands.

## Try the dashboard

1. Upload `samples/feed-with-errors.csv`. The dashboard should report **8 issues across 5 product rows**.
2. Open **Validation results** and match its CSV row numbers to the uploaded table. Row 1 is the header. A quoted record that spans several lines still counts as one row.
   If your feed has extra columns, use **Required extra columns** to decide which ones must have a value. For example, leave `origin` selected and deselect `secondary_color` if color is optional. All extra columns start selected for each new upload.
3. In **Review corrections**, enter values you can verify against your catalog, pricing, or inventory records. The app checks the draft after edits and shows remaining issues.
   Turn on **Show only rows with issues** to focus the editor on flagged rows. Rows keep their original CSV numbers and disappear from this view once all their issues are resolved. Toggle the checkbox to see every row again. Edits carry across both views, and export includes every row.
   If you delete or overwrite a value by accident, select **Undo last edit** to restore the previous draft. You can undo the most recent edit, even after switching views. Review and approve the restored draft again before exporting.
4. Review the current draft and its issues, check the review box, and select **Approve CSV export**. Select **Download reviewed CSV**. Editing the draft again clears the approval. You can explicitly approve a draft with unresolved issues when you need to send it for further review.

The original upload stays intact. The export keeps extra columns and values such as SKU `001`. If you open the CSV in spreadsheet software, import the SKU column as text to preserve leading zeros.

## Feed format and rules

Use a comma-separated UTF-8 file with the exact headers `sku`, `name`, `price`, and `stock` in any order. Additional columns are accepted. Each record must have the same number of fields as the header. An empty field is valid CSV syntax and is checked by the rules below.

| Field | Rule |
| --- | --- |
| `sku` | Required and unique after trimming surrounding whitespace. Matching is case-sensitive. Every row in a duplicate group is flagged. |
| `name` | Required. Whitespace-only names are flagged. |
| `price` | A decimal number greater than zero, such as `19.95`. Use a period as the decimal separator and omit currency symbols and thousands separators. |
| `stock` | A whole number of zero or more, such as `0` or `12`. |
| Selected extra columns such as `origin` | Empty and whitespace-only cells are flagged. Unselected extra columns can be blank and stay in the export. |

Changing the selection updates the uploaded-feed results and the draft, including the filtered editor. Edits and undo history stay available. Review the updated results and approve the draft again before exporting.

Surrounding whitespace is ignored during validation and preserved in export. `samples/feed-edge-cases.csv` includes quoted fields, a multiline name, whitespace, and invalid numeric formats.

## Optional AI troubleshooting

With the app stopped, set your OpenAI API key in the same PowerShell window you will use to launch Streamlit. The prompt keeps the key out of your command history.

```powershell
$env:OPENAI_API_KEY = Read-Host "OpenAI API key" -MaskInput
.\.venv\Scripts\python.exe -m streamlit run app.py
```

In Windows PowerShell 5.1, replace the first command with:

```powershell
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host "OpenAI API key" -AsSecureString)).Password
```

After uploading a feed with issues, expand **AI troubleshooting** and select **Generate troubleshooting guide**. That sends only issue types and counts to the OpenAI Responses API. The guide provides troubleshooting steps. Corrections still come from your verified records and require your approval. The default model is `gpt-4.1-mini`. Set `OPENAI_MODEL` in your terminal to override it. API calls may incur usage charges. [OpenAI Responses API reference](https://developers.openai.com/api/reference/resources/responses/methods/create)

Keep the key in your environment and out of shared files and Git. Closing the PowerShell window clears the session variable.

## Project structure

| Path | Purpose |
| --- | --- |
| `app.py` | Dashboard, upload, validation display, editor, approval, and download. |
| `feed.py` | Standalone CSV parsing, validation, and export. |
| `ai_help.py` | Optional API client for a read-only troubleshooting guide. |
| `samples/` | Two CSVs with intentional errors. |
| `tests/` | Automated core and mocked AI tests. |
| `requirements.txt` | Packages to install. |

`read_feed()` turns CSV bytes into a Pandas DataFrame (an in-memory table) with text cells. `validate_feed()` returns a second table with one entry per issue and uses the same rules for the upload and edited draft. `export_feed()` turns the draft back into CSV bytes. `explain_issues()` sends issue counts and returns guidance text.

## Run the tests

From the project folder, run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Look for **OK** at the bottom. The tests use local samples and mocked API responses, so they run without an API key.

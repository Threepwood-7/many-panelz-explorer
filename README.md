# many-panelz-explorer

Multi-panel, Windows-focused file explorer built with PySide6.

Tooling: this project uses uv + Hatch.

## UI Walkthrough

1. Configure panels and roots for your workspace.

   ![Configure panels and roots](docs/images/ui-01-overview.png)

   Multi-panel overview for opening and organizing primary working folders.

2. Navigate split views to compare locations quickly.

   ![Navigate split workflow](docs/images/ui-02-workflow.png)

   Tabbed and split workflow state for moving between folder contexts.

3. Inspect focused details before file operations.

   ![Inspect file details](docs/images/ui-03-details.png)

   Focused details/navigation state for reviewing selected paths.

## Setup

```powershell
uv sync --extra dev
```

## Run

```powershell
uv run many-panelz-explorer
```

## Check

```powershell
uv run ruff check .
uv run pytest -q
uv run hatch build
```

---

<!-- legal-disclaimer:start -->
## Legal Disclaimer

THIS SOFTWARE IS PROVIDED "AS IS" AND "AS AVAILABLE," WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, INCLUDING, WITHOUT LIMITATION, ANY IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, NON-INFRINGEMENT, ACCURACY, OR QUIET ENJOYMENT. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE AUTHORS, CONTRIBUTORS, MAINTAINERS, DISTRIBUTORS, AND AFFILIATED PARTIES SHALL NOT BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES, OR FOR ANY LOSS OF DATA, PROFITS, GOODWILL, BUSINESS OPPORTUNITY, OR SERVICE INTERRUPTION, ARISING OUT OF OR RELATING TO THE USE OF, OR INABILITY TO USE, THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES. THIS SOFTWARE HAS BEEN DEVELOPED, IN WHOLE OR IN PART, BY "INTELLIGENT TOOLS"; ACCORDINGLY, OUTPUTS MAY CONTAIN ERRORS OR OMISSIONS, AND YOU ASSUME FULL RESPONSIBILITY FOR INDEPENDENT VALIDATION, TESTING, LEGAL COMPLIANCE, AND SAFE OPERATION PRIOR TO ANY RELIANCE OR DEPLOYMENT.
<!-- legal-disclaimer:end -->

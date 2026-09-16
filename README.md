# 🎓 ENSAH Filière Analysis

A Streamlit application for exploring student rankings and engineering-program assignments at ENSAH (École Nationale des Sciences Appliquées d'Al Hoceima).

The application combines AP1 and AP2 results with a PDF of program assignments to compare students under a **50% AP1 + 50% AP2** ranking scenario. The interface is in French.

> Results describe this ranking scenario and the assignments detected in the supplied files. They do not establish official admission eligibility or reproduce the school's complete allocation procedure.

## Features

- Load two Excel result files and a PDF of assignments, either through the sidebar or from the repository directory.
- Match AP1 and AP2 records using normalized last and first names.
- Calculate combined averages and descending ranks.
- Search for a student by full name.
- Display AP1/AP2 averages, combined average, rank, and detected assignment.
- Summarize matched student counts and best/worst ranks for each program.
- Compare a student's rank with the worst observed rank among matched students in each program.
- Explore assigned students within ten ranking positions above or below the selected student.

## Supported Programs

| Code | Program |
|---|---|
| GC | Génie Civil |
| GI | Génie Informatique |
| ID | Ingénierie des Données |
| TDIA | Transformation Digitale et Intelligence Artificielle |
| GEER | Génie Énergétique et Énergies Renouvelables |
| GEE | Génie de l'Eau et de l'Environnement |
| GM | Génie Mécanique |

## How It Works

1. **Read Excel results:** detect the header row among the first 20 rows and select the successfully read worksheet containing the most data rows.
2. **Normalize names:** convert to uppercase, transliterate accented characters, and remove non-letter characters.
3. **Combine results:** use AP2 students as the starting list and attach matching AP1 averages.
4. **Calculate the scenario average:**

   `Combined average = (AP1 average + AP2 average) / 2`

5. **Rank students:** sort averages in descending order. Equal averages share the best applicable rank, leaving gaps afterward (for example: 1, 2, 2, 4).
6. **Extract assignments:** search normalized PDF text for each student's last name followed by first name and a recognized program code.
7. **Compare ranks:** show a positive verdict when the student's rank is less than or equal to the worst observed rank in that program.

The interface's **Places** value counts matched students assigned to a program; it is not an independently verified capacity. Labels such as **DÛ** represent the comparison in step 7.

## Input Files

| File | Expected content |
|---|---|
| `AP1.xlsx` | AP1 results with last name, first name, and average |
| `AP2.xlsx` | AP2 results with last name, first name, and average |
| `Filliéres.pdf` | Assignments with extractable student names and program codes |

Excel headers should include `Nom`, `Prénom` or `Prenom`, and an average column named `Moy` or containing `Moyenne`. Decimal commas and decimal points are accepted.

The PDF must contain extractable text; OCR for scanned documents is not implemented. Assignment detection depends on the extracted text order.

## Installation

Python 3.11 is used by the included development-container configuration.

Clone the repository:

```bash
git clone https://github.com/aarabmohamedamine/ensah_filliere.git
cd ensah_filliere
python -m venv .venv
```

Activate the virtual environment:

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Install the dependencies and start the application:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed in the terminal, normally `http://localhost:8501`.

## Usage

1. Upload all three source files in the sidebar, or enable **Utiliser les fichiers du dossier courant**.
2. For local-file mode, run the application from the repository root and preserve the exact filenames listed above.
3. Expand **Résumé global des filières** to inspect detected assignments and rank ranges.
4. Enter a student's full name in **NOM Prénom** order, then click **Analyser**.
5. Review the student profile and program comparison table.
6. Use the program selector to inspect the observed rank range and nearby students.

## Project Files

| File | Role |
|---|---|
| `app.py` | Data loading, matching, ranking, and Streamlit interface |
| `requirements.txt` | Python dependencies |
| `AP1.xlsx`, `AP2.xlsx` | Included result workbooks |
| `Filliéres.pdf` | Included assignment document |
| `.devcontainer/devcontainer.json` | Python 3.11 development environment and Streamlit startup configuration |

## Technologies

- **Streamlit:** interactive web interface and processing cache.
- **pandas:** Excel data preparation, merging, and ranking.
- **openpyxl:** Excel workbook support.
- **pdfplumber:** PDF text extraction.
- **Unidecode:** name transliteration for matching.

## Current Limitations

- Matching uses names rather than unique student identifiers. Duplicate names or normalization collisions can cause incorrect matches.
- PDF extraction and formatting can leave assignments undetected.
- Missing AP1 matches or invalid averages can produce missing ranks that some displays cannot handle.
- The partial-name search fallback currently contains an expression error; use a full name matching the normalized record.
- Student results are rendered inside the Analyze-button condition, so changing a selection can clear the results on a Streamlit rerun.
- The rank comparison does not model preferences, quotas, tie-breaking rules, or other assignment criteria.

## Author

**Mohamed Amine Aarab**  
Computer Engineering Student at ENSAH

- [GitHub](https://github.com/aarabmohamedamine)
- [LinkedIn](https://www.linkedin.com/in/aarabmedamine/)

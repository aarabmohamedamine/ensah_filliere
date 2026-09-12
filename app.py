import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
from unidecode import unidecode

# ============================================================
# 1. CONFIG PAGE
# ============================================================
st.set_page_config(
    page_title="Analyse Filières ENSAH",
    page_icon="🎓",
    layout="wide"
)

# ============================================================
# 2. STYLES CSS
# ============================================================
st.markdown("""
<style>
    .main-title {
        font-size: 2.5em;
        font-weight: bold;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 0.2em;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1em;
        margin-bottom: 2em;
    }
    .verdict-ok {
        background-color: #d4edda;
        color: #155724;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 1.2em;
        border-left: 6px solid #28a745;
        margin: 10px 0;
    }
    .verdict-no {
        background-color: #f8d7da;
        color: #721c24;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 1.2em;
        border-left: 6px solid #dc3545;
        margin: 10px 0;
    }
    .info-box {
        background-color: #e7f3ff;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2196F3;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 3. CONSTANTES
# ============================================================
FILIERES = {
    'GC':   'Génie Civil',
    'GI':   'Génie Informatique',
    'ID':   'Ingénierie des Données',
    'TDIA': 'Transformation Digitale et Intelligence Artificielle',
    'GEER': 'Génie Énergétique et Énergies Renouvelables',
    'GEE':  "Génie de l'Eau et de l'Environnement",
    'GM':   'Génie Mécanique',
}
ORDRE = ['GC', 'GI', 'ID', 'TDIA', 'GEER', 'GEE', 'GM']

# ============================================================
# 4. FONCTIONS UTILITAIRES
# ============================================================

def normalize(s):
    if pd.isna(s): return ''
    s = str(s).strip().upper()
    s = unidecode(s)
    return re.sub(r'[^A-Z]', '', s)


def to_float(x):
    if pd.isna(x): return None
    try: return float(str(x).replace(',', '.').strip())
    except: return None


def find_header_row_from_df(df_raw, max_rows=20):
    for i in range(min(len(df_raw), max_rows)):
        vals = [str(v).strip().lower() for v in df_raw.iloc[i].values if pd.notna(v)]
        if 'nom' in vals and ('prénom' in vals or 'prenom' in vals):
            return i
    return 0


def load_excel_from_file(file_obj, prefix):
    xls = pd.ExcelFile(file_obj)
    best_df, best_count = None, 0
    for sheet in xls.sheet_names:
        try:
            raw = pd.read_excel(file_obj, sheet_name=sheet, header=None)
            h = find_header_row_from_df(raw)
            df = pd.read_excel(file_obj, sheet_name=sheet, header=h).dropna(how='all')
            if len(df) > best_count:
                best_df, best_count = df, len(df)
        except: continue
    df = best_df
    col_nom = col_prenom = col_moy = None
    for c in df.columns:
        nc = normalize(c)
        if nc == 'NOM' and col_nom is None: col_nom = c
        elif nc == 'PRENOM': col_prenom = c
        elif 'MOYENNE' in nc or nc == 'MOY': col_moy = c
    result = pd.DataFrame()
    result['Nom'] = df[col_nom]
    result['Prénom'] = df[col_prenom]
    result[f'{prefix}_Moyenne'] = df[col_moy].apply(to_float)
    result['Nom_clean'] = result['Nom'].apply(normalize)
    result['Prenom_clean'] = result['Prénom'].apply(normalize)
    result['key'] = result['Nom_clean'] + '_' + result['Prenom_clean']
    return result


def get_affectations_from_pdf(pdf_obj, all_df):
    txt = ""
    with pdfplumber.open(pdf_obj) as pdf:
        for p in pdf.pages:
            txt += (p.extract_text() or "") + "\n"
    txt = normalize(txt)
    affectations = {}
    for _, row in all_df.iterrows():
        concat = row['Nom_clean'] + row['Prenom_clean']
        for code in FILIERES:
            if concat + code in txt:
                affectations[row['key']] = code
                break
    return affectations


@st.cache_data(show_spinner=False)
def process_files(ap1_bytes, ap2_bytes, pdf_bytes):
    ap1 = load_excel_from_file(io.BytesIO(ap1_bytes), 'AP1')
    ap2 = load_excel_from_file(io.BytesIO(ap2_bytes), 'AP2')
    df = ap2.merge(ap1[['key', 'AP1_Moyenne']].drop_duplicates('key'),
                   on='key', how='left')
    df['NomComplet'] = df['Nom'] + ' ' + df['Prénom']
    df['Moy_50_50'] = (df['AP1_Moyenne'] + df['AP2_Moyenne']) / 2
    df['Rang_50_50'] = df['Moy_50_50'].rank(ascending=False, method='min')
    df = df.sort_values('Rang_50_50').reset_index(drop=True)

    affectations = get_affectations_from_pdf(io.BytesIO(pdf_bytes), df)

    infos_filieres = {}
    for code in ORDRE:
        admis = df[df['key'].isin([k for k, v in affectations.items() if v == code])]
        infos_filieres[code] = {
            'nb': len(admis),
            'pire_rang': int(admis['Rang_50_50'].max()) if len(admis) > 0 else None,
            'meilleur_rang': int(admis['Rang_50_50'].min()) if len(admis) > 0 else None,
        }
    return df, affectations, infos_filieres


# ============================================================
# 5. FONCTION D'AFFICHAGE DE LA FICHE ÉTUDIANT
#    ⚠️ DOIT ÊTRE DÉFINIE AVANT LE BLOC INTERFACE
# ============================================================

def afficher_fiche(etudiant, total, affectations, infos_filieres, df):
    st.markdown("---")
    st.header(f"👤 {etudiant['NomComplet']}")

    # --- Fiche étudiant ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("AP1 Moyenne",
              f"{etudiant['AP1_Moyenne']:.2f}" if pd.notna(etudiant['AP1_Moyenne']) else "N/A")
    c2.metric("AP2 Moyenne",
              f"{etudiant['AP2_Moyenne']:.2f}" if pd.notna(etudiant['AP2_Moyenne']) else "N/A")
    c3.metric("Moyenne 50/50",
              f"{etudiant['Moy_50_50']:.2f}" if pd.notna(etudiant['Moy_50_50']) else "N/A")
    c4.metric("Rang 50/50", f"{int(etudiant['Rang_50_50'])} / {total}")

    aff_reelle = affectations.get(etudiant['key'])
    if aff_reelle:
        st.markdown(
            f'<div class="info-box"><b>Affectation actuelle :</b> '
            f'{FILIERES[aff_reelle]} ({aff_reelle})</div>',
            unsafe_allow_html=True
        )

    # --- Verdict par filière ---
    st.subheader("📋 Verdict par filière")
    rows = []
    for code in ORDRE:
        info = infos_filieres[code]
        pire = info['pire_rang']
        mon_rang = int(etudiant['Rang_50_50'])

        if pire is None:
            verdict = "—"
            statut = "Aucune donnée"
        elif mon_rang <= pire:
            verdict = "✅ DÛ"
            statut = f"Rang {mon_rang} ≤ dernier admis {pire}"
        else:
            diff = mon_rang - pire
            verdict = "❌ Non"
            statut = f"{diff} place(s) après le dernier admis"

        rows.append({
            'Filière': FILIERES[code],
            'Places': info['nb'],
            'Pire rang admis': pire if pire else '-',
            'Ton rang': mon_rang,
            'Verdict': verdict,
            'Détail': statut
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # --- Détail d'une filière ---
    st.subheader("🔍 Voir le détail d'une filière")
    code_choisi = st.selectbox(
        "Choisir une filière :",
        options=ORDRE,
        format_func=lambda c: f"{FILIERES[c]} ({c})"
    )

    if code_choisi:
        admis = df[df['key'].isin([k for k, v in affectations.items() if v == code_choisi])]
        admis = admis.sort_values('Rang_50_50')

        if len(admis) == 0:
            st.warning("Aucun étudiant admis dans cette filière.")
        else:
            st.markdown(f"### {FILIERES[code_choisi]}")

            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("Places", len(admis))
            cc2.metric("Meilleur rang", int(admis['Rang_50_50'].min()))
            cc3.metric("Pire rang", int(admis['Rang_50_50'].max()))

            dernier = admis.iloc[-1]
            st.markdown(
                f"**🚪 Dernier admis :** {dernier['NomComplet']} "
                f"(Rang {int(dernier['Rang_50_50'])}, "
                f"Moy : {dernier['Moy_50_50']:.2f})"
            )

            mon_rang = int(etudiant['Rang_50_50'])
            pire = int(admis['Rang_50_50'].max())
            if mon_rang <= pire:
                st.markdown(
                    f'<div class="verdict-ok">✅ Tu avais le DROIT à cette filière !<br>'
                    f'Ton rang ({mon_rang}) ≤ dernier admis ({pire})</div>',
                    unsafe_allow_html=True
                )
            else:
                diff = mon_rang - pire
                st.markdown(
                    f'<div class="verdict-no">❌ Tu n\'avais pas le droit à cette filière.<br>'
                    f'Tu es {diff} place(s) après le dernier admis ({pire}).</div>',
                    unsafe_allow_html=True
                )

            # Liste autour du rang
            st.markdown("#### 👥 Étudiants autour de ton rang")
            mon_rang_val = etudiant['Rang_50_50']
            fenetre = admis[
                (admis['Rang_50_50'] >= mon_rang_val - 10) &
                (admis['Rang_50_50'] <= mon_rang_val + 10)
            ]
            if len(fenetre) > 0:
                st.dataframe(
                    fenetre[['NomComplet', 'AP1_Moyenne', 'AP2_Moyenne',
                             'Moy_50_50', 'Rang_50_50']],
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("Aucun étudiant admis dans cette fenêtre autour de ton rang.")


# ============================================================
# 6. INTERFACE PRINCIPALE (appel des fonctions)
# ============================================================

st.markdown('<div class="main-title">🎓 Analyse des Filières ENSAH</div>',
            unsafe_allow_html=True)
st.markdown('<div class="subtitle">Scénario de classement : 50% AP1 + 50% AP2</div>',
            unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.header("📁 Fichiers source")
    uploaded_ap1 = st.file_uploader("AP1.xlsx", type=['xlsx'])
    uploaded_ap2 = st.file_uploader("AP2.xlsx", type=['xlsx'])
    uploaded_pdf = st.file_uploader("Filliéres.pdf", type=['pdf'])
    st.markdown("---")
    st.caption("💡 Charge les 3 fichiers pour commencer.")
    use_local = st.checkbox("Utiliser les fichiers du dossier courant", value=False)

# --- Chargement ---
df = affectations = infos_filieres = None

if use_local:
    try:
        with open('AP1.xlsx', 'rb') as f: ap1_bytes = f.read()
        with open('AP2.xlsx', 'rb') as f: ap2_bytes = f.read()
        with open('Filliéres.pdf', 'rb') as f: pdf_bytes = f.read()
        with st.spinner("Traitement des fichiers locaux..."):
            df, affectations, infos_filieres = process_files(ap1_bytes, ap2_bytes, pdf_bytes)
        st.success("✅ Fichiers locaux chargés")
    except FileNotFoundError as e:
        st.error(f"❌ Fichier introuvable : {e}")
elif uploaded_ap1 and uploaded_ap2 and uploaded_pdf:
    with st.spinner("Traitement des fichiers uploadés..."):
        df, affectations, infos_filieres = process_files(
            uploaded_ap1.getvalue(),
            uploaded_ap2.getvalue(),
            uploaded_pdf.getvalue()
        )
    st.success("✅ Fichiers chargés avec succès")

# --- Affichage principal ---
if df is not None:
    total = len(df)

    # Résumé global
    with st.expander("📊 Résumé global des filières", expanded=False):
        st.markdown(f"**Nombre total d'étudiants :** {total}")
        st.markdown(f"**Affectations détectées :** {len(affectations)}")

        rows = []
        for code in ORDRE:
            info = infos_filieres[code]
            rows.append({
                'Code': code,
                'Filière': FILIERES[code],
                'Places': info['nb'],
                'Meilleur rang': info['meilleur_rang'] or '-',
                'Pire rang': info['pire_rang'] or '-',
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")

    # Recherche étudiant
    st.header("🔍 Analyse d'un étudiant")

    col1, col2 = st.columns([3, 1])
    with col1:
        nom_input = st.text_input(
            "Nom complet de l'étudiant",
            placeholder="Ex: AARAB Mohamed Amine"
        )
    with col2:
        st.write("")
        st.write("")
        analyser = st.button("🔎 Analyser", type="primary", use_container_width=True)

    if analyser and nom_input:
        key = normalize(nom_input)
        matches = df[df['Nom_clean'] + df['Prenom_clean'] == key]
        if matches.empty:
            matches = df[df['Nom_clean'] + df['Prenom_clean'].str.contains(key, na=False)]

        if matches.empty:
            st.error(f"❌ Aucun étudiant trouvé pour **'{nom_input}'**")
            st.info("💡 Essayez : NOM Prénom (ex: AARAB Mohamed Amine)")
        elif len(matches) > 1:
            st.warning(f"⚠️ {len(matches)} étudiants trouvés. Sélectionnez :")
            options = [f"{r['NomComplet']} (Rang {int(r['Rang_50_50'])})"
                       for _, r in matches.iterrows()]
            choix = st.selectbox("Étudiant :", options)
            idx = options.index(choix)
            etudiant = matches.iloc[idx]
            afficher_fiche(etudiant, total, affectations, infos_filieres, df)
        else:
            etudiant = matches.iloc[0]
            afficher_fiche(etudiant, total, affectations, infos_filieres, df)

else:
    st.info("👈 Commence par charger les 3 fichiers dans la barre latérale, "
            "ou coche « Utiliser les fichiers du dossier courant ».")  
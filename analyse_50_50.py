import pdfplumber
import pandas as pd
import re
from unidecode import unidecode

# ------------------- CONFIG -------------------
FILLIERES_PDF = 'Filliéres.pdf'
AP1_FILE      = 'AP1.xlsx'
AP2_FILE      = 'AP2.xlsx'

# Codes des filières dans Filliéres.pdf
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


# ------------------- FONCTIONS -------------------

def normalize(s):
    if pd.isna(s): return ''
    s = str(s).strip().upper()
    s = unidecode(s)
    return re.sub(r'[^A-Z]', '', s)


def to_float(x):
    if pd.isna(x): return None
    try: return float(str(x).replace(',', '.').strip())
    except: return None


def find_header_row(path, sheet_name=0, max_rows=20):
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=max_rows)
    for i in range(len(raw)):
        vals = [str(v).strip().lower() for v in raw.iloc[i].values if pd.notna(v)]
        if 'nom' in vals and ('prénom' in vals or 'prenom' in vals):
            return i
    return 0


def load_excel(path, prefix):
    xls = pd.ExcelFile(path)
    best_df, best_count = None, 0
    for sheet in xls.sheet_names:
        try:
            h = find_header_row(path, sheet)
            df = pd.read_excel(path, sheet_name=sheet, header=h).dropna(how='all')
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


def get_affectations(pdf_path, all_df):
    """Retourne {key: code_filiere}."""
    txt = ""
    with pdfplumber.open(pdf_path) as pdf:
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


# ------------------- MAIN -------------------

if __name__ == '__main__':
    print("=" * 65)
    print("  ANALYSE DE FILIÈRE - SCÉNARIO 50/50 (AP1 + AP2)")
    print("=" * 65)

    # 1. Chargement
    print("\n⏳ Chargement des données...")
    ap1 = load_excel(AP1_FILE, 'AP1')
    ap2 = load_excel(AP2_FILE, 'AP2')
    df = ap2.merge(ap1[['key', 'AP1_Moyenne']].drop_duplicates('key'),
                   on='key', how='left')
    df['NomComplet'] = df['Nom'] + ' ' + df['Prénom']

    # 2. Moyenne 50/50
    df['Moy_50_50'] = (df['AP1_Moyenne'] + df['AP2_Moyenne']) / 2
    df['Rang_50_50'] = df['Moy_50_50'].rank(ascending=False, method='min')

    # Trier par rang 50/50
    df = df.sort_values('Rang_50_50').reset_index(drop=True)
    total = len(df)

    # 3. Affectations réelles
    affectations = get_affectations(FILLIERES_PDF, df)

    # 4. Capacités par filière
    capacites = {c: 0 for c in FILIERES}
    for code in affectations.values():
        capacites[code] += 1

    print(f"✅ {len(df)} étudiants chargés.")
    print(f"✅ {len(affectations)} affectations détectées dans le PDF.")

    # 5. Résumé global
    print("\n" + "=" * 65)
    print("  RÉSUMÉ DES FILIÈRES (scénario 50/50)")
    print("=" * 65)
    print(f"\n  {'Filière':<50} | {'Places':>6} | {'Pire rang':>9}")
    print("  " + "-" * 70)

    infos_filieres = {}
    for code in ORDRE:
        admis = df[df['key'].isin([k for k, v in affectations.items() if v == code])]
        if len(admis) > 0:
            pire_rang = int(admis['Rang_50_50'].max())
        else:
            pire_rang = '-'
        infos_filieres[code] = pire_rang
        print(f"  {FILIERES[code]:<50} | {len(admis):>6} | {str(pire_rang):>9}")

    # 6. Boucle : analyser un étudiant
    while True:
        print("\n" + "=" * 65)
        nom = input("Nom complet de l'étudiant (ex: AARAB Mohamed Amine)\n"
                    "ou 'q' pour quitter : ").strip()
        if nom.lower() in ('q', 'quit', 'exit', ''):
            print("\nAu revoir 👋")
            break

        key = normalize(nom)
        matches = df[df['Nom_clean'] + df['Prenom_clean'] == key]
        if matches.empty:
            matches = df[df['Nom_clean'] + df['Prenom_clean'].str.contains(key, na=False)]

        if matches.empty:
            print(f"❌ Aucun étudiant trouvé pour '{nom}'.")
            continue

        if len(matches) > 1:
            print(f"\n⚠️ {len(matches)} étudiants trouvés :")
            for i, (_, r) in enumerate(matches.iterrows(), 1):
                print(f"   {i}. {r['NomComplet']}")
            try:
                idx = int(input("Numéro : ")) - 1
                etudiant = matches.iloc[idx]
            except:
                continue
        else:
            etudiant = matches.iloc[0]

        # ------- Fiche étudiant -------
        print("\n" + "=" * 65)
        print(f"  FICHE : {etudiant['NomComplet']}")
        print("=" * 65)
        print(f"  AP1 Moyenne  : {etudiant['AP1_Moyenne']}")
        print(f"  AP2 Moyenne  : {etudiant['AP2_Moyenne']}")
        print(f"  Moyenne 50/50: {etudiant['Moy_50_50']:.2f}")
        print(f"  Rang 50/50   : {int(etudiant['Rang_50_50'])} / {total}")

        # Affectation réelle
        aff_reelle = affectations.get(etudiant['key'])
        if aff_reelle:
            print(f"  Affectation  : {FILIERES[aff_reelle]} ({aff_reelle})")
        else:
            print(f"  Affectation  : non trouvée dans le PDF")

        # ------- Analyse de chaque filière -------
        print("\n" + "=" * 65)
        print("  ANALYSE : DROIT OU PAS ? (pour chaque filière)")
        print("=" * 65)
        print(f"\n  {'Filière':<50} | {'Pire rang':>9} | {'Verdict':<15}")
        print("  " + "-" * 82)

        for code in ORDRE:
            pire_rang = infos_filieres[code]
            mon_rang = etudiant['Rang_50_50']

            if pire_rang == '-':
                verdict = "Aucune place"
            elif mon_rang <= pire_rang:
                verdict = "✅ DÛ"
            else:
                verdict = f"❌ Non ({int(mon_rang - pire_rang)} places)"

            marqueur = " ← ACTUELLE" if code == aff_reelle else ""
            print(f"  {FILIERES[code]:<50} | {str(pire_rang):>9} | {verdict}{marqueur}")

        # ------- Détail d'une filière au choix -------
        print("\n" + "=" * 65)
        rep = input("Voir le détail d'une filière ? Entrez son code (ex: GI) ou Entrée : ").strip().upper()
        if rep in FILIERES:
            print(f"\n🔍 DÉTAIL : {FILIERES[rep]}")
            print("=" * 65)
            admis = df[df['key'].isin([k for k, v in affectations.items() if v == rep])]
            admis = admis.sort_values('Rang_50_50')
            nb = len(admis)

            print(f"\n  Nombre de places : {nb}")
            print(f"  Pire rang admis  : {int(admis['Rang_50_50'].max())}")
            print(f"  Meilleur rang    : {int(admis['Rang_50_50'].min())}")

            # Voir le dernier admis
            dernier = admis.iloc[-1]
            print(f"\n  🚪 DERNIER ADMIS :")
            print(f"     {dernier['NomComplet']}  (Rang {int(dernier['Rang_50_50'])}, Moy 50/50 : {dernier['Moy_50_50']:.2f})")

            # Comparaison avec l'étudiant
            mon_rang = etudiant['Rang_50_50']
            if mon_rang <= dernier['Rang_50_50']:
                print(f"\n  ✅ Tu avais le DROIT à cette filière (rang {int(mon_rang)} ≤ {int(dernier['Rang_50_50'])})")
            else:
                diff = int(mon_rang - dernier['Rang_50_50'])
                print(f"\n  ❌ Tu étais {diff} place(s) après le dernier admis")

            # Voir les 10 étudiants autour de ton rang dans cette filière
            print(f"\n  📋 Étudiants autour de ton rang ({int(mon_rang)}) :")
            print(f"  {'Rang':>5} | {'Nom complet':<35} | {'Moy 50/50':>9} | Statut")
            print("  " + "-" * 75)
            for _, r in admis.iterrows():
                r_ = int(r['Rang_50_50'])
                if abs(r_ - mon_rang) <= 8:
                    statut = "ADMIS ✅"
                    print(f"  {r_:>5} | {r['NomComplet']:<35} | {r['Moy_50_50']:>9.2f} | {statut}")

            # Voir les étudiants juste après (non admis)
            non_admis = df[~df['key'].isin(admis['key'])]
            non_admis_proches = non_admis[
                (non_admis['Rang_50_50'] > dernier['Rang_50_50']) &
                (non_admis['Rang_50_50'] <= dernier['Rang_50_50'] + 10)
            ]
            if len(non_admis_proches) > 0:
                print(f"\n  ❌ Étudiants juste après (non admis) :")
                for _, r in non_admis_proches.iterrows():
                    r_ = int(r['Rang_50_50'])
                    aff = affectations.get(r['key'])
                    aff_nom = FILIERES.get(aff, 'N/A')
                    print(f"  {r_:>5} | {r['NomComplet']:<35} | {r['Moy_50_50']:>9.2f} | → {aff_nom}")

        input("\n⏎ Appuyez sur Entrée pour un autre étudiant...")
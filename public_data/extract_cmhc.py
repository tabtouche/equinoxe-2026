"""Extraction reproductible des cinq fichiers SCHL, sans dépendance Excel supplémentaire."""
from pathlib import Path
import posixpath
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import pandas as pd

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
MARKETS = {"Montréal (RMR)": "Montréal", "Ottawa-Gatineau (RMR) (ON)": "Ottawa — partie Ontario",
           "Ottawa-Gatineau (RMR) (partie ON)": "Ottawa — partie Ontario"}

def read_workbook(path):
    """Lit les valeurs enregistrées des cellules, y compris les chaînes partagées."""
    with ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(node.itertext()) for node in ET.fromstring(
                archive.read("xl/sharedStrings.xml")).findall("m:si", NS)]
        targets = {r.attrib["Id"]: r.attrib["Target"] for r in ET.fromstring(
            archive.read("xl/_rels/workbook.xml.rels"))}
        sheets = {}
        for sheet in ET.fromstring(archive.read("xl/workbook.xml")).findall("m:sheets/m:sheet", NS):
            target = targets[sheet.attrib[f"{{{REL}}}id"]]
            target = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
            rows = []
            for row in ET.fromstring(archive.read(target)).findall("m:sheetData/m:row", NS):
                cells = {}
                for cell in row.findall("m:c", NS):
                    value = cell.find("m:v", NS)
                    if cell.get("t") == "inlineStr":
                        text = "".join(cell.find("m:is", NS).itertext())
                    elif value is None:
                        continue
                    else:
                        text = strings[int(value.text)] if cell.get("t") == "s" else value.text
                    column = re.sub(r"\d+", "", cell.attrib["r"])
                    cells[column] = text
                rows.append((int(row.attrib["r"]), cells))
            sheets[sheet.attrib["name"]] = rows
        return sheets

def number(value):
    """Conserve les données supprimées/non disponibles comme valeurs manquantes."""
    if value is None:
        return float("nan")
    cleaned = re.sub(r"[\s\u00a0\u202f]", "", str(value)).replace(",", ".")
    return float(cleaned) if re.fullmatch(r"-?\d+(\.\d+)?", cleaned) else float("nan")

def extract_public_data(raw_dir="raw_public_data"):
    records, audit = [], []
    for year in range(2021, 2026):
        path = Path(raw_dir) / f"rmr-canada-{year}-fr.xlsx"
        sheets = read_workbook(path)
        name1 = next(name for name in sheets if re.fullmatch(r"Table(?:au)? 1\.0", name))
        name4 = next(name for name in sheets if re.fullmatch(r"Table(?:au)? 4\.1", name))
        rows1, rows4 = dict(sheets[name1]), dict(sheets[name4])
        # Vérifier les en-têtes avant d'appliquer les colonnes identifiées dans les cinq fichiers.
        assert "inoccupation" in rows1[6]["B"].lower()
        assert any(word in rows1[6]["G"].lower() for word in ["rotation", "roulement"])
        assert "deux chambres" in rows1[6]["L"].lower()
        assert "univers" in rows4[6]["L"].lower()
        period = rows1[7]["D"]
        assert str(year) in period or str(year)[-2:] in period, (path, period)
        universes = {MARKETS[cells["A"]]: (row, cells) for row, cells in sheets[name4]
                     if cells.get("A") in MARKETS}
        for row, cells in sheets[name1]:
            label = cells.get("A")
            if label not in MARKETS:
                continue
            market = MARKETS[label]
            universe_row, universe_cells = universes[market]
            # D/I/N = année du fichier dans 1.0 ; N = univers ELL, pas univers des copropriétés.
            record = {"year": year, "market": market,
                      "vacancy_rate": number(cells.get("D")),
                      "turnover_rate": number(cells.get("I")),
                      "rent": number(cells.get("N")),
                      "rental_universe": number(universe_cells.get("N"))}
            # Les valeurs ELL du tableau 4.1 doivent concorder avec celles du tableau 1.0.
            assert record["vacancy_rate"] == number(universe_cells.get("D")), (path, market)
            assert record["rent"] == number(universe_cells.get("I")), (path, market)
            records.append(record)
            for variable, table, source_row, column, source_cells, quality in [
                ("vacancy_rate", name1, row, "D", cells, "E"),
                ("turnover_rate", name1, row, "I", cells, "J"),
                ("rent", name1, row, "N", cells, "O"),
                ("rental_universe", name4, universe_row, "N", universe_cells, None),
            ]:
                audit.append({"year": year, "market": market, "variable": variable,
                              "source_file": path.name, "source_sheet": table,
                              "source_cell": f"{column}{source_row}",
                              "raw_value": source_cells.get(column),
                              "quality_code": source_cells.get(quality) if quality else None})
    df = pd.DataFrame(records).sort_values(["market", "year"]).reset_index(drop=True)
    df["rental_universe"] = df.rental_universe.astype("Int64")
    assert len(df) == 10 and not df.duplicated(["year", "market"]).any()
    assert df[["vacancy_rate", "turnover_rate", "rent", "rental_universe"]].notna().all().all()
    assert df.vacancy_rate.between(0, 100).all() and df.turnover_rate.between(0, 100).all()
    assert df.rent.gt(0).all() and df.rental_universe.gt(0).all()
    return df, pd.DataFrame(audit)

if __name__ == "__main__":
    df_public, sources = extract_public_data()
    output = Path("public_data")
    output.mkdir(exist_ok=True)
    df_public.to_csv(output / "cmhc_market_data.csv", index=False)
    sources.to_csv(output / "cmhc_market_sources.csv", index=False)
    print(df_public.to_string(index=False))
    print("Vérifications réussies : 10 observations, 40 valeurs traçables, cohérence entre tableaux 1.0 et 4.1.")

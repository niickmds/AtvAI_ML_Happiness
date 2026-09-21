"""Funções auxiliares do LAB Felicidade por Idade e por País.

O módulo prioriza os arquivos locais da pasta data/ para os dados do OWID.
Os indicadores do Banco Mundial são buscados pela API pública e salvos em
data/world_bank_country_table.csv na primeira execução.
"""

from __future__ import annotations

from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import requests

OWID_AGE_URL = "https://ourworldindata.org/grapher/cantril-ladder-age-groups.csv"
WB_API = "https://api.worldbank.org/v2"

AGE_MID = {
    "Up to 29 years": 22,
    "30-44 years": 37,
    "45-59 years": 52,
    "60+ years": 70,
}

WB_INDICATORS = {
    "gdp_pc": "NY.GDP.PCAP.PP.KD",
    "pop": "SP.POP.TOTL",
    "area_km2": "AG.LND.TOTL.K2",
}

HERE = Path(__file__).resolve().parent
DEFAULT_AGE_CSV = HERE / "data" / "cantril-ladder-age-groups.csv"
DEFAULT_WB_CACHE = HERE / "data" / "world_bank_country_table.csv"


def _read_age_raw(path: str | Path | None = None) -> pd.DataFrame:
    """Lê o CSV largo do OWID, priorizando o arquivo local do projeto."""
    if path is not None:
        return pd.read_csv(path)
    if DEFAULT_AGE_CSV.exists():
        return pd.read_csv(DEFAULT_AGE_CSV)
    return pd.read_csv(OWID_AGE_URL)


def load_owid_age(path: str | Path | None = None) -> pd.DataFrame:
    """Carrega o dado por idade e devolve formato longo."""
    raw = _read_age_raw(path)
    value_cols = ["Up to 29 years", "30-44 years", "45-59 years", "60+ years"]
    missing = [c for c in ["Entity", "Code", "Year", *value_cols] if c not in raw.columns]
    if missing:
        raise ValueError(f"Colunas esperadas ausentes no arquivo OWID: {missing}")

    age = (
        raw.melt(
            id_vars=["Entity", "Code", "Year"],
            value_vars=value_cols,
            var_name="age_group",
            value_name="ladder_mean",
        )
        .rename(columns={"Entity": "country", "Code": "iso3", "Year": "year"})
        .dropna(subset=["iso3", "ladder_mean"])
        .reset_index(drop=True)
    )
    age["window"] = "2021-2023"
    age["synthetic"] = False
    return age[["country", "iso3", "year", "age_group", "ladder_mean", "window", "synthetic"]]


_MANUAL_ISO3 = {
    "Bolivia": "BOL",
    "Bolivia (Plurinational State of)": "BOL",
    "Brunei": "BRN",
    "Cape Verde": "CPV",
    "Congo (Brazzaville)": "COG",
    "The Republic of the Congo": "COG",
    "Congo (Kinshasa)": "COD",
    "The Democratic Republic of the Congo": "COD",
    "Czech Republic": "CZE",
    "Czechia": "CZE",
    "Hong Kong S.A.R. of China": "HKG",
    "Hong Kong (S.A.R. of China)": "HKG",
    "Iran": "IRN",
    "Ivory Coast": "CIV",
    "Kosovo": "XKX",
    "Laos": "LAO",
    "Moldova": "MDA",
    "Palestinian Territories": "PSE",
    "State of Palestine": "PSE",
    "Russia": "RUS",
    "South Korea": "KOR",
    "Syria": "SYR",
    "Taiwan Province of China": "TWN",
    "Tanzania": "TZA",
    "Türkiye": "TUR",
    "Turkey": "TUR",
    "United States": "USA",
    "The Dominican Republic": "DOM",
    "The Comoros": "COM",
    "Venezuela": "VEN",
    "Vietnam": "VNM",
}


def _one_to_iso3(name: object) -> str | float:
    if pd.isna(name):
        return np.nan
    s = str(name).strip()
    if s in _MANUAL_ISO3:
        return _MANUAL_ISO3[s]

    try:
        import country_converter as coco
        code = coco.convert(names=s, to="ISO3", not_found=None)
        if code and str(code).lower() not in {"not found", "none", "nan"}:
            return str(code)
    except Exception:
        pass

    try:
        import pycountry
        return pycountry.countries.lookup(s).alpha_3
    except Exception:
        return np.nan


def to_iso3(names: pd.Series, verbose: bool = True) -> pd.Series:
    """Converte nomes de países para ISO3 e lista nomes não reconhecidos."""
    out = names.map(_one_to_iso3)
    if verbose:
        unmatched = sorted(names[out.isna()].dropna().astype(str).unique())
        if unmatched:
            print("Nomes sem correspondência ISO3:", unmatched)
        else:
            print("Todos os nomes foram convertidos para ISO3.")
    return out


def _request_json(url: str, params: dict) -> object:
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def _wb_country_metadata() -> pd.DataFrame:
    """Retorna somente economias/países, excluindo agregados regionais."""
    payload = _request_json(
        f"{WB_API}/country",
        {"format": "json", "per_page": 400},
    )
    rows = payload[1]
    keep = []
    for rec in rows:
        region = rec.get("region") or {}
        iso3 = rec.get("id")
        # Agregados do Banco Mundial têm region.id vazio.
        if iso3 and region.get("id"):
            keep.append({"iso3": iso3, "country_wb": rec.get("name")})
    return pd.DataFrame(keep).drop_duplicates("iso3")


def fetch_wb(indicator: str, start: int = 2019, end: int = 2023) -> pd.DataFrame:
    """Busca o último valor não faltante de um indicador na janela informada."""
    payload = _request_json(
        f"{WB_API}/country/all/indicator/{indicator}",
        {
            "format": "json",
            "per_page": 20000,
            "date": f"{start}:{end}",
        },
    )
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        raise RuntimeError(f"Resposta inesperada do Banco Mundial para {indicator}")

    valid = set(_wb_country_metadata()["iso3"])
    rows = []
    for rec in payload[1]:
        iso3 = rec.get("countryiso3code")
        value = rec.get("value")
        year = rec.get("date")
        if iso3 in valid and value is not None:
            rows.append({"iso3": iso3, "year": int(year), "value": float(value)})

    data = pd.DataFrame(rows)
    if data.empty:
        raise RuntimeError(f"Nenhum valor encontrado para {indicator} em {start}-{end}")

    # Último valor não faltante por país.
    latest = (
        data.sort_values(["iso3", "year"], ascending=[True, False])
        .drop_duplicates("iso3")
        .sort_values("iso3")
        .reset_index(drop=True)
    )
    return latest


def build_country_table(
    start: int = 2019,
    end: int = 2023,
    cache_path: str | Path | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """Monta PIB pc PPC, população e área por ISO3 e salva cache local."""
    cache = Path(cache_path) if cache_path is not None else DEFAULT_WB_CACHE
    if cache.exists() and not refresh:
        out = pd.read_csv(cache)
        required = {"iso3", "gdp_pc", "pop", "area_km2"}
        if required.issubset(out.columns):
            return out

    meta = _wb_country_metadata()
    out = meta.copy()

    for col, indicator in WB_INDICATORS.items():
        part = fetch_wb(indicator, start=start, end=end).rename(
            columns={"value": col, "year": f"{col}_year"}
        )
        out = out.merge(part, on="iso3", how="left", validate="one_to_one")

    cache.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(cache, index=False)
    return out


def make_synthetic_age_data(country_table: pd.DataFrame, random_state: int = 42) -> pd.DataFrame:
    """Fallback didático: simula dados por idade. Não usar como evidência empírica."""
    rng = np.random.default_rng(random_state)
    rows = []
    ct = country_table.dropna(subset=["gdp_pc"]).copy()
    if ct.empty:
        raise ValueError("country_table precisa conter gdp_pc para a simulação.")

    lgdp = np.log(ct["gdp_pc"])
    center = lgdp.mean()
    for _, r in ct.iterrows():
        base = 5.5 + 0.65 * (np.log(r["gdp_pc"]) - center)
        for group, age in AGE_MID.items():
            curve = 0.00045 * (age - 50) ** 2 - 0.25
            rows.append(
                {
                    "country": r.get("country_wb", r["iso3"]),
                    "iso3": r["iso3"],
                    "year": 2023,
                    "age_group": group,
                    "ladder_mean": float(np.clip(base + curve + rng.normal(0, 0.18), 0, 10)),
                    "window": "synthetic",
                    "synthetic": True,
                }
            )
    warnings.warn("Dados sintéticos gerados apenas para teste de pipeline.")
    return pd.DataFrame(rows)

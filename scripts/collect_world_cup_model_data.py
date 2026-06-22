from __future__ import annotations

import argparse
import io
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
from urllib.parse import urljoin


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


LOGGER = logging.getLogger("world_cup_data_collector")
pd = None
requests = None
BeautifulSoup = None

STATSBOMB_COMPETITION_ID = 43
STATSBOMB_2022_SEASON_ID = 106
FOOTBALL_DATA_INDEX_URL = "https://www.football-data.co.uk/data.php"


def require_runtime_dependencies() -> None:
    global BeautifulSoup, pd, requests
    missing = []
    for module_name in ["pandas", "requests", "bs4"]:
        try:
            module = import_module(module_name)
        except ImportError:
            missing.append(module_name)
            continue
        if module_name == "pandas":
            pd = module
        elif module_name == "requests":
            requests = module
        elif module_name == "bs4":
            BeautifulSoup = module.BeautifulSoup
    if missing:
        raise RuntimeError(
            "Missing runtime dependencies: "
            + ", ".join(missing)
            + '. Install project dependencies with: python -m pip install -e ".[data]"'
        )


@dataclass(frozen=True)
class MatchCandidate:
    row_index: int
    date: pd.Timestamp
    home_team: str
    away_team: str
    score: float


def configure_logging(log_file: Path, verbose: bool = False) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_file, encoding="utf-8")],
    )


def normalize_team_name(name: object) -> str:
    if pd.isna(name):
        return ""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    replacements = {
        "&": " and ",
        "u.s.a.": "usa",
        "united states": "usa",
        "south korea": "korea republic",
        "korea south": "korea republic",
        "czech republic": "czechia",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fuzzy_score(left: str, right: str) -> float:
    from difflib import SequenceMatcher

    left_norm = normalize_team_name(left)
    right_norm = normalize_team_name(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    token_score = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
    seq_score = SequenceMatcher(None, left_norm, right_norm).ratio()
    return max(token_score, seq_score)


def parse_date(date_value: object, time_value: object = None) -> pd.Timestamp:
    if pd.isna(date_value):
        return pd.NaT
    text = str(date_value).strip()
    if time_value is not None and not pd.isna(time_value) and str(time_value).strip():
        text = f"{text} {str(time_value).strip()}"
    parsed = pd.to_datetime(text, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        parsed = pd.to_datetime(str(date_value), errors="coerce")
    return parsed


def first_existing(row: pd.Series, names: Sequence[str]) -> object:
    for name in names:
        if name in row.index and not pd.isna(row[name]):
            return row[name]
    return pd.NA


def first_existing_column(df: pd.DataFrame, names: Sequence[str]) -> Optional[str]:
    lower_to_actual = {column.lower(): column for column in df.columns}
    for name in names:
        actual = lower_to_actual.get(name.lower())
        if actual:
            return actual
    return None


def download_url(url: str, timeout: float = 30.0) -> bytes:
    LOGGER.info("Downloading %s", url)
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "SportMira research data collector/0.1"})
    response.raise_for_status()
    return response.content


def discover_football_data_files(index_url: str = FOOTBALL_DATA_INDEX_URL) -> List[str]:
    try:
        html_bytes = download_url(index_url)
    except Exception:
        LOGGER.exception("Could not discover Football-Data links from %s", index_url)
        return []

    soup = BeautifulSoup(html_bytes, "lxml")
    discovered: List[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        text = anchor.get_text(" ", strip=True).lower()
        absolute = urljoin(index_url, href)
        if absolute.lower().endswith((".csv", ".xlsx", ".xls")) and (
            "world" in text or "international" in text or "cup" in text or "worldcup" in absolute.lower()
        ):
            discovered.append(absolute)
    unique = sorted(set(discovered))
    LOGGER.info("Discovered %d Football-Data downloadable candidate(s)", len(unique))
    return unique


def read_tabular_bytes(content: bytes, url: str) -> pd.DataFrame:
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(io.BytesIO(content))
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(io.BytesIO(content))
    raise ValueError(f"Unsupported Football-Data file extension for {url}")


def load_football_data(urls: Sequence[str]) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for url in urls:
        try:
            frame = read_tabular_bytes(download_url(url), url)
            frame["football_data_source_url"] = url
            frames.append(frame)
            LOGGER.info("Loaded Football-Data file %s with shape %s", url, frame.shape)
        except Exception:
            LOGGER.exception("Failed to load Football-Data file %s", url)
    if not frames:
        LOGGER.warning("No Football-Data files loaded; odds/card columns will be empty.")
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def clean_football_data(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return raw

    date_col = first_existing_column(raw, ["Date", "MatchDate", "Kickoff", "KickOff"])
    time_col = first_existing_column(raw, ["Time", "KickoffTime", "KickOffTime"])
    home_col = first_existing_column(raw, ["HomeTeam", "Home", "Home Team"])
    away_col = first_existing_column(raw, ["AwayTeam", "Away", "Away Team"])
    if not (date_col and home_col and away_col):
        raise ValueError("Football-Data file is missing required date/home/away columns.")

    records = []
    for _, row in raw.iterrows():
        match_date = parse_date(row[date_col], row[time_col] if time_col else None)
        records.append(
            {
                "fd_match_date": match_date,
                "fd_match_day": match_date.normalize() if not pd.isna(match_date) else pd.NaT,
                "fd_home_team": row[home_col],
                "fd_away_team": row[away_col],
                "fd_home_team_norm": normalize_team_name(row[home_col]),
                "fd_away_team_norm": normalize_team_name(row[away_col]),
                "home_yellow_cards": first_existing(row, ["HY", "HomeYellow", "HomeYellows"]),
                "away_yellow_cards": first_existing(row, ["AY", "AwayYellow", "AwayYellows"]),
                "home_red_cards": first_existing(row, ["HR", "HomeRed", "HomeReds"]),
                "away_red_cards": first_existing(row, ["AR", "AwayRed", "AwayReds"]),
                "b365_open_home": first_existing(row, ["B365H", "B365OH", "B365OpenH"]),
                "b365_open_draw": first_existing(row, ["B365D", "B365OD", "B365OpenD"]),
                "b365_open_away": first_existing(row, ["B365A", "B365OA", "B365OpenA"]),
                "b365_close_home": first_existing(row, ["B365CH", "B365CloseH", "B365C_H"]),
                "b365_close_draw": first_existing(row, ["B365CD", "B365CloseD", "B365C_D"]),
                "b365_close_away": first_existing(row, ["B365CA", "B365CloseA", "B365C_A"]),
                "b365_open_over_25": first_existing(row, ["B365>2.5", "B365O2.5", "B365Over2.5"]),
                "b365_open_under_25": first_existing(row, ["B365<2.5", "B365U2.5", "B365Under2.5"]),
                "b365_close_over_25": first_existing(row, ["B365C>2.5", "B365CO2.5", "B365CloseOver2.5"]),
                "b365_close_under_25": first_existing(row, ["B365C<2.5", "B365CU2.5", "B365CloseUnder2.5"]),
                "football_data_source_url": row.get("football_data_source_url", pd.NA),
            }
        )

    clean = pd.DataFrame(records)
    numeric_cols = [column for column in clean.columns if column.startswith(("home_", "away_", "b365_"))]
    for column in numeric_cols:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")
    LOGGER.info("Cleaned Football-Data frame shape: %s", clean.shape)
    return clean


def load_statsbomb_world_cup(competition_id: int, season_id: int) -> pd.DataFrame:
    try:
        from statsbombpy import sb
    except ImportError as exc:
        raise RuntimeError("statsbombpy is not installed. Install with: pip install statsbombpy") from exc

    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    LOGGER.info("Loaded %d StatsBomb matches", len(matches))

    team_rows = []
    for _, match in matches.iterrows():
        match_id = int(match["match_id"])
        home_team = str(match["home_team"])
        away_team = str(match["away_team"])
        match_date = parse_date(match.get("match_date"))
        try:
            events = sb.events(match_id=match_id, split=False, flatten_attrs=True)
        except Exception:
            LOGGER.exception("StatsBomb events failed for match_id=%s", match_id)
            continue

        if events.empty:
            LOGGER.warning("No StatsBomb events for match_id=%s", match_id)
            continue

        if "type" not in events.columns or "team" not in events.columns:
            LOGGER.warning("Unexpected StatsBomb event schema for match_id=%s", match_id)
            continue

        for team in [home_team, away_team]:
            team_events = events[events["team"].astype(str) == team].copy()
            shots = team_events[team_events["type"].astype(str) == "Shot"]
            passes = team_events[team_events["type"].astype(str) == "Pass"].copy()
            interceptions = team_events[team_events["type"].astype(str) == "Interception"]

            if "location" in passes.columns:
                passes["start_x"] = passes["location"].apply(lambda value: value[0] if isinstance(value, list) and value else pd.NA)
                attacking_third_passes = passes[pd.to_numeric(passes["start_x"], errors="coerce") >= 80]
            else:
                LOGGER.warning("StatsBomb pass location missing for match_id=%s; using all passes for team=%s", match_id, team)
                attacking_third_passes = passes

            if "pass_outcome" in attacking_third_passes.columns:
                successful_attacking_third_passes = attacking_third_passes["pass_outcome"].isna().sum()
            else:
                successful_attacking_third_passes = len(attacking_third_passes)

            attacking_pass_count = len(attacking_third_passes)
            team_rows.append(
                {
                    "statsbomb_match_id": match_id,
                    "match_date": match_date,
                    "match_day": match_date.normalize() if not pd.isna(match_date) else pd.NaT,
                    "home_team": home_team,
                    "away_team": away_team,
                    "team": team,
                    "team_norm": normalize_team_name(team),
                    "is_home": team == home_team,
                    "total_shots": len(shots),
                    "xg": pd.to_numeric(shots.get("shot_statsbomb_xg", pd.Series(dtype=float)), errors="coerce").sum(),
                    "attacking_third_pass_success_rate": (
                        successful_attacking_third_passes / attacking_pass_count if attacking_pass_count else pd.NA
                    ),
                    "attacking_third_passes": attacking_pass_count,
                    "defensive_interceptions": len(interceptions),
                }
            )

    team_frame = pd.DataFrame(team_rows)
    LOGGER.info("Built StatsBomb team-level frame shape: %s", team_frame.shape)
    return team_frame


def pivot_statsbomb_team_rows(team_rows: pd.DataFrame) -> pd.DataFrame:
    if team_rows.empty:
        return pd.DataFrame()

    home = team_rows[team_rows["is_home"]].add_prefix("home_")
    away = team_rows[~team_rows["is_home"]].add_prefix("away_")
    merged = home.merge(
        away,
        left_on="home_statsbomb_match_id",
        right_on="away_statsbomb_match_id",
        how="outer",
        suffixes=("", ""),
    )
    merged["statsbomb_match_id"] = merged["home_statsbomb_match_id"].combine_first(merged["away_statsbomb_match_id"])
    merged["match_date"] = merged["home_match_date"].combine_first(merged["away_match_date"])
    merged["match_day"] = merged["home_match_day"].combine_first(merged["away_match_day"])
    merged["home_team"] = merged["home_team"].combine_first(merged["away_home_team"])
    merged["away_team"] = merged["home_away_team"].combine_first(merged["away_away_team"])
    merged["home_team_norm"] = merged["home_team_norm"]
    merged["away_team_norm"] = merged["away_team_norm"]
    return merged


def build_match_candidates(frame: pd.DataFrame, date_col: str, home_col: str, away_col: str) -> List[MatchCandidate]:
    candidates = []
    for index, row in frame.iterrows():
        date = row.get(date_col)
        if pd.isna(date):
            continue
        candidates.append(
            MatchCandidate(
                row_index=int(index),
                date=pd.Timestamp(date).normalize(),
                home_team=str(row.get(home_col, "")),
                away_team=str(row.get(away_col, "")),
                score=0.0,
            )
        )
    return candidates


def find_best_match(
    date: pd.Timestamp,
    home_team: str,
    away_team: str,
    candidates: Sequence[MatchCandidate],
    date_tolerance_days: int,
    min_score: float,
) -> Optional[MatchCandidate]:
    best: Optional[MatchCandidate] = None
    best_score = 0.0
    for candidate in candidates:
        if abs((candidate.date - date).days) > date_tolerance_days:
            continue
        same_order = (fuzzy_score(home_team, candidate.home_team) + fuzzy_score(away_team, candidate.away_team)) / 2.0
        swapped = (fuzzy_score(home_team, candidate.away_team) + fuzzy_score(away_team, candidate.home_team)) / 2.0
        score = max(same_order, swapped)
        if score > best_score:
            best = MatchCandidate(candidate.row_index, candidate.date, candidate.home_team, candidate.away_team, score)
            best_score = score
    if best and best.score >= min_score:
        return best
    return None


def merge_statsbomb_and_football_data(statsbomb_matches: pd.DataFrame, football_data: pd.DataFrame) -> pd.DataFrame:
    if statsbomb_matches.empty:
        LOGGER.warning("StatsBomb match data is empty; cannot build match-level model data.")
        return pd.DataFrame()
    if football_data.empty:
        LOGGER.warning("Football-Data is empty; returning StatsBomb features only.")
        return statsbomb_matches.copy()

    fd_candidates = build_match_candidates(football_data, "fd_match_day", "fd_home_team", "fd_away_team")
    merged_rows = []
    for _, row in statsbomb_matches.iterrows():
        candidate = find_best_match(
            pd.Timestamp(row["match_day"]),
            str(row["home_team"]),
            str(row["away_team"]),
            fd_candidates,
            date_tolerance_days=1,
            min_score=0.82,
        )
        base = row.to_dict()
        if candidate is None:
            base["football_data_match_score"] = pd.NA
            merged_rows.append(base)
            LOGGER.warning("No Football-Data match found for %s vs %s on %s", row["home_team"], row["away_team"], row["match_day"])
            continue
        fd_row = football_data.loc[candidate.row_index].to_dict()
        base.update(fd_row)
        base["football_data_match_score"] = candidate.score
        merged_rows.append(base)
    merged = pd.DataFrame(merged_rows)
    LOGGER.info("Merged model data shape: %s", merged.shape)
    return merged


def parse_asian_handicap_page(url: str, html_content: Optional[bytes] = None) -> pd.DataFrame:
    """Generic template parser for public historical Asian Handicap pages.

    Historical bookmakers use different table schemas, so this function is a
    conservative scaffold: it extracts rows that contain a handicap line and at
    least two decimal prices. Site-specific selectors can be added later without
    changing the downstream merge contract.
    """

    if html_content is None:
        html_content = download_url(url)
    soup = BeautifulSoup(html_content, "lxml")
    rows = []
    line_pattern = re.compile(r"^[+-]?\d+(?:\.(?:0|00|25|5|50|75))?$")
    odds_pattern = re.compile(r"\b\d+\.\d{2}\b")

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
            if not cells:
                continue
            joined = " | ".join(cells)
            line_matches = [
                float(cell)
                for cell in cells
                if line_pattern.match(cell) and float(cell) in {-2.0, -1.75, -1.5, -1.25, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0}
            ]
            odds_matches = [float(match) for match in odds_pattern.findall(joined)]
            if not line_matches or len(odds_matches) < 2:
                continue
            rows.append(
                {
                    "asian_handicap_source_url": url,
                    "raw_row_text": joined,
                    "handicap_line": line_matches[0],
                    "home_ah_odds": odds_matches[0],
                    "away_ah_odds": odds_matches[1],
                    "bookmaker": cells[0] if cells else pd.NA,
                }
            )
    frame = pd.DataFrame(rows).drop_duplicates()
    LOGGER.info("Parsed %d Asian Handicap candidate rows from %s", len(frame), url)
    return frame


def attach_asian_handicap_summary(model_data: pd.DataFrame, ah_urls: Sequence[str]) -> pd.DataFrame:
    if model_data.empty or not ah_urls:
        return model_data

    frames = []
    for url in ah_urls:
        try:
            frames.append(parse_asian_handicap_page(url))
        except Exception:
            LOGGER.exception("Asian Handicap template parser failed for %s", url)
    if not frames:
        return model_data

    ah = pd.concat(frames, ignore_index=True, sort=False)
    ah_summary = {
        "asian_handicap_rows_collected": len(ah),
        "asian_handicap_unique_lines": sorted(ah["handicap_line"].dropna().unique().tolist()) if "handicap_line" in ah else [],
    }
    for key, value in ah_summary.items():
        model_data[key] = str(value) if isinstance(value, list) else value
    return model_data


def save_output(frame: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8")
    LOGGER.info("Wrote %d rows to %s", len(frame), output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and clean data for a World Cup prediction model.")
    parser.add_argument("--output", default="world_cup_model_data.csv", type=Path)
    parser.add_argument("--log-file", default="logs/world_cup_data_collector.log", type=Path)
    parser.add_argument("--statsbomb-competition-id", default=STATSBOMB_COMPETITION_ID, type=int)
    parser.add_argument("--statsbomb-season-id", default=STATSBOMB_2022_SEASON_ID, type=int)
    parser.add_argument("--football-data-url", action="append", default=[], help="Football-Data CSV/XLSX URL. May be provided more than once.")
    parser.add_argument("--discover-football-data", action="store_true", help="Discover World Cup/international CSV/XLSX links from football-data.co.uk/data.php")
    parser.add_argument("--asian-handicap-url", action="append", default=[], help="Public historical Asian Handicap page URL template input.")
    parser.add_argument("--skip-statsbomb", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.log_file, args.verbose)

    try:
        require_runtime_dependencies()
        football_urls = list(args.football_data_url)
        if args.discover_football_data or not football_urls:
            football_urls.extend(discover_football_data_files())
        football_urls = sorted(set(football_urls))
        LOGGER.info("Football-Data URLs selected: %s", football_urls)

        if args.skip_statsbomb:
            statsbomb_matches = pd.DataFrame()
            LOGGER.warning("Skipping StatsBomb collection by request.")
        else:
            statsbomb_team_rows = load_statsbomb_world_cup(args.statsbomb_competition_id, args.statsbomb_season_id)
            statsbomb_matches = pivot_statsbomb_team_rows(statsbomb_team_rows)

        football_raw = load_football_data(football_urls)
        football_clean = clean_football_data(football_raw)
        model_data = merge_statsbomb_and_football_data(statsbomb_matches, football_clean)
        model_data = attach_asian_handicap_summary(model_data, args.asian_handicap_url)
        save_output(model_data, args.output)
        return 0
    except Exception:
        LOGGER.exception("World Cup model data collection failed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

import sys
import csv
import re
import argparse
from pathlib import Path
from itertools import chain
from contextlib import ExitStack
from datetime import timedelta, datetime
from typing import Callable, Optional, Sequence, Union, Tuple, List, Dict
from unicodedata import normalize

DEFAULT_PATH_TO_DIR = "/path/to/dpc/files"
DEFAULT_OUTPUT_ROOT = Path("./outputs")
DEFAULT_TARGET_SHEET = "./pt_list.csv"
DEFAULT_DPC_FILE_ENCODING = "cp932"
DEFAULT_DELIMITER = "\t"
DEFAULT_MARGIN_DAYS = 90
PROGRESS_EVERY = 10000
WRITE_CHUNK_SIZE = 500
FILE_NAME_PATTERN = re.compile(r"^(EFn|FF1|EFg)_.+\.txt$", re.IGNORECASE)

DEFAULT_ENCODINGS = (
    "cp932",      # Windows日本語CSV
    "utf-8-sig",
    "utf-8",
    "shift_jis",
    "euc_jp",
    "iso2022_jp",
    "latin-1",
)

DEFAULT_DELIMITERS = ("\t", ",", ";", "|")
Logger = Callable[[str], None]

def detect_encoding(
    file_path: Union[str, Path],
    encoding_candidates: Sequence[str] = DEFAULT_ENCODINGS,
    sample_size: int = 65536,
    ) -> str:
    """
    ファイル先頭バイト列から encoding を推定する。
    BOM があれば優先し、なければ候補を順に試す。
    """
    file_path = Path(file_path)
    raw = file_path.read_bytes()[:sample_size]

    # BOM 判定
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16"
    if raw.startswith(b"\xff\xfe\x00\x00") or raw.startswith(b"\x00\x00\xfe\xff"):
        return "utf-32"

    # 候補順に decode を試す
    for enc in encoding_candidates:
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue

    # 最後の保険
    return "latin-1"


def _score_delimiter(
    lines: List[str],
    delimiter: str
    ) -> Tuple[int, float]:
    """
    delimiter ごとの妥当性スコアを返す。
    - 列数が 2 以上の行が多いほど良い
    - 行ごとの列数のばらつきが少ないほど良い
    """
    counts = []
    for line in lines:
        if not line.strip():
            continue
        try:
            row = next(csv.reader([line], delimiter=delimiter))
            counts.append(len(row))
        except Exception:
            continue

    if not counts:
        return (0, float("inf"))

    valid_rows = sum(1 for c in counts if c >= 2)
    mean = sum(counts) / len(counts)
    variance = sum((c - mean) ** 2 for c in counts) / len(counts)
    return (valid_rows, variance)


def detect_delimiter(
    file_path: Union[str, Path],
    encoding: str,
    delimiters: Sequence[str] = DEFAULT_DELIMITERS,
    sample_lines: int = 10,
    sample_size: int = 65536,
    ) -> str:
    """
    テキスト冒頭から delimiter を推定する。
    まず csv.Sniffer を使い、失敗時は列数安定性で補助判定する。
    """
    file_path = Path(file_path)

    with open(file_path, "r", encoding=encoding, errors="replace", newline="") as f:
        text = f.read(sample_size)

    lines = text.splitlines()[:sample_lines]
    sample_text = "\n".join(lines)

    # 1) csv.Sniffer を優先
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters="".join(delimiters))
        if dialect.delimiter in delimiters:
            return dialect.delimiter
    except csv.Error:
        pass

    # 2) 補助判定: 列数の一貫性を見る
    scored = [(d, *_score_delimiter(lines, d)) for d in delimiters]
    # valid_rows が多い順、variance が小さい順
    scored.sort(key=lambda x: (-x[1], x[2]))

    best_delimiter = scored[0][0]
    return best_delimiter


def detect_csv_format(
    file_path: Union[str, Path],
    delimiter: Optional[str] = None,
    encoding: Optional[str] = None,
    encoding_candidates: Sequence[str] = DEFAULT_ENCODINGS,
    delimiter_candidates: Sequence[str] = DEFAULT_DELIMITERS,
    ) -> Tuple[str, str]:
    """
    delimiter / encoding の両方を決定して返す。
    明示指定があればそれを優先する。
    """
    decided_encoding = encoding or detect_encoding(
        file_path=file_path,
        encoding_candidates=encoding_candidates,
    )
    decided_delimiter = delimiter or detect_delimiter(
        file_path=file_path,
        encoding=decided_encoding,
        delimiters=delimiter_candidates,
    )
    return decided_delimiter, decided_encoding


def collect_target_files(
    root_dir: Path,
    file_name_pattern: re.Pattern[str] = FILE_NAME_PATTERN,
    ) -> List[Path]:
    return sorted(
        path
        for path in root_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".txt"
        and file_name_pattern.match(path.name)
    )


def get_sub_dir_name(
    file_path: Path,
    logger: Optional[Logger] = None,
    ) -> str:
    """
    例:
      EFn_123456789_1504.txt -> 1504
    """
    parts = file_path.stem.split("_")
    if len(parts) < 3:
        if logger is not None:
            logger(f"想定外のファイル名です: {file_path.name}")
        return 'xxxx'  # 処理対象にはしておくが、隔離されたファイルとして扱う
    return parts[2]


def build_output_path(
    output_root: Path,
    research_id: str,
    sub_dir_name: str,
    file_name: str
    ) -> Path:
    return output_root / research_id / sub_dir_name / file_name


def format_progress_message(
    file_index: int,
    total_files: int,
    file_path: Path,
    line_no: int,
    extracted_rows: int
    ) -> str:
    percent = (file_index / total_files * 100.0) if total_files else 100.0
    return (
        f"[{file_index}/{total_files} | {percent:6.2f}%] "
        f"{file_path.name} | 現在 {line_no:,} 行目 | 抽出 {extracted_rows:,} 行"
    )


def show_progress(
    file_index: int,
    total_files: int,
    file_path: Path,
    line_no: int,
    extracted_rows: int,
    progress_callback: Optional[Logger] = None,
    ) -> str:
    msg = format_progress_message(
        file_index=file_index,
        total_files=total_files,
        file_path=file_path,
        line_no=line_no,
        extracted_rows=extracted_rows,
    )
    if progress_callback is None:
        sys.stdout.write(f"\r{msg}")
        sys.stdout.flush()
    else:
        progress_callback(msg)
    return msg


def flush_buffer(writer, buffer_list):
    if buffer_list:
        writer.writerows(buffer_list)
        buffer_list.clear()

def yymm_strings_for_period(
    pt_record: dict,
    *,
    margin_before_days: int = 0,
    margin_after_days: int = 0,
    ) -> List[str]:
    """
    [start_date - margin_before_days, end_date + margin_after_days]
    に一度でも含まれる月を '%y%m' で昇順列挙する。
    """
    start_date = datetime.strptime(pt_record['encounter_start_date'], '%Y%m%d')
    end_date = datetime.strptime(pt_record['encounter_end_date'], '%Y%m%d')

    left = start_date - timedelta(days=margin_before_days)
    right = end_date + timedelta(days=margin_after_days)

    start_idx = left.year * 12 + (left.month - 1)
    end_idx = right.year * 12 + (right.month - 1)

    result = []
    for idx in range(start_idx, end_idx + 1):
        year, month0 = divmod(idx, 12)
        month = month0 + 1
        result.append(f"{year % 100:02d}{month:02d}")

    return result

def load_pt_list(
    pt_list_path: Path,
    logger: Optional[Logger] = None,
    ) -> Dict[str, Dict[str, str]]:
    """
    対象患者リストを読み込む。
    """
    pt_dict = {}
    research_ids = set()
    pt_list_encoding = detect_encoding(pt_list_path)
    if logger is not None:
        logger(f"pt_list_encoding={pt_list_encoding}")
    with open(pt_list_path, 'r', encoding=pt_list_encoding, newline='') as f:
        reader = csv.reader(f)
        pt_list_header = None
        for i, row in enumerate(reader):
            row = [value.strip() for value in row]
            if i == 0:
                pt_list_header = row
                if len(row) != len(set(row)):
                    raise ValueError("pt_list.csv の header に重複列があります")
                required_columns = {
                    "data_identifier",
                    "research_id",
                    "encounter_start_date",
                    "encounter_end_date",
                }
                missing_columns = required_columns - set(pt_list_header)
                if missing_columns:
                    missing = ", ".join(sorted(missing_columns))
                    raise ValueError(f"pt_list.csv に必須列がありません: {missing}")
                continue
            if not row or not any(row):
                continue
            if len(row) != len(pt_list_header):
                raise ValueError(f"pt_list.csv {i + 1} 行目の列数が不正です")
            record = dict(zip(pt_list_header, row))
            raw_identifier = record["data_identifier"]
            if not re.fullmatch(r"[0-9]{1,10}", raw_identifier):
                raise ValueError(f"pt_list.csv {i + 1} 行目の data_identifier が不正です")
            data_identifier = raw_identifier.zfill(10)
            research_id = record["research_id"]
            reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(1, 10)), *(f"LPT{n}" for n in range(1, 10))}
            if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", research_id)
                    or research_id.upper() in reserved):
                raise ValueError(f"pt_list.csv {i + 1} 行目の research_id が不正です")
            if any("\r" in value or "\n" in value for value in record.values()):
                raise ValueError(f"pt_list.csv {i + 1} 行目に改行を含む項目があります")
            for column in ("encounter_start_date", "encounter_end_date", "event_date"):
                value = record.get(column, "")
                if not value and column == "event_date":
                    continue
                if not re.fullmatch(r"[0-9]{8}", value):
                    raise ValueError(f"pt_list.csv {i + 1} 行目の {column} が不正です")
                try:
                    datetime.strptime(value, "%Y%m%d")
                except ValueError as exc:
                    raise ValueError(f"pt_list.csv {i + 1} 行目の {column} が不正です") from exc
            if record["encounter_start_date"] > record["encounter_end_date"]:
                raise ValueError(f"pt_list.csv {i + 1} 行目の対象期間が逆転しています")
            if data_identifier in pt_dict:
                raise ValueError(f"pt_list.csv {i + 1} 行目の data_identifier が重複しています")
            if research_id in research_ids:
                raise ValueError(f"pt_list.csv {i + 1} 行目の research_id が重複しています")
            research_ids.add(research_id)
            if len(raw_identifier) < 10 and logger is not None:
                logger(f"pt_list.csv {i + 1} 行目の data_identifier を10桁へゼロ埋めしました")
            pt_dict[data_identifier] = {k: v for k, v in record.items()
                                        if k != "data_identifier"}
        if pt_list_header is None:
            raise ValueError("pt_list.csv が空です")
    return pt_dict

def process_one_file(
    file_path: Path,
    file_index: int,
    total_files: int,
    pt_list: Dict[str, Dict[str, str]],
    output_root: Path,
    dpc_file_encoding: Optional[str],
    delimiter: Optional[str],
    *,
    progress_every: int = PROGRESS_EVERY,
    write_chunk_size: int = WRITE_CHUNK_SIZE,
    logger: Optional[Logger] = None,
    progress_callback: Optional[Logger] = None,
    ):
    """
    1つの入力ファイルを処理して、対象行だけを
    ./outputs/<research_id>/<sub_dir_name>/<file_name>
    に保存する。

    main 側でファイル名 YYMM が全患者分の和集合に含まれるものに絞ったうえで呼ばれる。
    行ごとに data_identifier が pt_list にあり、かつ当該ファイルの YYMM (sub_dir_name) が
    その患者の encounter±margin に対応する月集合 (_yymm_set) に含まれる場合のみ出力する。
    """
    decided_delimiter, decided_encoding = detect_csv_format(file_path,
                                 delimiter=delimiter, encoding=dpc_file_encoding)
    sub_dir_name = get_sub_dir_name(file_path, logger=logger)

    # 出力先ごとの writer / buffer を保持
    writers = {}
    buffers = {}

    line_no = 0
    extracted_rows = 0
    malformed_rows = 0

    with ExitStack() as stack:
        src_f = stack.enter_context(
            open(file_path, mode="r", newline="", encoding=decided_encoding)
        )
        reader = csv.reader(src_f, delimiter=decided_delimiter)

        header = []
        try:
            for line_no, row in enumerate(reader, start=1):
                if len(row) <= 1:
                    malformed_rows += 1
                    if line_no % progress_every == 0:
                        show_progress(
                            file_index,
                            total_files,
                            file_path,
                            line_no,
                            extracted_rows,
                            progress_callback=progress_callback,
                        )
                    continue

                if line_no == 1:
                    if normalize('NFKC', row[1].strip()) == 'データ識別番号':
                        header = row
                        continue

                # index=1 に ID がある前提
                data_identifier = row[1]

                if data_identifier in pt_list:
                    pt_record = pt_list[data_identifier]
                    if sub_dir_name not in pt_record["_yymm_set"]:
                        continue

                    # 出力データの data_identifier は research_id に置換する
                    output_row = row.copy()
                    output_row[1] = pt_record["research_id"]
                    out_path = build_output_path(
                        output_root=output_root,
                        research_id=pt_record["research_id"],
                        sub_dir_name=sub_dir_name,
                        file_name=file_path.name,
                    )

                    key = str(out_path)

                    if key not in writers:
                        out_path.parent.mkdir(parents=True, exist_ok=True)

                        # 1入力ファイル -> 1出力ファイル の想定なので "w"
                        # 再実行時に追記したいなら "a" に変更
                        out_f = stack.enter_context(
                            open(out_path, mode="w", newline="", encoding=decided_encoding)
                        )
                        writers[key] = csv.writer(out_f, delimiter=decided_delimiter)
                        buffers[key] = [header] if header else []

                    buffers[key].append(output_row)
                    extracted_rows += 1

                    if len(buffers[key]) >= write_chunk_size:
                        flush_buffer(writers[key], buffers[key])

                if line_no % progress_every == 0:
                    show_progress(
                        file_index,
                        total_files,
                        file_path,
                        line_no,
                        extracted_rows,
                        progress_callback=progress_callback,
                    )
        finally:
            # 途中で例外が起きても、ここまでに溜まったバッファは書き出す
            for key in writers:
                flush_buffer(writers[key], buffers[key])

    # 最終表示を1回出して改行
    show_progress(
        file_index,
        total_files,
        file_path,
        line_no,
        extracted_rows,
        progress_callback=progress_callback,
    )
    if progress_callback is None:
        sys.stdout.write("\n")
        sys.stdout.flush()

    return {
        "line_count": line_no,
        "extracted_rows": extracted_rows,
        "output_files": len(writers),
        "malformed_rows": malformed_rows,
        "delimiter": decided_delimiter,
        "encoding": decided_encoding,
    }


def write_summary_csv(
    pt_list: Dict[str, Dict[str, str]],
    output_root: Path,
    summary_path: Path,
    ) -> None:
    """
    ./outputs ディレクトリ配下の出力を集計してサマリーCSVを書き出す。
    1行=1症例, 列は research_id, FF1, EFn, EFg。
    """
    header = ["research_id", "FF1", "EFn", "EFg"]
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    with open(summary_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        pt_records = sorted(
            pt_list.values(),
            key=lambda record: record["research_id"],
        )
        for pt_record in pt_records:
            research_id = pt_record["research_id"]
            base_dir = output_root / research_id
            ff1_count = 0
            efn_count = 0
            efg_count = 0

            if base_dir.exists() and base_dir.is_dir():
                for path in base_dir.rglob("*.txt"):
                    name = path.name
                    name_upper = name.upper()
                    if name_upper.startswith("FF1_"):
                        ff1_count += 1
                    elif name_upper.startswith("EFN_"):
                        efn_count += 1
                    elif name_upper.startswith("EFG_"):
                        efg_count += 1

            writer.writerow([research_id, ff1_count, efn_count, efg_count])


def main(
    root_dir: Path,
    target_sheet: str,
    dpc_file_encoding: Optional[str],
    delimiter: Optional[str],
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    margin_before_days: int = 90,
    margin_after_days: int = 90,
    *,
    logger: Logger = print,
    progress_callback: Optional[Logger] = None,
    progress_every: int = PROGRESS_EVERY,
    write_chunk_size: int = WRITE_CHUNK_SIZE,
    ) -> Dict[str, object]:
    """
    pt_list を読み、各患者に encounter±margin の月リストと _yymm_set を付与する。
    ファイルは名前の YYMM が全患者の月の和集合に含まれるものだけを対象とし、
    各ファイル内では患者ごとの _yymm_set で行をさらに絞る（process_one_file）。
    """
    started_at = datetime.now()
    pt_list = load_pt_list(Path(target_sheet), logger=logger)
    output_root.mkdir(parents=True, exist_ok=True)
    for pt_record in pt_list.values():
        yy_list = yymm_strings_for_period(
            pt_record,
            margin_before_days=margin_before_days,
            margin_after_days=margin_after_days,
        )
        pt_record["yymm_strings_for_period"] = yy_list
        pt_record["_yymm_set"] = set(yy_list)

    matched_files = collect_target_files(root_dir)

    # ファイル名 YYMM が「全患者の encounter±margin 月」の和集合に含まれるものだけを開く
    yymm_set = set(
        chain.from_iterable(
            pt_record["yymm_strings_for_period"] for pt_record in pt_list.values()
        )
    )
    # `_` で分割して 3番目の要素の先頭文字4つが yymm_set に含まれるものだけを開く
    # 典型例: EFn_123456789_1504.txt -> 1504
    # 末尾に不要な文字がついても対応させる: FF1_123456789_1504-1.txt -> 1504
    matched_files = [
        path for path in matched_files
        if len(path.stem.split("_")) >= 3 and path.stem.split("_")[2][:4] in yymm_set
    ]
    total_files = len(matched_files)

    if total_files == 0:
        logger("対象ファイルは見つかりませんでした。")
        return {
            "total_files": 0,
            "total_lines": 0,
            "total_extracted": 0,
            "total_output_files": 0,
            "total_malformed_rows": 0,
            "error_files": [],
            "summary_path": None,
            "elapsed": str(datetime.now() - started_at),
            "output_root": str(output_root),
        }

    logger(f"対象ファイル数: {total_files:,}")

    total_lines = 0
    total_extracted = 0
    total_output_files = 0
    total_malformed_rows = 0
    error_files = []

    for file_index, file_path in enumerate(matched_files, start=1):
        logger(f"\n開始 [{file_index}/{total_files}] {file_path}")

        try:
            result = process_one_file(
                file_path=file_path,
                file_index=file_index,
                total_files=total_files,
                pt_list=pt_list,
                output_root=output_root,
                dpc_file_encoding=dpc_file_encoding,
                delimiter=delimiter,
                progress_every=progress_every,
                write_chunk_size=write_chunk_size,
                logger=logger,
                progress_callback=progress_callback,
            )
        except Exception as e:
            logger(f"エラー: {file_path} -> {e}")
            error_files.append((file_path, str(e)))
            continue

        total_lines += result["line_count"]
        total_extracted += result["extracted_rows"]
        total_output_files += result["output_files"]
        total_malformed_rows += result["malformed_rows"]

        logger(
            "完了 "
            f"| 行数 {result['line_count']:,} "
            f"| 抽出 {result['extracted_rows']:,} "
            f"| 出力ファイル {result['output_files']:,} "
            f"| delimiter={result['delimiter']!r} "
            f"| encoding={result['encoding']!r}"
        )

    logger("\n===== 全体サマリ =====")
    logger(f"対象ファイル数      : {total_files:,}")
    logger(f"総処理行数          : {total_lines:,}")
    logger(f"総抽出行数          : {total_extracted:,}")
    logger(f"総出力ファイル数    : {total_output_files:,}")
    logger(f"不正行/短すぎる行数 : {total_malformed_rows:,}")
    logger(f"エラーファイル数    : {len(error_files):,}")

    if error_files:
        logger("\n===== エラー一覧 =====")
        for file_path, msg in error_files:
            logger(f"{file_path} -> {msg}")

    # サマリーCSV出力
    summary_path = output_root / "summary.csv"
    write_summary_csv(pt_list, output_root, summary_path)
    logger(f"\nサマリーCSVを出力しました: {summary_path}")

    elapsed = datetime.now() - started_at
    logger(f"合計処理時間        : {elapsed}")
    return {
        "total_files": total_files,
        "total_lines": total_lines,
        "total_extracted": total_extracted,
        "total_output_files": total_output_files,
        "total_malformed_rows": total_malformed_rows,
        "error_files": [
            {"file_path": str(file_path), "message": msg}
            for file_path, msg in error_files
        ],
        "summary_path": str(summary_path),
        "elapsed": str(elapsed),
        "output_root": str(output_root),
    }


def run_extraction_with_logs(
    root_dir: Union[str, Path],
    target_sheet: Union[str, Path] = DEFAULT_TARGET_SHEET,
    output_root: Union[str, Path] = DEFAULT_OUTPUT_ROOT,
    dpc_file_encoding: Optional[str] = DEFAULT_DPC_FILE_ENCODING,
    delimiter: Optional[str] = DEFAULT_DELIMITER,
    margin_days: int = DEFAULT_MARGIN_DAYS,
    progress_every: int = PROGRESS_EVERY,
    write_chunk_size: int = WRITE_CHUNK_SIZE,
    ) -> Dict[str, object]:
    logs: List[str] = []

    def collect_log(message: str) -> None:
        logs.append(str(message))

    result = main(
        root_dir=Path(root_dir),
        target_sheet=str(target_sheet),
        output_root=Path(output_root),
        dpc_file_encoding=dpc_file_encoding,
        delimiter=delimiter,
        margin_before_days=margin_days,
        margin_after_days=margin_days,
        logger=collect_log,
        progress_callback=collect_log,
        progress_every=progress_every,
        write_chunk_size=write_chunk_size,
    )
    return {
        "result": result,
        "logs": logs,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="DPCファイルを処理してpt_list.csvの患者データを抽出"
    )
    parser.add_argument(
        "--path-to-dir",
        type=str,
        default=DEFAULT_PATH_TO_DIR,
        help="入力元ディレクトリパス"
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(DEFAULT_OUTPUT_ROOT),
        help="出力先ルートディレクトリ"
    )
    parser.add_argument(
        "--target-sheet",
        type=str,
        default=DEFAULT_TARGET_SHEET,
        help="患者リストCSVへのパス"
    )
    parser.add_argument(
        "--dpc-file-encoding",
        type=str,
        default=DEFAULT_DPC_FILE_ENCODING,
        help="DPCファイルのエンコーディング"
    )
    parser.add_argument(
        "--delimiter",
        type=str,
        default=DEFAULT_DELIMITER,
        help="DPCファイルの区切り文字"
    )
    parser.add_argument(
        "--margin-days",
        type=int,
        default=DEFAULT_MARGIN_DAYS,
        help="許容する日付変動日数"
    )
    return parser


def cli() -> Dict[str, object]:
    parser = build_argument_parser()
    args, unknown = parser.parse_known_args()
    return main(
        root_dir=Path(args.path_to_dir),
        target_sheet=args.target_sheet,
        output_root=Path(args.output_root),
        dpc_file_encoding=args.dpc_file_encoding,
        delimiter=args.delimiter,
        margin_before_days=args.margin_days,
        margin_after_days=args.margin_days,
    )


if __name__ == "__main__":
    cli()

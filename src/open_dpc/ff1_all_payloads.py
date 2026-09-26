import csv
from datetime import datetime
from typing import Any, Callable

from open_dpc.variables import *

from open_dpc.schemas import legacy_schema as _legacy_schema
_legacy_ff1 = _legacy_schema()['ff1']
CSV_COLUMNS = _legacy_ff1['columns']
col_idx = {col: i for i, col in enumerate(CSV_COLUMNS)}


def is_header_row(row: list[str]) -> bool:
    """Return whether a row is the optional FF1 header row."""
    if len(row) < len(CSV_COLUMNS):
        return False
    return row[: len(CSV_COLUMNS)] == CSV_COLUMNS

# 既存 ff1.py と同様の前提
try:
    department_code_dict = {k[:2]: v for k, v in department_code_dict.items()}
except Exception:
    department_code_dict = {}


def payload(items: list[str], n: int) -> str:
    if n == 1:
        return items[col_idx['ﾍﾟｲﾛｰﾄﾞ1(日付等)']]
    if n == 2:
        return items[col_idx['ﾍﾟｲﾛｰﾄﾞ2(ｺｰﾄﾞ等)']]
    if 3 <= n <= 8:
        return items[col_idx[f'ﾍﾟｲﾛｰﾄﾞ{n}']]
    if n == 9:
        return items[col_idx['ﾍﾟｲﾛｰﾄﾞ9(可変長文字列)']]
    raise ValueError(f'payload number must be 1-9: {n}')


def format_date(date_str: str) -> str:
    if not date_str or len(date_str) != 8 or not date_str.isdigit():
        return date_str
    return f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}"


def maybe_date(date_str: str) -> str:
    return format_date(date_str) if date_str and len(date_str) == 8 and date_str.isdigit() else date_str


def maybe_int(value: str) -> int | str:
    return int(value) if isinstance(value, str) and value.isdigit() else value


def maybe_float(value: str) -> float | str:
    try:
        return float(value)
    except Exception:
        return value


def join_non_empty(values: list[str], sep: str = '|') -> str:
    return sep.join([v for v in values if v not in ('', None)])


def base_record(items: list[str]) -> dict[str, Any]:
    kaisu_number = items[col_idx['回数管理番号']]
    tokatu_number = items[col_idx['統括診療情報番号']]
    serial_number = items[col_idx['連番']]
    return {
        '施設コード': items[col_idx['施設ｺｰﾄﾞ']],
        'PID': items[col_idx['ﾃﾞｰﾀ識別番号']],
        '入院年月日': maybe_date(items[col_idx['入院年月日']]),
        '回数管理番号': maybe_int(kaisu_number),
        '統括診療情報番号': maybe_int(tokatu_number),
        'コード': items[col_idx['ｺｰﾄﾞ']],
        'バージョン': items[col_idx['ﾊﾞｰｼﾞｮﾝ']],
        '連番': maybe_int(serial_number),
    }


def add_raw_payloads(result: dict[str, Any], code: str, items: list[str]) -> dict[str, Any]:
    for n in range(1, 10):
        result[f'{code}_payload{n}_raw'] = payload(items, n)
    return result


def generic_payload_extractor(
    items: list[str],
    code: str,
    field_map: dict[int, str],
    date_payloads: set[int] | None = None,
    numeric_payloads: set[int] | None = None,
    float_payloads: set[int] | None = None,
    include_raw_payloads: bool = True,
) -> dict[str, Any]:
    date_payloads = date_payloads or set()
    numeric_payloads = numeric_payloads or set()
    float_payloads = float_payloads or set()

    result: dict[str, Any] = base_record(items)
    if include_raw_payloads:
        add_raw_payloads(result, code, items)

    for n, label in field_map.items():
        value = payload(items, n)
        if n in date_payloads:
            value = maybe_date(value)
        elif n in float_payloads:
            value = maybe_float(value)
        elif n in numeric_payloads:
            value = maybe_int(value)
        result[label] = value
    return result


def diagnosis_extractor(items: list[str], disease_label: str, include_additional_code: bool = False) -> dict[str, Any]:
    code = items[col_idx['ｺｰﾄﾞ']]
    modifier_list = [payload(items, i) for i in range(5, 9)]
    result = base_record(items)
    add_raw_payloads(result, code, items)
    result.update({
        disease_label: payload(items, 9),
        f'{disease_label}_ICD10コード': payload(items, 2),
        f'{disease_label}_傷病名コード': payload(items, 4),
        f'{disease_label}_修飾語コード': join_non_empty(modifier_list),
    })
    if include_additional_code:
        result[f'{disease_label}_病名付加コード'] = payload(items, 3)
    return result


def split_child_pugh(code_str: str) -> dict[str, str]:
    if len(code_str) != 5:
        return {}
    return {
        'ChildPugh_Bil': code_str[0],
        'ChildPugh_Alb': code_str[1],
        'ChildPugh_腹水': code_str[2],
        'ChildPugh_脳症': code_str[3],
        'ChildPugh_PT': code_str[4],
    }


def A000010(items: list[str], event_date: str | None = None) -> dict[str, Any]:
    birth_date_str = payload(items, 1)
    if event_date and len(event_date) == 8 and event_date.isdigit():
        reference_date_str = event_date
    else:
        reference_date_str = items[col_idx['入院年月日']]
    age = ''
    if len(birth_date_str) == 8 and birth_date_str.isdigit() and len(reference_date_str) == 8 and reference_date_str.isdigit():
        birth_date = datetime.strptime(birth_date_str, "%Y%m%d")
        ref_date = datetime.strptime(reference_date_str, "%Y%m%d")
        age = ref_date.year - birth_date.year
        if (ref_date.month, ref_date.day) < (birth_date.month, birth_date.day):
            age -= 1

    gender_code = payload(items, 2)
    if gender_code == '1':
        gender = '男'
    elif gender_code == '2':
        gender = '女'
    else:
        gender = gender_code

    result = base_record(items)
    add_raw_payloads(result, 'A000010', items)
    result.update({
        '生年月日': maybe_date(birth_date_str),
        '年齢': age,
        '性別': gender,
        '患者住所地域の郵便番号': payload(items, 3),
    })
    return result


def A000020(items: list[str]) -> dict[str, Any]:
    route_code = payload(items, 2)
    shokai_code = payload(items, 3)
    outside_code = payload(items, 4)
    emergency_code = payload(items, 5)
    ambulance_code = payload(items, 6)

    def emergency_code_300(emergency_code: str) -> str:
        code = emergency_code[-2:]
        return emergency_code_300_dict.get(code, '')

    emergency_status = ''
    if emergency_code == '100':
        emergency = '予定入院'
    elif emergency_code == '101':
        emergency = '予定再入院（悪性腫瘍患者に係る化学療法を実施）'
    elif emergency_code == '200':
        emergency = '救急医療入院以外の予定外入院'
    elif emergency_code == '':
        emergency = ''
    elif emergency_code.isdigit() and round(int(emergency_code), -2) == 300:
        emergency = '緊急入院'
        emergency_status = emergency_code_300(emergency_code)
    else:
        emergency = emergency_code

    result = base_record(items)
    add_raw_payloads(result, 'A000020', items)
    result.update({
        '入院情報_ペイロード1_入院年月日': maybe_date(payload(items, 1)),
        '入院経路コード': route_code,
        '入院経路': route_code_dict.get(route_code, route_code),
        '他院よりの紹介の有無コード': shokai_code,
        '他院よりの紹介の有無': bool_dict.get(shokai_code, shokai_code),
        '自院の外来からの入院コード': outside_code,
        '自院の外来からの入院': bool_dict.get(outside_code, outside_code),
        '予定・救急医療入院コード': emergency_code,
        '予定・緊急入院': emergency,
        '予定・緊急入院の状態': emergency_status,
        '救急車による搬送の有無コード': ambulance_code,
        '救急車による搬送の有無': bool_dict.get(ambulance_code, ambulance_code),
        '入院前の在宅医療の有無': payload(items, 7),
        '自傷行為・自殺企図の有無': payload(items, 8),
        '過去の自傷行為・自殺企図の有無': payload(items, 9),
    })
    return result


def A000030(items: list[str]) -> dict[str, Any]:
    discharge_date_string = payload(items, 1)
    hospitalization = ''
    if len(discharge_date_string) == 8 and discharge_date_string.isdigit() and discharge_date_string != '00000000':
        discharge_date = datetime.strptime(discharge_date_string, "%Y%m%d")
        admission_date = datetime.strptime(items[col_idx['入院年月日']], "%Y%m%d")
        hospitalization = (discharge_date - admission_date).days

    discharge_place_code = payload(items, 2)
    outcome_code = payload(items, 3)
    hour24_code = payload(items, 4)

    result = base_record(items)
    add_raw_payloads(result, 'A000030', items)
    result.update({
        '退院日': maybe_date(discharge_date_string),
        '退院先コード': discharge_place_code,
        '退院先': discharge_place_code_dict.get(discharge_place_code, discharge_place_code),
        '入院期間': hospitalization,
        '退院時転帰コード': outcome_code,
        '退院時転帰': outcome_code_dict.get(outcome_code, outcome_code),
        '24時間以内の死亡の有無コード': hour24_code,
        '24時間以内の死亡の有無': hour24_code_dict.get(hour24_code, hour24_code),
        '退院後の在宅医療の有無': payload(items, 5),
    })
    return result


def A000031(items: list[str]) -> dict[str, Any]:
    return generic_payload_extractor(
        items,
        code='A000031',
        field_map={1: '様式1開始日', 2: '様式1終了日'},
        date_payloads={1, 2},
    )


def A000040(items: list[str]) -> dict[str, Any]:
    dept_code = payload(items, 2)
    result = generic_payload_extractor(
        items,
        code='A000040',
        field_map={2: '診療科コード', 3: '転科の有無'},
    )
    result['診療科'] = department_code_dict.get(dept_code[:2], dept_code)
    return result


def A001010(items: list[str]) -> dict[str, Any]:
    return generic_payload_extractor(
        items,
        code='A001010',
        field_map={2: '身長', 3: '入院時体重', 4: '退院時体重'},
        float_payloads={2, 3, 4},
    )


def A006010(items: list[str]) -> dict[str, Any]:
    return diagnosis_extractor(items, '主傷病')


def A006020(items: list[str]) -> dict[str, Any]:
    return diagnosis_extractor(items, '入院契機')


def A006030(items: list[str]) -> dict[str, Any]:
    return diagnosis_extractor(items, '医療資源', include_additional_code=True)


def A006031(items: list[str]) -> dict[str, Any]:
    return diagnosis_extractor(items, '医療資源2')


def A006040(items: list[str]) -> dict[str, Any]:
    return diagnosis_extractor(items, '併存症')


def A006050(items: list[str]) -> dict[str, Any]:
    return diagnosis_extractor(items, '続発症')


def A006060(items: list[str]) -> dict[str, Any]:
    result = base_record(items)
    add_raw_payloads(result, 'A006060', items)
    result.update({
        '指定難病の告示番号1': payload(items, 2),
        '医療費助成の有無1_コード': payload(items, 3),
        '医療費助成の有無1': bool_dict.get(payload(items, 3), payload(items, 3)),
        '指定難病の告示番号2': payload(items, 4),
        '医療費助成の有無2_コード': payload(items, 5),
        '医療費助成の有無2': bool_dict.get(payload(items, 5), payload(items, 5)),
    })
    return result


def M120010(items: list[str]) -> dict[str, Any]:
    target = payload(items, 2)
    dist = {
        '1': '入院前1週間以内に分娩あり',
        '2': '入院中の分娩あり',
        '3': 'その他',
    }
    result = base_record(items)
    add_raw_payloads(result, 'M120010', items)
    result.update({
        '入院周辺の分娩の有無_コード': target,
        '入院周辺の分娩の有無': dist.get(target, target),
        '分娩時出血量': maybe_int(payload(items, 3)),
    })
    return result


def M060010(items: list[str]) -> dict[str, Any]:
    result = generic_payload_extractor(
        items,
        code='M060010',
        field_map={2: 'ChildPugh_5桁コード'},
    )
    result.update(split_child_pugh(payload(items, 2)))
    return result


PAYLOAD_REGISTRY = {code: {key: ({int(k): v for k, v in value.items()} if key == 'field_map' else set(value)) for key, value in spec.items()} for code, spec in _legacy_ff1['payload_registry'].items()}


SPECIAL_EXTRACTORS: dict[str, Callable[[list[str]], dict[str, Any]]] = {
    'A000010': A000010,
    'A000020': A000020,
    'A000030': A000030,
    'A000031': A000031,
    'A000040': A000040,
    'A001010': A001010,
    'A006010': A006010,
    'A006020': A006020,
    'A006030': A006030,
    'A006031': A006031,
    'A006040': A006040,
    'A006050': A006050,
    'A006060': A006060,
    'M060010': M060010,
    'M120010': M120010,
}


ALL_REGISTERED_CODES = set(SPECIAL_EXTRACTORS) | set(PAYLOAD_REGISTRY)


EXPECTED_70_CODES = {
    'A000010', 'A000020', 'A000030', 'A000031', 'A000040', 'A000050', 'A000060', 'A000070', 'A000080', 'A000090',
    'A001010', 'A001020', 'A001030', 'A001040', 'A002010', 'A003010', 'A004010', 'A004020', 'A004030', 'A004040', 'A004050',
    'A006010', 'A006020', 'A006030', 'A006031', 'A006040', 'A006050', 'A006060',
    'A007010',
    'ADL0010', 'ADL0020', 'ADL0030', 'ADL0040', 'FIM0010', 'FIM0020', 'JCS0010', 'JCS0020',
    'CAN0010', 'CAN0020', 'CAN0030', 'CAN0040',
    'M010010', 'M010020', 'M010030',
    'M040010', 'M040020', 'M040031',
    'M050011', 'M050020', 'M050030', 'M050041', 'M050051', 'M050070', 'M050080', 'M050090',
    'M060010', 'M060020',
    'M120010', 'M150010', 'M160010',
    'M170010', 'M170020', 'M170030', 'M170040', 'M170050', 'M170060',
    'M180010', 'M180011', 'M180020', 'M180021',
}

assert ALL_REGISTERED_CODES == EXPECTED_70_CODES, f'missing={EXPECTED_70_CODES - ALL_REGISTERED_CODES}, extra={ALL_REGISTERED_CODES - EXPECTED_70_CODES}'


def extract_one_record(
    items: list[str],
    include_raw_payloads: bool = True,
    event_date: str | None = None,
) -> dict[str, Any]:
    ff1_code = items[col_idx['ｺｰﾄﾞ']]
    if ff1_code in SPECIAL_EXTRACTORS:
        if ff1_code == 'A000010':
            result = A000010(items, event_date=event_date)
        else:
            result = SPECIAL_EXTRACTORS[ff1_code](items)
        if not include_raw_payloads:
            result = {k: v for k, v in result.items() if not k.endswith('_raw')}
        return result

    if ff1_code not in PAYLOAD_REGISTRY:
        raise KeyError(f'{ff1_code} is not registered')

    spec = PAYLOAD_REGISTRY[ff1_code]
    return generic_payload_extractor(
        items=items,
        code=ff1_code,
        field_map=spec['field_map'],
        date_payloads=spec.get('date_payloads', set()),
        numeric_payloads=spec.get('numeric_payloads', set()),
        float_payloads=spec.get('float_payloads', set()),
        include_raw_payloads=include_raw_payloads,
    )


def extract_info_from_dpc_ff1(
    read_file: str,
    encoding: str = 'cp932',
    delimiter: str = '\t',
    include_raw_payloads: bool = True,
    include_unregistered: bool = False,
    event_date: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    既存 ff1.py の result.update(...) では、同一コードの複数レコードや連番付きレコードが上書きされる。
    本関数では {コード: [レコード, ...]} の形で保持し、登録済みペイロード種目を漏れなく回収する。
    """
    result: dict[str, list[dict[str, Any]]] = {}

    with open(read_file, 'r', encoding=encoding) as csvfile:
        reader = csv.reader(csvfile, delimiter=delimiter)
        for row in reader:
            if is_header_row(row):
                continue
            ff1_code = row[col_idx['ｺｰﾄﾞ']]
            if ff1_code in ALL_REGISTERED_CODES:
                extracted = extract_one_record(
                    row,
                    include_raw_payloads=include_raw_payloads,
                    event_date=event_date,
                )
                result.setdefault(ff1_code, []).append(extracted)
            elif include_unregistered:
                unregistered = base_record(row)
                if include_raw_payloads:
                    add_raw_payloads(unregistered, ff1_code, row)
                result.setdefault(ff1_code, []).append(unregistered)

    return result


def extract_info_from_dpc_ff1_flat(
    read_file: str,
    encoding: str = 'cp932',
    include_raw_payloads: bool = True,
    event_date: str | None = None,
) -> dict[str, Any]:
    """
    互換用。連番や複数行がないコードだけを前提に平坦化したい場合に使う。
    複数レコードがあるコードは `{コード}` キーの list のまま残す。
    """
    nested = extract_info_from_dpc_ff1(
        read_file=read_file,
        encoding=encoding,
        include_raw_payloads=include_raw_payloads,
        include_unregistered=False,
        event_date=event_date,
    )
    flat: dict[str, Any] = {}
    for code, records in nested.items():
        if len(records) == 1 and records[0].get('連番', '') in ('', 1, '1'):
            flat.update(records[0])
        else:
            flat[code] = records
    return flat

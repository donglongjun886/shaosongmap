#!/usr/bin/env python3
"""CHGIS v6 数据下载与预处理脚本。

从 Harvard Dataverse 下载 CHGIS v6 原始数据集，筛选宋代（960-1279）
府/州/军/监/县级行政地名，输出与 geocoder 兼容的精简 CSV。

用法：
    python scripts/build_chgis.py              # 从 Dataverse 下载并处理
    python scripts/build_chgis.py <本地文件>    # 从本地 TSV/CSV 文件处理
"""

from __future__ import annotations

import csv
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import requests
import shapefile

# Harvard Dataverse 上的 CHGIS v6 数据集
DATAVERSE_DOI = 'doi:10.7910/DVN/WW1PD6'
DATASET_API = (
    f'https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId={DATAVERSE_DOI}'
)

# 输出路径（项目根目录下的 data/chgis_v6/）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'data' / 'chgis_v6'
OUTPUT_FILE = OUTPUT_DIR / 'chgis_v6_points.csv'

# 宋代时间范围
SONG_BEG = 960
SONG_END = 1279

# 目标行政层级（中文值）
TARGET_LEVELS = frozenset({'府', '州', '军', '监', '县'})

# 输出 CSV 列（与 geocoder.py 兼容）
OUTPUT_COLUMNS = ['name_ch', 'x_coord', 'y_coord', 'beg_yr', 'end_yr', 'lev', 'modern_name']

# 已知的 CHGIS 层级中文映射（lev_zh 列的常见值 -> 我们使用的标准化值）
LEV_MAPPING = {
    '府': '府',
    '州': '州',
    '军': '军',
    '监': '监',
    '县': '县',
    '散州': '州',
    '直隶州': '州',
    '直隶厅': '州',
    '厅': '监',
    '散厅': '监',
    '直隶县': '县',
}


def _find_column(headers: list[str], *candidates: str) -> str | None:
    """在表头中查找第一个匹配的列名（大小写不敏感）。"""
    for h in headers:
        h_lower = h.strip().lower()
        for c in candidates:
            if h_lower == c.lower():
                return h
    return None


def _normalize_lev(raw: str) -> str:
    """将 CHGIS 原始层级值标准化为府/州/军/监/县。"""
    cleaned = raw.strip()
    if cleaned in TARGET_LEVELS:
        return cleaned
    return LEV_MAPPING.get(cleaned, '')


def fetch_from_dataverse() -> tuple[str, list[str], list[dict]]:
    """从 Harvard Dataverse API 下载 CHGIS v6 数据并解析为行列表。

    Returns:
        (source_label, headers, rows): 来源描述、原始列名、数据行列表
    """
    # 先尝试通过 API 查询文件列表
    file_id = None
    filename = 'unknown'
    try:
        print(f'[1/4] 查询数据集元数据: {DATASET_API}')
        resp = requests.get(DATASET_API, timeout=60)
        resp.raise_for_status()
        dataset = resp.json()

        files = dataset.get('data', {}).get('latestVersion', {}).get('files', [])
        if files:
            print(f'  找到 {len(files)} 个文件')

            # 优先查找 UTF-8 WGS84 版本
            for f in files:
                df = f.get('dataFile', {})
                fn = df.get('filename', '')
                if 'utf_wgs84' in fn.lower() and fn.endswith('.zip'):
                    file_id = df['id']
                    filename = fn
                    break

            if not file_id:
                for f in files:
                    df = f.get('dataFile', {})
                    fn = df.get('filename', '')
                    if 'pref_pts' in fn.lower() and fn.endswith('.zip'):
                        file_id = df['id']
                        filename = fn
                        break
    except Exception as e:
        print(f'  API 查询失败: {e}，使用已知文件 ID 回退')

    # 回退：使用已知的 CHGIS v6 UTF-8 WGS84 文件 ID
    if not file_id:
        file_id = 2970286
        filename = 'v6_time_pref_pts_utf_wgs84.zip'
        print(f'  使用已知文件: {filename} (id={file_id})')

    print(f'[2/4] 下载数据文件: {filename} (id={file_id})')
    download_url = f'https://dataverse.harvard.edu/api/access/datafile/{file_id}'
    resp = requests.get(download_url, timeout=120)
    resp.raise_for_status()

    # 处理可能的压缩包
    if filename.endswith('.zip'):
        return _parse_zip(resp.content, filename)

    # 直接解析文本文件
    delimiter = _detect_delimiter(resp.text)
    reader = csv.reader(resp.text.splitlines(), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        raise RuntimeError('下载的文件为空')
    headers = [h.strip() for h in rows[0]]
    data_rows = [dict(zip(headers, row, strict=False)) for row in rows[1:]]
    return filename, headers, data_rows


def _detect_delimiter(text: str) -> str:
    """检测分隔符：优先 Tab，其次逗号。"""
    first_line = text.split('\n')[0]
    if first_line.count('\t') > first_line.count(','):
        return '\t'
    return ','


def _parse_zip(content: bytes, zip_name: str) -> tuple[str, list[str], list[dict]]:
    """从 zip 包中提取 Shapefile 或 TSV/CSV 并解析。"""
    print(f'  解压 zip 文件 ({len(content)} bytes)...')
    with ZipFile(BytesIO(content)) as zf:
        namelist = zf.namelist()

        # 检查是否为 Shapefile 格式
        shp_files = [n for n in namelist if n.lower().endswith('.shp')]
        if shp_files:
            return _parse_shapefile_from_zip(zf, shp_files[0], zip_name)

        # 回退：查找 TSV/CSV 文件
        candidates = [name for name in namelist if name.lower().endswith(('.tsv', '.csv', '.tab'))]
        if not candidates:
            raise RuntimeError(f'Zip 文件中未找到 Shapefile 或 TSV/CSV 文件。内容: {namelist}')

        target = candidates[0]
        for c in candidates:
            if 'pref_pts' in c.lower():
                target = c
                break

        print(f'  从 zip 中提取: {target}')
        raw_text = zf.read(target).decode('utf-8', errors='replace')

    delimiter = _detect_delimiter(raw_text)
    reader = csv.reader(raw_text.splitlines(), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        raise RuntimeError('解压后的文件为空')
    headers = [h.strip() for h in rows[0]]
    data_rows = [dict(zip(headers, row, strict=False)) for row in rows[1:]]
    return f'{zip_name}/{target}', headers, data_rows


def _parse_shapefile_from_zip(
    zf: ZipFile, shp_name: str, zip_name: str
) -> tuple[str, list[str], list[dict]]:
    """从 zip 中读取 Shapefile 并提取属性表。"""
    base = shp_name.rsplit('.', 1)[0]

    # 读取必需的 .shp / .shx / .dbf 文件
    shp_data = zf.read(shp_name)
    shx_name = base + '.shx'
    dbf_name = base + '.dbf'

    if shx_name not in zf.namelist() or dbf_name not in zf.namelist():
        raise RuntimeError(
            f'Shapefile 不完整，需要 .shp/.shx/.dbf 三个文件。'
            f'找到: {shp_name}, 缺少: {shx_name} 或 {dbf_name}'
        )

    shx_data = zf.read(shx_name)
    dbf_data = zf.read(dbf_name)

    print(f'  从 zip 中解析 Shapefile: {base}')

    reader = shapefile.Reader(
        shp=BytesIO(shp_data),
        shx=BytesIO(shx_data),
        dbf=BytesIO(dbf_data),
    )
    fields = [f[0] for f in reader.fields[1:]]  # 跳过 DeletionFlag
    headers = [f.strip() for f in fields]

    data_rows = []
    for record in reader.records():
        row = {}
        for i, value in enumerate(record):
            col_name = headers[i] if i < len(headers) else f'col_{i}'
            if isinstance(value, bytes):
                value = value.decode('utf-8', errors='replace')
            elif value is None:
                value = ''
            row[col_name] = str(value)
        data_rows.append(row)

    return f'{zip_name}/{base}', headers, data_rows


def load_local(filepath: str) -> tuple[str, list[str], list[dict]]:
    """从本地文件加载 TSV/CSV 数据。"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f'本地文件不存在: {filepath}')

    print(f'[1/4] 读取本地文件: {path}')
    raw_text = path.read_text(encoding='utf-8', errors='replace')
    delimiter = _detect_delimiter(raw_text)
    reader = csv.reader(raw_text.splitlines(), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        raise RuntimeError('本地文件为空')
    headers = [h.strip() for h in rows[0]]
    data_rows = [dict(zip(headers, row, strict=False)) for row in rows[1:]]
    return path.name, headers, data_rows


def filter_song_dynasty(rows: list[dict], headers: list[str]) -> list[dict]:
    """按宋代时间范围和行政层级筛选数据。"""
    print(f'[3/4] 筛选数据（原始 {len(rows)} 条记录）...')

    # 识别关键列
    name_col = _find_column(headers, 'name_ch', 'name_chinese', 'name_zh')
    x_col = _find_column(headers, 'x_coord', 'x_coor', 'x', 'longitude', 'lon', 'lng')
    y_col = _find_column(headers, 'y_coord', 'y_coor', 'y', 'latitude', 'lat')
    beg_col = _find_column(headers, 'beg_yr', 'beg_year', 'begin_year', 'start_yr', 'start_year')
    end_col = _find_column(headers, 'end_yr', 'end_year', 'finish_year', 'stop_yr', 'stop_year')
    lev_col = _find_column(headers, 'type_ch', 'lev_zh', 'lev', 'level_zh', 'admin_level')

    if not name_col:
        raise RuntimeError(f'无法识别地名列，可用列: {headers}')
    if not x_col or not y_col:
        raise RuntimeError(f'无法识别坐标列，可用列: {headers}')
    if not beg_col or not end_col:
        raise RuntimeError(f'无法识别时间列，可用列: {headers}')

    print(
        f'  列映射: name={name_col}, x={x_col}, y={y_col}, beg={beg_col}, end={end_col}, lev={lev_col or "(无)"}'
    )

    stats = {
        'total': len(rows),
        'no_time': 0,
        'time_mismatch': 0,
        'no_coord': 0,
        'wrong_level': 0,
        'kept': 0,
    }
    result = []

    for row in rows:
        # 解析时间
        try:
            beg_yr = int(float(row.get(beg_col, '') or '0'))
            end_yr = int(float(row.get(end_col, '') or '0'))
        except (ValueError, TypeError):
            stats['no_time'] += 1
            continue

        if beg_yr == 0 and end_yr == 0:
            stats['no_time'] += 1
            continue

        # 时间筛选：地名存在期与宋代有交集
        if not (beg_yr <= SONG_END and end_yr >= SONG_BEG):
            stats['time_mismatch'] += 1
            continue

        # 坐标完整性
        x_str = (row.get(x_col, '') or '').strip()
        y_str = (row.get(y_col, '') or '').strip()
        if not x_str or not y_str:
            stats['no_coord'] += 1
            continue

        try:
            x_coord = float(x_str)
            y_coord = float(y_str)
        except ValueError:
            stats['no_coord'] += 1
            continue

        # 行政层级筛选
        if lev_col:
            raw_lev = (row.get(lev_col, '') or '').strip()
            norm_lev = _normalize_lev(raw_lev)
            if not norm_lev:
                stats['wrong_level'] += 1
                continue
        else:
            norm_lev = ''

        name = (row.get(name_col, '') or '').strip()
        if not name:
            continue

        # 尝试从 PRES_LOC 提取现代地名信息
        pres_loc = ''
        for col_name in ('PRES_LOC', 'pres_loc', 'MODERN_NAM', 'modern_name'):
            val = (row.get(col_name, '') or '').strip()
            if val:
                pres_loc = val
                break

        result.append(
            {
                'name_ch': name,
                'x_coord': x_coord,
                'y_coord': y_coord,
                'beg_yr': beg_yr,
                'end_yr': end_yr,
                'lev': norm_lev,
                'modern_name': pres_loc,
            }
        )
        stats['kept'] += 1

    print(
        f'  统计: 总计 {stats["total"]}, 无时间 {stats["no_time"]}, '
        f'时间不符 {stats["time_mismatch"]}, 无坐标 {stats["no_coord"]}, '
        f'层级不符 {stats["wrong_level"]}, 保留 {stats["kept"]}'
    )
    return result


def merge_modern_names(records: list[dict]) -> list[dict]:
    """尝试从旧 CSV 中合并 modern_name 字段（按 name_ch 匹配）。"""
    old_csv = OUTPUT_FILE
    if not old_csv.exists():
        return records

    old_map: dict[str, str] = {}
    with open(old_csv, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('name_ch', '').strip()
            modern = row.get('modern_name', '').strip()
            if name and modern:
                old_map[name] = modern

    if not old_map:
        return records

    merged = 0
    for rec in records:
        if not rec['modern_name'] and rec['name_ch'] in old_map:
            rec['modern_name'] = old_map[rec['name_ch']]
            merged += 1

    if merged:
        print(f'  从旧数据合并了 {merged} 条 modern_name')
    return records


def add_known_modern_names(records: list[dict]) -> list[dict]:
    """补充已知的宋代地名 -> 现代地名映射。"""
    # 常见宋代地名现代对照表
    known_map = {
        '汴京': '河南开封',
        '东京': '河南开封',
        '临安': '浙江杭州',
        '行在': '浙江杭州',
        '西京': '河南洛阳',
        '南京': '河南商丘',
        '北京': '河北大名',
        '兴庆府': '宁夏银川',
        '中兴府': '宁夏银川',
        '灵州': '宁夏灵武',
        '夏州': '陕西靖边',
        '银州': '陕西横山',
        '绥州': '陕西绥德',
        '宥州': '内蒙古鄂托克前旗',
        '黄龙府': '吉林农安',
        '幽州': '北京',
        '燕京': '北京',
        '大名府': '河北大名',
        '太原府': '山西太原',
        '大同府': '山西大同',
        '凤翔府': '陕西凤翔',
        '京兆府': '陕西西安',
        '长安': '陕西西安',
        '江宁府': '江苏南京',
        '建康府': '江苏南京',
        '平江府': '江苏苏州',
        '绍兴府': '浙江绍兴',
        '庆元府': '浙江宁波',
        '成都府': '四川成都',
        '潼川府': '四川三台',
        '兴元府': '陕西汉中',
        '广州': '广东广州',
        '泉州': '福建泉州',
        '福州': '福建福州',
        '潭州': '湖南长沙',
        '鄂州': '湖北武汉',
        '江陵府': '湖北荆州',
        '襄阳府': '湖北襄阳',
        '邓州': '河南邓州',
        '唐州': '河南唐河',
        '蔡州': '河南汝南',
        '颍昌府': '河南许昌',
        '应天府': '河南商丘',
        '徐州': '江苏徐州',
        '楚州': '江苏淮安',
        '扬州': '江苏扬州',
        '庐州': '安徽合肥',
        '洪州': '江西南昌',
        '吉州': '江西吉安',
        '虔州': '江西赣州',
        '真定府': '河北正定',
        '河间府': '河北河间',
        '中山府': '河北定州',
        '延安府': '陕西延安',
        '渭州': '甘肃平凉',
        '秦州': '甘肃天水',
        '熙州': '甘肃临洮',
        '河州': '甘肃临夏',
        '洮州': '甘肃临潭',
        '兰州': '甘肃兰州',
        '西宁州': '青海西宁',
        '成都': '四川成都',
        '渝州': '重庆',
        '恭州': '重庆',
        '夔州': '重庆奉节',
        '金州': '陕西安康',
        '洋州': '陕西洋县',
        '衡州': '湖南衡阳',
        '永州': '湖南永州',
        '郴州': '湖南郴州',
        '桂州': '广西桂林',
        '静江府': '广西桂林',
        '邕州': '广西南宁',
        '琼州': '海南海口',
        '雷州': '广东雷州',
        '潮州': '广东潮州',
        '循州': '广东龙川',
        '端州': '广东肇庆',
        '封州': '广东封开',
        '连州': '广东连州',
        '贺州': '广西贺州',
        '昭州': '广西平乐',
        '梧州': '广西梧州',
    }

    updated = 0
    for rec in records:
        if not rec['modern_name'] and rec['name_ch'] in known_map:
            rec['modern_name'] = known_map[rec['name_ch']]
            updated += 1

    if updated:
        print(f'  补充了 {updated} 条已知现代地名映射')
    return records


def add_historical_aliases(records: list[dict]) -> list[dict]:
    """为常见历史别名补充额外记录（与主记录坐标相同但名称不同）。

    CHGIS 使用正式行政名称（如「开封府」），但历史文本常用别名（如「汴京」）。
    通过补充别名记录，确保 fuzzy match 能命中。
    """
    # 从已有记录中查找目标坐标
    coord_lookup: dict[str, tuple[float, float]] = {}
    for rec in records:
        key = rec['name_ch']
        if key not in coord_lookup:
            coord_lookup[key] = (rec['x_coord'], rec['y_coord'])

    # 别名 -> 正式名称映射（需要正式名称已在 records 中存在）
    aliases = {
        # 五京别名
        '汴京': '开封府',
        '东京': '开封府',
        '大梁': '开封府',
        '汴梁': '开封府',
        '临安': '临安府',
        '行在': '临安府',
        '杭州': '临安府',
        '西京': '河南府',
        '洛阳': '河南府',
        '南京': '应天府',
        '商丘': '应天府',
        '北京': '大名府',
        '大名': '大名府',
        '燕京': '幽州',
        '燕山府': '幽州',
        # 更多常见别名
        '扬州府': '扬州',
        '苏州': '平江府',
        '平江': '平江府',
        '绥州': '绥德军',
    }

    added = 0
    existing_names = {rec['name_ch'] for rec in records}
    for alias, formal in aliases.items():
        if alias in existing_names:
            continue
        if formal not in coord_lookup:
            continue
        x, y = coord_lookup[formal]
        # 找到 formal 的记录以复制其他字段
        for rec in records:
            if rec['name_ch'] == formal:
                records.append(
                    {
                        'name_ch': alias,
                        'x_coord': x,
                        'y_coord': y,
                        'beg_yr': rec['beg_yr'],
                        'end_yr': rec['end_yr'],
                        'lev': rec['lev'],
                        'modern_name': rec['modern_name'],
                    }
                )
                added += 1
                break

    # 补充 CHGIS 中完全缺失的关键地名（手动标记坐标）
    manual_entries = [
        # 西夏/宋夏边境地名（CHGIS 宋数据中常缺失）
        ('兴庆府', 106.2785, 38.4874, 1020, 1227, '府', '今宁夏银川市'),
        ('银州', 109.8141, 37.8238, 560, 1100, '州', '今陕西横山县党岔镇'),
        ('宥州', 107.5362, 38.1943, 738, 1100, '州', '今内蒙古鄂托克前旗城川镇'),
        # 金/辽地名（宋数据中缺失）
        ('黄龙府', 125.1689, 44.5333, 926, 1234, '府', '今吉林农安县'),
        # 宋代存在的州但在 CHGIS 中缺失
        ('唐州', 112.832, 32.690, 960, 1279, '州', '今河南唐河县'),
    ]
    for name, x, y, beg, end, lev, modern in manual_entries:
        if name in existing_names:
            continue
        records.append(
            {
                'name_ch': name,
                'x_coord': x,
                'y_coord': y,
                'beg_yr': beg,
                'end_yr': end,
                'lev': lev,
                'modern_name': modern,
            }
        )
        added += 1

    if added:
        print(f'  补充了 {added} 条历史别名/手动记录')
    return records


def write_output(records: list[dict]) -> int:
    """写入精简 CSV 到 data/chgis_v6/ 目录。"""
    print(f'[4/4] 写入输出文件: {OUTPUT_FILE}')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 去重：按 name_ch + beg_yr + end_yr 唯一
    seen = set()
    unique = []
    for rec in records:
        key = (rec['name_ch'], rec['beg_yr'], rec['end_yr'])
        if key not in seen:
            seen.add(key)
            unique.append(rec)

    if len(unique) < len(records):
        print(f'  去重: {len(records)} -> {len(unique)} 条')

    # 按 name_ch 字母序输出
    unique.sort(key=lambda r: r['name_ch'])

    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(unique)

    return len(unique)


def main():
    """主入口：下载或读取 -> 筛选 -> 补充现代名 -> 输出版本。"""
    source_path = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        if source_path:
            source_label, headers, rows = load_local(source_path)
        else:
            source_label, headers, rows = fetch_from_dataverse()
    except Exception as e:
        print(f'错误: {e}', file=sys.stderr)
        print(
            '提示: 也可以手动下载 CHGIS v6 数据后运行: python scripts/build_chgis.py <文件路径>',
            file=sys.stderr,
        )
        sys.exit(1)

    print(f'  数据来源: {source_label}, {len(rows)} 行, {len(headers)} 列')

    # 筛选
    filtered = filter_song_dynasty(rows, headers)
    if len(filtered) < 200:
        print(
            f'  ⚠ 警告: 仅筛选出 {len(filtered)} 条记录，可能筛选条件过严或数据列映射有误',
            file=sys.stderr,
        )

    # 补充现代地名和历史别名
    filtered = merge_modern_names(filtered)
    filtered = add_known_modern_names(filtered)
    filtered = add_historical_aliases(filtered)

    # 输出
    count = write_output(filtered)

    modern_pct = sum(1 for r in filtered if r['modern_name']) / max(count, 1) * 100
    print(f'\n✓ 完成! 输出 {count} 条宋代地名记录到 {OUTPUT_FILE}')
    print(f'  modern_name 覆盖率: {modern_pct:.0f}%')

    # 打印各级别分布
    lev_dist = {}
    for r in filtered:
        lv = r['lev'] or '未知'
        lev_dist[lv] = lev_dist.get(lv, 0) + 1
    for lv, cnt in sorted(lev_dist.items()):
        print(f'  {lv}: {cnt} 条')


if __name__ == '__main__':
    main()

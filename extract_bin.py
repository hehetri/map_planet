#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

XOR_KEY = 0xFF


def xor_bytes(data: bytes, key: int = XOR_KEY) -> bytes:
    return bytes(b ^ key for b in data)


def line_break_bytes(encoding: str) -> bytes:
    normalized = encoding.lower().replace("_", "-")
    if "utf-16le" in normalized:
        return b"\r\x00\n\x00"
    if "utf-16be" in normalized:
        return b"\x00\r\x00\n"
    return b"\r\n"


def detect_encoding(payload: bytes) -> str:
    if not payload:
        return "cp949"
    null_count = payload.count(0)
    if null_count == 0:
        return "cp949"
    even_nulls = payload[::2].count(0)
    odd_nulls = payload[1::2].count(0)
    if null_count > len(payload) // 4 and odd_nulls >= even_nulls:
        return "utf-16le"
    return "cp949"


def parse_payload(payload: bytes, encoding: str) -> dict:
    tail_bytes = b""
    line_break = line_break_bytes(encoding)
    last_break = payload.rfind(line_break)
    if last_break != -1 and last_break + len(line_break) < len(payload):
        tail_bytes = payload[last_break + len(line_break) :]
        payload = payload[: last_break + len(line_break)]

    text = payload.decode(encoding, errors="replace")
    lines = text.splitlines()

    data_start = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith(";"):
            data_start = idx
            break

    if data_start is None:
        data_start = len(lines)

    header_lines = lines[:data_start]

    columns = []
    indent_tab = False
    for line in reversed(header_lines):
        stripped = line.lstrip()
        if stripped.startswith(";") and "\t" in stripped:
            content = stripped[1:]
            if content.startswith("\t"):
                indent_tab = True
                content = content[1:]
            columns = [col.strip() for col in content.split("\t")]
            break

    rows = []
    line_items = []
    for line in lines[data_start:]:
        if not line.strip():
            line_items.append({"type": "blank", "value": line})
            continue
        if line.lstrip().startswith(";"):
            line_items.append({"type": "comment", "value": line})
            continue
        if indent_tab and line.startswith("\t"):
            line = line[1:]
        values = line.split("\t")
        line_items.append({"type": "data", "values": values})
        if columns:
            row = {col: values[idx] if idx < len(values) else "" for idx, col in enumerate(columns)}
            if len(values) > len(columns):
                row["_extra"] = values[len(columns):]
            rows.append(row)
        else:
            rows.append(values)

    return {
        "encoding": encoding,
        "header_lines": header_lines,
        "columns": columns,
        "indent_tab": indent_tab,
        "line_items": line_items,
        "rows": rows,
        "tail_bytes_hex": tail_bytes.hex(),
        "line_break_hex": line_break.hex(),
    }


def extract_file(path: Path, output_dir: Path, encoding: str) -> None:
    data = path.read_bytes()
    if len(data) < 8:
        raise ValueError(f"Arquivo muito curto: {path}")

    version = int.from_bytes(data[:4], "little")
    payload_len = int.from_bytes(data[4:8], "little")
    payload = data[8:]
    padding_bytes = b""

    if payload_len and payload_len <= len(payload):
        padding_bytes = payload[payload_len:]
        payload = payload[:payload_len]

    decoded = xor_bytes(payload)
    if encoding == "auto":
        encoding = detect_encoding(decoded)
    payload_data = parse_payload(decoded, encoding)
    payload_data.update({
        "version": version,
        "payload_length": payload_len,
        "file_padding_hex": padding_bytes.hex(),
    })

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{path.stem}.json"
    output_path.write_text(
        json.dumps(payload_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrai JSON de arquivos .bin com XOR 0xFF.")
    parser.add_argument("--input-dir", default="input", help="Diretório com os .bin")
    parser.add_argument("--output-dir", default="output", help="Diretório para salvar os JSONs")
    parser.add_argument("--encoding", default="auto", help="Encoding do payload (auto, cp949, utf-16le)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    bin_files = sorted(input_dir.glob("*.bin"))
    if not bin_files:
        raise SystemExit(f"Nenhum .bin encontrado em {input_dir}")

    for path in bin_files:
        extract_file(path, output_dir, args.encoding)


if __name__ == "__main__":
    main()

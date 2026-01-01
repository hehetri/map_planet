#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

XOR_KEY = 0xFF


def xor_bytes(data: bytes, key: int = XOR_KEY) -> bytes:
    return bytes(b ^ key for b in data)


def build_payload(data: dict) -> bytes:
    encoding = data.get("encoding", "cp949")
    header_lines = data.get("header_lines") or []
    columns = data.get("columns") or []
    indent_tab = data.get("indent_tab", False)
    line_items = data.get("line_items") or []
    rows = data.get("rows") or []
    tail_bytes_hex = data.get("tail_bytes_hex", "")
    line_break_hex = data.get("line_break_hex", "")

    lines = []
    if header_lines:
        lines.extend(header_lines)
    elif columns:
        prefix = ";\t" if indent_tab else ";"
        lines.append(prefix + "\t".join(columns))

    if line_items:
        for item in line_items:
            item_type = item.get("type")
            if item_type == "blank":
                lines.append(str(item.get("value", "")))
                continue
            if item_type == "comment":
                lines.append(str(item.get("value", "")))
                continue
            if item_type == "data":
                values = item.get("values", [])
                line = "\t".join(str(value) for value in values)
                if indent_tab:
                    line = "\t" + line
                lines.append(line)
                continue
    else:
        for row in rows:
            if isinstance(row, dict) and columns:
                values = [str(row.get(col, "")) for col in columns]
                extra = row.get("_extra")
                if isinstance(extra, list):
                    values.extend(str(item) for item in extra)
                line = "\t".join(values)
            elif isinstance(row, list):
                line = "\t".join(str(item) for item in row)
            else:
                line = str(row)
            if indent_tab:
                line = "\t" + line
            lines.append(line)

    line_break = "\r\n"
    if line_break_hex:
        line_break = bytes.fromhex(line_break_hex).decode(encoding, errors="replace")
    text = line_break.join(lines) + line_break
    payload = text.encode(encoding, errors="replace")
    if tail_bytes_hex:
        payload += bytes.fromhex(tail_bytes_hex)
    return payload


def pack_file(path: Path, output_dir: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = int(data.get("version", 1))
    file_padding_hex = data.get("file_padding_hex", "")
    payload = build_payload(data)
    encoded = xor_bytes(payload)
    header = version.to_bytes(4, "little") + len(encoded).to_bytes(4, "little")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{path.stem}.bin"
    file_bytes = header + encoded
    if file_padding_hex:
        file_bytes += bytes.fromhex(file_padding_hex)
    output_path.write_bytes(file_bytes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recompila JSON em .bin com XOR 0xFF.")
    parser.add_argument("--input-dir", default="output", help="Diretório com os JSONs")
    parser.add_argument("--output-dir", default="input", help="Diretório para salvar os .bin")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        raise SystemExit(f"Nenhum .json encontrado em {input_dir}")

    for path in json_files:
        pack_file(path, output_dir)


if __name__ == "__main__":
    main()

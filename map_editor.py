#!/usr/bin/env python3
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


COLUMN_LABELS = [
    "Número",
    "Nome do Mapa",
    "Caminho do Mapa",
    "Script",
    "Música de Fundo",
    "Imagem da Interface",
    "Evento: Chefe Original",
    "Evento: Chefe Alternativo",
    "Nível",
    "Limite de Tempo",
    "Horário de Início do Alarme",
    "Old Curling",
]


class MapEditorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Map Planet Editor")
        self.geometry("1200x700")

        self.json_path: Path | None = None
        self.json_data: dict | None = None
        self.rows: list[list[str]] = []

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=8)

        ttk.Button(toolbar, text="Carregar JSON", command=self.load_json).pack(side="left")
        ttk.Button(toolbar, text="Adicionar Mapa", command=self.add_row).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Editar Mapa", command=self.edit_selected).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Excluir Mapa", command=self.delete_selected).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Salvar JSON", command=self.save_json).pack(side="left", padx=4)

        self.tree = ttk.Treeview(self, columns=list(range(len(COLUMN_LABELS))), show="headings")
        for idx, label in enumerate(COLUMN_LABELS):
            self.tree.heading(idx, text=label)
            self.tree.column(idx, width=140, anchor="w")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)

    def load_json(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Selecione o JSON",
            filetypes=[("JSON", "*.json")],
            initialdir=str(Path.cwd() / "output"),
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            messagebox.showerror("Erro", f"JSON inválido: {exc}")
            return
        except OSError as exc:
            messagebox.showerror("Erro", f"Falha ao ler arquivo: {exc}")
            return

        self.json_path = path
        self.json_data = data
        self.rows = self._rows_from_data(data)
        self._refresh_tree()

    def save_json(self) -> None:
        if not self.json_data:
            messagebox.showwarning("Aviso", "Carregue um JSON primeiro.")
            return

        path_str = filedialog.asksaveasfilename(
            title="Salvar JSON",
            defaultextension=".json",
            initialfile=self.json_path.name if self.json_path else "map_planet.json",
            filetypes=[("JSON", "*.json")],
            initialdir=str(Path.cwd() / "output"),
        )
        if not path_str:
            return

        self._write_json(Path(path_str))

    def add_row(self) -> None:
        values = self._open_row_dialog("Adicionar Mapa")
        if values is None:
            return
        self.rows.append(values)
        self._refresh_tree()

    def edit_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione uma linha para editar.")
            return
        item_id = selection[0]
        index = self.tree.index(item_id)
        current = self.rows[index]
        updated = self._open_row_dialog("Editar Mapa", current)
        if updated is None:
            return
        self.rows[index] = updated
        self._refresh_tree()

    def delete_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione uma linha para excluir.")
            return
        item_id = selection[0]
        index = self.tree.index(item_id)
        if messagebox.askyesno("Confirmar", "Deseja remover este mapa?"):
            self.rows.pop(index)
            self._refresh_tree()

    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for row in self.rows:
            self.tree.insert("", "end", values=row)

    def _rows_from_data(self, data: dict) -> list[list[str]]:
        rows = []
        line_items = data.get("line_items", [])
        for item in line_items:
            if item.get("type") != "data":
                continue
            values = item.get("values", [])
            padded = [str(values[idx]) if idx < len(values) else "" for idx in range(len(COLUMN_LABELS))]
            rows.append(padded)
        return rows

    def _open_row_dialog(self, title: str, values: list[str] | None = None) -> list[str] | None:
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()

        entries: list[tk.Entry] = []
        for idx, label in enumerate(COLUMN_LABELS):
            ttk.Label(dialog, text=label).grid(row=idx, column=0, sticky="w", padx=8, pady=4)
            entry = ttk.Entry(dialog, width=60)
            entry.grid(row=idx, column=1, sticky="w", padx=8, pady=4)
            if values and idx < len(values):
                entry.insert(0, values[idx])
            entries.append(entry)

        result: list[str] | None = None

        def on_ok() -> None:
            nonlocal result
            result = [entry.get() for entry in entries]
            dialog.destroy()

        def on_cancel() -> None:
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=len(COLUMN_LABELS), column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Salvar", command=on_ok).pack(side="left", padx=4)
        ttk.Button(button_frame, text="Cancelar", command=on_cancel).pack(side="left", padx=4)

        dialog.wait_window()
        return result

    def _write_json(self, path: Path) -> None:
        if not self.json_data:
            return

        data = dict(self.json_data)
        data["columns"] = COLUMN_LABELS

        original_items = list(data.get("line_items", []))
        new_items = []
        row_index = 0
        for item in original_items:
            if item.get("type") != "data":
                new_items.append(item)
                continue
            if row_index >= len(self.rows):
                continue
            values = self.rows[row_index]
            new_items.append({"type": "data", "values": values})
            row_index += 1

        while row_index < len(self.rows):
            new_items.append({"type": "data", "values": self.rows[row_index]})
            row_index += 1

        data["line_items"] = new_items

        data["rows"] = [
            {COLUMN_LABELS[idx]: row[idx] for idx in range(len(COLUMN_LABELS))}
            for row in self.rows
        ]

        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("Sucesso", f"JSON salvo em {path}")
        except OSError as exc:
            messagebox.showerror("Erro", f"Falha ao salvar: {exc}")


def main() -> None:
    app = MapEditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()

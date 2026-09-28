import flet as ft
import sqlite3
import os
from datetime import date

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.db")


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_record(type_, amount, description):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    desc = description or ("支出" if type_ == "expense" else "收入")
    c.execute(
        "INSERT INTO records (type, amount, description, date) VALUES (?, ?, ?, ?)",
        (type_, float(amount), desc, date.today().isoformat()),
    )
    conn.commit()
    conn.close()


def delete_record(record_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def load_records():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, type, amount, description, date FROM records ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def calc_balance(month_only=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if month_only:
        c.execute(
            "SELECT type, amount FROM records WHERE strftime('%Y-%m', date) = ?",
            (date.today().strftime("%Y-%m"),),
        )
    else:
        c.execute("SELECT type, amount FROM records")
    rows = c.fetchall()
    conn.close()
    bal = 0
    for t, a in rows:
        bal += a if t == "income" else -a
    return bal


def main(page: ft.Page):
    page.title = "极简记账"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO

    init_db()

    expense_amount = ft.TextField(label="支出", keyboard_type=ft.KeyboardType.NUMBER, width=120)
    expense_desc = ft.TextField(label="描述", expand=True)
    income_amount = ft.TextField(label="收入", keyboard_type=ft.KeyboardType.NUMBER, width=120)
    income_desc = ft.TextField(label="描述", expand=True)

    month_label = ft.Text("月收支：¥0.00", size=18, weight=ft.FontWeight.BOLD)
    total_label = ft.Text("总收支：¥0.00", size=18, weight=ft.FontWeight.BOLD)

    list_column = ft.Column(spacing=4)

    def refresh():
        month_bal = calc_balance(month_only=True)
        total_bal = calc_balance(month_only=False)
        month_label.value = f"月收支：¥{month_bal:.2f}"
        total_label.value = f"总收支：¥{total_bal:.2f}"

        list_column.controls.clear()
        records = load_records()
        if not records:
            list_column.controls.append(ft.Text("暂无记录", color="grey"))
        else:
            for rid, t, a, desc, d in records:
                sign = "+" if t == "income" else "-"
                color = ft.Colors.GREEN if t == "income" else ft.Colors.RED
                def make_delete(r=rid):
                    def handler(e):
                        delete_record(r)
                        refresh()
                        page.update()
                    return handler
                row = ft.Row([
                    ft.Text(f"{d} · {desc}", expand=True),
                    ft.Text(f"{sign}¥{a:.2f}", color=color, weight=ft.FontWeight.BOLD),
                    ft.IconButton(ft.Icons.DELETE, icon_size=18, on_click=make_delete()),
                ])
                list_column.controls.append(row)
        page.update()

    def save(e):
        added = False
        try:
            if expense_amount.value:
                amt = float(expense_amount.value)
                if amt <= 0:
                    page.snack_bar = ft.SnackBar(ft.Text("支出金额必须大于 0"))
                    page.snack_bar.open = True
                    page.update()
                    return
                add_record("expense", amt, expense_desc.value)
                added = True
            if income_amount.value:
                amt = float(income_amount.value)
                if amt <= 0:
                    page.snack_bar = ft.SnackBar(ft.Text("收入金额必须大于 0"))
                    page.snack_bar.open = True
                    page.update()
                    return
                add_record("income", amt, income_desc.value)
                added = True
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("请输入有效数字"))
            page.snack_bar.open = True
            page.update()
            return

        if added:
            expense_amount.value = ""
            expense_desc.value = ""
            income_amount.value = ""
            income_desc.value = ""
            refresh()
        else:
            page.snack_bar = ft.SnackBar(ft.Text("请至少填写一项金额"))
            page.snack_bar.open = True
            page.update()

    expense_row = ft.Row([expense_amount, expense_desc])
    income_row = ft.Row([income_amount, income_desc])

    page.add(
        ft.Text("💰 极简记账", size=24, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        expense_row,
        income_row,
        ft.Button(content="保存", on_click=save, width=400),
        ft.Divider(),
        month_label,
        total_label,
        ft.Divider(),
        ft.Text("明细", size=16, weight=ft.FontWeight.BOLD),
        list_column,
    )

    refresh()


ft.run(main)
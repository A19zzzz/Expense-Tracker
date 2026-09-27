#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
from calendar import month_name
from datetime import date

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.json")

# 中文月份名
CN_MONTH = {
    1: "一月", 2: "二月", 3: "三月", 4: "四月",
    5: "五月", 6: "六月", 7: "七月", 8: "八月",
    9: "九月", 10: "十月", 11: "十一月", 12: "十二月",
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"expenses": [], "next_id": 1, "budgets": {}}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"加载数据失败：{e}", file=sys.stderr)
        sys.exit(1)

    data.setdefault("expenses", [])
    if "next_id" not in data:
        data["next_id"] = max([e["id"] for e in data["expenses"]], default=0) + 1
    data.setdefault("budgets", {})
    return data


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"保存数据失败：{e}", file=sys.stderr)
        sys.exit(1)


def format_amount(amount):
    if amount == int(amount):
        return f"${int(amount)}"
    return f"${amount:.2f}"


def parse_date(s):
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise ValueError("日期格式必须为 YYYY-MM-DD")


def find_expense(data, expense_id):
    for e in data["expenses"]:
        if e["id"] == expense_id:
            return e
    return None


def add_expense(data, description, amount, category=None, expense_date=None):
    if amount <= 0:
        raise ValueError("金额必须大于 0")
    if not description.strip():
        raise ValueError("描述不能为空")

    if expense_date is None:
        expense_date = date.today().isoformat()
    else:
        parse_date(expense_date)

    expense = {
        "id": data["next_id"],
        "date": expense_date,
        "description": description.strip(),
        "amount": float(amount),
        "category": category.strip() if category else "未分类",
    }
    data["expenses"].append(expense)
    data["next_id"] += 1
    save_data(data)
    return expense


def update_expense(data, expense_id, description=None, amount=None, category=None):
    expense = find_expense(data, expense_id)
    if expense is None:
        raise ValueError(f"未找到 ID 为 {expense_id} 的支出")

    if description is not None:
        if not description.strip():
            raise ValueError("描述不能为空")
        expense["description"] = description.strip()

    if amount is not None:
        if amount <= 0:
            raise ValueError("金额必须大于 0")
        expense["amount"] = float(amount)

    if category is not None:
        expense["category"] = category.strip() if category else "未分类"

    save_data(data)
    return expense


def delete_expense(data, expense_id):
    expense = find_expense(data, expense_id)
    if expense is None:
        raise ValueError(f"未找到 ID 为 {expense_id} 的支出")

    data["expenses"].remove(expense)
    save_data(data)
    return expense


def list_expenses(data, category=None, month=None, year=None):
    expenses = data["expenses"]

    if category:
        expenses = [
            e for e in expenses
            if e.get("category", "").lower() == category.lower()
        ]

    if month:
        if year is None:
            year = date.today().year
        expenses = [
            e for e in expenses
            if date.fromisoformat(e["date"]).month == month
            and date.fromisoformat(e["date"]).year == year
        ]

    if not expenses:
        print("没有找到支出记录。")
        return

    print(f"{'ID':<4} {'日期':<12} {'描述':<16} {'金额':>8}")
    for e in expenses:
        print(
            f"{e['id']:<4} {e['date']:<12} "
            f"{e['description']:<16} {format_amount(e['amount']):>8}"
        )


def summary(data, month=None, year=None):
    expenses = data["expenses"]

    if year is None:
        year = date.today().year

    if month:
        expenses = [
            e for e in expenses
            if date.fromisoformat(e["date"]).month == month
            and date.fromisoformat(e["date"]).year == year
        ]

    total = sum(e["amount"] for e in expenses)

    if month:
        print(f"{CN_MONTH[month]}总支出：{format_amount(total)}")
    else:
        print(f"总支出：{format_amount(total)}")


def set_budget(data, month, amount, year=None):
    if amount <= 0:
        raise ValueError("预算必须大于 0")

    if year is None:
        year = date.today().year

    key = f"{year}-{month:02d}"
    data["budgets"][key] = float(amount)
    save_data(data)
    print(f"已设置 {year} 年 {CN_MONTH[month]} 预算：{format_amount(amount)}")


def check_budget(data, expense_date):
    d = parse_date(expense_date)
    key = f"{d.year}-{d.month:02d}"
    budget = data["budgets"].get(key)

    if budget is None:
        return

    total = sum(
        e["amount"]
        for e in data["expenses"]
        if date.fromisoformat(e["date"]).year == d.year
        and date.fromisoformat(e["date"]).month == d.month
    )

    if total > budget:
        print(
            f"警告：您已超出 {d.year} 年 {CN_MONTH[d.month]} 的预算！"
            f"预算：{format_amount(budget)}，"
            f"已花费：{format_amount(total)}"
        )


def export_csv(data, filename):
    expenses = data["expenses"]

    if not expenses:
        print("没有支出记录可导出。")
        return

    fieldnames = ["id", "date", "description", "amount", "category"]

    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for e in expenses:
                writer.writerow({k: e.get(k, "") for k in fieldnames})
        print(f"支出已导出到 {filename}")
    except OSError as e:
        raise ValueError(f"无法写入 CSV 文件：{e}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="expense-tracker",
        description="简单的命令行支出追踪器"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = subparsers.add_parser("add", help="添加一笔支出")
    p_add.add_argument("--description", required=True, help="支出描述")
    p_add.add_argument("--amount", required=True, type=float, help="支出金额")
    p_add.add_argument("--category", default=None, help="支出类别")
    p_add.add_argument("--date", default=None, help="日期，格式 YYYY-MM-DD，默认为今天")

    # update
    p_update = subparsers.add_parser("update", help="更新一笔支出")
    p_update.add_argument("--id", required=True, type=int, help="支出 ID")
    p_update.add_argument("--description", default=None, help="新的描述")
    p_update.add_argument("--amount", type=float, default=None, help="新的金额")
    p_update.add_argument("--category", default=None, help="新的类别")

    # delete
    p_delete = subparsers.add_parser("delete", help="删除一笔支出")
    p_delete.add_argument("--id", required=True, type=int, help="支出 ID")

    # list
    p_list = subparsers.add_parser("list", help="列出支出")
    p_list.add_argument("--category", default=None, help="按类别筛选")
    p_list.add_argument("--month", type=int, default=None, help="按月份筛选")
    p_list.add_argument("--year", type=int, default=None, help="按年份筛选")

    # summary
    p_summary = subparsers.add_parser("summary", help="查看支出汇总")
    p_summary.add_argument("--month", type=int, default=None, help="按月份汇总")
    p_summary.add_argument("--year", type=int, default=None, help="按年份汇总")

    # budget
    p_budget = subparsers.add_parser("budget", help="设置每月预算")
    p_budget.add_argument("--month", required=True, type=int, help="月份（1-12）")
    p_budget.add_argument("--amount", required=True, type=float, help="预算金额")
    p_budget.add_argument("--year", type=int, default=None, help="年份，默认今年")

    # export
    p_export = subparsers.add_parser("export", help="导出为 CSV 文件")
    p_export.add_argument("--file", default="expenses.csv", help="CSV 文件名")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if hasattr(args, "month") and args.month is not None:
        if not 1 <= args.month <= 12:
            parser.error("月份必须在 1 到 12 之间")

    data = load_data()

    try:
        if args.command == "add":
            expense = add_expense(
                data, args.description, args.amount, args.category, args.date
            )
            print(f"支出添加成功（ID：{expense['id']}）")
            check_budget(data, expense["date"])

        elif args.command == "update":
            expense = update_expense(
                data, args.id, args.description, args.amount, args.category
            )
            print(f"支出更新成功（ID：{expense['id']}）")
            check_budget(data, expense["date"])

        elif args.command == "delete":
            delete_expense(data, args.id)
            print("支出删除成功")

        elif args.command == "list":
            list_expenses(data, args.category, args.month, args.year)

        elif args.command == "summary":
            summary(data, args.month, args.year)

        elif args.command == "budget":
            set_budget(data, args.month, args.amount, args.year)

        elif args.command == "export":
            export_csv(data, args.file)

    except ValueError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
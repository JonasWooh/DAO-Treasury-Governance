from __future__ import annotations

import argparse
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import xlsxwriter

from deliverable_common import EVIDENCE_MANIFEST_PATH, WORKBOOK_PATH, WORKBOOK_SUMMARY_PATH, load_json, validate_evidence_manifest

MONTHS = list(range(1, 13))
PRICE_PATHS = {
    'Bear': Decimal('0.70'),
    'Base': Decimal('1.00'),
    'Bull': Decimal('1.30'),
}
YIELD_ASSUMPTIONS = {
    '0%': Decimal('0.00'),
    '3% APR': Decimal('0.03'),
    '6% APR': Decimal('0.06'),
}
PAYOUT_SCHEDULES = {
    'Light': {6: Decimal('0.5')},
    'Medium': {3: Decimal('0.5'), 9: Decimal('0.5')},
    'Heavy': {3: Decimal('0.5'), 6: Decimal('0.5'), 9: Decimal('0.5')},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate the treasury analysis Excel workbook and summary JSON.')
    parser.add_argument('--evidence-manifest', default=str(EVIDENCE_MANIFEST_PATH))
    parser.add_argument('--output', default=str(WORKBOOK_PATH))
    parser.add_argument('--summary-output', default=str(WORKBOOK_SUMMARY_PATH))
    return parser.parse_args()


def as_decimal(raw: Any, scale: Decimal = Decimal('1')) -> Decimal:
    return (Decimal(str(raw)) / scale).quantize(Decimal('0.0000000001'))


def round_money(value: Decimal) -> float:
    return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def round_units(value: Decimal) -> float:
    return float(value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))


def derive_start_state(evidence_manifest: dict[str, Any]) -> dict[str, Decimal]:
    proposal_record = evidence_manifest.get('proposals', {}).get('proposal2_deposit_idle_funds')
    if not isinstance(proposal_record, dict):
        raise ValueError('Evidence manifest is missing proposal2_deposit_idle_funds.')

    snapshots = proposal_record.get('snapshots', {})
    if not isinstance(snapshots, dict) or 'postExecution' not in snapshots:
        raise ValueError('Evidence manifest is missing proposal2_deposit_idle_funds.snapshots.postExecution.')

    post_execution = snapshots['postExecution']
    if not isinstance(post_execution, dict) or 'treasury' not in post_execution:
        raise ValueError('Evidence manifest is missing the treasury postExecution snapshot for Proposal 2.')

    treasury = post_execution['treasury']
    if not isinstance(treasury, dict):
        raise ValueError('Proposal 2 treasury snapshot must be an object.')

    liquid_weth = as_decimal(treasury['liquidWeth'], Decimal(10**18))
    supplied_weth = as_decimal(treasury['suppliedWeth'], Decimal(10**18))
    total_managed_weth = as_decimal(treasury['totalManagedWeth'], Decimal(10**18))
    nav_usd = as_decimal(treasury['navUsd'], Decimal(10**18))

    if total_managed_weth == 0:
        raise ValueError('Proposal 2 treasury snapshot has zero managed WETH, which is invalid for workbook generation.')

    eth_price_usd = (nav_usd / total_managed_weth).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return {
        'liquid_weth': liquid_weth,
        'supplied_weth': supplied_weth,
        'total_managed_weth': total_managed_weth,
        'nav_usd': nav_usd,
        'eth_price_usd': eth_price_usd,
    }


def payout_total(schedule: dict[int, Decimal]) -> Decimal:
    return sum(schedule.values(), start=Decimal('0'))


def simulate_end_state(start_state: dict[str, Decimal], price_end_multiplier: Decimal, apr: Decimal, payouts: dict[int, Decimal]) -> dict[str, Decimal]:
    monthly_rate = apr / Decimal('12')
    liquid = start_state['liquid_weth']
    supplied = start_state['supplied_weth']

    for month in MONTHS:
        supplied *= (Decimal('1') + monthly_rate)
        payout = payouts.get(month, Decimal('0'))
        if payout == 0:
            continue
        liquid_after = liquid - payout
        if liquid_after >= 0:
            liquid = liquid_after
            continue
        required_from_supplied = -liquid_after
        liquid = Decimal('0')
        supplied -= required_from_supplied
        if supplied < 0:
            raise ValueError('Payout schedule would drive supplied WETH negative. Check analytical assumptions.')

    end_price = (start_state['eth_price_usd'] * price_end_multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_managed = liquid + supplied
    reserve_ratio = (liquid / total_managed) if total_managed != 0 else Decimal('0')
    nav_usd = total_managed * end_price
    unrealized_gain_loss = nav_usd - (total_managed * start_state['eth_price_usd'])

    return {
        'liquid_weth': liquid,
        'supplied_weth': supplied,
        'total_managed_weth': total_managed,
        'reserve_ratio': reserve_ratio,
        'eth_price_usd': end_price,
        'nav_usd': nav_usd,
        'unrealized_gain_loss_usd': unrealized_gain_loss,
    }


def build_monthly_projection(start_state: dict[str, Decimal], price_name: str, apr_name: str, payout_name: str) -> list[dict[str, float | int | str]]:
    price_end_multiplier = PRICE_PATHS[price_name]
    apr = YIELD_ASSUMPTIONS[apr_name]
    payouts = PAYOUT_SCHEDULES[payout_name]
    monthly_rate = apr / Decimal('12')

    liquid = start_state['liquid_weth']
    supplied = start_state['supplied_weth']
    rows: list[dict[str, float | int | str]] = []

    for month in [0] + MONTHS:
        if month == 0:
            multiplier = Decimal('1.0')
            payout = Decimal('0')
        else:
            supplied *= (Decimal('1') + monthly_rate)
            payout = payouts.get(month, Decimal('0'))
            if payout != 0:
                liquid_after = liquid - payout
                if liquid_after >= 0:
                    liquid = liquid_after
                else:
                    required_from_supplied = -liquid_after
                    liquid = Decimal('0')
                    supplied -= required_from_supplied
            multiplier = Decimal('1.0') + ((price_end_multiplier - Decimal('1.0')) * Decimal(month) / Decimal('12'))

        eth_price = (start_state['eth_price_usd'] * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_managed = liquid + supplied
        reserve_ratio = (liquid / total_managed) if total_managed != 0 else Decimal('0')
        nav_usd = total_managed * eth_price
        rows.append(
            {
                'month': month,
                'price_path': price_name,
                'yield_assumption': apr_name,
                'payout_schedule': payout_name,
                'payout_weth': round_units(payout),
                'liquid_weth': round_units(liquid),
                'supplied_weth': round_units(supplied),
                'total_managed_weth': round_units(total_managed),
                'eth_price_usd': round_money(eth_price),
                'reserve_ratio': float((reserve_ratio * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'nav_usd': round_money(nav_usd),
            }
        )

    return rows


def write_inputs_sheet(workbook, start_state: dict[str, Decimal]) -> None:
    sheet = workbook.add_worksheet('Inputs')
    bold = workbook.add_format({'bold': True})
    percent = workbook.add_format({'num_format': '0.00%'})
    money = workbook.add_format({'num_format': '$#,##0.00'})
    units = workbook.add_format({'num_format': '0.0000'})

    rows = [
        ('Starting Total Managed WETH', round_units(start_state['total_managed_weth']), units),
        ('Starting Liquid WETH', round_units(start_state['liquid_weth']), units),
        ('Starting Supplied WETH', round_units(start_state['supplied_weth']), units),
        ('Starting ETH Price (USD)', round_money(start_state['eth_price_usd']), money),
    ]
    sheet.write_row('A1', ['Input', 'Value'], bold)
    for index, (label, value, cell_format) in enumerate(rows, start=2):
        sheet.write(f'A{index}', label)
        sheet.write_number(f'B{index}', value, cell_format)

    sheet.write_row('D1', ['Price Path', 'End Multiplier'], bold)
    for index, (label, value) in enumerate(PRICE_PATHS.items(), start=2):
        sheet.write(f'D{index}', label)
        sheet.write_number(f'E{index}', float(value), percent)

    sheet.write_row('G1', ['Yield Assumption', 'APR'], bold)
    for index, (label, value) in enumerate(YIELD_ASSUMPTIONS.items(), start=2):
        sheet.write(f'G{index}', label)
        sheet.write_number(f'H{index}', float(value), percent)

    sheet.write_row('J1', ['Payout Schedule', 'Total Payout WETH'], bold)
    for index, (label, value) in enumerate(PAYOUT_SCHEDULES.items(), start=2):
        sheet.write(f'J{index}', label)
        sheet.write_number(f'K{index}', round_units(payout_total(value)), units)


def write_scenario_matrix_sheet(workbook, start_state: dict[str, Decimal]) -> list[dict[str, Any]]:
    sheet = workbook.add_worksheet('ScenarioMatrix')
    bold = workbook.add_format({'bold': True})
    percent = workbook.add_format({'num_format': '0.00%'})
    money = workbook.add_format({'num_format': '$#,##0.00'})
    units = workbook.add_format({'num_format': '0.0000'})

    headers = [
        'Scenario',
        'Price Path',
        'Yield Assumption',
        'Payout Schedule',
        'End ETH Price USD',
        'End Liquid WETH',
        'End Supplied WETH',
        'End Total Managed WETH',
        'End Reserve Ratio',
        'End NAV USD',
        'Unrealized Gain/Loss USD',
    ]
    sheet.write_row(0, 0, headers, bold)

    rows: list[dict[str, Any]] = []
    row_index = 1
    for price_name, price_multiplier in PRICE_PATHS.items():
        for apr_name, apr in YIELD_ASSUMPTIONS.items():
            for payout_name, payouts in PAYOUT_SCHEDULES.items():
                scenario_name = f'{price_name} / {apr_name} / {payout_name}'
                end_state = simulate_end_state(start_state, price_multiplier, apr, payouts)
                rows.append({'scenario': scenario_name, **end_state, 'price_path': price_name, 'yield': apr_name, 'payout': payout_name})
                sheet.write_row(row_index, 0, [scenario_name, price_name, apr_name, payout_name])
                sheet.write_number(row_index, 4, round_money(end_state['eth_price_usd']), money)
                sheet.write_number(row_index, 5, round_units(end_state['liquid_weth']), units)
                sheet.write_number(row_index, 6, round_units(end_state['supplied_weth']), units)
                sheet.write_number(row_index, 7, round_units(end_state['total_managed_weth']), units)
                sheet.write_number(row_index, 8, float(end_state['reserve_ratio']), percent)
                sheet.write_number(row_index, 9, round_money(end_state['nav_usd']), money)
                sheet.write_number(row_index, 10, round_money(end_state['unrealized_gain_loss_usd']), money)
                row_index += 1
    return rows


def write_nav_projection_sheet(workbook, start_state: dict[str, Decimal]) -> list[dict[str, float | int | str]]:
    sheet = workbook.add_worksheet('NAVProjection')
    bold = workbook.add_format({'bold': True})
    money = workbook.add_format({'num_format': '$#,##0.00'})
    units = workbook.add_format({'num_format': '0.0000'})
    percent = workbook.add_format({'num_format': '0.00'})

    headers = [
        'Month', 'Price Path', 'Yield Assumption', 'Payout Schedule', 'Payout WETH',
        'Liquid WETH', 'Supplied WETH', 'Total Managed WETH', 'ETH Price USD', 'Reserve Ratio %', 'NAV USD'
    ]
    sheet.write_row(0, 0, headers, bold)

    projections: list[dict[str, float | int | str]] = []
    row_index = 1
    for price_name in PRICE_PATHS:
        price_rows = build_monthly_projection(start_state, price_name, '3% APR', 'Medium')
        projections.extend(price_rows)
        for row in price_rows:
            sheet.write_row(row_index, 0, [row['month'], row['price_path'], row['yield_assumption'], row['payout_schedule']])
            sheet.write_number(row_index, 4, row['payout_weth'], units)
            sheet.write_number(row_index, 5, row['liquid_weth'], units)
            sheet.write_number(row_index, 6, row['supplied_weth'], units)
            sheet.write_number(row_index, 7, row['total_managed_weth'], units)
            sheet.write_number(row_index, 8, row['eth_price_usd'], money)
            sheet.write_number(row_index, 9, row['reserve_ratio'], percent)
            sheet.write_number(row_index, 10, row['nav_usd'], money)
            row_index += 1
    return projections


def write_reserve_sensitivity_sheet(workbook, start_state: dict[str, Decimal]) -> list[dict[str, Any]]:
    sheet = workbook.add_worksheet('ReserveSensitivity')
    bold = workbook.add_format({'bold': True})
    percent = workbook.add_format({'num_format': '0.00%'})

    payout_names = list(PAYOUT_SCHEDULES.keys())
    sheet.write(0, 0, 'Yield / Payout', bold)
    for column, payout_name in enumerate(payout_names, start=1):
        sheet.write(0, column, payout_name, bold)

    matrix: list[dict[str, Any]] = []
    for row_index, (yield_name, apr) in enumerate(YIELD_ASSUMPTIONS.items(), start=1):
        sheet.write(row_index, 0, yield_name, bold)
        for column, payout_name in enumerate(payout_names, start=1):
            end_state = simulate_end_state(start_state, PRICE_PATHS['Base'], apr, PAYOUT_SCHEDULES[payout_name])
            matrix.append({'yield': yield_name, 'payout': payout_name, 'reserve_ratio': float(end_state['reserve_ratio'])})
            sheet.write_number(row_index, column, float(end_state['reserve_ratio']), percent)
    return matrix


def write_charts_sheet(workbook, nav_projection_rows: list[dict[str, float | int | str]], reserve_matrix: list[dict[str, Any]]) -> None:
    sheet = workbook.add_worksheet('Charts')
    bold = workbook.add_format({'bold': True})
    sheet.write('A1', 'Charts generated from the NAVProjection and ReserveSensitivity sheets.', bold)

    line_chart = workbook.add_chart({'type': 'line'})
    for index, price_name in enumerate(PRICE_PATHS.keys()):
        start_row = 2 + (index * 13)
        end_row = start_row + 12
        line_chart.add_series({
            'name': price_name,
            'categories': f'=NAVProjection!$A${start_row}:$A${end_row}',
            'values': f'=NAVProjection!$K${start_row}:$K${end_row}',
        })
    line_chart.set_title({'name': 'NAV projection under Bear / Base / Bull price paths'})
    line_chart.set_x_axis({'name': 'Month'})
    line_chart.set_y_axis({'name': 'NAV (USD)'})
    sheet.insert_chart('A3', line_chart, {'x_scale': 1.4, 'y_scale': 1.2})

    column_chart = workbook.add_chart({'type': 'column'})
    column_chart.add_series({
        'name': 'Reserve Ratio',
        'categories': '=ReserveSensitivity!$B$1:$D$1',
        'values': '=ReserveSensitivity!$B$2:$D$2',
    })
    column_chart.set_title({'name': 'Reserve ratio sensitivity (0% yield row)'})
    column_chart.set_x_axis({'name': 'Payout schedule'})
    column_chart.set_y_axis({'name': 'Reserve ratio'})
    sheet.insert_chart('A22', column_chart, {'x_scale': 1.4, 'y_scale': 1.2})


def write_commentary_sheet(workbook, start_state: dict[str, Decimal], scenario_rows: list[dict[str, Any]]) -> None:
    sheet = workbook.add_worksheet('Commentary')
    bold = workbook.add_format({'bold': True})
    worst_case = min(scenario_rows, key=lambda row: row['nav_usd'])
    best_case = max(scenario_rows, key=lambda row: row['nav_usd'])

    lines = [
        'Campus Innovation Fund Treasury Analysis',
        '',
        f"Starting state is sourced from the Proposal 2 post-execution snapshot: {round_units(start_state['total_managed_weth'])} total WETH, {round_units(start_state['liquid_weth'])} liquid WETH, {round_units(start_state['supplied_weth'])} supplied WETH.",
        f"Initial ETH price baseline is {round_money(start_state['eth_price_usd'])} USD.",
        f"Worst scenario by ending NAV: {worst_case['scenario']} -> {round_money(worst_case['nav_usd'])} USD.",
        f"Best scenario by ending NAV: {best_case['scenario']} -> {round_money(best_case['nav_usd'])} USD.",
        'Reserve ratio is computed exactly as liquid_weth / total_managed_weth.',
        'Treasury NAV is computed exactly as total_managed_weth * ETH_price.',
        'Unrealized gain/loss is interpreted against the initial ETH price baseline.',
    ]
    for index, line in enumerate(lines):
        sheet.write(index, 0, line, bold if index == 0 else None)


def build_summary_payload(start_state: dict[str, Decimal], scenario_rows: list[dict[str, Any]]) -> dict[str, Any]:
    worst_case = min(scenario_rows, key=lambda row: row['nav_usd'])
    best_case = max(scenario_rows, key=lambda row: row['nav_usd'])
    return {
        'startingState': {
            'totalManagedWeth': round_units(start_state['total_managed_weth']),
            'liquidWeth': round_units(start_state['liquid_weth']),
            'suppliedWeth': round_units(start_state['supplied_weth']),
            'ethPriceUsd': round_money(start_state['eth_price_usd']),
        },
        'scenarioCount': len(scenario_rows),
        'worstCase': {
            'scenario': worst_case['scenario'],
            'navUsd': round_money(worst_case['nav_usd']),
            'reserveRatio': float((worst_case['reserve_ratio'] * Decimal('100')).quantize(Decimal('0.01'))),
        },
        'bestCase': {
            'scenario': best_case['scenario'],
            'navUsd': round_money(best_case['nav_usd']),
            'reserveRatio': float((best_case['reserve_ratio'] * Decimal('100')).quantize(Decimal('0.01'))),
        },
    }


def main() -> None:
    args = parse_args()
    evidence_manifest = validate_evidence_manifest(load_json(Path(args.evidence_manifest)))
    start_state = derive_start_state(evidence_manifest)

    output_path = Path(args.output)
    summary_output_path = Path(args.summary_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = xlsxwriter.Workbook(output_path)
    write_inputs_sheet(workbook, start_state)
    scenario_rows = write_scenario_matrix_sheet(workbook, start_state)
    nav_projection_rows = write_nav_projection_sheet(workbook, start_state)
    reserve_matrix = write_reserve_sensitivity_sheet(workbook, start_state)
    write_charts_sheet(workbook, nav_projection_rows, reserve_matrix)
    write_commentary_sheet(workbook, start_state, scenario_rows)
    workbook.close()

    summary_payload = build_summary_payload(start_state, scenario_rows)
    summary_output_path.write_text(json.dumps(summary_payload, indent=2), encoding='utf-8')

    print(f'Workbook written to {output_path}')
    print(f'Workbook summary written to {summary_output_path}')


if __name__ == '__main__':
    main()

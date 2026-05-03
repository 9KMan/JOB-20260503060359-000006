"""Excel/structure validation layer."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    row: int
    column: str
    message: str
    severity: str


class Validator:
    REQUIRED_COLUMNS = [
        "transaction_id", "date", "customer_id", "product_id",
        "list_price", "invoice_price", "net_price", "pocket_price", "gross_margin"
    ]

    def validate_structure(self, df) -> List[ValidationError]:
        errors = []
        for col in self.REQUIRED_COLUMNS:
            if col not in df.columns:
                errors.append(ValidationError(
                    row=0, column=col,
                    message=f"Missing required column: {col}",
                    severity="ERROR"
                ))
        return errors

    def validate_data_types(self, df) -> List[ValidationError]:
        errors = []
        for col in ["list_price", "invoice_price", "net_price", "pocket_price", "gross_margin"]:
            if col in df.columns:
                for idx, val in enumerate(df[col], start=2):
                    try:
                        float(val)
                    except (ValueError, TypeError):
                        errors.append(ValidationError(
                            row=idx, column=col,
                            message=f"Invalid numeric value: {val}",
                            severity="ERROR"
                        ))
        return errors

    def validate_values(self, df) -> List[ValidationError]:
        errors = []
        for idx, row in df.iterrows():
            try:
                lp = float(row.get("list_price", 0))
                ip = float(row.get("invoice_price", 0))
                np = float(row.get("net_price", 0))
                pp = float(row.get("pocket_price", 0))
                if ip > lp:
                    errors.append(ValidationError(
                        row=idx + 2, column="invoice_price",
                        message="Invoice price exceeds list price",
                        severity="ERROR"
                    ))
                if np > ip:
                    errors.append(ValidationError(
                        row=idx + 2, column="net_price",
                        message="Net price exceeds invoice price",
                        severity="ERROR"
                    ))
                if pp > np:
                    errors.append(ValidationError(
                        row=idx + 2, column="pocket_price",
                        message="Pocket price exceeds net price",
                        severity="WARNING"
                    ))
            except (ValueError, TypeError):
                continue
        return errors

    def validate(self, df) -> List[ValidationError]:
        all_errors = []
        all_errors.extend(self.validate_structure(df))
        if not all_errors:
            all_errors.extend(self.validate_data_types(df))
            all_errors.extend(self.validate_values(df))
        return all_errors

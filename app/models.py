from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DonationRecord:
    record_id: str
    donate_time: str
    donor: str
    major: str
    alumni_assoc: str
    project_name: str
    donate_amount: Decimal
